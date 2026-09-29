"""CSH-072 harness failure and oracle regressions, not provider conformance."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pty_harness

from host_contract_inventory import utility_owner
from host_filesystem import run_case, stdout_matches, stderr_matches
from host_filesystem_cases import UTILITIES, DATA, case, cases, audit_cases, terminal_cases, effect_errors


class FilesystemHarnessTests(unittest.TestCase):
    def test_complete_unique_case_inventory(self):
        rows = list(cases()) + list(audit_cases()) + list(terminal_cases())
        self.assertEqual({r['utility'] for r in rows}, set(UTILITIES))
        self.assertEqual(len({r['id'] for r in rows}), len(rows))
        self.assertTrue(all('gap' not in r for r in rows))

    def test_missing_provider_is_setup_failure_and_cleaned(self):
        with tempfile.TemporaryDirectory() as root:
            row = case('cp', 'missing-provider', ['data', 'copy'])
            record = run_case(Path('/missing-shell'), {'cp': {'path': None}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_timeout_is_fatal_and_owned_process_disappears(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            provider = root / 'slow'
            provider.write_text('#!' + sys.executable + '\nimport os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n')
            provider.chmod(0o700)
            record = run_case(provider, {'basename': {'path': str(provider)}}, os.defpath,
                              case('basename', 'timeout', ['a']), 'direct', root, None, timeout=1)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertTrue(any('timeout' in error for error in record['errors']))
            pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
            self.assertTrue(record['cleanup'])
            self.assertFalse(list(root.glob('csh-filesystem-*')))

    def test_unavailable_terminal_is_failure_with_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            row = next(terminal_cases())
            with patch('host_filesystem.smoke.capture', side_effect=pty_harness.PtyUnavailable('no terminal')):
                record = run_case(Path('/bin/rm'), {'rm': {'path': '/bin/rm'}}, os.defpath,
                                  row, 'pty-direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertIn('no terminal', record['error'])
            self.assertTrue(record['cleanup'])

    def test_corrupt_archive_is_failed_assertion_with_cleanup(self):
        import tarfile
        with tempfile.TemporaryDirectory() as root:
            row = case('pax', 'corrupt-archive', [], archive='write')
            with patch('host_filesystem.smoke.capture', return_value=(0, {'stdout': b'', 'stderr': b''}, [])), \
                    patch('host_filesystem.effect_errors', side_effect=tarfile.ReadError('bad archive')):
                record = run_case(Path('/bin/pax'), {'pax': {'path': '/bin/pax'}}, os.defpath,
                                  row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'assertion'))
            self.assertIn('bad archive', record['error'])
            self.assertTrue(record['cleanup'])

    def test_effect_oracle_rejects_link_instead_of_regular_copy(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / 'data').write_bytes(DATA)
            (root / 'copy').symlink_to('data')
            errors, _ = effect_errors(root, case('cp', 'bytes', [], effects={'copy': {'content': DATA}}))
            self.assertEqual(errors, ['effect mismatch: copy'])

    def test_new_required_contract_failures_are_not_allowed(self):
        row = next(r for r in audit_cases() if r['utility'] == 'readlink')
        self.assertFalse(stderr_matches(row, b''))
        self.assertTrue(stderr_matches(row, b'not a symbolic link\n'))

    def test_df_oracle_checks_percentage_header_and_record_count(self):
        good = b'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/example 120 30 70 30% /\n'
        self.assertTrue(stdout_matches('df-portable', good, None, None, {}))
        for bad in (good.replace(b'30%', b'31%'), good + b'junk\n', good.replace(b'1024-blocks', b'512-blocks')):
            self.assertFalse(stdout_matches('df-portable', bad, None, None, {}))

    def test_clause_map_preserves_every_provider_and_normative_section(self):
        root = Path(__file__).resolve().parent
        mapping = json.loads((root / 'host_filesystem_contracts.json').read_text())
        self.assertEqual({r['utility'] for r in mapping['utilities']}, set(UTILITIES))
        ids = {r['id'] for r in list(cases()) + list(audit_cases()) + list(terminal_cases())}
        for row in mapping['utilities']:
            self.assertFalse(row['full_contract_qualified'])
            self.assertTrue(row['remaining'])
            self.assertTrue(set(row['assertions']) <= ids)
            self.assertEqual(set(row['normative_headings']), set(row['sections']))
            self.assertTrue(all(value['disposition'] for value in row['sections'].values()))
            self.assertEqual(row['owner'], utility_owner(row['utility']))


if __name__ == '__main__':
    unittest.main()
