#!/usr/bin/env python3
"""Regression checks for lost ownership and current report attribution."""
import re
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from host_contract_inventory import ROOT, load_contracts, validate
from host_capability_limits import RESIDUAL, limitations
from host_utilities import setup_failure


class ContractOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.contracts = load_contracts()

    def test_current_ledger(self):
        self.assertEqual(validate(self.contracts), [])

    def test_dropped_required_utility(self):
        self.contracts['owners'][0]['utilities'].remove('printf')
        self.assertIn('unowned utility: printf', validate(self.contracts))

    def test_duplicate_utility(self):
        self.contracts['owners'][1]['utilities'].append('printf')
        self.assertIn('duplicate utility: printf', validate(self.contracts))

    def test_dropped_residual(self):
        self.contracts['owners'][0]['conditions'].remove('U-035/full-format')
        self.assertIn('unowned condition: U-035/full-format', validate(self.contracts))

    def test_duplicate_residual(self):
        self.contracts['owners'][1]['conditions'].append('U-035/full-format')
        self.assertIn('duplicate condition: U-035/full-format', validate(self.contracts))

    def test_dropped_conditional_prerequisite(self):
        del self.contracts['conditional_owners']['U-040/GB18030-locale']
        self.assertIn('conditional prerequisite ownership differs from emitted conditions',
                      validate(self.contracts))

    def test_closed_owner(self):
        original = Path.read_text
        target = ROOT / self.contracts['owners'][0]['path']

        def read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return re.sub(r'^- Status: .*$', '- Status: done', text, flags=re.M) if path == target else text

        with patch.object(Path, 'read_text', read):
            self.assertIn('CSH-070: outstanding contracts require an open ticket',
                          validate(self.contracts))

    def test_stale_markdown_owner(self):
        original = Path.read_text
        target = ROOT / 'docs/host-system-inventory.md'

        def read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            return text.replace('[CSH-070](', '[CSH-068](') if path == target else text

        with patch.object(Path, 'read_text', read):
            self.assertIn('printf: inventory owner differs from CSH-070', validate(self.contracts))

    def test_service_map_cannot_claim_full_qualification(self):
        original = Path.read_text
        target = ROOT / 'tests/host_service_contracts.json'

        def read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == target:
                document = json.loads(text)
                document['full_contract_qualified'] = True
                return json.dumps(document)
            return text

        with patch.object(Path, 'read_text', read):
            self.assertIn('CSH-078: incorrect bounded qualification boundary', validate(self.contracts))

    def test_service_map_cannot_drop_page_section(self):
        original = Path.read_text
        target = ROOT / 'tests/host_service_contracts.json'

        def read(path, *args, **kwargs):
            text = original(path, *args, **kwargs)
            if path == target:
                document = json.loads(text)
                del document['utilities'][0]['sections']['ASYNCHRONOUS EVENTS']
                return json.dumps(document)
            return text

        with patch.object(Path, 'read_text', read):
            self.assertIn('CSH-078/at: missing page-section disposition', validate(self.contracts))

    def test_live_residual_reports_preserve_evidence(self):
        environment = {'platform': 'fixture'}
        identities = {u: {'sha256': u} for _, u, _ in RESIDUAL}
        identities['['] = {'sha256': 'bracket'}
        rows = limitations(environment, identities)
        self.assertEqual(len(rows), 30)
        for row, (condition, utility, reason) in zip(rows, RESIDUAL):
            self.assertEqual(row['condition'], condition)
            self.assertEqual(row['reason'], reason)
            self.assertIs(row['environment'], environment)
            self.assertIs(row['executable'], identities[utility])
            self.assertNotIn(row['owner'], ('CSH-064', 'CSH-068'))
            self.assertEqual(row['implementation_owner'], 'selected utility/libc/platform vendor')
        self.assertEqual(next(r for r in rows if r['condition'] == 'U-037/ACLs')['owner'], 'CSH-071')
        self.assertEqual(next(r for r in rows if r['condition'] == 'U-040/sh-host-semantics')['owner'], 'CSH-075')

    def test_setup_failure_remains_strict_with_current_owner(self):
        row = setup_failure('fixture', {}, PermissionError(13, 'fixture denied'))
        self.assertEqual((row['verdict'], row['phase'], row['owner']), ('FAIL', 'setup', 'CSH-071'))
        self.assertEqual(row['actual']['errno'], 13)


if __name__ == '__main__':
    unittest.main()
