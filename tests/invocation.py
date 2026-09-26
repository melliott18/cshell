#!/usr/bin/env python3
"""CSH-046 public-runtime invocation/descriptor probes (not module fixtures).

See docs/invocation-syntax-evidence.md for normative clauses and policies.
Every child has a new session, resource/output limits and a five-second deadline.
The parent retains input descriptors to inspect the shared flags after exit.
"""
import argparse
import errno
import fcntl
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import tempfile
import termios
import time

import smoke

TIMEOUT = 5
LIMIT = 65536


def environment(directory):
    return dict(PATH=os.defpath, HOME=str(directory), TMPDIR=str(directory),
                LC_ALL='C', LANG='C', TZ='UTC0', PS1='$ ', PS2='> ')


def run(binary, directory, args=(), data=b'', *, argv0='csh-046-name',
        input_fd=None, error_fd=None, identity=None, ready=None):
    def prepare():
        smoke.child_limits(TIMEOUT, LIMIT)
        if identity == 'uid':
            os.setresuid(0, 65534, 0)
            assert os.getuid() != os.geteuid()
        elif identity == 'gid':
            os.setresgid(0, 65534, 0)
            assert os.getgid() != os.getegid()

    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(
            [argv0, *args], executable=str(binary), cwd=directory,
            env=environment(directory), stdin=input_fd if input_fd is not None else subprocess.PIPE,
            stdout=output, stderr=error_fd if error_fd is not None else errors,
            start_new_session=True, preexec_fn=prepare)
        deadline = time.monotonic() + TIMEOUT
        try:
            if ready:
                # A ready line emitted by the real shell precedes the utility read.
                while os.fstat(output.fileno()).st_size < len(b'ready\n'):
                    if process.poll() is not None:
                        raise AssertionError('shell exited before ready')
                    if time.monotonic() >= deadline:
                        raise AssertionError('ready deadline expired')
                    time.sleep(0.005)
                ready()
            process.communicate(data if input_fd is None else None,
                                timeout=max(0.001, deadline - time.monotonic()))
            output.seek(0); errors.seek(0)
            stdout, stderr = output.read(LIMIT + 1), errors.read(LIMIT + 1)
            assert len(stdout) <= LIMIT and len(stderr) <= LIMIT, 'output limit exceeded'
            return process.returncode, stdout, stderr
        finally:
            smoke.kill_group(process)
            process.wait(timeout=2)
            if process.stdin is not None:
                process.stdin.close()


def expect(actual, stdout=b'', status=0, stderr=b''):
    assert actual == (status, stdout, stderr), repr(actual)


def terminal_pair():
    master, slave = pty.openpty()
    attrs = termios.tcgetattr(slave)
    attrs[3] &= ~termios.ECHO
    attrs[1] &= ~termios.OPOST
    termios.tcsetattr(slave, termios.TCSANOW, attrs)
    return master, slave


def drain(fd):
    data = b''
    while select.select([fd], [], [], 0)[0]:
        try:
            chunk = os.read(fd, LIMIT + 1 - len(data))
        except OSError as error:
            if error.errno == errno.EIO:
                break
            raise
        if not chunk:
            break
        data += chunk
        assert len(data) <= LIMIT, 'terminal output limit exceeded'
    return data


def mappings(binary, directory):
    script = 'printf "<%s>\\n" "$0" "$#" "$@"\n'
    path = directory / 'script'
    path.write_text(script); path.chmod(0o600)
    dash = directory / '-script'
    dash.write_text(script); dash.chmod(0o600)
    for name, args, data, zero, parameters in (
        ('implicit stdin', [], script.encode(), 'csh-046-name', []),
        ('standalone dash stdin', ['-'], script.encode(), 'csh-046-name', []),
        ('explicit stdin operands', ['-s', 'one', '-two', ''], script.encode(), 'csh-046-name', ['one', '-two', '']),
        ('stdin dash operand', ['-s', '-', 'one'], script.encode(), 'csh-046-name', ['one']),
        ('command default name', ['-c', script], b'', 'csh-046-name', []),
        ('command explicit name', ['-c', script, 'name', 'one', '-two', ''], b'', 'name', ['one', '-two', '']),
        ('command empty name', ['-c', script, '', 'one'], b'', '', ['one']),
        ('command standalone dash', ['-c', '-', script, 'name'], b'', 'name', []),
        ('slashless non-executable script', ['script', 'one', '-two', ''], b'', 'script', ['one', '-two', '']),
        ('relative slash script', ['./script', 'one'], b'', './script', ['one']),
        ('absolute slash script', [str(path), 'one'], b'', str(path), ['one']),
        ('standalone dash script', ['-', '-script', 'one'], b'', '-script', ['one']),
        ('double dash script', ['--', '-script', 'one'], b'', '-script', ['one']),
    ):
        def check(args=args, data=data, zero=zero, parameters=parameters):
            expected = ''.join(f'<{v}>\n' for v in [zero, str(len(parameters)), *parameters]).encode()
            expect(run(binary, directory, args, data), expected)
        yield 'SH-002 ' + name, check


def path_only(binary, directory):
    folder = directory / 'bin'; folder.mkdir()
    target = folder / 'path-only'; target.write_text('printf wrong >effect\n'); target.chmod(0o755)
    # Invoke via the public shell, changing PATH without changing the process runner.
    script = f'PATH={folder}; export PATH; exec {binary} path-only'
    expect(run(binary, directory, ['-c', script]), status=127,
           stderr=f'cshell: path-only: 1:1: cannot open script: {os.strerror(errno.ENOENT)}\n'.encode())
    assert not (directory / 'effect').exists()


def shared_binary(binary, directory, kind):
    # NUL/non-character bytes occur only after the character-only parsed prefix.
    payload = b'\x00\xffpayload\n'
    # read consumes exactly its data line; parser then resumes at the following command.
    expect(run(binary, directory, data=b'read value\ntext\nprintf "<%s>\\n" "$value"\n'), b'<text>\n')
    content = b'/bin/cat\n' + payload
    if kind == 'pipe':
        expect(run(binary, directory, data=content), payload)
    else:
        with tempfile.TemporaryFile() as source:
            source.write(content); source.seek(0)
            expect(run(binary, directory, input_fd=source), payload)
            assert source.tell() == len(content)


def detection(binary, directory, stdin_tty, stderr_tty, mode):
    master, slave = terminal_pair()
    script = 'case $- in *i*) printf interactive;; *) printf batch;; esac\nexit 7\n'
    try:
        args = ['+m']  # No controlling-terminal job setup is needed for isatty.
        if mode == 'forced': args += ['-i']
        if mode == 'string': args += ['-c', script]
        if mode == 'file':
            (directory / 'detect').write_text(script); args += ['detect']
        stdin_mode = mode in ('stdin', 'forced')
        if stdin_tty and stdin_mode: os.write(master, script.encode())
        interactive = mode == 'forced' or (stdin_mode and stdin_tty and stderr_tty)
        actual = run(binary, directory, args, script.encode() if stdin_mode else b'',
                     input_fd=slave if stdin_tty else None,
                     error_fd=slave if stderr_tty else None)
        prompts = b'$ $ ' if interactive and stdin_mode else b''
        expect(actual, b'interactive' if interactive else b'batch', 7,
               b'' if stderr_tty else prompts)
        assert drain(master) == (prompts if stderr_tty else b'')
    finally:
        os.close(master); os.close(slave)


def nonblocking(binary, directory, kind, mode):
    if kind == 'terminal':
        writer, reader = terminal_pair()
    elif kind == 'fifo':
        path = directory / 'fifo'; os.mkfifo(path)
        reader = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        writer = os.open(path, os.O_WRONLY | os.O_NONBLOCK)
    else:
        reader, writer = os.pipe()
    try:
        old = fcntl.fcntl(reader, fcntl.F_GETFL)
        fcntl.fcntl(reader, fcntl.F_SETFL, old | os.O_NONBLOCK)
        initial = fcntl.fcntl(reader, fcntl.F_GETFL)
        script = 'printf "ready\\n"\nread value\nprintf "%s\\n" "$value"\nexit 7\n'
        if mode == 'stdin':
            # The read command shares stdin; place its payload directly after it.
            os.write(writer, b'printf "ready\\n"\nread value\n')
            args = []
        elif mode == 'string': args = ['-c', script]
        else:
            (directory / 'source').write_text(script); args = ['source']
        observed = []
        def ready():
            observed.append(fcntl.fcntl(reader, fcntl.F_GETFL))
            data = b'payload\n'
            if mode == 'stdin': data += b'printf "%s\\n" "$value"\nexit 7\n'
            os.write(writer, data)
        actual = run(binary, directory, args, input_fd=reader, ready=ready)
        final = fcntl.fcntl(reader, fcntl.F_GETFL)
        assert observed == [initial & ~os.O_NONBLOCK], ('during read', initial, observed)
        assert final == initial & ~os.O_NONBLOCK, ('after exit', initial, final)
        expect(actual, b'ready\npayload\n', 7)
    finally:
        os.close(reader); os.close(writer)


def nesting(binary, directory, depth):
    # Braces avoid spawning a process at every level, isolating parser depth.
    script = '{ ' * depth + ': >effect; ' + '}; ' * depth + '\n'
    actual = run(binary, directory, ['-c', script])
    if depth == 127:
        expect(actual)
        assert (directory / 'effect').read_bytes() == b''
    else:
        status, stdout, stderr = actual
        assert status == 2 and stdout == b'', actual
        diagnostic = (b'invalid or excessively nested execution tree' if depth == 128
                      else b'parser nesting limit exceeded')
        assert diagnostic in stderr, actual
        assert not (directory / 'effect').exists()


def independent_stdin(binary, directory, mode, closed):
    script = 'printf "okay\\n"\n'
    if mode == 'file':
        (directory / 'independent').write_text(script)
        args = ['independent']
    else:
        args = ['-c', script]
    if closed:
        # Redirection in an outer cshell closes fd 0 before the tested exec.
        import shlex
        command = 'exec ' + ' '.join(shlex.quote(x) for x in [str(binary), *args]) + ' <&-'
        expect(run(binary, directory, ['-c', command]), b'okay\n')
    else:
        with tempfile.TemporaryFile() as source:
            flags = fcntl.fcntl(source, fcntl.F_GETFL) | os.O_NONBLOCK
            fcntl.fcntl(source, fcntl.F_SETFL, flags)
            flags = fcntl.fcntl(source, fcntl.F_GETFL)
            expect(run(binary, directory, args, input_fd=source), b'okay\n')
            assert fcntl.fcntl(source, fcntl.F_GETFL) == flags


def alias_new_shell(binary, directory):
    import shlex
    script = "alias private_alias='printf inherited'\n" + shlex.quote(str(binary)) + " -c 'alias private_alias'\n"
    expect(run(binary, directory, ['-c', script]), status=1,
           stderr=b'alias: private_alias: not found\n')


def cases(binary, directory):
    yield from mappings(binary, directory)
    yield 'LEX-006/U-017 aliases not inherited by new invocation', lambda: alias_new_shell(binary, directory)
    for mode in ('string', 'file'):
        for closed in (False, True):
            yield f'SH-007 independent {mode} stdin closed={closed}', lambda m=mode, c=closed: independent_stdin(binary, directory, m, c)
    yield 'SH-003 PATH-only negative (D-001)', lambda: path_only(binary, directory)
    for kind in ('pipe', 'regular file'):
        yield 'SH-001/006 binary tail ' + kind, lambda kind=kind: shared_binary(binary, directory, kind)
    for mode in ('stdin', 'forced', 'string', 'file'):
        for input_tty in (False, True):
            for error_tty in (False, True):
                yield f'SH-004 {mode} stdin-tty={input_tty} stderr-tty={error_tty}', lambda m=mode, i=input_tty, e=error_tty: detection(binary, directory, i, e, m)
    for kind in ('pipe', 'fifo', 'terminal'):
        for mode in ('stdin', 'string', 'file'):
            # Separate directories avoid FIFO/path reuse between probes.
            def check(kind=kind, mode=mode):
                with tempfile.TemporaryDirectory(dir=directory) as temporary:
                    nonblocking(binary, Path(temporary), kind, mode)
            yield f'SH-007 nonblocking {kind} ({mode})', check
    for depth in (127, 128, 129):
        def check(depth=depth):
            with tempfile.TemporaryDirectory(dir=directory) as temporary:
                nesting(binary, Path(temporary), depth)
        yield f'GRAM-005 parser guard depth {depth}', check
    for identity in ('uid', 'gid'):
        def check(identity=identity):
            script = 'case $- in *i*) printf interactive;; esac; exit 7'
            expect(run(binary, directory, ['-ic', script], identity=identity), b'interactive', 7)
        yield 'SH-004 unequal ' + identity + ' accepts -i (D-001)', check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    args = parser.parse_args()
    passed = failed = skipped = 0
    with tempfile.TemporaryDirectory(prefix='cshell-invocation-') as temporary:
        directory = Path(temporary); directory.chmod(0o755)
        for name, check in cases(args.binary.resolve(), directory):
            if 'unequal' in name and not (sys.platform == 'linux' and os.geteuid() == 0):
                print('SKIP:', name, ': requires Linux root setresuid/setresgid; owner CSH-046; Docker root runs it')
                skipped += 1; continue
            try:
                check()
            except (AssertionError, OSError, subprocess.SubprocessError) as error:
                failed += 1; print('FAIL:', name, repr(error), flush=True)
            else:
                passed += 1; print('PASS:', name, flush=True)
    print(f'Result: {passed} passed, {failed} failed, {skipped} skipped')
    return bool(failed)


if __name__ == '__main__':
    sys.exit(main())
