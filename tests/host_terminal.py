#!/usr/bin/env python3
"""CSH-077: strict, bounded terminal-provider witnesses on disposable PTYs."""
import argparse
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shlex
import shutil
import struct
import subprocess
import tempfile
import termios
import time

import pty_harness
import smoke
from host_utilities import serial, sha, source_identity, sanitizer_diagnostic

NAMES = ('stty', 'tabs', 'tput', 'tty', 'mesg', 'who', 'write')
MODES = ('direct', 'command', 'file', 'stdin', 'exec')
BASE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'
TIMEOUT, LIMIT = 3, 65536


def capture(*args, **kwargs):
    # Reap only adopted children in this invocation's owned group on Linux.
    libc = None
    if platform.system() == 'Linux':
        libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        if libc.prctl(37, ctypes.byref(previous), 0, 0, 0) or libc.prctl(36, 1, 0, 0, 0):
            raise OSError(ctypes.get_errno(), 'child subreaper setup')
    try:
        return _capture(*args, **kwargs)
    finally:
        if libc is not None and libc.prctl(36, previous.value, 0, 0, 0):
            raise OSError(ctypes.get_errno(), 'restore child subreaper')


def _capture(argv, directory, env, master, slave, input_file, tty_fds=(), data=b'',
            timeout=TIMEOUT, limit=LIMIT, fd_map=None, extra_terminals=None,
            terminal_input=b'', credentials=None, signal_on_terminal=None, signal_executable=None):
    """One owned process group; bounded pipes and PTY, even after leader exit."""
    fd_map = fd_map or {}
    extra_terminals = extra_terminals or {}

    def child():
        os.setpgrp()
        smoke.child_limits(timeout, limit)
        if credentials is not None:
            os.setgroups([])
            os.setgid(credentials[1])
            os.setuid(credentials[0])
            if (os.getresuid() != (credentials[0],) * 3 or
                    os.getresgid() != (credentials[1],) * 3 or os.getgroups()):
                raise RuntimeError('credential drop did not remove saved privileges')

    streams = dict(stdout=bytearray(), stderr=bytearray(), terminal=bytearray())
    streams.update({name: bytearray() for name in extra_terminals})
    failures = []
    signal_delivery = None
    start = time.monotonic()
    process = subprocess.Popen(argv, cwd=directory, env=env,
        stdin=fd_map.get(0, slave if 0 in tty_fds else (subprocess.PIPE if data else input_file)),
        stdout=fd_map.get(1, slave if 1 in tty_fds else subprocess.PIPE),
        stderr=fd_map.get(2, slave if 2 in tty_fds else subprocess.PIPE),
        pass_fds=(slave, input_file.fileno()), preexec_fn=child)
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(master, selectors.EVENT_READ, 'terminal')
            for name, fd in extra_terminals.items():
                selector.register(fd, selectors.EVENT_READ, name)
            if terminal_input and os.write(master, terminal_input) != len(terminal_input):
                raise OSError('short write of bounded terminal input')
            for stream, name in ((process.stdout, 'stdout'), (process.stderr, 'stderr')):
                if stream:
                    os.set_blocking(stream.fileno(), False)
                    selector.register(stream, selectors.EVENT_READ, name)
            if data:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, 'input')
            while True:
                if time.monotonic() - start >= timeout:
                    failures.append('timeout')
                    break
                exited_before_select = process.poll() is not None
                events = selector.select(0.02)
                for key, _ in events:
                    if key.data == 'input':
                        try:
                            count = os.write(key.fd, data)
                            data = data[count:]
                        except BrokenPipeError:
                            data = b''
                        except BlockingIOError:
                            continue
                        if not data:
                            selector.unregister(key.fileobj)
                            process.stdin.close()
                        continue
                    try:
                        chunk = os.read(key.fd, min(8192, limit + 1))
                    except BlockingIOError:
                        continue
                    except OSError as error:
                        if key.data != 'terminal' or error.errno != errno.EIO:
                            raise
                        chunk = b''
                    if chunk:
                        streams[key.data].extend(chunk)
                        if (signal_on_terminal is not None and key.data == 'terminal'
                                and signal_on_terminal[0] in streams['terminal']):
                            target = process.pid
                            if signal_executable:
                                # Linux registered-session fixture: identify only
                                # the selected executable in this owned group.
                                targets = []
                                for entry in Path('/proc').iterdir():
                                    if entry.name.isdigit():
                                        try:
                                            pid = int(entry.name)
                                            if os.getpgid(pid) != process.pid:
                                                continue
                                            argv0 = (entry / 'cmdline').read_bytes().split(b'\0')[0]
                                            expected = Path(signal_executable)
                                            # Cross-uid /proc/exe needs CAP_SYS_PTRACE.
                                            # These are only our fixture's descendants;
                                            # check both argv[0] and kernel comm without
                                            # granting the runner that capability.
                                            if (os.fsdecode(argv0) in (str(expected), expected.name) and
                                                    (entry / 'comm').read_text().strip() == expected.name):
                                                targets.append(pid)
                                        except (OSError, ProcessLookupError):
                                            pass
                                if len(targets) != 1:
                                    raise RuntimeError('expected one owned signal target: ' + str(targets))
                                target = targets[0]
                            os.kill(target, signal_on_terminal[1])
                            signal_delivery = dict(pid=target, signal=int(signal_on_terminal[1]),
                                                   executable=signal_executable, ready=True)
                            signal_on_terminal = None
                    else:
                        selector.unregister(key.fileobj)
                if sum(map(len, streams.values())) > limit:
                    failures.append('output limit exceeded')
                    break
                # Parent holds slave to inspect effects, so master need not reach EOF.
                if exited_before_select and not events:
                    break
    finally:
        try:
            smoke.kill_group(process, time.monotonic() + 1)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            failures.append('cleanup: ' + str(error))
            process.kill()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream and not stream.closed:
                stream.close()
        try:
            process.wait(timeout=1)
            deadline = time.monotonic() + 1
            if platform.system() == 'Linux':
                while True:
                    try:
                        pid, _ = os.waitpid(-process.pid, os.WNOHANG)
                    except ChildProcessError:
                        break
                    if not pid:
                        if time.monotonic() >= deadline:
                            failures.append('descendant reap timeout')
                            break
                        time.sleep(0.01)
        except subprocess.TimeoutExpired:
            failures.append('leader reap timeout')
    return dict(status=process.returncode, **{k: bytes(v) for k, v in streams.items()},
                failures=failures, signal_delivery=signal_delivery, elapsed_seconds=round(time.monotonic() - start, 4))


def inventory(search_path):
    result = {}
    for name in (*NAMES, 'tic'):
        found = shutil.which(name, path=search_path)
        entry = dict(path=found)
        if found:
            entry.update(realpath=os.path.realpath(found), sha256=sha(found))
        result[name] = entry
    commands = ([['sw_vers']] if platform.system() == 'Darwin' else
                [['dpkg-query', '-W', 'coreutils', 'ncurses-bin', 'libncurses6', 'util-linux', 'bsdextrautils', 'libc6']])
    commands.append(['cc', '--version'])
    packages = []
    for argv in commands:
        try:
            p = subprocess.run(argv, capture_output=True, timeout=5)
            packages.append(dict(argv=argv, status=p.returncode, stdout=p.stdout, stderr=p.stderr))
        except (OSError, subprocess.TimeoutExpired) as error:
            packages.append(dict(argv=argv, failure=str(error)))
    return result, packages


def cases():
    def c(name, utility, args=(), **kw):
        return dict(name=name, utility=utility, args=list(args), status=0,
                    stdout=b'', stderr=b'', terminal=b'', **kw)
    yield c('tty/name', 'tty', input_tty=True, oracle='ttyname')
    row = c('tty/not-terminal', 'tty'); row.update(status=1, stdout=b'not a tty\n'); yield row
    for index, names in ((0, 'ignbrk brkint ignpar parmrk inpck istrip inlcr igncr icrnl ixon ixany ixoff'),
                         (1, 'opost'), (3, 'isig icanon iexten echo echoe echok echonl noflsh tostop')):
        for name in names.split():
            for enabled in (False, True):
                arg = name if enabled else '-' + name
                yield c('stty/' + arg, 'stty', [arg], input_tty=True,
                        flag=[index, name.upper(), enabled])
    for name in ('eof', 'eol', 'erase', 'intr', 'kill', 'quit', 'susp', 'start', 'stop'):
        for value, expected in (('x', 120), ('^C', 3), ('^?', 127), ('undef', 'disable'), ('^-', 'disable')):
            yield c('stty/' + name + '/' + value, 'stty', [name, value], input_tty=True,
                    control=['V' + name.upper(), expected])
    row = c('stty/size', 'stty', ['size'], input_tty=True); row['stdout'] = b'24 41\n'; yield row
    yield c('stty/window', 'stty', ['rows', '31', 'cols', '73'], input_tty=True, oracle='window')
    row = c('stty/restore', 'stty', ['-g'], input_tty=True, oracle='restore'); row['stdout'] = None; yield row
    yield c('stty/min-time', 'stty', ['-icanon', 'min', '2', 'time', '3'], input_tty=True, oracle='min-time')
    for arg in ([], ['-a'], ['-g']):
        row = c('stty/report-' + (arg[0] if arg else 'default'), 'stty', arg, input_tty=True, oracle='report')
        row['stdout'] = None; yield row
    for name, arg, want in (('clear', ['clear'], b'CLEAR'), ('type-override', ['-T', 'csh077plain', 'clear'], b'CLEAR'),
                            ('init', ['init'], b'INIT'), ('reset', ['reset'], b'RESET')):
        row = c('tput/' + name, 'tput', arg, tty_fds=[1], term='absent-csh077' if name == 'type-override' else 'csh077plain')
        row['terminal'] = want; yield row
    row = c('tput/multiple', 'tput', ['clear', 'init', 'reset'], tty_fds=[1], term='csh077plain'); row['terminal'] = b'CLEARINITRESET'; yield row
    for name, args, term, expected in (
            ('no-operations', ['clear', 'init', 'reset'], 'csh077empty', b''),
            ('missing-clear-continues', ['clear', 'init', 'reset'], 'csh077partial', b'INITRESET'),
            ('attached-type', ['-Tcsh077plain', 'clear'], 'absent-csh077', b'CLEAR'),
            ('repeated-type', ['-T', 'absent-csh077', '-Tcsh077plain', 'clear'], 'absent-csh077', b'CLEAR')):
        row = c('tput/' + name, 'tput', args, tty_fds=[1], term=term)
        row['terminal'] = expected
        yield row
    row = c('mesg/no-terminal', 'mesg', [], input_tty=False)
    row.update(status='gt1', stderr='diagnostic')
    yield row
    for label, args in (('zero', ['-0']), ('regular', ['-8']), ('default', []),
                        ('absolute', ['1,10,20,30']), ('relative', ['1 10 +10 +10']),
                        ('type-override', ['-T', 'csh077', '1,10,20,30'])):
        row = c('tabs/' + label, 'tabs', args, tty_fds=[1], oracle='tabs',
                stops=[] if label == 'zero' else ([0, 8, 16, 24, 32, 40] if label in ('regular', 'default') else [0, 9, 19, 29]),
                term='absent-csh077' if label == 'type-override' else 'csh077')
        row['terminal'] = None; yield row
    for fd in (0, 1, 2):
        for allow in (False, True):
            row = c(f'mesg/{fd}/' + ('y' if allow else 'n'), 'mesg', ['y' if allow else 'n'],
                    input_tty=fd == 0, tty_fds=[fd] if fd else [], permission=allow)
            row['status'] = 0 if allow else 1; yield row
    for allow in (False, True):
        row = c('mesg/query-' + ('y' if allow else 'n'), 'mesg', input_tty=True, query_permission=allow)
        row.update(status=0 if allow else 1, stdout=b'is y\n' if allow else b'is n\n'); yield row
    yield c('who/empty-records', 'who', ['{empty}'])
    row = c('who/private-records', 'who', ['{records}'], oracle='who'); row['stdout'] = None; yield row
    for name, utility, args, status in (('tty/invalid-option', 'tty', ['-@'], 'gt1'),
            ('stty/invalid-operand', 'stty', ['csh077-invalid'], 'positive'),
            ('stty/missing-value', 'stty', ['erase'], 'positive'),
            ('tput/unknown-terminal', 'tput', ['-T', 'absent-csh077', 'clear'], 3),
            ('tput/invalid-operand', 'tput', ['csh077-invalid'], 4),
            ('tabs/unknown-terminal', 'tabs', ['-T', 'absent-csh077', '-8'], 'positive'),
            ('mesg/invalid-operand', 'mesg', ['invalid'], 'gt1'),
            ('who/missing-file', 'who', ['{absent}'], 'positive'),
            ('write/missing-user', 'write', [], 'positive')):
        row = c(name, utility, args, input_tty=True, tty_fds=[1] if utility in ('tabs', 'tput') else [])
        row.update(status=status, stderr='diagnostic'); yield row


def tab_effect(output):
    """Interpret ONLY capabilities authored in host_terminal.ti, not vendor output."""
    stops, column, cleared = [], 0, False
    while output:
        if output.startswith(b'CLEAR_TABS'):
            stops, cleared, output = [], True, output[10:]
        elif output.startswith(b'SET_TAB'):
            stops.append(column); output = output[7:]
        elif output.startswith(b'\r'):
            column = 0; output = output[1:]
        elif output.startswith(b' '):
            column += 1; output = output[1:]
        else:
            return None
    return stops if cleared else None


def run_case(case, mode, binary, providers, directory, environment):
    master, slave = pty_harness.open_terminal()
    input_file = None
    output_fd = None
    alias_fd = None
    try:
        input_file = open(directory / 'input', 'rb')
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', *case.get('window', [24, 41]), 0, 0))
        before = termios.tcgetattr(slave)
        if 'flag' in case:
            index, name, enabled = case['flag']
            bit = getattr(termios, name)
            before[index] = before[index] & ~bit if enabled else before[index] | bit
            termios.tcsetattr(slave, termios.TCSANOW, before)
        if 'query_permission' in case:
            os.fchmod(slave, 0o620 if case['query_permission'] else 0o600)
        if 'permission' in case:
            os.fchmod(slave, 0o600 if case['permission'] else 0o620)
        before = termios.tcgetattr(slave)
        if case.get('oracle') == 'who':
            (directory / 'recordsx').write_bytes(b'')
            subprocess.run([str(Path('build/tests/host_session_records').resolve()), str(directory / 'recordsx'), os.ttyname(slave).removeprefix('/dev/')], check=True, capture_output=True, timeout=5)
        args = [s.format(records=directory / 'recordsx', empty=directory / 'emptyx', absent=directory / 'absentx') for s in case['args']]
        selected = providers[case['utility']]['path']
        if not selected:
            raise OSError('missing provider: ' + case['utility'])
        tty_fds = case.get('tty_fds', [])
        input_name = os.ttyname(slave) if case.get('input_tty') else str(directory / 'input')
        command = shlex.join([selected if mode == 'exec' else case['utility'], *args]) + (' < ' + shlex.quote(input_name) if case.get('input_tty') else ' <& ' + str(input_file.fileno()))
        if mode == 'exec':
            command = 'exec ' + command
        data = b''
        if mode == 'direct':
            argv = [selected, *args]
            tty_fds = tty_fds + ([0] if case.get('input_tty') else [])
        elif mode == 'file':
            (directory / 'script').write_text(command + '\n')
            argv = [str(binary), str(directory / 'script')]
        elif mode == 'stdin':
            argv, data = [str(binary)], (command + '\n').encode()
        else:
            argv = [str(binary), '-c', command]
        env = dict(environment, TERM=case.get('term', 'csh077'))
        for key, value in case.get('environment', {}).items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value
        fd_map = {}
        if case.get('input_alias'):
            alias = directory / 'terminal-alias'
            alias.unlink(missing_ok=True)
            alias.symlink_to(os.ttyname(slave))
            alias_fd = os.open(alias, os.O_RDONLY | os.O_NOCTTY)
            if mode == 'direct':
                fd_map[0] = alias_fd
            else:
                # argv/script/data have already been built; substitute only the
                # shell redirection path, never a utility argument or source.
                alias_code = command.rsplit(' < ', 1)[0] + ' < ' + shlex.quote(str(alias))
                if mode == 'file':
                    (directory / 'script').write_text(alias_code + '\n')
                elif mode == 'stdin':
                    data = (alias_code + '\n').encode()
                else:
                    argv = [str(binary), '-c', alias_code]
        if case.get('readonly_stdout'):
            output_fd = os.open(os.ttyname(slave), os.O_RDONLY | os.O_NOCTTY)
            fd_map[1] = output_fd
        actual = capture(argv, directory, env, master, slave, input_file, tty_fds, data, fd_map=fd_map)
        offset = input_file.tell()
        after = termios.tcgetattr(slave)
        failures = list(actual['failures'])
        if sanitizer_diagnostic({k: actual[k] for k in ('stdout', 'stderr', 'terminal')}):
            failures.append('sanitizer diagnostic')
        if case.get('oracle') == 'window':
            size = struct.unpack('HHHH', fcntl.ioctl(slave, termios.TIOCGWINSZ, b'\0' * 8))
            if size[:2] != (31, 73):
                failures.append('window size mismatch')
        if 'query_permission' in case and bool(os.fstat(slave).st_mode & 0o022) != case['query_permission']:
            failures.append('query changed permissions')
        if case.get('oracle') == 'restore':
            token = actual['stdout'].rstrip(b'\n').decode('ascii')
            altered = termios.tcgetattr(slave)
            altered[3] ^= termios.ECHO
            termios.tcsetattr(slave, termios.TCSANOW, altered)
            restore_command = shlex.join([selected if mode == 'exec' else 'stty', token]) + ' < ' + shlex.quote(input_name)
            if mode == 'exec':
                restore_command = 'exec ' + restore_command
            restore_data = b''
            if mode == 'direct':
                restore_argv = [selected, token]
            elif mode == 'file':
                (directory / 'script').write_text(restore_command + '\n')
                restore_argv = argv
            elif mode == 'stdin':
                restore_argv, restore_data = argv, (restore_command + '\n').encode()
            else:
                restore_argv = [str(binary), '-c', restore_command]
            with open(directory / 'input', 'rb') as stream:
                restored = capture(restore_argv, directory, env, master, slave, stream, tty_fds, restore_data)
            actual['restore'] = restored
            if restored['status'] or restored['failures'] or any(restored[k] for k in ('stdout', 'stderr', 'terminal')) or termios.tcgetattr(slave) != before:
                failures.append('saved state did not restore independent termios snapshot')
        for stream in ('stdout', 'stderr', 'terminal'):
            expected = case[stream]
            if case.get('oracle') == 'ttyname' and stream == 'stdout':
                expected = (os.ttyname(slave) + '\n').encode()
            valid = bool(actual[stream]) if expected == 'diagnostic' else (expected is None or actual[stream] == expected)
            if not valid:
                failures.append(stream + ' mismatch')
        expected = case['status']
        if not (actual['status'] > (1 if expected == 'gt1' else 0) if isinstance(expected, str) else actual['status'] == expected):
            failures.append('status mismatch')
        if 'flag' in case and bool(after[index] & bit) != enabled:
            failures.append('termios flag mismatch')
        if 'control' in case:
            slot, expected = case['control']
            expected = os.fpathconf(slave, 'PC_VDISABLE') if expected == 'disable' else expected
            got = after[6][getattr(termios, slot)]
            if (got if isinstance(got, int) else got[0]) != expected:
                failures.append('control character mismatch')
        if case.get('oracle') == 'min-time' and [after[6][s] for s in (termios.VMIN, termios.VTIME)] != [2, 3]:
            failures.append('min/time mismatch')
        if case.get('oracle') == 'who':
            lines = actual['stdout'].splitlines()
            expected_names = [b'csh077a', b'csh077b']
            if len(lines) != 2 or any(line.split()[:2] != [name, os.ttyname(slave).removeprefix('/dev/').encode()] or b' '.join(line.split()[2:]) != case.get('who_time', b'Jan 1 00:00') for name, line in zip(expected_names, lines)):
                failures.append('private session rows mismatch')
        if case.get('oracle') == 'report':
            if not actual['stdout'] or before != after:
                failures.append('empty report or changed state')
            if case['args'] == ['-g']:
                token = actual['stdout'].rstrip(b'\n')
                if actual['stdout'] != token + b'\n' or any(c < 33 or c > 126 or c in b'*?[' for c in token):
                    failures.append('nonportable saved state')
        if case.get('oracle') == 'tabs' and tab_effect(actual['terminal']) != case['stops']:
            failures.append('tab stop effect mismatch')
        if 'permission' in case and bool(os.fstat(slave).st_mode & 0o022) != case['permission']:
            failures.append('terminal write permission mismatch')
        if 'controls' in case:
            for slot, expected in case['controls'].items():
                value = after[6][getattr(termios, slot)]
                if (value if isinstance(value, int) else value[0]) != expected:
                    failures.append(slot + ' control mismatch')
        for index, name, enabled in case.get('flags', []):
            if bool(after[index] & getattr(termios, name)) != enabled:
                failures.append(name + ' combination flag mismatch')
        if 'report_tokens' in case:
            tokens = set(re.findall(rb'[-a-zA-Z0-9]+', actual['stdout']))
            for token in case['report_tokens']:
                if token.encode() not in tokens:
                    failures.append('missing report token: ' + token)
            if before != after:
                failures.append('report changed terminal state')
        if not case.get('input_tty') and offset != 0:
            failures.append('unused stdin consumed')
        return dict(name=case['name'], mode=mode, utility=case['utility'], source=BASE + case['utility'] + '.html',
                    verdict='FAIL' if failures else 'PASS', expected=case, actual=actual,
                    failures=failures, argv=argv, termios_before=before, termios_after=after,
                    input_offset=offset, terminal_mode=oct(os.fstat(slave).st_mode & 0o777))
    finally:
        if input_file is not None:
            input_file.close()
        if output_fd is not None:
            os.close(output_fd)
        if alias_fd is not None:
            os.close(alias_fd)
        os.close(slave)
        os.close(master)


def main(cases_factory=cases):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--path', default=os.environ.get('CSH_TEST_PATH', os.defpath))
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--case', help='Run only matching case name (diagnosis, no full-subset claim)')
    args = parser.parse_args()
    # Isolate from any developer controlling terminal. Children own groups but
    # are not session leaders, so opening a slave cannot acquire/revoke it.
    if os.getsid(0) != os.getpid():
        os.setsid()
    inputs = source_identity()
    providers, packages = inventory(args.path)
    rows = []
    with tempfile.TemporaryDirectory(prefix='csh077-') as temp:
        directory = Path(temp)
        (directory / 'input').write_bytes(b'unused\x80\xff\n')
        (directory / 'recordsx').touch()
        (directory / 'emptyx').touch()
        (directory / 'terminfo').mkdir()
        env = dict(PATH=args.path, LC_ALL='C', LANG='C', TZ='UTC0', HOME=temp,
                   TERMINFO=str(directory / 'terminfo'), TERMINFO_DIRS=str(directory / 'terminfo'))
        env.update({key: os.environ[key] for key in ('ASAN_OPTIONS', 'UBSAN_OPTIONS', 'MallocNanoZone') if key in os.environ})
        try:
            subprocess.run([providers['tic']['path'], '-x', '-o', env['TERMINFO'],
                str(Path(__file__).with_suffix('.ti').resolve())], check=True, capture_output=True, timeout=5)
            for case in cases_factory():
                if args.case and args.case not in case['name']:
                    continue
                for mode in MODES:
                    try:
                        row = run_case(case, mode, args.binary.resolve(), providers, directory, env)
                    except (OSError, ValueError, termios.error, pty_harness.PtyUnavailable, subprocess.SubprocessError) as error:
                        row = dict(name=case['name'], mode=mode, verdict='FAIL', phase='setup', reason=str(error), actual=serial(dict(argv=getattr(error, 'cmd', None), status=getattr(error, 'returncode', None), stdout=getattr(error, 'stdout', None), stderr=getattr(error, 'stderr', None), errno=getattr(error, 'errno', None), timeout=getattr(error, 'timeout', None))))
                    rows.append(row)
                    if row['verdict'] == 'FAIL':
                        print('FAIL:', case['name'], mode, row.get('failures', row.get('reason')))
        except (OSError, TypeError, subprocess.SubprocessError) as error:
            rows.append(dict(name='terminfo', verdict='FAIL', phase='setup', reason=str(error), actual=serial(dict(argv=getattr(error, 'cmd', None), status=getattr(error, 'returncode', None), stdout=getattr(error, 'stdout', None), stderr=getattr(error, 'stderr', None), errno=getattr(error, 'errno', None), timeout=getattr(error, 'timeout', None)))))
        for name in ('stty', 'tabs', 'tput', 'tty', 'mesg', 'who'):
            provider = Path('/bin' if name == 'stty' else '/usr/bin') / name
            providers[name]['vendor'] = dict(path=str(provider), realpath=str(provider.resolve()), sha256=sha(provider), comparison_only=name in ('tabs', 'tty')) if provider.exists() else None
        report = dict(schema_version=1, platform=platform.platform(), uid=os.getuid(), gid=os.getgid(),
            path=args.path, providers=providers, packages=packages, environment=env,
            binary=dict(path=str(args.binary.resolve()), sha256=sha(args.binary)),
            source_identity=inputs, command=os.sys.argv, cases=rows,
            residual_owner='CSH-081', residuals=['U-040/stty-physical-terminal', 'terminal/full-page-contracts', 'write/native-darwin-sessions', 'terminal/locales-signals-io-limits'],
            bounds=dict(timeout_seconds=TIMEOUT, output_bytes=LIMIT, group_cleanup_seconds=1, leader_reap_seconds=1, descendant_reap_seconds=1),
            qualification='selected cases only; full contracts remain open',
            totals=dict(passed=sum(r['verdict'] == 'PASS' for r in rows), failed=sum(r['verdict'] == 'FAIL' for r in rows)))
    if source_identity() != inputs:
        rows.append(dict(name='source-stability', verdict='FAIL', phase='setup', reason='build/test source changed during run'))
        report['totals']['failed'] += 1
    report['fixture_directory_removed'] = not directory.exists()
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(serial(report), indent=2) + '\n')
    print(json.dumps(report['totals']))
    return int(bool(report['totals']['failed']) or not rows or not report['fixture_directory_removed'])


if __name__ == '__main__':
    raise SystemExit(main())
