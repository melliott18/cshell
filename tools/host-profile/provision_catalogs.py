#!/usr/bin/env python3
"""Publish verified, reusable catalogs and encoding samples for other tracks."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
import smoke
from host_catalogs import check_mo
from host_utilities import serial, sha, source_identity
from locale_catalog_fixtures import (ENCODINGS, GB18030_UTF8, GERMAN, MESSAGES,
                                    PO, mo_bytes)


def provision(probe, search, sanitizer=False):
    parent = ROOT / 'build/host-profile'
    parent.mkdir(parents=True, exist_ok=True)
    record = dict(schema_version=1, owner='CSH-076', verified=False, checks=[], failures=[],
                  providers={}, probe_sha256=sha(probe), source_identity=source_identity())
    with tempfile.TemporaryDirectory(prefix='.catalog-setup-', dir=parent) as temporary:
        root = Path(temporary)
        try:
            locales = json.loads((parent / 'locales.json').read_text())
            if locales['failures'] or len(locales['locales']) != 5 or not all(
                    row['verified'] for row in locales['locales']):
                raise ValueError('shared locales are not verified; run make host-locales')
            record['locale_setup'] = locales
            base_env = dict(PATH=search, LC_ALL='C', LANG='C', LANGUAGE='')
            if sanitizer:
                # Match the strict suite's Linux policy for external providers
                # whose process-lifetime allocations are released by exit.
                base_env.update(ASAN_OPTIONS='halt_on_error=1' +
                    (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                    UBSAN_OPTIONS='halt_on_error=1')
            if locales.get('locale_path'):
                base_env['LOCPATH'] = locales['locale_path']
            for name in ('gencat', 'msgfmt', 'gettext', 'ngettext', 'iconv'):
                path = shutil.which(name, path=search)
                if not path:
                    raise ValueError('missing provider: ' + name)
                record['providers'][name] = dict(path=path, realpath=os.path.realpath(path), sha256=sha(path))

            def run(name, args, expected=b'', stdin=b'', env=None):
                binary = probe if name == '@probe' else record['providers'][name]['path']
                fixture = dict(args=args, stdin=stdin, env=dict(base_env, **(env or {})))
                status, output, failures = smoke.capture(Path(binary), fixture, root, 5, 65536,
                                                        file_size_limit=8 * 1024 * 1024)
                for directory in ('.home', '.tmp'):
                    shutil.rmtree(root / directory)
                record['checks'].append(serial(dict(utility=name, invocation=fixture,
                    status=status, output={key: bytes(value) for key, value in output.items()}, failures=failures, expected_stdout=expected)))
                if status != 0 or failures or output['stderr'] or output['stdout'] != expected:
                    raise ValueError('fixture qualification failed: ' + name + ' ' + repr(args))

            for encoding, data in ENCODINGS.items():
                (root / (encoding + '.txt')).write_bytes(data)
            (root / 'GB18030-as-UTF-8.txt').write_bytes(GB18030_UTF8)
            for source, target, data, expected in (
                ('UTF-8', 'ISO-8859-1', ENCODINGS['UTF-8'], ENCODINGS['ISO-8859-1']),
                ('ISO-8859-1', 'UTF-8', ENCODINGS['ISO-8859-1'], ENCODINGS['UTF-8']),
                ('GB18030', 'UTF-8', ENCODINGS['GB18030'], GB18030_UTF8),
                ('UTF-8', 'GB18030', GB18030_UTF8, ENCODINGS['GB18030'])):
                run('iconv', ['-f', source, '-t', target], expected, data)

            (root / 'messages.po').write_bytes(PO)
            run('msgfmt', ['-o', 'compiled.mo', 'messages.po'])
            check_mo(root / 'compiled.mo', MESSAGES)
            profile_path = parent / 'manifest.json'
            if profile_path.exists():
                profile = json.loads(profile_path.read_text())
                if all(profile['executables'][name]['target'] == row['path']
                       for name, row in record['providers'].items()):
                    record['profile'] = profile
            record['mo_reader'] = 'Python gettext.GNUTranslations: exact authored message map'
            for locale, messages in (('fr_FR.UTF-8', MESSAGES), ('de_DE.UTF-8', GERMAN)):
                directory = root / 'messages' / locale / 'LC_MESSAGES'
                directory.mkdir(parents=True)
                (directory / 'demo.mo').write_bytes(mo_bytes(messages))
                check_mo(directory / 'demo.mo', messages)
                env = dict(LC_ALL=locale, TEXTDOMAIN='demo', TEXTDOMAINDIR=str(root / 'messages'))
                run('gettext', ['hello'], messages['hello'].encode(), env=env)
            compiled = root / 'messages/fr_FR.UTF-8/LC_MESSAGES/compiled.mo'
            shutil.copyfile(root / 'compiled.mo', compiled)
            env = dict(LC_ALL='fr_FR.UTF-8', TEXTDOMAIN='compiled', TEXTDOMAINDIR=str(root / 'messages'))
            run('gettext', ['cafe'], b'caf\xc3\xa9', env=env)
            for count, expected in ((0, b'aucun'), (1, b'un'), (2, b'deux'), (3, b'plusieurs')):
                run('ngettext', ['one', 'many', str(count)], expected, env=env)
            (root / 'messages.msg').write_bytes(b'$set 1\n1 bonjour\n2 caf\xc3\xa9\n')
            run('gencat', ['messages.cat', 'messages.msg'], env={'LC_ALL': 'fr_FR.UTF-8'})
            for number, expected in ((1, b'bonjour'), (2, b'caf\xc3\xa9'), (3, b'<missing>')):
                run('@probe', ['catalog', './messages.cat', '1', str(number)], expected,
                    env={'LC_ALL': 'fr_FR.UTF-8'})

            generation = parent / ('catalogs-' + uuid.uuid4().hex)
            record['root'] = str(generation)
            record['profiles'] = {}
            for row in locales['locales']:
                env = dict(base_env, LC_ALL=row['name'], TEXTDOMAIN='demo',
                           TEXTDOMAINDIR=str(generation / 'messages'))
                record['profiles'][row['name']] = dict(env=env,
                    codeset=row['expected_codeset'], decimal_point=row['expected_decimal_point'])
            record['files'] = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}
            record['catalogs'] = dict(gencat='messages.cat', gettext_domain='demo',
                                     compiled_domain='compiled', plural_counts=[0, 1, 2, 3],
                                     plural_expected=['aucun', 'un', 'deux', 'plusieurs'])
            record['verified'] = True
            # Consumers keep this immutable manifest and generation, even if a
            # subsequent provisioning run publishes a different latest record.
            (root / 'manifest.json').write_text(json.dumps(record, indent=2) + '\n')
            root.rename(generation)
        except (OSError, ValueError, KeyError) as error:
            record['verified'] = False
            record['failures'].append(str(error))
    record_path = parent / ('.fixtures-' + uuid.uuid4().hex + '.json')
    record_path.write_text(json.dumps(record, indent=2) + '\n')
    os.replace(record_path, parent / 'fixtures.json')
    for error in record['failures']:
        print('FAIL:', error, file=sys.stderr)
    print('Shared catalog fixtures: ' + ('verified' if record['verified'] else 'FAILED'))
    return int(not record['verified'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--path', required=True)
    parser.add_argument('--sanitizer', action='store_true')
    args = parser.parse_args()
    raise SystemExit(provision(args.probe.resolve(), args.path, args.sanitizer))
