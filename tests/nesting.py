#!/usr/bin/env python3
"""CSH-066 finite depth witnesses and actual stack-resource failures."""
import argparse
import os
from pathlib import Path
import resource
import subprocess
import tempfile

from smoke import kill_group


def run(binary, directory, source, mode, stack=None, descriptors=1024):
    def limits():
        # Source recursion deliberately retains more than the ordinary
        # runner's 64 descriptors; preserve bounded CPU/output/core limits.
        for kind, value in ((resource.RLIMIT_CORE, 0), (resource.RLIMIT_CPU, 31),
                            (resource.RLIMIT_FSIZE, 65536), (resource.RLIMIT_NOFILE, descriptors)):
            soft, hard = resource.getrlimit(kind)
            bound = min([value] + [n for n in (soft, hard) if n != resource.RLIM_INFINITY])
            resource.setrlimit(kind, (bound, bound))
        if stack is not None:
            resource.setrlimit(resource.RLIMIT_STACK, (stack, stack))
    script = directory / 'input.sh'
    script.write_text(source + '\n')
    args = ['-c', source] if mode == 'string' else [str(script)] if mode == 'file' else []
    environment = dict(os.environ, LC_ALL='C', ENV='', HOME=str(directory))
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen([str(binary), *args], cwd=directory,
            env=environment, stdin=subprocess.PIPE, stdout=output, stderr=errors,
            start_new_session=True, preexec_fn=limits)
        try:
            process.communicate((source + '\n').encode() if mode == 'stdin' else b'', timeout=30)
            output.seek(0); errors.seek(0)
            return process.returncode, output.read(65537), errors.read(65537)
        finally:
            kill_group(process)
            process.wait(timeout=5)


def cases():
    yield '512 braces', '{ ' * 512 + 'printf ok; ' + '}; ' * 512, b'ok'
    # Each mixed layer contains a list and a compound; no subprocess per level.
    body = 'printf ok; '
    wrappers = [('{ ', '}; '), ('if :; then ', 'fi; '),
                ('for x in once; do ', 'done; '), ('case x in x) ', ';; esac; ')]
    for index in range(192):
        prefix, suffix = wrappers[index % len(wrappers)]
        body = prefix + body + suffix
    yield '192 mixed compounds', body, b'ok'
    yield '512 parameters', 'printf %s ' + '${absent:-' * 512 + 'ok' + '}' * 512, b'ok'
    yield '1024 arithmetic parentheses', 'printf %s "$(( ' + '(' * 1024 + '1' + ')' * 1024 + ' ))"', b'1'
    yield '256 arithmetic checkpoints', 'printf %s ' + '$(( ' * 256 + '1' + ' ))' * 256, b'1'
    yield '256 unary operators', 'printf %s "$(( ' + '! ' * 256 + '1 ))"', b'1'
    yield '160 functions', 'f() { case $1 in 0) printf ok;; *) f $(($1-1));; esac; }; f 160', b'ok'
    yield '256 command wrappers', 'command ' * 256 + 'printf ok', b'ok'
    yield '160 eval calls', "n=160; x='case $n in 0) printf ok;; *) n=$((n-1)); eval \"$x\";; esac'; eval \"$x\"", b'ok'
    yield '160 dot scripts', 'n=160; . ./source.sh', b'ok'
    body = 'printf ok'
    for _ in range(129):
        body = 'printf %s "$(' + body + ')"'
    yield '129 command substitutions', body, b'ok'
    yield '512 lazy parameters', "set=yes; printf %s " + '${set:-' * 512 + '$(touch effect)' + '}' * 512, b'yes'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve()
    count = 0
    with tempfile.TemporaryDirectory(prefix='cshell-nesting-') as temporary:
        directory = Path(temporary)
        (directory / 'source.sh').write_text('case $n in 0) printf ok;; *) n=$((n-1)); . ./source.sh;; esac\n')
        for name, source, expected in cases():
            for mode in ('string', 'file', 'stdin'):
                actual = run(binary, directory, source, mode)
                assert actual == (0, expected, b''), (name, mode, actual)
                assert not (directory / 'effect').exists(), name
                count += 1
                print(f'PASS: {name} ({mode})', flush=True)
        # Same syntax fails with little actual stack and succeeds with more.
        source = '{ ' * 192 + ': >effect; ' + '}; ' * 192
        for mode in ('string', 'file', 'stdin'):
            status, output, errors = run(binary, directory, source, mode, 256 * 1024)
            assert status == 1 and output == b'' and b'parser stack exhausted' in errors, (status, output, errors)
            assert not (directory / 'effect').exists()
            assert run(binary, directory, source, mode, 8 * 1024 * 1024) == (0, b'', b'')
            assert (directory / 'effect').read_bytes() == b''
            (directory / 'effect').unlink()
            count += 1
            print(f'PASS: actual stack limit changes capacity ({mode})', flush=True)
        status, output, errors = run(binary, directory,
            'n=160; . ./source.sh; printf unintended', 'string', descriptors=64)
        assert status == 1 and output == b'' and b'Too many open files' in errors, (status, output, errors)
        count += 1
        print('PASS: dot recursion exhausts actual descriptors safely', flush=True)
        for name, source in [('function', 'f() { f; }; f'),
                             ('eval', "x='eval \"$x\"'; eval \"$x\"")]:
            status, output, errors = run(binary, directory, source, 'string', 512 * 1024)
            assert status == 1 and output == b'' and b'stack exhausted' in errors, (name, status, output, errors)
            assert b'AddressSanitizer' not in errors and b'runtime error:' not in errors, errors
            count += 1
            print(f'PASS: {name} exhausts actual stack safely', flush=True)
    print(f'{count} nesting/resource witnesses passed')


if __name__ == '__main__':
    main()
