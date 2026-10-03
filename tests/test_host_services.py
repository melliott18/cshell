#!/usr/bin/env python3
"""Exercise failure/timeout ownership without submitting any host service work."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from host_services import Suite, require_container, main


class ServiceHarnessTests(unittest.TestCase):
    def test_services_refuse_native_before_operations(self):
        with patch('host_services.platform.system', return_value='Darwin'):
            with self.assertRaisesRegex(RuntimeError, 'dedicated disposable'):
                require_container()

    def test_missing_provider_is_failure(self):
        suite = Suite(Path('/bin/sh'), '/nonexistent')
        with suite.directory() as directory, contextlib.redirect_stdout(io.StringIO()):
            suite.invoke('missing', 'logger', [], directory, 'direct')
        self.assertEqual(suite.results[-1]['verdict'], 'FAIL')
        self.assertEqual(suite.results[-1]['phase'], 'setup')

    def test_nonzero_and_false_success_are_not_qualified(self):
        suite = Suite(Path('/bin/sh'), os.defpath)
        with suite.directory() as directory, contextlib.redirect_stdout(io.StringIO()):
            suite.providers['date']['path'] = '/bin/sh'
            suite.invoke('bad-status', 'date', ['-c', 'exit 7'], directory, 'direct')
            suite.invoke('wrong-output', 'date', ['-c', 'printf wrong'], directory, 'direct', stdout=b'right')
            suite.invoke('missing-effect', 'date', ['-c', ':'], directory, 'direct', check=lambda a: False)
        self.assertEqual([r['verdict'] for r in suite.results], ['FAIL'] * 3)

    def test_timeout_reaps_owned_child_and_preserves_unrelated(self):
        suite = Suite(Path('/bin/sh'), os.defpath)
        unrelated = subprocess.Popen(['/bin/sleep', '10'])
        try:
            with suite.directory() as directory:
                result = suite.call(['/bin/sh', '-c', 'sleep 20 & echo $! > child; wait'], directory, timeout=0.3)
                pid = int((directory / 'child').read_text())
                self.assertEqual(result['failure'], 'timeout')
                self.assertLess(result['seconds'], 3)
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    try: os.kill(pid, 0)
                    except ProcessLookupError: break
                    time.sleep(0.05)
                else: self.fail('owned descendant survived cleanup')
                self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate(); unrelated.wait(timeout=2)

    def test_interrupted_profile_cannot_claim_success(self):
        with tempfile.TemporaryDirectory() as directory:
            record = Path(directory) / 'record.json'
            with patch('sys.argv', ['host_services.py', '/bin/sh', '--record', str(record)]), \
                    patch('host_services.encoding_cases', side_effect=KeyboardInterrupt), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)
            data = json.loads(record.read_text())
            self.assertFalse(data['completed'])
            self.assertFalse(data['qualified_subset'])
            self.assertEqual(data['results'][0]['name'], 'profile-interrupted')

    def test_unreaped_child_preserves_diagnostic_and_stops_profile(self):
        suite = Suite(Path('/bin/sh'), os.defpath)
        child = Mock(pid=999999999, returncode=None)
        child.wait.side_effect = subprocess.TimeoutExpired('fixture', 2)
        def launch(*args, **kwargs):
            kwargs['stderr'].write(b'sanitizer diagnostic before abort\n')
            return child
        with suite.directory() as directory, \
                patch('host_services.subprocess.Popen', side_effect=launch), \
                patch('host_services.smoke.kill_group'), \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'remains alive'):
                suite.invoke('unreaped', 'date', [], directory, 'direct')
        self.assertEqual(suite.results[-1]['verdict'], 'FAIL')
        actual = suite.results[-1]['actual']
        self.assertIn('was not reaped', actual['failure'])
        self.assertEqual(bytes.fromhex(actual['stderr']['hex']), b'sanitizer diagnostic before abort\n')

    def test_output_limit_is_failure(self):
        suite = Suite(Path('/bin/sh'), os.defpath)
        with suite.directory() as directory:
            result = suite.call(['/usr/bin/yes'], directory, timeout=2)
            self.assertNotEqual(result['status'], 0)
            self.assertLessEqual(len(result['stdout']), 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
