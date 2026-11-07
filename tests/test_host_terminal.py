"""Fail-closed terminal harness, fixture oracle and owned-child cleanup checks."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import termios
import unittest
from unittest.mock import patch
import selectors

from host_terminal import capture, cases, tab_effect, run_case, MODES, report_errors
from host_terminal_residuals import cases as residual_cases
from pty_harness import open_terminal


class TerminalHarnessTests(unittest.TestCase):
    def test_report_oracle_rejects_wrong_values_and_contradictory_flags(self):
        attrs = [termios.ICRNL, termios.OPOST, termios.CS8 | termios.CREAD,
                 termios.ICANON | termios.ISIG, termios.B9600, termios.B9600, [b'\0'] * termios.NCCS]
        for name, value in {'EOF': 4, 'ERASE': 127, 'INTR': 3, 'KILL': 21,
                            'QUIT': 28, 'SUSP': 26, 'START': 17, 'STOP': 19, 'MIN': 1}.items():
            attrs[6][getattr(termios, 'V' + name)] = bytes([value])
        output = (b'speed 9600 baud; 24 rows; 41 columns; '
                  b'-ignbrk -brkint -ignpar -parmrk -inpck -istrip -inlcr -igncr icrnl -ixon -ixoff -ixany '
                  b'opost -parenb -parodd -hupcl -cstopb cread -clocal cs8 '
                  b'isig icanon -iexten -echo -echoe -echok -echonl -noflsh -tostop '
                  b'eof = ^D; eol = <undef>; erase = ^?; intr = ^C; kill = ^U; quit = ^\\; '
                  b'susp = ^Z; start = ^Q; stop = ^S; min = 1; time = 0;')
        self.assertEqual(report_errors(output, attrs, 0, [24, 41]), [])
        for old, new, failure in [(b'icrnl', b'-icrnl', 'report flag mismatch: ICRNL'),
                                  (b'^D', b'^A', 'report control mismatch: eof'),
                                  (b'9600', b'19200', 'report speed mismatch'),
                                  (b'41 columns', b'40 columns', 'report window mismatch: columns')]:
            with self.subTest(failure=failure):
                self.assertIn(failure, report_errors(output.replace(old, new), attrs, 0, [24, 41]))
        self.assertIn('report flag mismatch: ECHO', report_errors(output + b' echo', attrs, 0, [24, 41]))

    def test_tab_oracle_requires_clear_and_rejects_unknown_output(self):
        self.assertEqual(tab_effect(b'\rCLEAR_TABSSET_TAB   SET_TAB\r'), [0, 3])
        self.assertIsNone(tab_effect(b'SET_TAB'))
        self.assertIsNone(tab_effect(b'CLEAR_TABSunexpected'))

    def test_case_names_unique_and_no_gap_allowance(self):
        rows = list(cases())
        self.assertEqual(len(rows), len({r['name'] for r in rows}))
        self.assertTrue(all('gap' not in r for r in rows))

    def test_residual_names_unique_and_strict(self):
        rows = list(residual_cases())
        self.assertGreater(len(rows), 70)
        self.assertEqual(len(rows), len({row['name'] for row in rows}))
        self.assertTrue(all('gap' not in row and 'status' in row for row in rows))

    def test_unused_offset_detects_consumption_in_every_shell_path(self):
        binary = Path('cshell').resolve()
        with tempfile.TemporaryDirectory(prefix='csh077-offset-') as temp:
            directory = Path(temp)
            provider = directory / 'tty'
            provider.write_text('#!' + sys.executable + '\nimport os\nos.read(0,1)\nprint("not a tty")\nraise SystemExit(1)\n')
            provider.chmod(0o755)
            (directory / 'input').write_bytes(b'unused')
            providers = {'tty': {'path': str(provider)}}
            case = dict(name='consume-input', utility='tty', args=[], stdout=b'not a tty\n',
                        stderr=b'', terminal=b'', status=1)
            for mode in MODES:
                with self.subTest(mode=mode):
                    row = run_case(case, mode, binary, providers, directory,
                                   dict(PATH=temp + ':' + os.defpath, LC_ALL='C'))
                    self.assertEqual(row['input_offset'], 1)
                    self.assertEqual(row['failures'], ['unused stdin consumed'])

    def run_child(self, program, timeout=1, limit=1024, **kwargs):
        master, slave = open_terminal()
        try:
            with tempfile.TemporaryDirectory(prefix='csh077-harness-') as temp:
                with open(os.devnull, 'rb') as source:
                    return capture([sys.executable, '-c', program], Path(temp),
                        dict(PATH=os.defpath, CSH_TEST_SLAVE=str(slave)), master, slave, source,
                        timeout=timeout, limit=limit, **kwargs)
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

    def test_signal_waits_for_terminal_readiness(self):
        result = self.run_child(
            'import os,signal,sys,time\n'
            'def stop(sig, frame): print("interrupted",flush=True); sys.exit(7)\n'
            'signal.signal(signal.SIGINT,stop)\n'
            'os.write(int(os.environ["CSH_TEST_SLAVE"]),b"\\a\\a")\n'
            'time.sleep(30)', signal_on_terminal=(b'\a\a', signal.SIGINT))
        self.assertEqual(result['terminal'], b'\a\a')
        self.assertEqual(result['stdout'], b'interrupted\n')
        self.assertEqual(result['status'], 7)
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
