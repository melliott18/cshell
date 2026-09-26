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
import subprocess
import tempfile

import smoke
from host_utility_cases import HOSTS, INTRINSICS, cases


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inventory():
    result = {}
    for name in HOSTS:
        path = shutil.which(name, path=os.defpath)
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


def setup(directory):
    contents = {'data': b'one\ntwo\n', 'edit': b'edit\n', 'remove': b'',
                'first': b'first\n', 'second': b'second\n', 'tree/leaf': b'',
                'old': b'', 'new': b'', 'setuid': b'', 'setgid': b'',
                'executable': b'', 'high': bytes(range(128, 256)),
                'binary': bytes(range(256))}
    for name, content in contents.items():
        path = directory / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(content)
    os.utime(directory / 'old', (1000000000, 1000000000))
    os.utime(directory / 'new', (1000000002, 1000000002))
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


def serial(value):
    if isinstance(value, bytes):
        return {'hex': value.hex()}
    if isinstance(value, dict):
        return {key: serial(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [serial(item) for item in value]
    return value


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('helper', type=Path)
    parser.add_argument('--record', type=Path)
    parser.add_argument('--strict-gaps', action='store_true')
    parser.add_argument('--sanitizer', action='store_true',
                        help='Set ASan/UBSan in the actual case environment; disable Linux leak scanning')
    args = parser.parse_args()
    binary = args.binary.resolve()
    helper = shlex.quote(str(args.helper.resolve()))
    tools = inventory()
    paths = {name: entry['path'] for name, entry in tools.items()}
    records = []
    totals = dict(passed=0, failed=0, gaps=0)
    for case in cases(paths, helper):
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
            with tempfile.TemporaryDirectory(prefix='csh-host-') as temporary:
                directory = Path(temporary)
                connection = setup(directory)
                try:
                    fixture = {'args': [], 'stdin': '', 'env': {}}
                    if args.sanitizer:
                        fixture['env'] = {'ASAN_OPTIONS': 'halt_on_error=1' +
                                         (':detect_leaks=0' if platform.system() == 'Linux' else ''),
                                         'UBSAN_OPTIONS': 'halt_on_error=1'}
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
                    actual_files = {}
                    for path, expected in case.get('files', {}).items():
                        target = directory / path
                        actual_files[path] = target.read_bytes() if target.exists() else None
                    ok = (not errors and match(case['status'], status) and
                          match(case['stdout'], bytes(output['stdout'])) and
                          match(case['stderr'], bytes(output['stderr'])) and
                          actual_files == case.get('files', {}))
                    gap = not ok and not errors and known_gap(case, status, output)
                    verdict = 'PASS' if ok else 'GAP' if gap else 'FAIL'
                    totals['passed' if ok else 'gaps' if gap else 'failed'] += 1
                    record = {'name': name, 'verdict': verdict, 'case': serial(case),
                              'invocation': fixture, 'actual': serial(dict(status=status,
                                  stdout=bytes(output['stdout']), stderr=bytes(output['stderr']),
                                  files=actual_files, errors=errors))}
                    records.append(record)
                    print(verdict + ': host: ' + name, flush=True)
                    if not ok:
                        print(json.dumps(record['actual']), flush=True)
                finally:
                    connection.close()
    result = {'platform': platform.platform(), 'path': os.defpath, 'inventory': tools,
              'binary_sha256': sha(binary), 'helper_sha256': sha(args.helper),
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
