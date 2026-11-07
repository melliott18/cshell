#!/usr/bin/env python3
"""Guard strict evidence against incorrect effects, missing setup and timeout."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from host_permission_cases import case
from host_permissions import run_case
from host_permissions_child import process_groups


class PermissionsEvidenceTests(unittest.TestCase):
    def test_darwin_process_groups_do_not_use_account_membership(self):
        # Simulate CPython's directory-membership result differing from the
        # process credentials; accepting it would hide inherited privileges.
        with patch('host_permissions_child.sys.platform', 'darwin'), \
                patch('host_permissions_child.os.getgroups', side_effect=AssertionError('account lookup')):
            groups = process_groups()
        self.assertTrue(all(isinstance(group, int) and group >= 0 for group in groups))

    def run_provider(self, content, expected):
        with tempfile.TemporaryDirectory(prefix='csh-permission-selftest-') as name:
            root = Path(name)
            provider = root / 'provider'
            provider.write_text('#!/bin/sh\n' + content)
            provider.chmod(0o700)
            result = run_case(Path('/bin/sh'), {'chmod': {'path': str(provider)}},
                              os.defpath, expected, 'direct', root)
            self.assertTrue(result['cleanup'])
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['provider'])
            return result

    def test_success_cannot_hide_wrong_metadata(self):
        result = self.run_provider('exit 0\n', case('chmod', 'lying', ['600', 'subject'],
                                  metadata={'subject': {'mode': 0o600}}))
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('metadata differs from clause oracle', result['actual']['errors'])

    def test_control(self):
        result = self.run_provider('exec /bin/chmod 600 subject\n',
                                  case('chmod', 'control', ['600', 'subject'],
                                       metadata={'subject': {'mode': 0o600}}))
        self.assertEqual(result['verdict'], 'PASS')

    def test_timeout_is_failure_and_removes_fixture(self):
        result = self.run_provider('echo $$; exec sleep 30\n', case('chmod', 'timeout', []))
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertEqual(len(result['actual']['errors']), 1)
        self.assertIn('timeout after 5s', result['actual']['errors'][0])
        pid = int(bytes.fromhex(result['actual']['stdout']['hex']))
        self.assertEqual(result['process']['pid'], pid)
        self.assertTrue(result['process']['reaped'])
        self.assertGreaterEqual(result['process']['timeout_seconds'], 5)
        self.assertTrue('timeout_process' in result['process'] or
                        'timeout_process_error' in result['process'])
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_acl_cleanup_failure_is_retained(self):
        with patch('host_permissions.setup_acl', return_value='fixture ACL'), \
                patch('host_permissions.clear_acls', side_effect=OSError('cleanup rejected')):
            result = self.run_provider('exit 0\n', case('chmod', 'cleanup', [], acl={'fixture': True},
                access={'permission': 'r', 'allowed': True}))
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertIn('cleanup rejected', result['cleanup_errors'][0])

    def test_missing_provider_is_setup_failure(self):
        with tempfile.TemporaryDirectory() as name:
            result = run_case(Path('/bin/sh'), {'chmod': {'path': None}}, os.defpath,
                              case('chmod', 'missing', []), 'direct', Path(name))
            self.assertEqual((result['verdict'], result['phase']), ('FAIL', 'setup'))
            self.assertTrue(result['cleanup'])
            self.assertEqual(list(Path(name).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
