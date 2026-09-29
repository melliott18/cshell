#!/usr/bin/env python3
"""Bounded, strict CSH-071 provider qualification in private temporary directories."""
import argparse
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import tempfile

import smoke
from host_contract_inventory import load_contracts
from host_permission_cases import UTILITIES, cases
from host_platform import credential_namespace, filesystem_identity
from host_utilities import inventory, match, serial, sha, source_identity, sanitizer_diagnostic

CHILD = Path(__file__).with_name('host_permissions_child.py').resolve()


def setup(root, case):
    root.chmod(0o777 if case.get('credentials') else 0o700)
    for name, data in {'data': b'private\n', 'empty': b'', 'subject': b'original\n',
                       'old': b'', 'new': b'', 'setuid': b'', 'setgid': b'',
                       'executable': b'#!/bin/sh\nexit 0\n'}.items():
        (root / name).write_bytes(data)
        (root / name).chmod(0o644)
    if case.get('access'):
        (root / 'access').write_bytes(b'#!/bin/sh\nexit 0\n' if case['access']['permission'] == 'x' else b'private\n')
        (root / 'access').chmod(0o777 if case['access']['allowed'] else 0)
    (root / 'subject').chmod(case.get('initial', 0o644))
    (root / 'setuid').chmod(0o4600)
    (root / 'setgid').chmod(0o2600)
    (root / 'executable').chmod(0o700)
    (root / 'tree').mkdir(mode=0o755)
    (root / 'tree/leaf').write_bytes(b'leaf\n')
    (root / 'tree/leaf').chmod(0o644)
    if case.get('traversal'):
        (root / 'outside').mkdir(mode=0o755)
        (root / 'outside/leaf').write_bytes(b'outside\n')
        (root / 'tree/nested-link').symlink_to('../outside')
    (root / 'tree').chmod(case.get('tree_mode', 0o755))
    (root / 'tree-link').symlink_to('tree')
    (root / 'link').symlink_to('data')
    (root / 'dangling').symlink_to('missing')
    os.link(root / 'data', root / 'hardlink')
    os.mkfifo(root / 'fifo')
    os.utime(root / 'old', (1000000000, 1000000000))
    os.utime(root / 'new', (1000000002, 1000000002))
    connection = socket.socket(socket.AF_UNIX)
    old = os.getcwd()
    try:
        os.chdir(root)
        connection.bind('socket')
    except BaseException:
        connection.close()
        raise
    finally:
        os.chdir(old)
    return connection


def metadata(root, expected):
    result = {}
    for name, fields in expected.items():
        value = (root / name).lstat() if fields.get('nofollow') else (root / name).stat()
        available = dict(mode=stat.S_IMODE(value.st_mode), uid=value.st_uid, gid=value.st_gid)
        result[name] = {key: available[key] for key in fields if key != 'nofollow'}
    return result


def check(case, status, output, identity):
    expected = {key: case[key] for key in ('status', 'stdout', 'stderr')}
    if case.get('login'):
        expected = (dict(status=0, stdout=(identity['login'] + '\n').encode(), stderr=b'')
                    if 'login' in identity else dict(status='nonzero', stdout=b'', stderr='nonempty'))
    if case.get('groups'):
        # Group order is not prescribed; require each distinct ID exactly once and exact separators.
        groups = {identity['gid'], identity['egid'], *identity['groups']}
        data = bytes(output['stdout'])
        try:
            values = [int(value) for value in data.rstrip(b'\n').split(b' ')]
        except ValueError:
            return False
        if (set(values) != groups or len(values) != len(groups) or
                data != (' '.join(map(str, values)) + '\n').encode()):
            return False
        expected['stdout'] = data
    return (match(expected['status'], status) and
            match(expected['stdout'], bytes(output['stdout'])) and
            match(expected['stderr'], bytes(output['stderr'])))


def run_case(binary, tools, search_path, case, mode, fixture_root, sanitizer=False):
    record = dict(name=case['name'], mode=mode, case=serial(case), verdict='FAIL', phase='setup')
    temporary = tempfile.TemporaryDirectory(prefix='csh-permissions-', dir=fixture_root)
    root = Path(temporary.name)
    connection = None
    try:
        connection = setup(root, case)
        name = case['utility']
        executable = tools[name]['path']
        if not executable:
            raise FileNotFoundError('required provider missing: ' + name)
        args = case['args'] + ([']'] if name == '[' and case.get('closing', True) else [])
        script = shlex.join([name] + args)
        stdin = ''
        if mode == 'direct':
            argv = [name] + args  # [ must have argv[0] exactly '[' (test DESCRIPTION).
            stdin = case.get('shell_input', '')
        else:
            executable = str(binary)
            if 'shell_input' in case:
                script += " <<'CSH_071_INPUT'\n" + case['shell_input'] + 'CSH_071_INPUT\n'
            script += '\n'
            if mode == 'string':
                argv = ['cshell', '-c', script]
            elif mode == 'file':
                (root / 'script').write_text(script)
                (root / 'script').chmod(0o644)
                argv = ['cshell', 'script']
            else:
                argv = ['cshell']
                stdin = script
        spec = dict(executable=executable, argv=argv, umask=case.get('umask', 0o022),
                    credentials=case.get('credentials'), access=case.get('access'))
        (root / 'exec.json').write_text(json.dumps(spec))
        record['invocation'] = spec
        env = dict(PATH=search_path, **case.get('env', {}))
        if sanitizer:
            env.update(ASAN_OPTIONS='halt_on_error=1' + (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                       UBSAN_OPTIONS='halt_on_error=1')
        fixture = dict(args=[str(CHILD), 'exec.json'], stdin=stdin, env=env)
        status, output, errors = smoke.capture(Path(sys.executable), fixture, root, 5, 65536)
        record['phase'] = 'assertion'
        record['actual'] = serial(dict(status=status, **{k: bytes(v) for k, v in output.items()}, errors=errors))
        if sanitizer_diagnostic(output):
            errors.append('sanitizer diagnostic')
        identity = json.loads((root / 'identity.json').read_text())
        record['identity'] = identity
        if case.get('credentials'):
            real, effective = case['credentials']
            if identity.get('capabilities', {}).get('CapEff') != '0000000000000000':
                errors.append('controlled child retained effective capabilities')
            if [identity[k] for k in ('uid', 'euid', 'gid', 'egid')] != [real, effective, real, effective] or identity['groups']:
                errors.append('credential setup differs from requested IDs')
        if case.get('access'):
            access = identity.get('access', {})
            if access.get('allowed') != case['access']['allowed']:
                errors.append('independent access operation differs from required permission')
            if access.get('allowed'):
                permission = case['access']['permission']
                if ((permission == 'r' and access.get('data') != b'private\n'.hex()) or
                    (permission == 'w' and (access.get('count') != 8 or (root / 'access').read_bytes() != b'private\nwritten\n')) or
                    (permission == 'x' and (access.get('status') != 0 or access.get('stdout') or access.get('stderr')))):
                    errors.append('independent access operation had unexpected effects')
        if 'session_gid' in case:
            session = json.loads((root / 'session.json').read_text())
            record['session'] = session
            if (session['gid'] != case['session_gid'] or session['egid'] != case['session_gid'] or
                    session['cwd'] != str(root.resolve()) or session['umask'] != case['umask'] or
                    session['exported'] != 'retained'):
                errors.append('newgrp environment differs from required preserved state')
        observed = metadata(root, case.get('metadata', {}))
        expected = {p: {k: v for k, v in f.items() if k != 'nofollow'}
                    for p, f in case.get('metadata', {}).items()}
        if observed != expected:
            errors.append('metadata differs from clause oracle')
        record.update(identity=identity, actual=serial(dict(status=status, **{k: bytes(v) for k, v in output.items()},
                      metadata=observed, errors=errors)))
        if not errors and check(case, status, output, identity):
            record['verdict'] = 'PASS'
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        record['error'] = repr(error)
    finally:
        if connection is not None:
            connection.close()
        # A tested chmod may remove search permission from our private directories.
        for directory in ('tree', 'outside'):
            if (root / directory).is_dir():
                (root / directory).chmod(0o700)
        temporary.cleanup()
        record['cleanup'] = not root.exists()
        if not record['cleanup']:
            record['verdict'] = 'FAIL'
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--fixture-root', type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument('--case-prefix', help='Run an explicitly selected case prefix; recorded in evidence')
    parser.add_argument('--sanitizer', action='store_true')
    parser.add_argument('--controlled-identities', action='store_true')
    parser.add_argument('--session-controls', action='store_true')
    parser.add_argument('--vendor-residuals', action='store_true', help='Strict chmod original-X reproducer; fails on GNU 9.1')
    args = parser.parse_args()
    if (args.controlled_identities or args.session_controls) and (platform.system() != 'Linux' or os.geteuid() != 0):
        parser.error('controlled identities/sessions require a disposable Linux root environment')
    tools = inventory(args.path, names=UTILITIES)
    result = dict(schema_version=1, owner='CSH-071', claim='selected assertions only; full contracts unqualified',
                  platform=platform.platform(), libc=platform.libc_ver(), path=args.path,
                  binary_sha256=sha(args.binary), source_identity=source_identity(), providers=tools,
                  filesystem=filesystem_identity(args.fixture_root), credential_namespace=credential_namespace(),
                  controlled=args.controlled_identities, sessions=args.session_controls, vendor_residuals=args.vendor_residuals,
                  limits=dict(seconds=5, output_bytes=65536, child_resources='smoke.child_limits'), cases=[])
    profile = Path(tools['test']['path']).parent.parent / 'manifest.json' if tools['test']['path'] else None
    if profile and profile.is_file():
        result['profile_manifest'] = json.loads(profile.read_text())
    if platform.system() == 'Darwin':
        result['os_build'] = subprocess.check_output(['sw_vers'], text=True)
        for provider in list(tools.values()) + [p['backend'] for p in tools.values() if 'backend' in p]:
            if provider['realpath']:
                receipt = Path(provider['realpath']).parent.parent / 'INSTALL_RECEIPT.json'
                if receipt.is_file():
                    provider['package_receipt'] = dict(path=str(receipt), sha256=sha(receipt),
                                                       contents=json.loads(receipt.read_text()))
    elif shutil.which('dpkg-query'):
        result['packages'] = subprocess.check_output(['dpkg-query', '-W', '-f=${Package} ${Version}\n'], text=True)
    result['case_prefix'] = args.case_prefix
    for case in cases(args.controlled_identities, args.session_controls, args.vendor_residuals):
        if args.case_prefix and not case['name'].startswith(args.case_prefix):
            continue
        for mode in case.get('modes', ('direct', 'string', 'file', 'stdin')):
            record = run_case(args.binary.resolve(), tools, args.path, case, mode, args.fixture_root, args.sanitizer)
            result['cases'].append(record)
            print(f"{record['verdict']}: permissions: {record['name']} ({mode})", flush=True)
            if record['verdict'] != 'PASS':
                print(json.dumps(record), flush=True)
    owner = next(o for o in load_contracts()['owners'] if o['ticket'] == 'CSH-071')
    result['unqualified'] = dict(utilities=list(UTILITIES), retained_conditions=owner['conditions'],
                                reason='See docs/host-permissions-identities.md for clause-level boundaries')
    result['totals'] = {verdict.lower(): sum(r['verdict'] == verdict for r in result['cases'])
                        for verdict in ('PASS', 'FAIL')}
    if not result['cases']:
        parser.error('case selection matched no assertions')
    missing = [name for name, provider in tools.items() if not provider['path']]
    result['missing_providers'] = missing
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print('Result: ' + str(result['totals']) + '; missing providers: ' + str(missing))
    return int(bool(result['totals']['fail'] or missing))


if __name__ == '__main__':
    raise SystemExit(main())
