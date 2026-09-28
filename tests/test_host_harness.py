"""Keep known host limitations from hiding new failures."""
import unittest
from unittest.mock import patch

from host_capability_limits import RESIDUAL, limitations
from host_environment_cases import cases as environment_cases
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
            self.assertEqual(row['owner'], 'CSH-063')
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

    def test_unequal_acl_grant_failure_stays_fatal(self):
        paths = {name: '/selected/' + name for name in HOSTS}
        cases = list(environment_cases(paths, '/helper', None, {}, True, True))
        grants = [case for case in cases if 'acl ' in case['name'] and 'effective=10001' in case['name']]
        self.assertEqual(len(grants), 2)  # test and bracket, each run in three modes
        for case in grants:
            output = dict(stdout=case['stdout'], stderr=b'')
            self.assertFalse(matches_case(case, 1, output))
            self.assertFalse(known_gap(case, 1, output))

    def test_acl_matrix_denials_and_operations_are_independent(self):
        from host_acl_cases import cases
        paths = {name: '/selected/' + name for name in HOSTS}
        rows = list(cases(paths, '/helper'))
        self.assertEqual(len(rows), 216)
        for row in rows:
            output = dict(stdout=row['stdout'], stderr=b'')
            if row['status'] == 0:
                self.assertFalse(matches_case(row, 1, output))
                self.assertFalse(known_gap(row, 1, output))
            else:
                self.assertFalse(matches_case(row, 0, output))
            if row['name'].endswith('operation') and row['controlled_fixture']['permission'] == 'w':
                self.assertEqual(row['files']['controlled'], b'private\nwritten\n' if row['status'] == 0 else b'private\n')

    def test_multiple_group_unequal_grants_remain_strict(self):
        from host_acl_cases import combinations
        paths = {name: '/selected/' + name for name in HOSTS}
        rows = list(combinations(paths, '/helper', True))
        grants = [row for row in rows if row['status'] == 0]
        self.assertEqual(len(grants), 54)
        for row in grants:
            self.assertFalse(matches_case(row, 1, dict(stdout=row['stdout'], stderr=b'')))
            self.assertFalse(known_gap(row, 1, dict(stdout=row['stdout'], stderr=b'')))
        for row in rows:
            if 'group' in row['name'] or 'user-precedence' in row['name']:
                self.assertIn(b'groups=2:10003:10004', row['stdout'])
            self.assertNotIn(b'uid=10002 euid=10002', row['stdout'])
            self.assertNotIn(b'uid=10001 euid=10001', row['stdout'])

    def test_fixture_mount_identity_uses_longest_component_match(self):
        import tempfile
        from pathlib import Path
        from host_platform import filesystem_identity
        with tempfile.TemporaryDirectory(prefix='acl fs ') as root:
            root = str(Path(root).resolve())
            encoded = root.replace(' ', r'\040')
            mounts = ('1 0 0:1 / / rw - overlay overlay rw\n' +
                      f'2 1 0:2 / {encoded} rw - tmpfs tmpfs rw\n' +
                      f'3 1 0:3 / {encoded}-other rw - ext4 other rw\n')
            result = filesystem_identity(Path(root), mounts)
            self.assertEqual(result['mount']['type'], 'tmpfs')
            self.assertEqual(result['mount']['mountpoint'], root)
            self.assertEqual(result['device'], Path(root).stat().st_dev)

    def test_setup_failure_retains_acl_diagnostic_and_cannot_pass(self):
        import subprocess
        from host_utilities import setup_failure
        case = dict(name='grant', status=0, stdout=b'', stderr=b'')
        error = subprocess.CalledProcessError(1, ['setfacl', '-m', 'u:10001:r--', 'private'],
                                            output=b'', stderr=b'Operation not supported\n')
        result = setup_failure('grant (string)', case, error)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertEqual(result['phase'], 'setup')
        self.assertEqual(result['actual']['status'], 1)
        self.assertEqual(result['actual']['stderr'], {'hex': error.stderr.hex()})
        self.assertEqual(result['case']['status'], 0)
        self.assertTrue(result['owner'])
        self.assertTrue(result['source'])
