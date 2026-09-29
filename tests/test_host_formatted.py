"""Failure oracles and process cleanup for the CSH-070 threshold search."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from host_echo_threshold import threshold
from host_formatted_failures import run_owned


class ThresholdFailures(unittest.TestCase):
    def test_utility_failure_is_not_e2big(self):
        result = threshold('/usr/bin/false', 'single', 0, 1024 * 1024)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('output/status mismatch', result['error'])
        self.assertEqual(result['trials'][0]['status'], 1)
        self.assertNotIn('largest_success', result)

    def test_timeout_is_reaped_and_unrelated_child_survives(self):
        unrelated = subprocess.Popen(['/bin/sleep', '20'])
        try:
            with tempfile.TemporaryDirectory() as temporary:
                helper = Path(temporary) / 'slow'
                helper.write_text('#!/bin/sh\nexec /bin/sleep 20\n')
                helper.chmod(0o700)
                result = threshold(helper, 'single', 0, 1024 * 1024, timeout=0.1)
            self.assertEqual(result['verdict'], 'FAIL')
            trial = result['trials'][0]
            self.assertEqual(trial['error'], 'timeout')
            self.assertTrue(trial['reaped'])
            with self.assertRaises(ProcessLookupError):
                os.kill(trial['pid'], 0)
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=2)


class ProviderFailureCleanup(unittest.TestCase):
    def test_owned_timeout_reaped_without_touching_unrelated_child(self):
        unrelated = subprocess.Popen(['/bin/sleep', '20'])
        try:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
                record = run_owned(['/bin/sleep', '20'], {'LC_ALL': 'C'}, output,
                                   diagnostic, timeout=0.1)
            self.assertEqual(record['errors'], ['execution timeout'])
            self.assertTrue(record['reaped'])
            with self.assertRaises(ProcessLookupError):
                os.kill(record['pid'], 0)
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=2)

    def test_exec_setup_failure_cannot_be_a_signal_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as diagnostic:
                record = run_owned([temporary + '/missing'], {'LC_ALL': 'C'}, output, diagnostic)
        self.assertIsNone(record['status'])
        self.assertIsNone(record['pid'])
        self.assertFalse(record['reaped'])
        self.assertTrue(record['errors'][0].startswith('setup:'))


if __name__ == '__main__':
    unittest.main()
