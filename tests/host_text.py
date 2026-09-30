#!/usr/bin/env python3
"""Strict CSH-073 subset; --audit also executes explicitly unqualified contracts."""
import argparse
import json
import locale
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

import smoke
from host_platform import filesystem_identity
from host_text_cases import UTILITIES, cases
from host_text_data import write_recipe, check_recipe, MAX_FILE
from host_utilities import match, serial, sha, source_identity, sanitizer_diagnostic

ROOT = Path(__file__).resolve().parent.parent


def providers(path):
    result = {}
    for name in UTILITIES + ('ed',):
        selected = shutil.which(name, path=path)
        row = dict(path=selected, realpath=os.path.realpath(selected) if selected else None)
        if selected:
            row['sha256'] = sha(selected)
            build_manifest = Path(row['realpath']).parent.parent / 'manifest.json'
            if build_manifest.is_file():
                metadata = json.loads(build_manifest.read_text())
                selected_build = metadata.get('executables', {}).get(name, {})
                if selected_build.get('sha256') == row['sha256'] and 'recipe' in metadata:
                    row['provider_build'] = metadata
            if shutil.which('dpkg-query'):
                query = subprocess.run(['dpkg-query', '-S', selected, row['realpath']], capture_output=True, timeout=5)
                row['package_query'] = serial(dict(status=query.returncode, stdout=query.stdout, stderr=query.stderr))
            else:
                row['package_identity'] = ('Pinned local source build' if 'provider_build' in row
                                           else 'OS build plus executable hash; selected system tools')
        result[name] = row
    return result


def utf8_locale():
    previous = locale.setlocale(locale.LC_CTYPE)
    try:
        for candidate in ('en_US.UTF-8', 'en_US.utf8', 'C.UTF-8'):
            try:
                locale.setlocale(locale.LC_CTYPE, candidate)
                if locale.nl_langinfo(locale.CODESET).lower().replace('-', '') == 'utf8':
                    return candidate
            except locale.Error:
                pass
    finally:
        locale.setlocale(locale.LC_CTYPE, previous)
    return None


def stream_matches(case, name, actual):
    pattern = case.get(name + '_re')
    if pattern is not None:
        return re.fullmatch(pattern, actual) is not None
    if name == 'stdout' and 'numbers' in case:
        # od permits padding, different line widths and a final empty line.
        return (re.fullmatch(rb'[ \t\n]*(?:[0-9]+[ \t\n]+)*', actual) is not None
                and [int(x) for x in actual.split()] == case['numbers'])
    return match(case[name], actual)


def setup(directory, case):
    (directory / 'input').write_bytes(case['input'])
    for name, data in case.get('inputs', {}).items():
        (directory / name).write_bytes(data)
    for name, recipe in case.get('generated_inputs', {}).items():
        write_recipe(directory / name, recipe)
    if case.get('sparse'):
        for name, marker in [('a', b'X'), ('b', b'Y')]:
            with (directory / name).open('wb') as stream:
                stream.seek(1 << 31)
                stream.write(marker)
        return {name: dict(size=(directory/name).stat().st_size,
                           blocks=(directory/name).stat().st_blocks,
                           marker_offset=1 << 31, marker=marker.hex())
                for name, marker in [('a',b'X'),('b',b'Y')]}
    return None


def run_case(binary, path, identity, case, mode, fixture_root):
    row = dict(id=case['id'], mode=mode, case=serial(case), verdict='FAIL')
    with tempfile.TemporaryDirectory(prefix='csh-text-', dir=fixture_root) as temporary:
        directory = Path(temporary)
        row['fixture_directory'] = temporary
        try:
            row['sparse'] = setup(directory, case)
            row['generated_inputs'] = {name: dict(bytes=(directory/name).stat().st_size, sha256=sha(directory/name))
                                       for name in case.get('generated_inputs', {})}
            selected = identity[case['utility']]['path']
            if selected is None:
                raise FileNotFoundError('required provider missing: ' + case['utility'])
            env = dict(PATH=path, **case.get('env', {}))
            if mode == 'direct':
                target = Path(selected)
                fixture = dict(args=case['args'], stdin=case['input'], env=env)
                if case.get('generated_inputs') or case.get('stdout_file'):
                    target = Path(sys.executable)
                    fixture['args'] = [str(ROOT/'tests/host_text_io.py'), 'input',
                                       case.get('stdout_file', '-'), selected] + case['args']
            else:
                target = binary
                script = shlex.join([case['utility']] + case['args']) + ' < input'
                if case.get('stdout_file'):
                    script += ' > ' + shlex.quote(case['stdout_file'])
                script += '\n'
                if mode == 'string':
                    fixture = dict(args=['-c',script], stdin=b'', env=env)
                elif mode == 'file':
                    (directory/'script').write_text(script)
                    fixture = dict(args=['script'], stdin=b'', env=env)
                else:
                    fixture = dict(args=[], stdin=script, env=env)
            row['invocation'] = serial(dict(binary=str(target), **fixture))
            status, output, errors = smoke.capture(target, fixture, directory,
                                        20 if case.get('sparse') or case.get('generated_inputs') else 5, 65536,
                                        file_size_limit=MAX_FILE if case.get('generated_inputs') else None)
            if sanitizer_diagnostic(output):
                errors.append('sanitizer diagnostic')
            effects = {name: (directory/name).read_bytes() if (directory/name).is_file() else None for name in case.get('files', {})}
            if case.get('products') and not case.get('generated_files'):
                effects = {p.name: p.read_bytes() for p in directory.glob(case['products']) if p.is_file()}
            generated_effects = {name: check_recipe(directory/name, recipe)
                                 for name, recipe in case.get('generated_files', {}).items()}
            if case.get('products') and case.get('generated_files'):
                actual_names = {p.name for p in directory.glob(case['products'])}
                if actual_names != set(case['generated_files']):
                    errors.append('generated output file set differs: ' + repr(sorted(actual_names)))
            ok = (all(effect['matches'] for effect in generated_effects.values()) and not errors and match(case['status'], status)
                  and all(stream_matches(case, name, bytes(output[name])) for name in ('stdout','stderr'))
                  and effects == case.get('files', {}))
            row.update(verdict='PASS' if ok else 'FAIL', phase='assertion',
                       actual=serial(dict(status=status, stdout=bytes(output['stdout']), stderr=bytes(output['stderr']), files=effects, generated_files=generated_effects, errors=errors)))
        except (OSError, subprocess.SubprocessError) as error:
            row.update(phase='setup', error=str(error), errno=getattr(error,'errno',None))
    row['fixture_removed'] = not Path(temporary).exists()
    if not row['fixture_removed']:
        row['verdict'] = 'FAIL'
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--fixture-root', type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--boundaries', action='store_true')
    parser.add_argument('--capacity-root', type=Path, help='Explicit disposable filesystem <=2 MiB')
    args = parser.parse_args()
    binary = args.binary.resolve()
    inputs_identity = source_identity()
    identity = providers(args.path)
    utf8 = utf8_locale()
    rows = []
    for case in cases(utf8, args.audit):
        for mode in ('direct', 'string', 'file', 'stdin'):
            row = run_case(binary, args.path, identity, case, mode, args.fixture_root)
            rows.append(row)
            print(row['verdict'] + ': text: ' + row['id'] + ' (' + mode + ')', flush=True)
            if row['verdict'] != 'PASS':
                print(json.dumps(row.get('actual', row)), flush=True)
    if args.boundaries:
        from host_text_boundaries import run_boundaries
        rows.extend(run_boundaries(binary, args.path, identity, args.fixture_root, args.capacity_root, args.audit))
    totals = {state.lower(): sum(row['verdict'] == state for row in rows) for state in ('PASS','FAIL','UNAVAILABLE')}
    group_totals = {}
    for group in ('transformations', 'offsets', 'large-inputs', 'interruptions'):
        members = [row for row in rows if row.get('category', row.get('case', {}).get('category')) == group]
        group_totals[group] = {state.lower(): sum(row['verdict'] == state for row in members)
                               for state in ('PASS', 'FAIL', 'UNAVAILABLE')}
    result = dict(qualification_groups=group_totals, schema_version=1, owner='CSH-073', full_contracts_qualified=False,
                  scope='required-contract audit' if args.audit else 'declared bounded subset',
                  path=args.path, platform=platform.platform(), libc=platform.libc_ver(),
                  inventory=identity, utf8_locale=utf8, binary_sha256=sha(binary),
                  source_identity=inputs_identity, filesystem=filesystem_identity(args.fixture_root),
                  command=sys.argv, credentials=dict(uid=os.getuid(),euid=os.geteuid(),gid=os.getgid(),egid=os.getegid(),groups=os.getgroups()),
                  capacity_filesystem=filesystem_identity(args.capacity_root) if args.capacity_root else None,
                  limits=dict(timeout_seconds=5, sparse_timeout_seconds=20, capture_bytes=65536,
                              child_resources='smoke.child_limits', sparse_offset=1 << 31, generated_file_bytes=MAX_FILE, large_timeout_seconds=20),
                  totals=totals, cases=rows)
    if platform.system() == 'Darwin':
        result['os_build'] = subprocess.check_output(['sw_vers'], text=True)
    if shutil.which('dpkg-query'):
        result['packages'] = subprocess.check_output(['dpkg-query','-W','-f=${Package} ${Version}\n'], text=True)
    if not utf8:
        result['unavailable_locale'] = dict(owner='CSH-073', reason='No UTF-8 locale; multibyte contracts unqualified')
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2)+'\n')
    print('Text result: ' + str(totals), flush=True)
    return int(bool(totals['fail']))


if __name__ == '__main__':
    raise SystemExit(main())
