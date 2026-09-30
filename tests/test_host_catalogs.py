"""Prevent adapters and qualification bookkeeping from manufacturing passes."""
import io
import json
import gettext
from pathlib import Path
import sys
import tempfile
import unittest

from host_catalog_cases import MESSAGES, mo_bytes, step
from host_catalogs import check_mo, matches, run_case


class CatalogTests(unittest.TestCase):
    def test_shared_fixture_rejects_failure_and_corruption(self):
        import hashlib
        from locale_catalog_fixtures import load_fixtures
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / 'sample'
            sample.write_bytes(b'authored')
            manifest = root / 'manifest.json'
            record = dict(schema_version=1, verified=True, failures=[], root=tmp,
                          files={'sample': hashlib.sha256(b'authored').hexdigest()},
                          locale_setup={})
            manifest.write_text(json.dumps(record))
            self.assertEqual(load_fixtures(manifest)['root'], tmp)
            sample.write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                load_fixtures(manifest)
            record['verified'] = False
            manifest.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError, 'did not succeed'):
                load_fixtures(manifest)

    def test_failed_shared_setup_publishes_failure_and_preserves_consumers(self):
        import importlib.util
        from unittest.mock import patch
        script = Path(__file__).resolve().parents[1] / 'tools/host-profile/provision_catalogs.py'
        spec = importlib.util.spec_from_file_location('provision_catalogs_test', script)
        provisioner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(provisioner)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / 'build/host-profile'
            parent.mkdir(parents=True)
            (parent / 'locales.json').write_text(json.dumps(dict(failures=[],
                locales=[dict(verified=True)] * 5)))
            retained = parent / 'catalogs-existing'
            retained.mkdir()
            (retained / 'consumer').write_bytes(b'held')
            with patch.object(provisioner, 'ROOT', root):
                self.assertEqual(provisioner.provision(Path(sys.executable), ''), 1)
            record = json.loads((parent / 'fixtures.json').read_text())
            self.assertFalse(record['verified'])
            self.assertIn('missing provider: gencat', record['failures'])
            self.assertEqual((retained / 'consumer').read_bytes(), b'held')
            self.assertFalse(list(parent.glob('.catalog-setup-*')))

    def test_clause_map_and_exclusions_cover_real_owned_cases(self):
        from host_catalog_cases import UTILITIES, cases
        root = Path(__file__).parent
        mapping = json.loads((root / 'host_catalog_clauses.json').read_text())
        scope = json.loads((root / 'host_catalog_scope.json').read_text())
        self.assertEqual(set(mapping['utilities']), set(UTILITIES))
        self.assertEqual(set(scope['unqualified']), set(UTILITIES))
        expected_sections = {'DESCRIPTION', 'OPTIONS', 'OPERANDS', 'STDIN', 'INPUT FILES',
            'ENVIRONMENT VARIABLES', 'ASYNCHRONOUS EVENTS', 'STDOUT', 'STDERR', 'OUTPUT FILES',
            'EXTENDED DESCRIPTION', 'EXIT STATUS', 'CONSEQUENCES OF ERRORS'}
        for system in ('Darwin', 'Linux'):
            names = [case['name'] for case in cases(system)]
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(set(scope['excluded_cases'][system]) <= set(names))
        for utility, row in mapping['utilities'].items():
            names = {case['name'] for system in ('Darwin', 'Linux') for case in cases(system)
                     if case['utility'] == utility}
            self.assertEqual(set(row['cases']), names)
            self.assertEqual(set(row['sections']), expected_sections)
            for section in row['sections'].values():
                self.assertTrue(set(section['witnesses']) <= names)
                self.assertTrue(section['disposition'])

    def test_handwritten_mo_is_independently_readable(self):
        translations = gettext.GNUTranslations(io.BytesIO(mo_bytes(MESSAGES)))
        self.assertEqual(translations.gettext('cafe'), 'café')
        for n, expected in ((0, 'aucun'), (1, 'un'), (2, 'deux'), (3, 'plusieurs')):
            self.assertEqual(translations.ngettext('one', 'many', n), expected)

    def test_mo_wrong_or_missing_translation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'catalog.mo'
            path.write_bytes(mo_bytes(MESSAGES))
            check_mo(path, MESSAGES)
            for wrong in (dict(MESSAGES, hello='wrong'), {'': MESSAGES['']}):
                with self.assertRaises(ValueError):
                    check_mo(path, wrong)
            path.write_bytes(b'not an MO')
            with self.assertRaises(OSError):
                check_mo(path, MESSAGES)

    def test_error_status_never_accepts_signals(self):
        for status in (-15, 0, 128, 139):
            self.assertFalse(matches('nonzero', status))
        self.assertTrue(matches('nonzero', 1))
        self.assertFalse(matches('greater3', 3))
        self.assertTrue(matches('greater3', 4))

    def test_list_oracle_does_not_accept_empty_or_missing_posix(self):
        for data in (b'', b'C\n', b'POSIX\nPOSIX\n'):
            self.assertFalse(matches('locales', data))
        self.assertTrue(matches('locales', b'C\nPOSIX\n'))

    def test_timeout_and_assertion_failure_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            for program, timeout in (("print('wrong')", 5), ('import time; time.sleep(5)', 0.2)):
                case = dict(name='harness/failure', utility='fake', steps=[
                    step('fake', ['-c', program], out=b'expected\n', timeout=timeout)])
                result = run_case(case, 'direct', Path(sys.executable), Path(sys.executable),
                                  {'fake': {'path': sys.executable}}, '/usr/bin:/bin', tmp)
                self.assertEqual(result['verdict'], 'FAIL')
                self.assertTrue(result['cleanup'])
                self.assertFalse(list(Path(tmp).iterdir()))

    def test_missing_provider_is_setup_failure(self):
        result = run_case(dict(name='missing', utility='fake', steps=[step('fake')]),
                          'direct', Path(sys.executable), Path(sys.executable),
                          {'fake': {'path': None}}, '/usr/bin:/bin')
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertEqual(result['steps'][0]['phase'], 'setup')
        self.assertTrue(result['cleanup'])


if __name__ == '__main__':
    unittest.main()
