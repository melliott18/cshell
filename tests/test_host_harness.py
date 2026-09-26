"""Keep known host limitations from hiding new failures."""
import unittest
from unittest.mock import patch

from host_utilities import known_gap, match


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
