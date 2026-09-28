#!/usr/bin/env python3
"""Run CSH-052 host assertions with bounded capture and byte-exact records."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import socket
import stat
import locale
import subprocess
import tempfile

from host_platform import filesystem_identity

import smoke
from host_utility_cases import HOSTS, INTRINSICS, cases
from host_boundary_cases import cases as boundary_cases
from host_capability_cases import cases as capability_cases
from host_environment_cases import cases as environment_cases, setup_controlled
from host_capability_limits import limitations as residual_limitations, BASE


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory(search_path=os.defpath):
    result = {}
    for name in HOSTS:
        path = shutil.which(name, path=search_path)
        entry = {'path': path, 'realpath': os.path.realpath(path) if path else None}
        if path:
            entry['sha256'] = sha(path)
            if platform.system() == 'Linux':
                # Package identity is safer than passing --version to tools that
                # interpret it as an operand (notably test, echo and ed).
                query = subprocess.run(['dpkg-query', '-S', path, os.path.realpath(path)],
                                       capture_output=True, text=True, timeout=5) if shutil.which('dpkg-query') else None
                entry['package_owners'] = query.stdout.strip() if query else 'unavailable'
            else:
                entry['version_identity'] = 'OS build and executable SHA-256 (no portable version option)'
        result[name] = entry
    return result


def setup(directory, extra_files=None):
    contents = {'data': b'one\ntwo\n', 'edit': b'edit\n', 'remove': b'',
                'first': b'first\n', 'second': b'second\n', 'tree/leaf': b'',
                'old': b'', 'new': b'', 'setuid': b'', 'setgid': b'',
                'executable': b'', 'high': bytes(range(128, 256)),
                'binary': bytes(range(256)), 'denied': b'private',
                'long': b'x' * 8192 + b'\n'}
    contents.update(extra_files or {})
    for name, content in contents.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    os.utime(directory / 'old', (1000000000, 1000000000))
    os.utime(directory / 'new', (1000000002, 1000000002))
    os.chmod(directory / 'denied', 0)
    os.chmod(directory / 'setuid', 0o4600)
    os.chmod(directory / 'setgid', 0o2600)
    os.chmod(directory / 'executable', 0o700)
    (directory / 'link').symlink_to('data')
    (directory / 'dangling').symlink_to('absent')
    os.link(directory / 'data', directory / 'hardlink')
    os.mkfifo(directory / 'fifo')
    connection = socket.socket(socket.AF_UNIX)
    # Use a relative path to stay below macOS sockaddr_un's pathname bound.
    previous = os.getcwd()
    try:
        os.chdir(directory)
        connection.bind('socket')
    finally:
        os.chdir(previous)
    (directory / 'shadow').mkdir()
    for name in set(HOSTS + INTRINSICS):
        path = directory / 'shadow' / name
        path.write_text('#!/bin/sh\nexit 73\n')
        path.chmod(0o700)
    return connection


def match(expected, actual):
    if expected == 'nonzero':
        return actual > 0
    if expected == 'error':
        return actual > 1
    if expected == 'nonempty':
        return bool(actual)
    if expected == 'any':
        return True
    return expected == actual


def matches_case(case, status, output):
    return any(match(expected['status'], status) and
               match(expected['stdout'], bytes(output['stdout'])) and
               match(expected['stderr'], bytes(output['stderr']))
               for expected in case.get('alternatives', [case]))


def serial(value):
    if isinstance(value, bytes):
        return {'hex': value.hex()}
    if isinstance(value, dict):
        return {key: serial(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(item) for item in value]
    return value


def sanitizer_diagnostic(output):
    return any(marker in bytes(stream) for stream in output.values()
               for marker in (b"AddressSanitizer", b"UndefinedBehaviorSanitizer",
                              b"LeakSanitizer", b"runtime error:"))


def known_gap(case, status, output):
    # Exact, separately reported baseline signatures only. A new symptom fails.
    # These are not passing requirements; --strict-gaps makes them fatal.
    if platform.system() == 'Darwin' and case.get('gap') == 'test-missing-time':
        return status == 1 and not output['stdout'] and not output['stderr']
    if platform.system() != 'Linux':
        return False
    if case.get('gap') == 'kill-status':
        return (status == 0 and not output['stdout'] and
                bytes(output['stderr']) == b'/bin/kill: unknown signal name 143\n')
    if case.get('gap') == 'printf-b-precision':
        return (status == 1 and bytes(output['stdout']) == b'[' and
                bytes(output['stderr']) == b'printf: %.3b: invalid conversion specification\n')
    if case.get('gap') == 'printf-numbered':
        return (status == 1 and not output['stdout'] and
                bytes(output['stderr']) == b'printf: %2$: invalid conversion specification\n')
    return False


def setup_failure(name, case, error):
    return dict(name=name, verdict='FAIL', phase='setup', case=serial(case),
                reason=str(error), owner='CSH-063', source=BASE + 'test.html',
                actual=serial(dict(errno=getattr(error, 'errno', None),
                    argv=getattr(error, 'cmd', None), status=getattr(error, 'returncode', None),
                    stdout=getattr(error, 'stdout', None), stderr=getattr(error, 'stderr', None))))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('helper', type=Path)
    parser.add_argument('--record', type=Path)
    parser.add_argument('--fixture-root', type=Path,
                        help='Existing disposable fixture directory (for a supplied alternate filesystem)')
    parser.add_argument('--path', default=os.environ.get('CSH_TEST_PATH', os.defpath),
                        help='Explicit utility search path, also used inside the shell')
    parser.add_argument('--strict-gaps', action='store_true')
    parser.add_argument('--boundaries', action='store_true')
    parser.add_argument('--printf-faults', type=Path,
                        help='Test-only instrumented copy of the profile printf source')
    parser.add_argument('--controlled-identities', action='store_true',
                        help='Linux root opt-in: private ACL, credential and device fixtures')
    parser.add_argument('--unequal-acl', action='store_true',
                        help='Also require ACL access with unequal IDs (strict known-failure reproducer on Debian 12)')
    parser.add_argument('--echo-policy', choices=('darwin', 'gnu', 'busybox-fancy'),
                        default='darwin' if platform.system() == 'Darwin' else 'gnu')
    parser.add_argument('--block-device', type=Path,
                        help='Stat-only positive predicate witness; never opened')
    parser.add_argument('--sanitizer', action='store_true',
                        help='Set ASan/UBSan in the actual case environment; disable Linux leak scanning')
    args = parser.parse_args()
    if args.controlled_identities and (not args.boundaries or platform.system() != 'Linux' or os.geteuid() != 0):
        parser.error('--controlled-identities requires --boundaries and Linux root')
    if args.unequal_acl and not args.controlled_identities:
        parser.error('--unequal-acl requires --controlled-identities')
    fixture_root = args.fixture_root.resolve() if args.fixture_root else Path(tempfile.gettempdir())
    if not fixture_root.is_dir():
        parser.error('--fixture-root must be an existing directory')
    filesystem = filesystem_identity(fixture_root)
    binary = args.binary.resolve()
    helper = shlex.quote(str(args.helper.resolve()))
    tools = inventory(args.path)
    paths = {name: entry['path'] for name, entry in tools.items()}
    records = []
    capabilities = {'uid': os.getuid(), 'gid': os.getgid(),
                    'euid': os.geteuid(), 'egid': os.getegid(),
                    'groups': os.getgroups(), 'permission_denial': os.geteuid() != 0,
                    'block_device': None, 'numeric_locale': None, 'utf8_locale': None,
                    'controlled_identities': args.controlled_identities,
                    'unequal_acl': args.unequal_acl,
                    'german_locale': None, 'gb18030_locale': None}
    if args.block_device:
        if not stat.S_ISBLK(args.block_device.stat().st_mode):
            parser.error('--block-device must name a block device')
        capabilities['block_device'] = str(args.block_device.resolve())
    if args.boundaries:
        previous = locale.setlocale(locale.LC_NUMERIC)
        try:
            for candidate in ('fr_FR.UTF-8', 'fr_FR.utf8'):
                try:
                    locale.setlocale(locale.LC_NUMERIC, candidate)
                except locale.Error:
                    continue
                if locale.localeconv()['decimal_point'] == ',':
                    capabilities['numeric_locale'] = candidate
                    break
        finally:
            locale.setlocale(locale.LC_NUMERIC, previous)
    if args.boundaries:
        previous = locale.setlocale(locale.LC_CTYPE)
        try:
            for candidate in ('en_US.UTF-8', 'en_US.utf8', 'C.UTF-8'):
                try:
                    locale.setlocale(locale.LC_CTYPE, candidate)
                except locale.Error:
                    continue
                if locale.nl_langinfo(locale.CODESET).lower().replace('-', '') == 'utf8':
                    capabilities['utf8_locale'] = candidate
                    break
        finally:
            locale.setlocale(locale.LC_CTYPE, previous)
        previous = locale.setlocale(locale.LC_ALL)
        try:
            for key, names in (
                    ('german_locale', ('de_DE.UTF-8', 'de_DE.utf8')),
                    ('gb18030_locale', ('zh_CN.GB18030', 'zh_CN.gb18030'))):
                for candidate in names:
                    try:
                        locale.setlocale(locale.LC_ALL, candidate)
                    except locale.Error:
                        continue
                    valid = (locale.localeconv()['decimal_point'] == ',' if key == 'german_locale'
                             else locale.nl_langinfo(locale.CODESET).lower() == 'gb18030')
                    if valid:
                        capabilities[key] = candidate
                        break
        finally:
            locale.setlocale(locale.LC_ALL, previous)
    selected = list(cases(paths, helper, args.echo_policy))
    limitations = []
    if args.boundaries:
        selected.extend(boundary_cases(helper, args.echo_policy,
                                       capabilities['numeric_locale'],
                                       capabilities['block_device'],
                                       capabilities['permission_denial']))
        selected.extend(capability_cases(paths, capabilities['utf8_locale']))
        selected.extend(environment_cases(paths, helper,
                         args.printf_faults.resolve() if args.printf_faults else None,
                         dict(german=capabilities['german_locale'], gb18030=capabilities['gb18030_locale'],
                              utf8=capabilities['utf8_locale']), args.controlled_identities, args.unequal_acl))
        environment = dict(platform=platform.platform(), capabilities=capabilities, filesystem=filesystem)
        limitations.extend(residual_limitations(environment, tools))
        for condition, available, reason in (
            ('U-035/allocation-injection', args.printf_faults, 'No test-only printf allocation helper supplied'),
            ('U-035/German-locale', capabilities['german_locale'], 'German numeric locale unavailable'),
            ('U-040/GB18030-locale', capabilities['gb18030_locale'], 'GB18030 multibyte locale unavailable'),
            ('U-037/controlled-environment', args.controlled_identities, 'Linux root ACL/credential/private-node fixtures not requested'),
            ('U-040/UTF-8-locale', capabilities['utf8_locale'], 'UTF-8 test locale unavailable'),
            ('U-035/locale-errors', capabilities['numeric_locale'], 'French numeric locale unavailable'),
            ('U-037/permission-denial', capabilities['permission_denial'], 'effective UID 0 bypasses mode-bit denial'),
            ('U-037/block-device', capabilities['block_device'], 'no explicit stat-only block-device witness supplied')):
            if not available:
                limitations.append(dict(condition=condition, reason=reason, owner='CSH-063',
                                        environment=environment, source=BASE +
                                        ('test.html' if condition.startswith('U-037') else 'V3_chap01.html'),
                                        executable=tools['test' if condition.startswith('U-037') else
                                                         'sed' if condition == 'U-040/GB18030-locale' else
                                                         'find' if condition == 'U-040/UTF-8-locale' else 'printf'],
                                        related_executable=tools['['] if condition.startswith('U-037') else None))
        for limitation in limitations:
            print('LIMITATION: ' + json.dumps(limitation), flush=True)
    totals = dict(passed=0, failed=0, gaps=0)
    for case in selected:
        for mode in case.get('modes', ('string', 'file', 'stdin')):
            name = case['name'] + ' (' + mode + ')'
            if case.get('requires') and not paths[case['requires']]:
                # ed is the documented image limitation. Losing another required
                # dependency is a failure, not a newly inferred capability skip.
                known = case['requires'] == 'ed' and platform.system() == 'Linux'
                totals['gaps' if known else 'failed'] += 1
                records.append({'name': name, 'verdict': 'GAP' if known else 'FAIL',
                                'reason': 'Missing host executable; CSH-056/U-034-host-ed'})
                print(('GAP' if known else 'FAIL') + ': host: ' + name + ' (missing executable)', flush=True)
                continue
            with tempfile.TemporaryDirectory(prefix='csh-host-', dir=fixture_root) as temporary:
                directory = Path(temporary)
                connection = None
                try:
                    try:
                        connection = setup(directory, case.get('input_files'))
                        controlled = (setup_controlled(directory, case['controlled_fixture'])
                                      if case.get('controlled_fixture') else None)
                    except (OSError, subprocess.CalledProcessError) as error:
                        # Unsupported ACL/filesystem operations are failed setup,
                        # never a passing assertion or an absent/stale record.
                        record = setup_failure(name, case, error)
                        records.append(record)
                        totals['failed'] += 1
                        print('FAIL: host: ' + name + ' (fixture setup)', flush=True)
                        continue
                    fixture = {'args': [], 'stdin': '', 'env': {'PATH': args.path}}
                    fixture['env'].update(case.get('env', {}))
                    if args.sanitizer:
                        fixture['env'].update({'ASAN_OPTIONS': 'halt_on_error=1' +
                                         (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                                         'UBSAN_OPTIONS': 'halt_on_error=1'})
                    if mode == 'pty':
                        fixture.update(transport='pty', steps=[], args=['-c', case['script']])
                    elif mode == 'string':
                        fixture['args'] = ['-c', case['script']]
                    elif mode == 'file':
                        (directory / 'script').write_text(case['script'])
                        fixture['args'] = ['script']
                    else:
                        fixture['stdin'] = case['script']
                    status, output, errors = smoke.capture(binary, fixture, directory, 5, 65536)
                    if mode == 'pty':
                        output = {'stdout': output['output'], 'stderr': b''}
                    if sanitizer_diagnostic(output):
                        errors.append('sanitizer diagnostic')
                    exec_boundary = None
                    if case.get('exec_boundary'):
                        try:
                            exec_boundary = json.loads((directory / 'exec-boundary.json').read_text())
                            if (exec_boundary['operand_string_bytes_with_nuls'] <= exec_boundary['ARG_MAX'] or
                                    exec_boundary['environment_bytes_with_nuls'] != 9):
                                errors.append('invalid exec boundary measurements')
                        except (OSError, ValueError, KeyError, TypeError) as error:
                            errors.append('missing/invalid exec boundary record: ' + str(error))
                    if controlled:
                        observed = (directory / 'controlled').stat()
                        if (observed.st_uid, observed.st_gid, oct(observed.st_mode), observed.st_rdev) != (
                                controlled['uid'], controlled['gid'], controlled['mode'], controlled['rdev']):
                            errors.append('controlled fixture changed unexpectedly')
                    actual_files = {}
                    for path, expected in case.get('files', {}).items():
                        target = directory / path
                        actual_files[path] = target.read_bytes() if target.exists() else None
                    ok = (not errors and matches_case(case, status, output) and
                          actual_files == case.get('files', {}))
                    gap = not ok and not errors and known_gap(case, status, output)
                    verdict = 'PASS' if ok else 'GAP' if gap else 'FAIL'
                    totals['passed' if ok else 'gaps' if gap else 'failed'] += 1
                    record = {'name': name, 'verdict': verdict, 'case': serial(case),
                              'controlled_fixture': controlled,
                              'exec_boundary': exec_boundary,
                              'invocation': fixture, 'actual': serial(dict(status=status,
                                  stdout=bytes(output['stdout']), stderr=bytes(output['stderr']),
                                  files=actual_files, errors=errors))}
                    records.append(record)
                    print(verdict + ': host: ' + name, flush=True)
                    if not ok:
                        print(json.dumps(record['actual']), flush=True)
                finally:
                    if connection is not None:
                        connection.close()
    # Query the filesystem that actually hosts fixtures, not the source checkout.
    with tempfile.TemporaryDirectory(prefix='csh-host-query-', dir=fixture_root) as temporary:
        directory = Path(temporary)
        filesystem_limits = {name: os.pathconf(directory, name) for name in
                             ('PC_NAME_MAX', 'PC_PATH_MAX', 'PC_PIPE_BUF')}
        query = dict(args=['limits'], stdin='', env={'PATH': args.path})
        if args.sanitizer:
            query['env'].update(ASAN_OPTIONS='halt_on_error=1' +
                               (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                               UBSAN_OPTIONS='halt_on_error=1')
        status, output, errors = smoke.capture(args.helper.resolve(), query, directory, 5, 65536)
        if status != 0 or errors or output['stderr']:
            raise RuntimeError('child resource query failed: ' + repr((status, output, errors)))
        child_resources = json.loads(bytes(output['stdout']))
        filesystem_query_path = str(directory)
    result = {'platform': platform.platform(), 'libc': platform.libc_ver(), 'path': args.path, 'inventory': tools,
              'capabilities': capabilities, 'limitations': limitations,
              'echo_policy': args.echo_policy,
              'echo_policy_source': {
                  'darwin': 'https://github.com/apple-oss-distributions/shell_cmds/blob/main/echo/echo.c',
                  'gnu': 'https://github.com/coreutils/coreutils/blob/v9.1/src/echo.c',
                  'busybox-fancy': 'https://git.busybox.net/busybox/tree/coreutils/echo.c?h=1_35_0',
              }[args.echo_policy],
              'host_limits': {name: os.sysconf(name) for name in
                              ('SC_ARG_MAX', 'SC_OPEN_MAX', 'SC_LINE_MAX')},
              'filesystem_limits': filesystem_limits, 'filesystem': filesystem,
              'filesystem_query_path': filesystem_query_path,
              'child_resources': child_resources,
              'binary_sha256': sha(binary), 'helper_sha256': sha(args.helper),
              'printf_faults': ({'path': str(args.printf_faults.resolve()), 'sha256': sha(args.printf_faults)}
                                if args.printf_faults else None),
              'limits': {'timeout_seconds': 5, 'combined_output_bytes': 65536,
                         'child_resources': 'smoke.child_limits'},
              'setup': 'tests/host_utilities.py:setup', 'totals': totals, 'cases': records}
    if platform.system() == 'Linux' and shutil.which('dpkg-query'):
        result['package_versions'] = subprocess.check_output(
            ['dpkg-query', '-W', '-f=${Package} ${Version}\n'], text=True)
    if args.record:
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(result, indent=2) + '\n')
    print('Result: ' + ', '.join(str(value) + ' ' + name for name, value in totals.items()))
    return int(bool(totals['failed'] or (args.strict_gaps and totals['gaps'])))


if __name__ == '__main__':
    raise SystemExit(main())
