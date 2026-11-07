#!/usr/bin/env python3
"""Independent failure and native ABI checks for Darwin cleanup snapshots."""
import ctypes
import errno
import os
import selectors
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

import darwin_processes as snapshots


class DarwinSnapshotTests(unittest.TestCase):
    def test_growth_retries_instead_of_accepting_truncated_list(self):
        sizes = []
        def listing(kind, value, buffer, size):
            if buffer is None:
                return 4
            sizes.append(size)
            if len(sizes) == 1:
                return size
            buffer[0], buffer[1] = 123, 456
            return 8
        with mock.patch.object(snapshots, 'library') as library:
            library.return_value.proc_listpids.side_effect = listing
            self.assertEqual(snapshots.process_ids(time.monotonic() + 1), [123, 456])
        self.assertEqual(sizes[1], sizes[0] * 2)

    def test_snapshot_bound_and_invalid_results_fail_closed(self):
        for returned in (-1, 0, 3, 10000000):
            with self.subTest(returned=returned), mock.patch.object(snapshots, 'library') as library:
                library.return_value.proc_listpids.side_effect = [4, returned]
                with self.assertRaises(OSError):
                    snapshots.process_ids(time.monotonic() + 1)
        with mock.patch.object(snapshots, 'library') as library:
            library.return_value.proc_listpids.return_value = snapshots.MAX_SNAPSHOT_BYTES
            with self.assertRaisesRegex(OSError, 'exceeds 1 MiB'):
                snapshots.process_ids(time.monotonic() + 1)

    def test_deadline_is_checked_before_and_after_kernel_query(self):
        with mock.patch.object(snapshots, 'library') as library:
            with self.assertRaises(TimeoutError):
                snapshots.process_ids(time.monotonic() - 1)
            library.assert_not_called()
        with mock.patch.object(snapshots, 'library') as library, \
                mock.patch.object(snapshots.time, 'monotonic', side_effect=[0, 2]):
            library.return_value.proc_listpids.return_value = 4
            with self.assertRaises(TimeoutError):
                snapshots.process_ids(1)

    def test_vanished_pid_is_distinct_from_denied_or_invalid_metadata(self):
        for error in (errno.ESRCH, errno.EPERM, 0):
            def lookup(*args):
                ctypes.set_errno(error)
                return 0
            with self.subTest(error=error), mock.patch.object(snapshots, 'library') as library:
                library.return_value.proc_pidinfo.side_effect = lookup
                if error == errno.ESRCH:
                    self.assertIsNone(snapshots.process_info(123, time.monotonic() + 1))
                else:
                    with self.assertRaises(OSError):
                        snapshots.process_info(123, time.monotonic() + 1)
        with mock.patch.object(snapshots, 'library') as library:
            library.return_value.proc_pidinfo.return_value = ctypes.sizeof(snapshots.ShortBSDInfo)
            with self.assertRaises(OSError):
                snapshots.process_info(123, time.monotonic() + 1)  # PID mismatch

    def test_only_owned_live_members_survive_fresh_session_validation(self):
        rows = {11: mock.Mock(status=2, pgid=11), 12: mock.Mock(status=5, pgid=12),
                13: None, 14: mock.Mock(status=2, pgid=14)}
        with mock.patch.object(snapshots, 'process_ids', return_value=[10, 11, 12, 13, 14]), \
                mock.patch.object(snapshots.os, 'getsid', side_effect=[99, 42, 42, 42, 42, 42, 99]), \
                mock.patch.object(snapshots, 'process_info', side_effect=lambda pid, _: rows[pid]) as info:
            self.assertEqual(snapshots.session_members(42, time.monotonic() + 1), [(11, 11)])
        self.assertNotIn(10, [call.args[0] for call in info.call_args_list])

    @unittest.skipUnless(sys.platform == 'darwin', 'native Darwin libproc ABI')
    def test_native_live_and_unreaped_zombie_without_spawning_ps(self):
        child = subprocess.Popen([sys.executable, '-c',
                                  'import os,signal; os.write(1,b"ready"); signal.pause()'],
                                 stdout=subprocess.PIPE, start_new_session=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(child.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(3))
                self.assertEqual(os.read(child.stdout.fileno(), 5), b'ready')
            with mock.patch.object(subprocess, 'run', side_effect=AssertionError('ps is forbidden')):
                deadline = time.monotonic() + 3
                info = snapshots.process_info(child.pid, deadline)
                self.assertEqual(info.pid, child.pid)
                self.assertEqual(info.ppid, os.getpid())
                self.assertEqual(info.pgid, child.pid)
                self.assertEqual(info.uid, os.getuid())
                self.assertEqual(snapshots.session_members(child.pid, deadline), [(child.pid, child.pid)])
                os.kill(child.pid, signal.SIGKILL)
                while True:
                    info = snapshots.process_info(child.pid, deadline)
                    # proc_pidinfo may report ESRCH once the process exits,
                    # even while its unreaped PID still exists in the kernel.
                    if info is None or info.status == snapshots.SZOMB:
                        break
                    time.sleep(0.005)
                os.kill(child.pid, 0)
                self.assertEqual(snapshots.session_members(child.pid, deadline), [])
                self.assertIsNone(child.returncode, 'zombie must remain unreaped')
        finally:
            child.kill()
            child.stdout.close()
            child.wait(timeout=2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
