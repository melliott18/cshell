#!/usr/bin/env python3
"""Real Git races and strict identity checks, without GitHub writes."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from tickets import Registry, REGISTRY_REF, command, main, registry_errors, validate


def git(cwd, *args, data=None):
    return command('git', *args, cwd=cwd, data=data).stdout.strip()


class ReservationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        remote = self.root / 'remote.git'
        git(self.root, 'init', '--bare', str(remote))
        self.clients = []
        for number in range(2):
            client = self.root / str(number)
            git(self.root, 'clone', str(remote), str(client))
            git(client, 'config', 'user.name', 'Ticket test')
            git(client, 'config', 'user.email', 'ticket-test@example.invalid')
            self.clients.append(client)
        initial = dict(schema_version=1, reservations={'CSH-082': 169})
        client = self.clients[0]
        blob = git(client, 'hash-object', '-w', '--stdin', data=json.dumps(initial))
        tree = git(client, 'mktree', data=f'100644 blob {blob}\tallocations.json\n')
        commit = git(client, 'commit-tree', tree, data='Initialize test registry\n')
        git(client, 'push', 'origin', commit + ':' + REGISTRY_REF)

    def test_concurrent_clients_get_distinct_sequential_ids(self):
        barrier = threading.Barrier(2)

        class RacingRegistry(Registry):
            first = True

            def publish(self, revision, value):
                if self.first:
                    self.first = False
                    barrier.wait(timeout=10)
                return super().publish(revision, value)

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(RacingRegistry(client).reserve, 200 + index)
                       for index, client in enumerate(self.clients)]
            ids = [future.result(timeout=30)[0] for future in futures]
        self.assertEqual(set(ids), {'CSH-083', 'CSH-084'})
        _, value = Registry(self.clients[0]).read()
        self.assertEqual(set(value['reservations'].values()), {169, 200, 201})

    def test_retry_after_publication_failure_keeps_same_reservation(self):
        client = Registry(self.clients[0])
        ticket, _ = client.reserve(200)
        revision = client.tip()
        self.assertEqual(Registry(self.clients[1]).reserve(200)[0], ticket)
        self.assertEqual(client.tip(), revision)

    def test_lost_success_response_recovers_without_duplicate_allocation(self):
        class LostResponse(Registry):
            def publish(self, revision, value):
                result = super().publish(revision, value)
                return subprocess.CompletedProcess(result.args, 1, '', 'simulated lost response')

        client = LostResponse(self.clients[0])
        self.assertEqual(client.reserve(200)[0], 'CSH-083')
        self.assertEqual(len(client.read()[1]['reservations']), 2)

    def test_permission_failure_is_not_retried_as_an_allocation(self):
        class Rejected(Registry):
            def publish(self, revision, value):
                return subprocess.CompletedProcess([], 1, '', 'denied')

        with self.assertRaisesRegex(ValueError, 'without a competing update'):
            Rejected(self.clients[0]).reserve(200)
        self.assertEqual(len(Registry(self.clients[0]).read()[1]['reservations']), 1)

    def test_missing_registry_never_falls_back_to_local_numbering(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            Registry(self.clients[0], ref='refs/heads/missing').reserve(200)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.registry = dict(schema_version=1, reservations={'CSH-080': 158})
        self.path = 'docs/tickets/CSH-080-filesystem.md'
        self.body = '# CSH-080: Filesystem\n\n- Status: ready\n- Issue: [#158](https://github.com/owner/repo/issues/158)\n'
        self.documents = {self.path: self.body,
                          'docs/tickets/README.md': '[CSH-080](CSH-080-filesystem.md)'}
        self.issues = [dict(number=158, title='CSH-080: Filesystem', body=self.body, state='open')]

    def errors(self):
        return validate(self.documents, self.issues, self.registry)[0]

    def test_aligned_identity(self):
        self.assertEqual(self.errors(), [])

    def test_empty_live_issue_list_rejects_missing_linked_issue(self):
        self.issues = []
        self.assertIn(f'{self.path}: linked GitHub issue is missing', self.errors())

    def test_offline_validation_does_not_require_github_issues(self):
        self.assertEqual(validate(self.documents, None, self.registry)[0], [])

    def test_duplicate_issue_titles_are_rejected(self):
        extra = copy.deepcopy(self.issues[0]); extra['number'] = 159
        self.issues.append(extra)
        self.assertTrue(any('duplicate GitHub' in error for error in self.errors()))

    def test_unreserved_ticket_is_rejected(self):
        self.registry['reservations'] = {}
        self.assertTrue(any('does not own' in error for error in self.errors()))

    def test_two_ids_for_one_issue_are_rejected(self):
        self.registry['reservations']['CSH-081'] = 158
        self.assertIn('issue #158 has multiple reservations', self.errors())

    def test_filename_heading_and_index_mismatch(self):
        self.documents[self.path] = self.body.replace('# CSH-080:', '# CSH-081:')
        self.documents['docs/tickets/README.md'] = '[CSH-081](CSH-080-filesystem.md)'
        errors = self.errors()
        self.assertTrue(any('heading disagree' in error for error in errors))
        self.assertTrue(any('index: CSH-081 links to CSH-080' in error for error in errors))

    def test_duplicate_files_and_wrong_issue_link(self):
        self.documents['docs/tickets/CSH-080-other.md'] = self.body
        self.documents[self.path] = self.body.replace('issues/158', 'issues/159')
        errors = self.errors()
        self.assertTrue(any('duplicate ticket files' in error for error in errors))
        self.assertTrue(any('inconsistent Issue link' in error for error in errors))

    def test_closed_stale_status_is_reported_separately(self):
        self.issues[0]['state'] = 'closed'
        errors, warnings = validate(self.documents, self.issues, self.registry)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ['CSH-080: closed issue body still says ready'])

    def test_body_heading_mismatch_is_rejected(self):
        self.issues[0]['body'] = self.body.replace('Filesystem', 'Different')
        self.assertTrue(any('body heading differs' in error for error in self.errors()))

    def test_wrong_repository_link_is_rejected(self):
        self.issues[0]['html_url'] = 'https://github.com/owner/repo/issues/158'
        self.documents[self.path] = self.body.replace('owner/repo', 'other/repo')
        self.assertTrue(any('different repository' in error for error in self.errors()))

    def test_shared_branch_allowed_only_for_historical_completed_work(self):
        self.documents[self.path] += '- Branch: test/CSH-037-audit-follow-up\n'
        self.assertTrue(any('branch field identifies' in error for error in self.errors()))
        self.documents[self.path] = self.documents[self.path].replace('Status: ready', 'Status: done')
        errors, warnings = validate(self.documents, self.issues, self.registry)
        self.assertEqual(errors, [])
        self.assertTrue(any('historical shared branch' in warning for warning in warnings))

    def test_malformed_registry_is_rejected(self):
        self.assertTrue(registry_errors(dict(schema_version=1, reservations={'CSH-80': {}})))
        self.assertTrue(registry_errors([]))
        self.assertTrue(registry_errors(None))

    def test_malformed_numbered_title_cannot_hide_as_a_draft(self):
        self.issues[0]['title'] = 'CSH-080 Filesystem'
        self.assertIn('issue #158: malformed CSH title', self.errors())


class CheckCommandTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        git(self.root, 'init')
        git(self.root, 'config', 'user.name', 'Ticket test')
        git(self.root, 'config', 'user.email', 'ticket-test@example.invalid')
        git(self.root, 'remote', 'add', 'origin', 'https://github.com/owner/repo.git')
        self.directory = self.root / 'docs/tickets'
        self.directory.mkdir(parents=True)
        self.snapshot = self.directory / 'allocations.json'
        self.registry = dict(schema_version=1, reservations={'CSH-080': 158, 'CSH-081': 159})
        self.snapshot.write_text(json.dumps(self.registry))
        self.body = '# CSH-080: Filesystem\n\n- Status: ready\n- Issue: [#158](https://github.com/owner/repo/issues/158)\n'
        (self.directory / 'CSH-080-filesystem.md').write_text(self.body)
        (self.directory / 'README.md').write_text('[CSH-080](CSH-080-filesystem.md)')
        self.issues = [dict(number=158, title='CSH-080: Filesystem', body=self.body, state='open')]
        self.commit()

    def commit(self):
        git(self.root, 'add', '.')
        git(self.root, 'commit', '-m', 'Test snapshot')
        return git(self.root, 'rev-parse', 'HEAD')

    def check(self, *args):
        output = io.StringIO()

        def local_command(*command_args, **kwargs):
            kwargs.setdefault('cwd', self.root)
            return command(*command_args, **kwargs)

        with patch('tickets.command', side_effect=local_command), \
                patch('tickets.Registry.read', return_value=('test-tip', self.registry)), \
                patch('tickets.all_issues', return_value=self.issues), redirect_stdout(output):
            status = main(['check', *args])
        return status, output.getvalue()

    def test_live_check_rejects_empty_issue_response(self):
        self.issues = []
        status, output = self.check('--live')
        self.assertEqual(status, 1)
        self.assertIn('linked GitHub issue is missing', output)

    def test_ref_snapshot_conflicts_are_reported_even_without_a_ticket_file(self):
        conflicting = copy.deepcopy(self.registry)
        conflicting['reservations']['CSH-081'] = 999
        self.snapshot.write_text(json.dumps(conflicting))
        revision = self.commit()
        self.snapshot.write_text(json.dumps(self.registry))
        for mode in ([], ['--live']):
            with self.subTest(mode=mode):
                status, output = self.check(*mode, '--ref', revision)
                self.assertEqual(status, 1)
                self.assertIn(f'FAIL {revision}: snapshot conflicts', output)
                self.assertIn('CSH-081', output)
                self.assertNotIn('FAIL worktree:', output)

    def test_ref_snapshot_malformed_json_and_schema_fail(self):
        for value in ('{', '[]', '{"schema_version": 1, "reservations": []}'):
            with self.subTest(value=value):
                self.snapshot.write_text(value)
                revision = self.commit()
                self.snapshot.write_text(json.dumps(self.registry))
                status, output = self.check('--live', '--ref', revision)
                self.assertEqual(status, 1)
                self.assertIn(f'FAIL {revision}: invalid allocation snapshot', output)

    def test_stale_ref_snapshot_can_omit_newer_reservations(self):
        self.snapshot.write_text(json.dumps(dict(schema_version=1, reservations={'CSH-080': 158})))
        revision = self.commit()
        self.snapshot.write_text(json.dumps(self.registry))
        self.assertEqual(self.check('--live', '--ref', revision)[0], 0)

    def test_ref_predating_registry_can_omit_snapshot(self):
        self.snapshot.unlink()
        revision = self.commit()
        self.snapshot.write_text(json.dumps(self.registry))
        self.assertEqual(self.check('--live', '--ref', revision)[0], 0)


if __name__ == '__main__':
    unittest.main()
