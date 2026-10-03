#!/usr/bin/env python3
"""CSH-077 real PTY data effects, descriptor priority and private sessions."""
import argparse
import fcntl
import glob
import json
import os
from pathlib import Path
import platform
import select
import shlex
import shutil
import stat
import struct
import subprocess
import tempfile
import termios
import time

from host_terminal import BASE, MODES, capture, inventory
from host_utilities import serial, sha, source_identity, sanitizer_diagnostic
from pty_harness import open_terminal


def environment(search_path, directory):
    env = dict(PATH=search_path, LC_ALL='C', LANG='C', TZ='UTC0', HOME=str(directory))
    env.update({key: os.environ[key] for key in ('ASAN_OPTIONS', 'UBSAN_OPTIONS', 'MallocNanoZone') if key in os.environ})
    return env


def invoke(binary, providers, name, args, mode, directory, env, terminals, descriptors=(0,), **kwargs):
    """Apply terminal stdin at utility dispatch, including shell source on stdin."""
    master, slave = terminals[0]
    selected = providers[name]['path']
    if not selected:
        raise OSError('missing provider: ' + name)
    code = shlex.join([selected if mode == 'exec' else name, *map(str, args)])
    if 0 in descriptors:
        code += ' < ' + shlex.quote(os.ttyname(slave))
    if mode == 'exec':
        code = 'exec ' + code
    data = b''
    if mode == 'direct':
        argv = [selected, *map(str, args)]
    elif mode == 'file':
        (directory / 'script').write_text(code + '\n')
        (directory / 'script').chmod(0o644)
        argv = [str(binary), str(directory / 'script')]
    elif mode == 'stdin':
        argv, data = [str(binary)], (code + '\n').encode()
    else:
        argv = [str(binary), '-c', code]
    mapping = {fd: terminals[fd][1] for fd in descriptors if fd != 0 or mode == 'direct'}
    extra = {'terminal' + str(i): t[0] for i, t in enumerate(terminals[1:], 1)}
    with open(os.devnull, 'rb') as source:
        result = capture(argv, directory, env, master, slave, source, data=data,
                         fd_map=mapping, extra_terminals=extra, **kwargs)
    result['argv'] = argv
    return result


def received(fd, expected_length, timeout=1):
    """Bounded independent PTY reader; capture extras, not just an expected prefix."""
    data = bytearray()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        wait = min(.02 if len(data) >= expected_length else .1, deadline - time.monotonic())
        if select.select([fd], [], [], wait)[0]:
            data.extend(os.read(fd, 65536))
        elif len(data) >= expected_length:
            break
    return bytes(data)


def data_cases():
    yield 'icrnl', ['icanon', '-echo', 'icrnl', '-igncr', '-inlcr'], b'alpha\r', b'alpha\n', 'input'
    yield 'inlcr', ['-icanon', 'min', '1', 'time', '0', '-echo', '-icrnl', '-igncr', 'inlcr'], b'A\nB', b'A\rB', 'input'
    yield 'igncr', ['icanon', '-echo', 'igncr', '-icrnl'], b'A\rB\n', b'AB\n', 'input'
    yield 'eight-bit', ['-icanon', 'min', '1', 'time', '0', '-echo', '-istrip'], b'A\x80\xff', b'A\x80\xff', 'input'
    yield 'istrip', ['-icanon', 'min', '1', 'time', '0', '-echo', 'istrip'], b'A\xc2\xe1', b'ABa', 'input'
    yield 'erase', ['icanon', '-echo', 'erase', '^H'], b'ab\x08c\n', b'ac\n', 'input'
    yield 'kill', ['icanon', '-echo', 'kill', '^U'], b'old\x15new\n', b'new\n', 'input'
    yield 'eof', ['icanon', '-echo', 'eof', '^D'], b'last\x04', b'last', 'input'
    yield 'echo', ['icanon', 'echo', '-opost'], b'echo\n', b'echo\n', 'echo'
    yield 'no-echo', ['icanon', '-echo', '-echonl'], b'quiet\n', b'', 'echo'
    yield 'no-opost', ['-opost'], b'A\n\x80\xff', b'A\n\x80\xff', 'output'


def check_command(actual, stdout=b'', status=0):
    errors = list(actual['failures'])
    if actual['status'] != status:
        errors.append('status mismatch')
    if actual['stdout'] != stdout or actual['stderr'] or any(v for k, v in actual.items() if k.startswith('terminal')):
        errors.append('unexpected command output')
    if sanitizer_diagnostic({k: v for k, v in actual.items() if isinstance(v, bytes)}):
        errors.append('sanitizer diagnostic')
    return errors


def run(binary, providers, directory, env, rows):
    def retain(name, mode, actual, failures, **details):
        rows.append(dict(name=name, mode=mode, verdict='FAIL' if failures else 'PASS',
                         actual=actual, failures=failures, **details))
        if failures:
            print('FAIL:', name, mode, failures, flush=True)

    for mode in MODES:
        for name, args, payload, expected, direction in data_cases():
            master, slave = open_terminal()
            try:
                actual = invoke(binary, providers, 'stty', args, mode, directory, env, [(master, slave)])
                failures = check_command(actual)
                before = termios.tcgetattr(slave)
                os.set_blocking(slave, False)
                sent = slave if direction == 'output' else master
                read = slave if direction == 'input' else master
                if os.write(sent, payload) != len(payload):
                    failures.append('short PTY input write')
                got = received(read, len(expected))
                if got != expected:
                    failures.append('PTY data mismatch')
                retain('stty/data-' + name, mode, actual, failures, payload=payload,
                       expected=expected, received=got, termios=before, source=BASE + 'stty.html')
            finally:
                os.close(slave); os.close(master)
        for descriptors in ((0, 1, 2), (1, 2)):
            for allow in (False, True):
                terminals = []
                try:
                    for _ in range(3):
                        terminals.append(open_terminal())
                    initial = 0o600 if allow else 0o620
                    for _, slave in terminals:
                        os.fchmod(slave, initial)
                    actual = invoke(binary, providers, 'mesg', ['y' if allow else 'n'], mode,
                                    directory, env, terminals, descriptors)
                    permissions = [stat.S_IMODE(os.fstat(slave).st_mode) for _, slave in terminals]
                    failures = check_command(actual, status=0 if allow else 1)
                    first = min(descriptors)
                    for index, permission in enumerate(permissions):
                        if index == first:
                            if bool(permission & 0o022) != allow:
                                failures.append('first terminal not changed')
                        elif permission != initial:
                            failures.append('later terminal changed')
                    retain('mesg/priority-' + ''.join(map(str, descriptors)) + ('-y' if allow else '-n'),
                           mode, actual, failures, permissions=permissions, initial=initial,
                           source=BASE + 'mesg.html')
                finally:
                    for master, slave in terminals:
                        os.close(slave); os.close(master)
        terminals = []
        try:
            for _ in range(2):
                terminals.append(open_terminal())
            first, second = [os.ttyname(t[1]).removeprefix('/dev/') for t in terminals]
            records = directory / 'sessionsx'
            records.write_bytes(b'')
            subprocess.run([str(Path('build/tests/host_session_records').resolve()), str(records), first, second],
                           check=True, capture_output=True, timeout=5)
            for enabled in (False, True):
                for _, slave in terminals:
                    os.fchmod(slave, 0o620 if enabled else 0o600)
                actual = invoke(binary, providers, 'who', ['-T', str(records)], mode, directory, env, terminals)
                lines = [line.split() for line in actual['stdout'].splitlines()]
                expected = [[b'csh077a', b'+' if enabled else b'-', first.encode(), b'Jan', b'1', b'00:00'],
                            [b'csh077b', b'+' if enabled else b'-', second.encode(), b'Jan', b'1', b'00:00']]
                failures = check_command(actual, stdout=actual['stdout'])
                if lines != expected:
                    failures.append('who terminal permission/name/time mismatch')
                retain('who/terminal-state-' + ('y' if enabled else 'n'), mode, actual, failures,
                       expected_fields=expected, source=BASE + 'who.html')
            actual = invoke(binary, providers, 'who', ['-m', str(records)], mode, directory, env, terminals)
            failures = check_command(actual, stdout=actual['stdout'])
            expected = [[b'csh077a', first.encode(), b'Jan', b'1', b'00:00']]
            if [line.split() for line in actual['stdout'].splitlines()] != expected:
                failures.append('who selected a different terminal')
            retain('who/current-terminal', mode, actual, failures, expected_fields=expected, source=BASE + 'who.html')
        finally:
            for master, slave in terminals:
                os.close(slave); os.close(master)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--record', required=True, type=Path)
    args = parser.parse_args()
    if os.getsid(0) != os.getpid():
        os.setsid()
    inputs = source_identity()
    providers, packages = inventory(args.path)
    rows = []
    with tempfile.TemporaryDirectory(prefix='csh077-effects-') as temp:
        directory = Path(temp)
        env = environment(args.path, directory)
        try:
            run(args.binary.resolve(), providers, directory, env, rows)
        except (OSError, ValueError, termios.error, subprocess.SubprocessError) as error:
            rows.append(dict(name='setup', verdict='FAIL', reason=str(error),
                stdout=getattr(error, 'stdout', None), stderr=getattr(error, 'stderr', None)))
        report = dict(platform=platform.platform(), path=args.path, environment=env,
                      uid=os.getuid(), gid=os.getgid(), providers=providers, packages=packages,
                      binary_sha256=sha(args.binary), source_identity=inputs, command=os.sys.argv,
                      cases=rows, capabilities=dict(owned_ptys=True, private_session_records=True,
                      physical_hardware_supplied=False, physical_probe='not performed',
                      physical_condition='U-040/stty-physical-terminal', residual_owner='CSH-081'))
    if source_identity() != inputs:
        rows.append(dict(name='source-stability', verdict='FAIL', reason='source changed during run'))
    report['fixture_directory_removed'] = not directory.exists()
    report['totals'] = dict(passed=sum(r['verdict']=='PASS' for r in rows), failed=sum(r['verdict']=='FAIL' for r in rows))
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(serial(report), indent=2) + '\n')
    print(json.dumps(report['totals']))
    return int(bool(report['totals']['failed']) or not rows or not report['fixture_directory_removed'])


if __name__ == '__main__':
    raise SystemExit(main())
