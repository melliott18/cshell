#!/usr/bin/env python3
"""Focused process-group cleanup regressions, independent of shell behavior."""

import errno
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
import unittest
from unittest import mock

import pty_harness
import execute


class GroupCleanupTests(unittest.TestCase):
    GROUP = 41234
    SESSION = 41233

    def test_executor_fixture_accepts_a_verified_exited_darwin_group(self):
        process = mock.Mock(pid=self.GROUP, returncode=0)
        with mock.patch.object(execute.subprocess, "Popen", return_value=process), \
                mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=
                                  PermissionError(errno.EPERM, "zombie group")), \
                mock.patch.object(pty_harness, "session_members", return_value=[]) as members:
            result = execute.bounded_run(["fixture"], cwd=Path.cwd(), env={}, timeout=1)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b"", b""))
        self.assertEqual(members.call_args.args[0], self.GROUP)

    def test_executor_fixture_preserves_real_cleanup_permission_errors(self):
        process = mock.Mock(pid=self.GROUP, returncode=0)
        with mock.patch.object(execute.subprocess, "Popen", return_value=process), \
                mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=
                                  PermissionError(errno.EPERM, "live group denied")), \
                mock.patch.object(pty_harness, "session_members", return_value=[(41235, self.GROUP)]):
            with self.assertRaises(PermissionError):
                execute.bounded_run(["fixture"], cwd=Path.cwd(), env={}, timeout=1)

    def test_missing_group_is_already_clean_without_a_snapshot(self):
        with mock.patch.object(pty_harness.os, "killpg", side_effect=
                               ProcessLookupError(errno.ESRCH, "no group")) as kill, \
                mock.patch.object(pty_harness, "session_members") as members:
            pty_harness.kill_group(self.GROUP, self.SESSION, time.monotonic() + 1)
        kill.assert_called_once_with(self.GROUP, signal.SIGKILL)
        members.assert_not_called()

    def test_darwin_permission_error_requires_a_fresh_empty_group_snapshot(self):
        # session_members excludes zombies. Other live groups in the owned
        # session do not make an exited target group a permission failure.
        deadline = time.monotonic() + 1
        with mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=
                                  PermissionError(errno.EPERM, "zombie group")) as kill, \
                mock.patch.object(pty_harness, "session_members",
                                  side_effect=[[], [(41235, 41235)]]) as members:
            pty_harness.kill_group(self.GROUP, self.SESSION, deadline)
            pty_harness.kill_group(self.GROUP, self.SESSION, deadline)
        self.assertEqual(kill.call_count, 2)
        self.assertEqual(members.call_args_list,
                         [mock.call(self.SESSION, deadline)] * 2)

    def test_darwin_permission_error_with_live_group_members_is_reported(self):
        error = PermissionError(errno.EPERM, "live group denied")
        with mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=error), \
                mock.patch.object(pty_harness, "session_members",
                                  return_value=[(41235, self.GROUP)]):
            with self.assertRaises(PermissionError) as raised:
                pty_harness.kill_group(self.GROUP, self.SESSION, time.monotonic() + 1)
        self.assertIs(raised.exception, error)

    def test_other_permission_errors_are_reported_without_a_snapshot(self):
        for platform, number in (("linux", errno.EPERM), ("darwin", errno.EACCES)):
            with self.subTest(platform=platform, number=number):
                error = PermissionError(number, "genuine permission failure")
                with mock.patch.object(pty_harness.sys, "platform", platform), \
                        mock.patch.object(pty_harness.os, "killpg", side_effect=error), \
                        mock.patch.object(pty_harness, "session_members") as members:
                    with self.assertRaises(PermissionError) as raised:
                        pty_harness.kill_group(self.GROUP, self.SESSION,
                                              time.monotonic() + 1)
                self.assertIs(raised.exception, error)
                members.assert_not_called()

    def test_failed_snapshot_cannot_hide_a_permission_error(self):
        with mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=
                                  PermissionError(errno.EPERM, "group denied")), \
                mock.patch.object(pty_harness, "session_members", side_effect=
                                  OSError("injected process snapshot failure")):
            with self.assertRaisesRegex(OSError, "injected process snapshot failure"):
                pty_harness.kill_group(self.GROUP, self.SESSION, time.monotonic() + 1)

    def test_expired_snapshot_deadline_cannot_hide_a_permission_error(self):
        with mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=
                                  PermissionError(errno.EPERM, "group denied")), \
                mock.patch.object(pty_harness.subprocess, "run") as snapshot:
            with self.assertRaisesRegex(TimeoutError, "cleanup deadline"):
                pty_harness.kill_group(self.GROUP, self.SESSION, time.monotonic() - 1)
        snapshot.assert_not_called()

    def test_pty_cleanup_accepts_groups_that_exit_after_the_snapshot(self):
        process = mock.Mock(pid=self.SESSION)
        with mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "tcgetpgrp", return_value=-1), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=
                                  PermissionError(errno.EPERM, "zombie group")) as kill, \
                mock.patch.object(pty_harness, "session_members", side_effect=
                                  [[(41235, self.GROUP)], [], [], []]):
            failures = pty_harness.cleanup_session(process, master=0)
        self.assertEqual(failures, [])
        self.assertEqual(kill.call_args_list, [mock.call(self.GROUP, signal.SIGKILL),
                                              mock.call(self.SESSION, signal.SIGKILL)])
        process.wait.assert_called_once()

    def test_pty_cleanup_reports_permission_failure_for_a_live_group(self):
        process = mock.Mock(pid=self.SESSION)
        with mock.patch.object(pty_harness.sys, "platform", "darwin"), \
                mock.patch.object(pty_harness.os, "tcgetpgrp", return_value=-1), \
                mock.patch.object(pty_harness.os, "killpg", side_effect=
                                  PermissionError(errno.EPERM, "live group denied")), \
                mock.patch.object(pty_harness, "session_members",
                                  return_value=[(41235, self.GROUP)]):
            failures = pty_harness.cleanup_session(process, master=0)
        self.assertTrue(any("cleanup failed" in failure and "live group denied" in failure
                            for failure in failures), failures)
        process.wait.assert_called_once()

    @unittest.skipUnless(sys.platform in ("darwin", "linux"),
                         "process snapshots support native macOS and Linux")
    def test_repeated_cleanup_of_a_real_unreaped_zombie_group(self):
        # Keep this direct child unreaped until after repeated group signals.
        # Unlike an orphan adopted by PID 1, its zombie lifetime is controlled.
        process = subprocess.Popen(
            [sys.executable, "-c",
             "import os, signal; os.write(1, b'ready\\n'); signal.pause()"],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
        deadline = time.monotonic() + 3
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                self.assertTrue(selector.select(max(0, deadline - time.monotonic())),
                                "child did not enter its owned process group")
                self.assertEqual(os.read(process.stdout.fileno(), 6), b"ready\n")
            # The first signal acts on a live group and must actually kill it.
            pty_harness.kill_group(process.pid, process.pid, deadline)
            while True:
                remaining = deadline - time.monotonic()
                self.assertGreater(remaining, 0, "child did not become a zombie")
                if sys.platform == "linux":
                    state = Path(f"/proc/{process.pid}/stat").read_text().rsplit(
                        ")", 1)[1].split()[0]
                else:
                    result = subprocess.run(
                        ["/bin/ps", "-p", str(process.pid), "-o", "stat="],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        timeout=remaining, check=True,
                    )
                    state = result.stdout.strip()
                if state.startswith("Z"):
                    break
                time.sleep(min(0.01, remaining))
            self.assertIsNone(process.returncode, "zombie must remain unreaped")
            if sys.platform == "darwin":
                with self.assertRaises(PermissionError) as raised:
                    os.killpg(process.pid, signal.SIGKILL)
                self.assertEqual(raised.exception.errno, errno.EPERM)
            for _ in range(3):
                pty_harness.kill_group(process.pid, process.pid, deadline)
        finally:
            # Direct-PID cleanup also works while Darwin rejects zombie groups.
            try:
                process.kill()
            except ProcessLookupError:
                pass
            process.stdout.close()
            process.wait(timeout=2)
        self.assertEqual(process.returncode, -signal.SIGKILL)


if __name__ == "__main__":
    unittest.main(verbosity=2)
