"""Fail-closed terminal harness, fixture oracle and owned-child cleanup checks."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import selectors

from host_terminal import capture, cases, tab_effect
from pty_harness import open_terminal


class TerminalHarnessTests(unittest.TestCase):
    def test_tab_oracle_requires_clear_and_rejects_unknown_output(self):
        self.assertEqual(tab_effect(b'\rCLEAR_TABSSET_TAB   SET_TAB\r'), [0, 3])
        self.assertIsNone(tab_effect(b'SET_TAB'))
        self.assertIsNone(tab_effect(b'CLEAR_TABSunexpected'))

    def test_case_names_unique_and_no_gap_allowance(self):
        rows = list(cases())
        self.assertEqual(len(rows), len({r['name'] for r in rows}))
        self.assertTrue(all('gap' not in r for r in rows))

    def run_child(self, program, timeout=1, limit=1024):
        master, slave = open_terminal()
        try:
            with tempfile.TemporaryDirectory(prefix='csh077-harness-') as temp:
                with open(os.devnull, 'rb') as source:
                    return capture([sys.executable, '-c', program], Path(temp),
                        dict(PATH=os.defpath), master, slave, source,
                        timeout=timeout, limit=limit)
        finally:
            os.close(master)
            os.close(slave)

    def test_control_preserves_exact_output_and_status(self):
        result = self.run_child('import sys; print("control"); sys.exit(7)')
        self.assertEqual(result['stdout'], b'control\n')
        self.assertEqual(result['status'], 7)
        self.assertFalse(result['failures'])

    def test_output_arriving_between_select_and_exit_observation_is_drained(self):
        real_selector = selectors.DefaultSelector
        with tempfile.TemporaryDirectory(prefix='csh077-gate-') as temp:
            gate = Path(temp) / 'release'

            class DelayedSelector:
                def __init__(self):
                    self.inner = real_selector()
                    self.first = True

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    self.inner.close()

                def register(self, *args):
                    return self.inner.register(*args)

                def unregister(self, *args):
                    return self.inner.unregister(*args)

                def select(self, timeout):
                    if self.first:
                        self.first = False
                        gate.touch()
                        # Force an empty select result just before the child's
                        # output/exit is observed. Do not consume any bytes.
                        self.inner.select(1)
                        time.sleep(0.05)
                        return []
                    return self.inner.select(timeout)

            with patch('host_terminal.selectors.DefaultSelector', DelayedSelector):
                result = self.run_child('from pathlib import Path\nimport time\n'
                    + 'while not Path(' + repr(str(gate)) + ').exists(): time.sleep(.001)\n'
                    + 'print("tail")')
            self.assertEqual(result['stdout'], b'tail\n')
            self.assertEqual(result['status'], 0)
            self.assertFalse(result['failures'])

    def test_output_flood_is_failure(self):
        result = self.run_child('import os;\nwhile True: os.write(1,b"x"*8192)')
        self.assertIn('output limit exceeded', result['failures'])
        self.assertLess(result['elapsed_seconds'], 4)

    def test_timeout_kills_forked_descendant_and_preserves_unrelated_child(self):
        unrelated = subprocess.Popen(['/bin/sleep', '30'])
        pids = []
        try:
            result = self.run_child('import os,time\nchild=os.fork()\n'
                'if child == 0: time.sleep(30); os._exit(0)\n'
                'print(os.getpid(),child,flush=True)\ntime.sleep(30)')
            pids = list(map(int, result['stdout'].split()))
            self.assertIn('timeout', result['failures'])
            self.assertEqual(len(pids), 2)
            self.assertLess(result['elapsed_seconds'], 5)
            deadline = time.monotonic() + 2
            for pid in pids:
                while True:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        break
                    if time.monotonic() >= deadline:
                        self.fail(f'owned process {pid} survived cleanup')
                    time.sleep(0.01)
            self.assertIsNone(unrelated.poll())
        finally:
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            unrelated.kill()
            unrelated.wait(timeout=1)


if __name__ == '__main__':
    if os.getsid(0) != os.getpid():
        os.setsid()
    unittest.main()
