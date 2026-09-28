#!/usr/bin/env python3
"""CSH-058: SIG-001/002/003 and U-015/026/032. See clause/evidence map."""
import errno
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time

from execute import bounded_run
from smoke import child_limits
from signal_contracts import signal_name
from pty_harness import capture as pty_capture

NAMES = 'INT HUP CHLD QUIT TERM TSTP TTIN TTOU'.split()


def public_wait(binary, directory, env, selected, operand, mode):
    """Observe sleep after a builtin-only marker, without modifying cshell.

    trap -p writes one short line to an empty regular file. After that marker
    the only blocking operation on the parent path is wait's sigsuspend. The
    child cannot exit until explicitly released. Linux also verifies wchan.
    A polling delay is never evidence of entering the wait.
    """
    release = directory / 'release'
    os.mkfifo(release)
    signals = sorted((signal.SIGUSR1, signal.SIGUSR2)) if selected == 'both' else [getattr(signal, 'SIG' + selected)]
    traps = '; '.join(f"trap 'printf \"trap:{n}:%s\\n\" \"$?\"' {n}" for n in signals)
    script = (traps + '; '
              '{ read token <release; exit 23; } & p=$!; '
              'trap -p EXIT >armed; '
              f'wait {operand}; printf "wait:%s\\n" "$?"; '
              'echo go >release; wait "$p"; printf "second:%s\\n" "$?"; '
              'wait "$p" 2>/dev/null; printf "third:%s\\n" "$?"\n')
    args = [binary, '-c', script]
    if mode == 'file':
        (directory / 'script').write_text(script)
        args = [binary, 'script']
    elif mode == 'stdin':
        (directory / 'script').write_text(script)
        args = [binary]
    with (directory / 'script').open('ab+') as source, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        source.seek(0)
        process = subprocess.Popen(args, cwd=directory, env=env,
                                   stdin=source if mode == 'stdin' else subprocess.DEVNULL,
                                   stdout=out, stderr=err, start_new_session=True,
                                   preexec_fn=lambda: child_limits(5, 65536))
        try:
            deadline = time.monotonic() + 5
            observed = None
            while time.monotonic() < deadline:
                assert process.poll() is None, 'wait exited before signal'
                armed = directory / 'armed'
                if armed.exists() and armed.read_bytes() == b"trap -- '-' EXIT\n":
                    if sys.platform.startswith('linux'):
                        channel = Path(f'/proc/{process.pid}/wchan').read_text().strip()
                        if 'sigsuspend' in channel:
                            observed = channel
                            break
                    elif sys.platform == 'darwin':
                        result = subprocess.run(['/bin/ps', '-o', 'state=', '-p', str(process.pid)],
                                                capture_output=True, timeout=1, check=True)
                        if result.stdout.strip().startswith(b'S'):
                            observed = 'macOS interruptible sleep after builtin marker'
                            break
                    else:
                        raise AssertionError('blocked-wait observation unsupported on this host')
                time.sleep(0.002)
            assert observed, 'did not observe blocked wait within five seconds'
            if selected == 'both':
                os.kill(process.pid, signal.SIGSTOP)
                # WUNTRACED confirms the stop before queuing both conditions.
                while True:
                    pid, state = os.waitpid(process.pid, os.WUNTRACED | os.WNOHANG)
                    if pid:
                        assert os.WIFSTOPPED(state) and os.WSTOPSIG(state) == signal.SIGSTOP
                        break
                    assert time.monotonic() < deadline, 'did not observe stopped waiter'
                    time.sleep(0.002)
            for number in signals:
                os.kill(process.pid, number)
            if selected == 'both':
                os.kill(process.pid, signal.SIGCONT)
            process.wait(timeout=max(0.01, deadline - time.monotonic()))
            out.seek(0)
            err.seek(0)
            status = 128 + signals[0]
            expected = (''.join(f'trap:{n}:{status}\n' for n in signals) + f'wait:{status}\nsecond:23\nthird:127\n').encode()
            assert (process.returncode, out.read(), err.read()) == (0, expected, b'')
            print(f'PASS wait/{selected}/{operand or "all"}/{mode}: {observed}', flush=True)
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=1)
    release.unlink()
    (directory / 'armed').unlink()


def main():
    binary, helper = [str(Path(p).resolve()) for p in sys.argv[1:3]]
    count = 0
    with tempfile.TemporaryDirectory(prefix='cshell-signal-edges-') as temp:
        directory = Path(temp)
        env = dict(PATH=os.defpath, HOME=temp, TMPDIR=temp, LANG='C', LC_ALL='C')
        for option in ('ASAN_OPTIONS', 'UBSAN_OPTIONS', 'MallocNanoZone'):
            if option in os.environ:
                env[option] = os.environ[option]

        def run(label, args, stdout=b'', stderr=b'', status=0):
            nonlocal count
            result = bounded_run(args, cwd=directory, env=env, timeout=5)
            assert (result.returncode, result.stdout) == (status, stdout), (label, result, stdout, status)
            if stderr is None:
                assert re.fullmatch(rb'\[1\] [1-9][0-9]*\n', result.stderr), (label, result)
            else:
                assert result.stderr == stderr, (label, result, stderr)
            count += 1
            print('PASS ' + label, flush=True)
            return result

        for name in NAMES:
            n = int(getattr(signal, 'SIG' + name))
            for interactive in (0, 1):
                for inherited in (0, 1):
                    for action in range(5):
                        label = f'{name}/interactive={interactive}/entry-ignore={inherited}/action={action}'
                        # API queries the shell process before exec, including
                        # CHLD's intentional no-op handler rather than SIG_IGN.
                        for shape in range(3):
                            run(f'api/{label}/shape={shape}', [helper, 'api', str(n), str(interactive), str(inherited), str(action), str(shape)])
                        parent = ('', f"trap ':' {name}; ", f"trap '' {name}; ",
                                  f"trap ':' {name}; trap '' {name}; ",
                                  f"trap '' {name}; trap - {name}; ")[action]
                        locked = inherited and not interactive
                        caught = not locked and action == 1
                        ignored = inherited if locked or action in (0, 4) else action in (2, 3)
                        probe = f'{shlex.quote(helper)} probe {n}'
                        shapes = {
                            'subshell': lambda s: f'( {s} )',
                            'pipeline': lambda s: f'{{ {s}; }} | /bin/cat',
                            'background': lambda s: f'{{ {s}; }} & wait; wait; :',
                            'substitution': lambda s: f'v=$({s}; :); printf "%s\\n" "$v"',
                        }
                        for shape, wrap in shapes.items():
                            forced = shape == 'background' and name in ('INT', 'QUIT')
                            for reset in (False, True):
                                ignore = forced or (inherited and not caught if reset else ignored)
                                disposition = 'ignored' if ignore else 'default'
                                delivery = 'survived' if ignore or name == 'CHLD' else 'stopped' if name in ('TSTP', 'TTIN', 'TTOU') else 'terminated'
                                script = parent + wrap((f'trap - {name}; ' if reset else '') + probe)
                                run(f'runtime/{label}/{shape}/reset={reset}',
                                    [helper, 'launch', str(n), str(inherited), binary, '-ic' if interactive else '-c', script],
                                    f'{disposition}:{delivery}\n'.encode(),
                                    stderr=None if interactive and shape == 'background' else b'')
                                if interactive:
                                    # A controlling PTY enables monitor. Its background
                                    # stages must not receive the unmonitored INT/QUIT ignore.
                                    ignore = (inherited and not caught) if reset else ignored
                                    disposition = 'ignored' if ignore else 'default'
                                    delivery = 'survived' if ignore or name == 'CHLD' else 'stopped' if name in ('TSTP', 'TTIN', 'TTOU') else 'terminated'
                                    pty_script = parent + '{ ' + wrap((f'trap - {name}; ' if reset else '') + probe) + '; } 2>announcements'
                                    args = ['launch', str(n), str(inherited), binary, '-ic', pty_script]
                                    status, output, failures = pty_capture(helper, dict(args=args, steps=[]), directory, 5, 65536, env, child_limits)
                                    expected = f'{disposition}:{delivery}\n'.encode()
                                    errors = (directory / 'announcements').read_bytes()
                                    assert (status, bytes(output['output']), failures) == (0, expected, []), (label, shape, reset, status, output, failures, expected, errors)
                                    if shape == 'background':
                                        assert re.fullmatch(rb'\[1\] [1-9][0-9]*\n', errors), errors
                                    else:
                                        assert errors == b'', errors
                                    print(f'PASS monitored/{label}/{shape}/reset={reset}', flush=True)
                                    count += 1
        for pid in ('123456789', '-123456789', '0'):
            run('permission/' + pid, [str(Path(sys.argv[3]).resolve()), pid],
                b'EPERM; continued; delivered\n',
                f'cshell: kill: {os.strerror(errno.EPERM)}: {pid}\n'.encode())
        for negative in (0, 1):
            run(f'group/negative={negative}', [helper, 'group', binary, str(negative)], b'delivered:A,B\n')
        conditions = bounded_run([helper, 'conditions'], cwd=directory, env=env, timeout=5)
        assert (conditions.returncode, conditions.stderr) == (0, b'')
        assert int(signal.NSIG) <= 1024, 'host signal range exceeds discovery bound'
        numbers = [int(n) for n in conditions.stdout.split()]
        print('HOST signal conditions: ' + ','.join(map(str, numbers)), flush=True)
        # Numeric conditions are a documented extension. No silently skipped
        # host signal beyond the runtime range: require reinput for every one.
        for n in numbers:
            run(f'host-condition/{n}', [binary, '-c', f"trap ':' {n}; trap -p {n}"], f"trap -- ':' {signal_name(n)}\n".encode())
        for command, lines in [('trap -p', len(numbers) + 1), ("trap ':' USR1; trap", 1), ('trap -p USR1 USR2', 2)]:
            run('output-failure/' + command, [binary, '-c', command + ' >&-'],
                stderr=b'cshell: trap: cannot write output\n' * lines, status=1)
        # KILL/STOP installation is undefined by POSIX; these assert the
        # documented host-error/operand-continuation robustness contract only.
        for name in ('KILL', 'STOP'):
            run('uninstallable/' + name, [binary, '-c', f"trap ':' USR1 {name} USR2; r=$?; trap -p USR1 USR2; exit \"$r\""],
                b"trap -- ':' USR1\ntrap -- ':' USR2\n", b'cshell: trap: cannot install signal\n', 1)
        run('standalone-trap-exception', [binary, '-c', "trap ':' HUP; v=$(trap -p HUP); printf '%s\\n' \"$v\""], b"trap -- ':' HUP\n")
        for selected in ('INT', 'USR1', 'TERM', 'both'):
            for operand in ('"$p"', ''):
                for mode in ('string', 'file', 'stdin'):
                    public_wait(binary, directory, env, selected, operand, mode)
                    count += 1
    print(f'CSH-058 signal edges passed ({count} cases)', flush=True)


if __name__ == '__main__':
    main()
