#!/usr/bin/env python3
"""Strict CSH-076 provider qualification with independent, bounded oracles."""
import argparse
import gettext
import io
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tempfile

import smoke
from host_catalog_cases import UTILITIES, cases
from host_utilities import serial, sha, source_identity, sanitizer_diagnostic


def matches(expected, actual):
    if expected == 'nonzero':
        return isinstance(actual, int) and 0 < actual < 128
    if expected == 'greater3':
        return isinstance(actual, int) and 3 < actual < 128
    if expected == 'nonempty':
        return bool(actual)
    if expected == 'any':
        return True
    if expected in ('codesets', 'locales', 'charmaps', 'locale-environment'):
        try:
            text = actual.decode('ascii')
        except UnicodeDecodeError:
            return False
        lines = text.splitlines()
        if expected == 'codesets':
            return 'UTF-8' in text and 'GB18030' in text
        if expected == 'locales':
            return 'POSIX' in lines and len(set(lines)) == len(lines) and text.endswith('\n')
        if expected == 'charmaps':
            return 'UTF-8' in lines and text.endswith('\n') and all(lines)
        required = ('LC_CTYPE', 'LC_NUMERIC', 'LC_TIME', 'LC_COLLATE', 'LC_MONETARY', 'LC_MESSAGES')
        return (lines[0:1] == ['LANG=C'] and lines[-1:] == ['LC_ALL=C'] and
                all(lines.count(key + '="C"') == 1 for key in required) and
                len({line.split('=', 1)[0] for line in lines}) == len(lines))
    return expected == actual


def check_mo(path, expected):
    """Python's MO reader independently checks the GNU provider's output format."""
    catalog = gettext.GNUTranslations(io.BytesIO(path.read_bytes()))._catalog
    wanted = {}
    for key, value in expected.items():
        if '\0' in key:
            singular = key.split('\0')[0]
            wanted.update({(singular, index): text for index, text in enumerate(value.split('\0'))})
        else:
            wanted[key] = value
    if catalog != wanted:
        raise ValueError(f'MO contents differ: expected {wanted!r}, got {catalog!r}')


def command_identity(argv):
    try:
        result = subprocess.run(argv, capture_output=True, timeout=10)
        return serial(dict(argv=argv, status=result.returncode, stdout=result.stdout, stderr=result.stderr))
    except (OSError, subprocess.SubprocessError) as error:
        return dict(argv=argv, unavailable=str(error))


def inventory(search):
    result = {}
    for name in UTILITIES:
        path = shutil.which(name, path=search)
        item = dict(path=path, realpath=os.path.realpath(path) if path else None)
        if path:
            item['sha256'] = sha(path)
            if platform.system() == 'Linux':
                item['package'] = command_identity(['dpkg-query', '-S', path, os.path.realpath(path)])
        result[name] = item
    return result


def run_case(case, mode, binary, probe, providers, search, fixture_root=None, locale_path=None, sanitizer=False):
    records = []
    errors = []
    with tempfile.TemporaryDirectory(prefix='csh-catalog-', dir=fixture_root) as temporary:
        root = Path(temporary)
        expand = lambda value: value.replace('@ROOT', str(root))
        env = {'PATH': search, 'LANG': 'C', 'LC_ALL': 'C', 'LANGUAGE': '',
               'TEXTDOMAIN': '', 'TEXTDOMAINDIR': '', 'NLSPATH': ''}
        if sanitizer:
            env.update(ASAN_OPTIONS='halt_on_error=1' + (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                       UBSAN_OPTIONS='halt_on_error=1')
        if locale_path and platform.system() == 'Linux':
            env['LOCPATH'] = str(locale_path)
        env.update({key: expand(value) for key, value in case.get('env', {}).items()})
        try:
            for name, data in case.get('files', {}).items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            for index, step in enumerate(case['steps']):
                utility = step['utility']
                path = str(probe) if utility == '@probe' else providers[utility]['path']
                if not path:
                    errors.append('missing provider: ' + utility)
                    records.append(dict(phase='setup', utility=utility, error=errors[-1]))
                    break
                argv = [expand(arg) for arg in step['args']]
                stdin = step.get('stdin', b'')
                if 'stdin_from' in step:
                    stdin = Path(step['stdin_from']).read_bytes()
                fixture = dict(env=env, args=argv, stdin=stdin)
                executable = Path(path)
                if mode != 'direct' and utility != '@probe':
                    executable = binary
                    prefix = ('exec ' + shlex.quote(path)) if mode == 'exec' else shlex.quote(utility)
                    script = prefix + ' ' + ' '.join(map(shlex.quote, argv))
                    # A private input file keeps shell-stdin scripts distinct from utility stdin.
                    (root / 'step-input').write_bytes(stdin)
                    script += ' <step-input'
                    if step.get('redirect'):
                        script += ' >' + shlex.quote(step['redirect'])
                    script += '\n'
                    fixture['stdin'] = b''
                    if mode in ('string', 'exec'):
                        fixture['args'] = ['-c', script]
                    elif mode == 'file':
                        (root / 'step-script').write_text(script)
                        fixture['args'] = ['step-script']
                    else:
                        fixture['args'] = []
                        fixture['stdin'] = script
                status, output, failures = smoke.capture(executable, fixture, root,
                    step.get('timeout', 5), 65536, file_size_limit=8 * 1024 * 1024)
                # capture owns these reserved fixture directories, per invocation.
                for reserved in ('.home', '.tmp'):
                    shutil.rmtree(root / reserved)
                output = {key: bytes(value) for key, value in output.items()}
                if step.get('redirect') and mode == 'direct':
                    (root / step['redirect']).write_bytes(output['stdout'])
                    output['stdout'] = b''
                if sanitizer_diagnostic(output):
                    failures.append('sanitizer diagnostic')
                if not (matches(step['status'], status) and matches(step['stdout'], output['stdout'])
                        and matches(step['stderr'], output['stderr'])):
                    failures.append('status/stream assertion differs')
                records.append(dict(phase='assertion', utility=utility, invocation=serial(fixture),
                    executable=str(executable), expected=serial(step),
                    actual=serial(dict(status=status, **output)), errors=failures))
                errors.extend(failures)
                if failures:
                    break
            if not errors:
                for name, messages in case.get('mo', {}).items():
                    check_mo(root / name, messages)
                if case.get('no_output'):
                    target = root / case['no_output']
                    if target.is_file() or (target.exists() and any(p.is_file() for p in target.rglob('*'))):
                        errors.append('permanent locale output left after error')
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append(str(error))
            records.append(dict(phase='setup' if not records else 'effect', error=str(error)))
    if root.exists():
        errors.append('fixture cleanup failed')
    return dict(name=case['name'], utility=case['utility'], mode=mode,
                verdict='FAIL' if errors else 'PASS', steps=records, errors=errors,
                fixture=str(root), cleanup=not root.exists(), case=serial(case))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('probe', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--locale-path', type=Path)
    parser.add_argument('--sanitizer', action='store_true')
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--scope', choices=('qualified', 'all'), default='qualified',
                        help='all also runs retained strict vendor-gap reproducers')
    parser.add_argument('--utility', choices=UTILITIES, help='Focused diagnostic run; not full profile')
    args = parser.parse_args()
    providers = inventory(args.path)
    scope = json.loads(Path(__file__).with_name('host_catalog_scope.json').read_text())
    excluded = scope['excluded_cases'][platform.system()]
    records = []
    for case in cases(platform.system()):
        if args.scope == 'qualified' and case['name'] in excluded:
            continue
        if args.utility and case['utility'] != args.utility:
            continue
        for mode in ('direct', 'string', 'file', 'stdin', 'exec'):
            record = run_case(case, mode, args.binary.resolve(), args.probe.resolve(), providers, args.path, locale_path=args.locale_path, sanitizer=args.sanitizer)
            records.append(record)
            print(f"{record['verdict']}: {case['name']} ({mode})", flush=True)
            if record['errors']:
                print(json.dumps(record['steps'][-1]), flush=True)
    missing = [name for name, provider in providers.items() if not provider['path']]
    limitations = [dict(condition=name, owner=scope['owner'], reason=reason)
                   for name, reason in excluded.items()]
    if platform.system() != 'Linux':
        limitations.append(dict(condition='localedef/private-sources', owner='CSH-076',
            reason='Darwin private LC_NUMERIC generation and libc consumption are tested; other generated categories, charmaps and public installation remain unqualified'))
    result = dict(platform=platform.platform(), libc=platform.libc_ver(), path=args.path,
        inventory=providers, source_identity=source_identity(), binary_sha256=sha(args.binary),
        probe_sha256=sha(args.probe), selected_utility=args.utility, scope=args.scope,
        qualification_boundary=scope['qualified_boundary'], unqualified=scope['unqualified'],
        limits=dict(timeout_seconds=5, localedef_timeout_seconds=30, output_bytes=65536,
                    file_bytes=8 * 1024 * 1024, child_resources='smoke.child_limits'),
        limitations=limitations, missing_providers=missing, cases=records,
        totals=dict(passed=sum(r['verdict'] == 'PASS' for r in records),
                    failed=sum(r['verdict'] == 'FAIL' for r in records)))
    profile = Path(__file__).resolve().parents[1] / 'build/host-profile/manifest.json'
    locale_record = profile.with_name('locales.json')
    if locale_record.exists():
        result['locale_provisioning'] = json.loads(locale_record.read_text())
    if profile.exists():
        manifest = json.loads(profile.read_text())
        if all(providers[name]['path'] == manifest['executables'][name]['target']
               for name in ('gettext', 'msgfmt', 'ngettext')):
            result['provisioning'] = manifest
    if 'provisioning' in result:
        for name in ('gettext', 'msgfmt', 'ngettext'):
            provider = result['provisioning']['executables'][name]['provider']
            providers[name]['vendor_version'] = command_identity([provider, '--version'])
            providers[name]['linked_libraries'] = command_identity(
                ['ldd', provider] if platform.system() == 'Linux' else ['otool', '-L', provider])
    if platform.system() == 'Linux':
        result['packages'] = command_identity(['dpkg-query', '-W', '-f=${Package} ${Version}\n'])
    else:
        result['os_build'] = command_identity(['sw_vers'])
        if 'provisioning' in result:
            result['catalog_package'] = command_identity([result['provisioning']['executables']['gettext']['provider'], '--version'])
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print('Result:', result['totals'], flush=True)
    return int(bool(missing or result['totals']['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
