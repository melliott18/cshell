"""CSH-072 harness failure and oracle regressions, not provider conformance."""
import json
import errno
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import pty_harness

from host_filesystem_extended import cases as extended_cases
from host_filesystem_remaining import cases as remaining_cases
from host_filesystem_residual_cases import cases as residual_cases
from host_contract_inventory import utility_owner
from host_filesystem import run_case, stdout_matches, stderr_matches
from host_filesystem_cases import UTILITIES, DATA, case, cases, audit_cases, terminal_cases, effect_errors


class FilesystemHarnessTests(unittest.TestCase):
    def test_permission_setup_rejects_root_and_cleans_private_tree(self):
        row = next(r for r in residual_cases() if r.get('permission_denied'))
        with tempfile.TemporaryDirectory() as root, patch('host_filesystem_residual_cases.os.geteuid', return_value=0):
            record = run_case(Path('/bin/true'), {'cp': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_permission_denial_must_be_independently_proved(self):
        import host_filesystem_residual_cases as residual
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            row = next(r for r in residual_cases() if r.get('permission_denied'))
            with patch.object(residual.os, 'geteuid', return_value=10001):
                residual.setup(root, row)
            # Simulate a filesystem that ignores mode bits. It cannot qualify.
            with patch.object(Path, 'chmod'):
                with self.assertRaisesRegex(OSError, 'unexpectedly succeeded'):
                    residual.arm(root, row)
            residual.restore(root, row)

    def test_residual_timeout_cleanup_for_each_environment(self):
        for capability in ('permission_denied', 'files', 'byte_link'):
            with self.subTest(capability=capability), tempfile.TemporaryDirectory() as root:
                root = Path(root)
                provider = root / 'slow'
                provider.write_text('#!' + sys.executable + ' -S\nimport os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n')
                provider.chmod(0o700)
                row = next(r for r in residual_cases() if r.get(capability))
                record = run_case(provider, {row['utility']: {'path': str(provider)}}, os.defpath,
                                  row, 'direct', root, None, timeout=2)
                self.assertEqual(record['verdict'], 'FAIL')
                self.assertTrue(record['cleanup'])
                self.assertTrue(any('timeout' in e for e in record['errors']))
                pid = int(bytes.fromhex(record['actual']['stdout']['hex']))
                with self.assertRaises(ProcessLookupError):
                    os.kill(pid, 0)
                self.assertEqual(list(root.iterdir()), [provider])

    def test_residual_effect_failure_is_not_hidden_by_permission_restore(self):
        row = next(r for r in residual_cases() if r['utility'] == 'rm')
        def corrupt(*args, **kwargs):
            directory = args[2]
            (directory / 'denied').chmod(0o700)
            (directory / 'denied/leaf').unlink()
            return 1, {'stdout': b'', 'stderr': b'denied'}, []
        with tempfile.TemporaryDirectory() as root, patch('host_filesystem.smoke.capture', side_effect=corrupt):
            record = run_case(Path('/bin/true'), {'rm': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertIn('effect mismatch: denied/leaf', record['errors'])
            self.assertTrue(record['cleanup'])

    def test_magic_setup_write_failure_is_not_a_provider_result(self):
        original = Path.write_bytes
        def fail_sample(path, data):
            if path.name == 'sample':
                raise OSError('injected fixture write failure')
            return original(path, data)
        row = next(r for r in residual_cases() if r.get('files'))
        with tempfile.TemporaryDirectory() as root, patch.object(Path, 'write_bytes', fail_sample):
            record = run_case(Path('/bin/true'), {'file': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_byte_link_setup_failure_is_not_a_provider_result(self):
        original = os.symlink
        def fail_bytes(target, link, *args, **kwargs):
            if isinstance(target, bytes):
                raise OSError('injected fixture symlink failure')
            return original(target, link, *args, **kwargs)
        row = next(r for r in residual_cases() if r.get('byte_link'))
        with tempfile.TemporaryDirectory() as root, patch('os.symlink', side_effect=fail_bytes):
            record = run_case(Path('/bin/true'), {'readlink': {'path': '/bin/true'}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_magic_and_byte_oracles_reject_changed_output(self):
        for row in residual_cases():
            if row.get('files') or row.get('byte_link'):
                output = row['stdout']
                self.assertTrue(stdout_matches(output, output, Path('.'), Path('.'), row))
                self.assertFalse(stdout_matches(output, output + b'wrong', Path('.'), Path('.'), row))

    def test_complete_unique_case_inventory(self):
        rows = list(cases()) + list(audit_cases()) + list(terminal_cases()) + list(extended_cases("Linux")) + list(remaining_cases()) + list(residual_cases())
        self.assertEqual({r['utility'] for r in rows}, set(UTILITIES))
        self.assertEqual(len({r['id'] for r in rows}), len(rows))
        self.assertTrue(all('gap' not in r for r in rows))

    def test_remaining_capability_setup_failure_is_cleaned(self):
        with tempfile.TemporaryDirectory() as root:
            row = next(r for r in remaining_cases() if r.get('utf8'))
            record = run_case(Path('/bin/true'), {row['utility']: {'path': '/bin/true'}},
                              os.defpath, row, 'direct', Path(root), None)
            self.assertEqual((record['verdict'], record['phase']), ('FAIL', 'setup'))
            self.assertTrue(record['cleanup'])

    def test_allocation_markers_reject_missing_unarmed_and_malformed_results(self):
        from host_filesystem import allocation_marker_matches
        expected = dict(requested=2, triggered=1, calls_min=2, calls_max=4)
        self.assertTrue(allocation_marker_matches(expected, dict(requested=2, triggered=1, calls=3)))
        for marker in ({}, [], dict(requested=2, triggered=0, calls=2),
                       dict(requested=2, triggered=1, calls=1), dict(requested=2, triggered=1, calls=5),
                       dict(requested=2, triggered=True, calls=2)):
            self.assertFalse(allocation_marker_matches(expected, marker))
        with tempfile.TemporaryDirectory() as root:
            row = case('readlink', 'unarmed-allocation', ['link'], status='nonzero', err='nonempty',
                       allocation_fault=expected)
            with patch('host_filesystem.smoke.capture', return_value=(1, {'stdout': b'', 'stderr': b'failed'}, [])):
                record = run_case(Path('/bin/true'), {'readlink': {'path': '/bin/true'}}, os.defpath,
                                  row, 'direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertTrue(any('allocation marker' in e for e in record['errors']))
            self.assertTrue(record['cleanup'])

    def test_child_markers_cannot_hang_or_redirect_the_oracle(self):
        # The outer watchdog catches a regression that blocks in the parent
        # after smoke.capture has already reaped the provider.
        tests = Path(__file__).resolve().parent
        for action in ('allocation', 'kernel'):
            for kind in ('fifo', 'symlink', 'directory', 'oversized', 'nonobject'):
                with self.subTest(action=action, kind=kind), tempfile.TemporaryDirectory() as root:
                    root = Path(root)
                    marker = '.allocation-fault.json' if action == 'allocation' else '.io-fault.json'
                    row = case('readlink', 'invalid-marker', ['link'], status='nonzero', err='nonempty')
                    if action == 'allocation':
                        row['allocation_fault'] = dict(requested=1, triggered=1, calls_min=1, calls_max=1)
                    else:
                        row['io_action'] = 'broken-pipe'
                    provider = root / 'provider'
                    payload = (dict(requested=1, triggered=1, calls=1) if action == 'allocation'
                               else dict(phase='armed', action='broken-pipe',
                                         provider=str(provider), errno=errno.EPIPE))
                    encoded = json.dumps(payload)
                    program = (
                        '#!' + sys.executable + '\n'
                        'import os,sys\nfrom pathlib import Path\n'
                        f'p=Path({marker!r})\np.unlink(missing_ok=True)\n'
                    )
                    if kind == 'fifo':
                        program += 'os.mkfifo(p)\n'
                    elif kind == 'symlink':
                        program += f"Path('payload').write_text({encoded!r})\np.symlink_to('payload')\n"
                    elif kind == 'directory':
                        program += 'p.mkdir()\n'
                    elif kind == 'oversized':
                        program += f"p.write_text({encoded!r} + ' ' * 4096)\n"
                    else:
                        program += "p.write_text('[]')\n"
                    provider.write_text(program + "print('injected error',file=sys.stderr)\nsys.exit(1)\n")
                    provider.chmod(0o700)
                    script = (
                        'import json,os,sys\nfrom pathlib import Path\n'
                        f'sys.path.insert(0,{str(tests)!r})\n'
                        'from host_filesystem import run_case\n'
                        f'record=run_case(Path({str(provider)!r}),'
                        f'{{"readlink":{{"path":{str(provider)!r}}}}},os.defpath,'
                        f'{row!r},"direct",Path({str(root)!r}),None)\n'
                        'print(json.dumps(record))\n'
                    )
                    result = subprocess.run([sys.executable, '-c', script],
                                            capture_output=True, text=True, timeout=5, check=True)
                    record = json.loads(result.stdout)
                    self.assertEqual(record['verdict'], 'FAIL')
                    self.assertTrue(any('marker' in e for e in record['errors']))
                    self.assertTrue(record['cleanup'])
                    self.assertFalse(list(root.glob('csh-filesystem-*')))

    def test_dd_oracle_rejects_padded_input_as_whole_record(self):
        row = next(r for r in remaining_cases() if r['id'] == 'dd/remaining-sync')
        good = b'0+1 records in\n1+0 records out\n4 bytes copied, 1 s, 4 B/s\n'
        self.assertTrue(stderr_matches(row, good))
        self.assertFalse(stderr_matches(row, good.replace(b'0+1', b'1+0')))
        self.assertFalse(stderr_matches(row, good.replace(b'4 bytes', b'5 bytes')))

    def test_each_remaining_contract_has_environment_reason_and_owner(self):
        root = Path(__file__).resolve().parent
        ledger = json.loads((root / 'host_filesystem_residuals.json').read_text())
        self.assertFalse(ledger['full_contracts_qualified'])
        self.assertEqual({r['utility'] for r in ledger['utilities']}, set(UTILITIES))
        self.assertEqual(len(ledger['utilities']), len(UTILITIES))
        for row in ledger['utilities']:
            self.assertEqual(row['next_owner'], utility_owner(row['utility']))
            self.assertEqual(row['status'], 'open')
            self.assertTrue(all(row[key] for key in ('reason', 'required_environment', 'remaining', 'implementation_owner')))
        manifest = json.loads((root / 'host_contracts.json').read_text())
        conditions = {c for owner in manifest['owners'] if 'basename' in owner['utilities'] for c in owner['conditions']}
        self.assertEqual({r['id'] for r in ledger['conditions']}, conditions)
        self.assertTrue(all(r['next_owner'] == utility_owner('basename') for r in ledger['conditions']))

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
            provider.write_text('#!' + sys.executable + ' -S\nimport os,time\nprint(os.getpid(),flush=True)\ntime.sleep(60)\n')
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

    def test_fault_setup_failure_cannot_satisfy_error_oracle(self):
        with tempfile.TemporaryDirectory() as root:
            row = case('dd', 'broken-pipe', ['if=data'], status='nonzero', err='nonempty', io_action='broken-pipe')
            with patch('host_filesystem.smoke.capture', return_value=(125, {'stdout': b'', 'stderr': b'loader failed'}, [])):
                record = run_case(Path('/missing-shell'), {'dd': {'path': '/bin/dd'}}, os.defpath,
                                  row, 'direct', Path(root), None)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertTrue(any('kernel fault marker' in e for e in record['errors']))
            self.assertTrue(record['cleanup'])

    def test_real_kernel_fault_control_does_not_accept_success(self):
        import errno
        import shutil
        with tempfile.TemporaryDirectory() as root:
            provider = shutil.which('true', path=os.defpath)
            row = case('dd', 'success-under-fault', [], status='nonzero', err='nonempty', io_action='broken-pipe')
            record = run_case(Path(provider), {'dd': {'path': provider}}, os.defpath,
                              row, 'direct', Path(root), None)
            self.assertEqual(record['kernel_fault']['phase'], 'armed')
            self.assertEqual(record['kernel_fault']['errno'], errno.EPIPE)
            self.assertEqual(record['verdict'], 'FAIL')
            self.assertIn('status mismatch', record['errors'])
            self.assertTrue(record['cleanup'])

    def test_archive_oracle_rejects_duplicate_members(self):
        import tarfile
        from host_filesystem_extended import archive_errors
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            with tarfile.open(root / 'archive', 'w') as archive:
                for _ in range(2):
                    archive.addfile(tarfile.TarInfo('archived'))
            errors, _ = archive_errors(root, {'archive_output': 'append'})
            self.assertEqual(errors, ['archive member set mismatch'])

    def test_effect_oracle_rejects_link_instead_of_regular_copy(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / 'data').write_bytes(DATA)
            (root / 'copy').symlink_to('data')
            errors, _ = effect_errors(root, case('cp', 'bytes', [], effects={'copy': {'content': DATA}}))
            self.assertEqual(errors, ['effect mismatch: copy'])

    def test_archive_oracle_does_not_open_fifo(self):
        from host_filesystem_extended import archive_errors
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            os.mkfifo(root / 'archive')
            errors, _ = archive_errors(root, {'archive_output': 'types'})
            self.assertEqual(errors, ['archive is not a bounded regular file'])

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
        ids = {r['id'] for r in list(cases()) + list(audit_cases()) + list(terminal_cases()) + list(extended_cases("Linux")) + list(remaining_cases()) + list(residual_cases())}
        for row in mapping['utilities']:
            self.assertFalse(row['full_contract_qualified'])
            self.assertTrue(row['remaining'])
            self.assertTrue(set(row['assertions']) <= ids)
            self.assertEqual(set(row['normative_headings']), set(row['sections']))
            self.assertTrue(all(value['disposition'] for value in row['sections'].values()))
            self.assertEqual(row['owner'], utility_owner(row['utility']))
        self.assertEqual({i for row in mapping['utilities'] for i in row['assertions']}, ids)
        for row in extended_cases('Linux'):
            mapping_row = next(r for r in mapping['utilities'] if r['utility'] == row['utility'])
            bucket = 'strict_provider_audit' if row.get('provider_audit') else 'passing_scope'
            self.assertIn(row['id'], mapping_row['extended_qualification'][bucket])


if __name__ == '__main__':
    unittest.main()
