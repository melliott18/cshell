#!/usr/bin/env python3
"""CSH-055 public-runtime descriptor and unrecoverable command-read witnesses."""
import errno
import os
from pathlib import Path
import shlex
import sys
import tempfile
from execute import bounded_run

binary, fault, helper = (str(Path(p).resolve()) for p in sys.argv[1:])
checked = 0
with tempfile.TemporaryDirectory(prefix='cshell-contracts-') as temporary:
    temporary = str(Path(temporary).resolve())
    cwd = Path(temporary)
    env = dict(PATH=os.defpath, HOME=temporary, TMPDIR=temporary, LC_ALL='C')
    if sys.platform == 'darwin':
        env['MallocNanoZone'] = '0'

    def run(argv, *, stdout=b'', stderr=b'', status=0, extra=None):
        global checked
        result = bounded_run(argv, cwd=temporary, env=dict(env, **(extra or {})), timeout=5)
        assert (result.returncode, result.stdout, result.stderr) == (status, stdout, stderr), result
        checked += 1

    # No-name redirections and builtin restoration run before direct/PATH exec.
    # The observer checks inherited O_APPEND/O_RDWR/FD flags and exact argv[0].
    for mask in range(8):
        for mode in ('string', 'file'):
            for lookup in ('direct', 'PATH'):
                (cwd / 'inherited').write_text('seed\n')
                if not (cwd / 'observer').exists():
                    os.symlink(helper, cwd / 'observer')
                command = helper if lookup == 'direct' else 'observer'
                script = (': >redirect; : 8>alternate; : 8<&-; pwd >builtin; '
                          f'PATH=. {shlex.quote(command)} inspect-inherited {shlex.quote(command)} {mask}; '
                          'result=$?; printf "%s\\n" "$result" >status; exit "$result"\n')
                (cwd / 'script').write_text(script)
                args = ['-c', script] if mode == 'string' else ['script']
                run([helper, 'launch-fds', str(mask), binary, *args])
                assert (cwd / 'inherited').read_bytes() == b'seed\ninherited-ok\n'
                assert (cwd / 'status').read_bytes() == b'0\n'
                assert (cwd / 'redirect').read_bytes() == b''
                assert (cwd / 'builtin').read_text() == temporary + '\n'

    trap = 'trap \'printf "exit:%s\\n" "$?"\' EXIT\n'
    # Failure after a full command plus ';' has been read into the partial line,
    # and after a complete line inside a not-yet-complete compound command.
    prefixes = ('printf forbidden; ', '{\nprintf forbidden\n')
    for prefix in prefixes:
        source = trap + prefix + 'printf later\n}\n'
        (cwd / 'fault-source').write_text(source)
        extra = {'CSH_TEST_READ_FILE': 'fault-source', 'CSH_TEST_READ_AFTER': str(len(trap + prefix))}
        line = (trap + prefix).count('\n') + 1
        column = len((trap + prefix).rsplit('\n', 1)[-1]) + 1
        diagnostic = f'cshell: fault-source: {line}:{column}: cannot read input: {os.strerror(errno.EIO)}\n'.encode()
        for interactive in (False, True):
            run([fault, *(['-i'] if interactive else []), 'fault-source'],
                stdout=b'exit:128\n', stderr=diagnostic, status=128, extra=extra)
        # stdin is delivered through a redirection in a launcher shell, retaining
        # the same inode while exercising the public stdin invocation path.
        run([binary, '-c', f'{shlex.quote(fault)} <fault-source'],
            stdout=b'exit:128\n', stderr=diagnostic.replace(b'fault-source:', b'stdin:'), status=128, extra=extra)

    # A caught signal becomes pending at the failing read, before finalization.
    source = 'trap \'printf forbidden-trap\' USR1\n' + trap + 'printf forbidden; '
    (cwd / 'fault-source').write_text(source)
    run([fault, 'fault-source'], stdout=b'exit:128\n', status=128,
        stderr=f'cshell: fault-source: 3:19: cannot read input: {os.strerror(errno.EIO)}\n'.encode(),
        extra={'CSH_TEST_READ_FILE': 'fault-source', 'CSH_TEST_READ_AFTER': str(len(source)),
               'CSH_TEST_READ_SIGNAL': '1'})

    # Use quoted formats, so exact bytes have no accidental shell escapes.
    source = 'printf "sourced\\n"\n' + 'printf forbidden; printf later\n'
    boundary = len(source.splitlines(keepends=True)[0]) + len('printf forbidden; ')
    (cwd / 'fault-source').write_text(source)
    extra = {'CSH_TEST_READ_FILE': 'fault-source', 'CSH_TEST_READ_AFTER': str(boundary)}
    diagnostic = f'cshell: cannot read input: {os.strerror(errno.EIO)}\n'.encode()
    for interactive in (False, True):
        for command in ('.', 'command .'):
            for mode in ('string', 'file', 'stdin'):
                script = trap + command + ' ./fault-source\nprintf "continued:%s\\n" "$?"\n'
                (cwd / 'script').write_text(script)
                args = [fault, *(['-i'] if interactive else [])]
                if mode == 'string': args += ['-c', script]
                elif mode == 'file': args += ['script']
                else:
                    args = [binary, '-c', shlex.join(args) + ' <script']
                fatal = not interactive and command == '.'
                run(args, stdout=b'sourced\n' + (b'exit:128\n' if fatal else b'continued:128\nexit:0\n'),
                    stderr=(b'$ $ ' + diagnostic + b'$ $ ') if interactive and mode == 'stdin' else diagnostic,
                    status=128 if fatal else 0, extra=extra)
print(f'execution contracts: {checked} passed (32 descriptor, 7 main-read, 12 dot-read)')
