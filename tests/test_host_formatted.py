"""Failure oracles and process cleanup for the CSH-070 threshold search."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from host_echo_threshold import threshold


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


if __name__ == '__main__':
    unittest.main()
