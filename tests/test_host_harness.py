"""Keep known host limitations from hiding new failures."""
import unittest
from unittest.mock import patch

from host_capability_limits import RESIDUAL, limitations
from host_utility_cases import HOSTS
from host_utilities import known_gap, match, matches_case, sanitizer_diagnostic


class HostEvidenceTests(unittest.TestCase):
    def test_status_predicates_do_not_accept_process_signal_death(self):
        self.assertTrue(match('nonzero', 7))
        self.assertFalse(match('nonzero', 0))
        self.assertFalse(match('nonzero', -15))
        self.assertFalse(match('error', 1))
        self.assertTrue(match('error', 2))

    @patch('host_utilities.platform.system', return_value='Linux')
    def test_known_kill_gap_requires_exact_signature(self, _):
        case = {'gap': 'kill-status'}
        output = {'stdout': b'', 'stderr': b'/bin/kill: unknown signal name 143\n'}
        self.assertTrue(known_gap(case, 0, output))
        self.assertFalse(known_gap(case, 1, output))
        self.assertFalse(known_gap(case, 0, dict(output, stdout=b'unexpected')))
        self.assertFalse(known_gap(case, 0, dict(output, stderr=output['stderr'] + b'AddressSanitizer: error\n')))
        self.assertFalse(known_gap({}, 0, output))

    @patch('host_utilities.platform.system', return_value='Linux')
    def test_native_gap_is_not_a_linux_allowance(self, _):
        self.assertFalse(known_gap({'gap': 'test-missing-time'}, 1,
                                   {'stdout': b'', 'stderr': b''}))

    def test_sanitizer_cannot_satisfy_a_diagnostic_predicate(self):
        for marker in (b'AddressSanitizer', b'UndefinedBehaviorSanitizer',
                       b'LeakSanitizer', b'runtime error:'):
            output = {'stdout': b'', 'stderr': b'ordinary diagnostic\n' + marker}
            self.assertTrue(match('nonempty', output['stderr']))
            self.assertTrue(sanitizer_diagnostic(output))
        self.assertFalse(sanitizer_diagnostic({'stderr': b'expected host error'}))

    def test_numbered_alternatives_require_consistent_streams_and_status(self):
        case = {'alternatives': [
            dict(stdout=b':a\n', stderr=b'', status=0),
            dict(stdout='any', stderr='nonempty', status='nonzero')]}
        self.assertTrue(matches_case(case, 0, dict(stdout=b':a\n', stderr=b'')))
        self.assertTrue(matches_case(case, 1, dict(stdout=b'', stderr=b'missing')))
        self.assertFalse(matches_case(case, 0, dict(stdout=b'', stderr=b'missing')))
        self.assertFalse(matches_case(case, 1, dict(stdout=b':a\n', stderr=b'')))
        self.assertFalse(matches_case(case, -11, dict(stdout=b'', stderr=b'crash')))

    def test_residual_capabilities_are_distinct_and_have_provenance(self):
        inventory = {name: {'path': '/selected/' + name, 'sha256': name} for name in HOSTS}
        rows = limitations('test environment', inventory)
        self.assertEqual(len({row['condition'] for row in rows}), len(RESIDUAL))
        for row in rows:
            self.assertEqual(row['environment'], 'test environment')
            self.assertEqual(row['owner'], 'CSH-060')
            self.assertTrue(row['source'].startswith('https://pubs.opengroup.org/'))
            self.assertTrue(row['reason'])
            self.assertTrue(row['executable']['sha256'])
            self.assertNotIn('verdict', row)
        for row in rows:
            if row['condition'].startswith('U-037/'):
                self.assertEqual(row['related_executable'], inventory['['])

    def test_binary_printf_regression_has_no_known_gap_allowance(self):
        case = {'name': 'U-035 b all bytes', 'stdout': bytes(range(256)),
                'stderr': b'', 'status': 0}
        output = {'stdout': b'', 'stderr': b''}
        self.assertFalse(matches_case(case, 0, output))
        self.assertFalse(known_gap(case, 0, output))
