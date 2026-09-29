"""Protect strict CSH-075 evidence from false passes and accounting loss."""
import json
from pathlib import Path
import signal
import os
import subprocess
import unittest
from unittest.mock import patch

from host_execution import run_case, reap_owned
from host_execution_controls import duration_total
from host_execution_cases import UTILITIES, cases, matches

ROOT = Path(__file__).resolve().parent


class ExecutionEvidenceTests(unittest.TestCase):
    def test_duration_chunks_preserve_the_total_without_overflow(self):
        self.assertEqual(duration_total('2147483647 0\n1 0\n'), 2147483648 * 10**9)
        for text in (None, '', '-1 0\n', '1 1000000000\n', '1\n', 'bad data\n'):
            self.assertIsNone(duration_total(text))
        self.assertNotEqual(duration_total('2147483647 0\n'), 2147483648 * 10**9)

    def test_cleanup_does_not_signal_or_reap_unrelated_children(self):
        unrelated = subprocess.Popen(['/bin/sleep', '10'])
        child = os.fork()
        if child == 0:
            while True:
                signal.pause()
        try:
            reap_owned(child)
            with self.assertRaises(ChildProcessError):
                os.waitpid(child, os.WNOHANG)
            self.assertIsNone(unrelated.poll())
        finally:
            try:
                remaining, _ = os.waitpid(child, os.WNOHANG)
            except ChildProcessError:
                pass
            else:
                if remaining == 0:
                    os.kill(child, signal.SIGKILL)
                    os.waitpid(child, 0)
            unrelated.kill()
            unrelated.wait(timeout=2)

    def test_false_status_is_the_normative_range(self):
        for status in (-15, 0, 126, 127, 255):
            self.assertFalse(matches('false-status', status, 'direct', {}))
        self.assertTrue(matches('false-status', 125, 'direct', {}))

    def test_timeout_preserves_the_actual_signal(self):
        case = {}
        self.assertTrue(matches('term-status', -signal.SIGTERM, 'direct', case))
        self.assertFalse(matches('term-status', -signal.SIGSEGV, 'direct', case))
        self.assertFalse(matches('term-status', 139, 'string', case))
        self.assertFalse(matches('kill-status', 139, 'string', case))

    def test_timing_requires_all_fields_and_clock_precision(self):
        with patch('host_execution_cases.os.sysconf', return_value=100):
            case = {'status': 0}
            self.assertTrue(matches('timing', b'real 0.01\nuser 0.00\nsys 0.00\n', 'direct', case))
            for text in (b'', b'real 0.0\nuser 0.0\nsys 0.0\n', b'real nan\nuser 0.00\nsys 0.00\n'):
                self.assertFalse(matches('timing', text, 'direct', case))

    def test_missing_provider_is_a_failure(self):
        record = run_case('/unused', Path('/unused'), {'true': {'path': None}}, '/missing', 'true/status', 'direct')
        self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'provider'))

    def test_capture_timeout_and_sanitizer_are_never_passes(self):
        for output, errors in [({'stdout': b'', 'stderr': b''}, ['timeout']),
                               ({'stdout': b'', 'stderr': b'AddressSanitizer'}, [])]:
            with patch('host_execution.smoke.capture', return_value=(0, output, errors)):
                record = run_case('/unused', Path('/unused'), {'true': {'path': '/unused'}}, '/missing', 'true/status', 'direct')
                self.assertEqual(record['verdict'], 'FAIL')

    def test_sources_sections_and_case_references_are_complete(self):
        contract = json.loads((ROOT / 'host_execution_contracts.json').read_text())
        names = [r['utility'] for r in contract['utilities']]
        self.assertEqual(sorted(names), sorted(UTILITIES))
        required = {'NAME','SYNOPSIS','DESCRIPTION','OPTIONS','OPERANDS','STDIN','INPUT FILES',
                    'ENVIRONMENT VARIABLES','ASYNCHRONOUS EVENTS','STDOUT','STDERR','OUTPUT FILES',
                    'EXTENDED DESCRIPTION','EXIT STATUS','CONSEQUENCES OF ERRORS'}
        definitions = list(cases('/helper', Path('.'), 0))
        all_ids = [row['id'] for row in definitions]
        self.assertEqual(len(all_ids), len(set(all_ids)))
        for utility in contract['utilities']:
            self.assertEqual(set(utility['sections']), required)
            self.assertEqual(utility['whole_page'], 'unqualified')
            valid = {c['id'] for c in definitions if c['utility'] == utility['utility']}
            for section in utility['sections'].values():
                self.assertLessEqual(set(section.get('cases', [])), valid)
                self.assertTrue(section.get('reason') or section.get('remaining'))
        for system in ('darwin','linux'):
            subset = json.loads((ROOT / ('host_execution_subset_' + system + '.json')).read_text())
            self.assertEqual(len(subset), len(set(subset)))
            self.assertLess(set(subset), set(all_ids))
            self.assertIn('timeout/expiry', subset)
            self.assertNotIn('timeout/foreground', subset)


if __name__ == '__main__':
    unittest.main()
