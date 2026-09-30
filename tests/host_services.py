#!/usr/bin/env python3
"""CSH-078: strict, bounded service witnesses; native mode has no service effects."""
import argparse
import base64
import binascii
from contextlib import contextmanager
from email.utils import getaddresses, parsedate_to_datetime
import json
import mailbox
import os
from pathlib import Path
import platform
import resource
import math
import re
import shlex
import shutil
import signal
import stat
import subprocess
import tempfile
import time

import smoke
from host_utilities import serial, sha, source_identity

NAMES = 'at batch crontab date logger lp mailx uudecode uuencode'.split()
MODES = ('direct', 'command', 'exec', 'file', 'stdin')
SOURCE = 'https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'
TIMEOUT = 8
LIMIT = 1024 * 1024


def limits(timeout, services=False):
    if not services:
        smoke.child_limits(timeout, LIMIT)
        return
    # Exim sets its descriptor limit to 1024 during local delivery. Supply that
    # bounded capability instead of inducing unrelated startup diagnostics.
    for kind, wanted in ((resource.RLIMIT_CORE, 0), (resource.RLIMIT_CPU, math.ceil(timeout) + 1),
                         (resource.RLIMIT_FSIZE, LIMIT), (resource.RLIMIT_NOFILE, 1024)):
        _, hard = resource.getrlimit(kind)
        value = min(wanted, hard) if hard != resource.RLIM_INFINITY else wanted
        resource.setrlimit(kind, (value, value))
    os.umask(0o077)


def require_container():
    """Fail closed before any service operation, even if --services was supplied."""
    marker = Path('/etc/cshell-service-fixture')
    if (platform.system() != 'Linux' or os.geteuid() != 0 or
            not Path('/.dockerenv').exists() or not marker.is_file() or
            marker.read_text() != 'CSH-078 disposable services v1\n'):
        raise RuntimeError('services require the dedicated disposable Docker image')
    status = Path('/proc/self/status').read_text()
    for key in ('CapEff', 'CapPrm', 'CapBnd'):
        value = int(re.search(r'^' + key + r':\s*([0-9a-f]+)', status, re.M)[1], 16)
        if value & ((1 << 25) | (1 << 21) | (1 << 12)):
            raise RuntimeError('SYS_TIME, SYS_ADMIN and NET_ADMIN must be absent, including the bounding set')
    if any(p.name != 'lo' and int((p / 'flags').read_text(), 16) & 1
           for p in Path('/sys/class/net').iterdir()):
        raise RuntimeError('services require --network none (loopback only)')
    # Refuse host-bound spool/config/output trees: the launcher uses no volumes.
    for line in Path('/proc/self/mountinfo').read_text().splitlines():
        target = line.split()[4]
        if target != '/' and any(target == p or target.startswith(p + '/') or p.startswith(target + '/') for p in
               ('/work', '/var/spool', '/var/mail', '/etc/cups', '/etc/exim4', '/home', '/usr/lib/cups/backend')):
            raise RuntimeError('service fixture paths must not be mounted: ' + target)


def providers(search):
    result = {}
    for name in NAMES:
        path = shutil.which(name, path=search)
        row = dict(path=path, realpath=os.path.realpath(path) if path else None)
        if path:
            row['sha256'] = sha(path)
            if platform.system() == 'Linux' and shutil.which('dpkg-query'):
                query = subprocess.run(['dpkg-query', '-S', path, os.path.realpath(path)],
                                       capture_output=True, text=True, timeout=5)
                row['package_owners'] = query.stdout.strip()
                row['package_query_status'] = query.returncode
        result[name] = row
    return result


class Suite:
    def __init__(self, binary, search, services=False):
        self.binary = str(binary.resolve())
        self.search = search
        self.services = services
        self.results = []
        self.providers = providers(search)
        self.daemons = []
        self.environment = dict(PATH=search, LANG='C', LC_ALL='C', TZ='UTC0',
                                HOME='/home/cshell' if services else '/nonexistent',
                                SHELL='/bin/sh')
        for key in ('ASAN_OPTIONS', 'UBSAN_OPTIONS', 'MallocNanoZone'):
            if key in os.environ:
                self.environment[key] = os.environ[key]

    @contextmanager
    def directory(self):
        with tempfile.TemporaryDirectory(prefix='csh078-') as value:
            root = Path(value)
            if self.services:
                os.chown(root, 10001, 10001)
            yield root

    def record(self, name, utility, ok, **details):
        self.results.append(dict(name=name, utility=utility, owner='CSH-078',
                                 source=SOURCE + utility + '.html',
                                 verdict='PASS' if ok else 'FAIL', **serial(details)))
        if not ok:
            print('FAIL:', name, flush=True)
        return ok

    def call(self, argv, directory, data=b'', env=None, user=True, timeout=TIMEOUT):
        environment = {**self.environment, **(env or {})}
        command = list(map(str, argv))
        if self.services and user:
            command = ['/usr/sbin/runuser', '-u', 'cshell', '--', '/usr/bin/env',
                       *[f'{k}={v}' for k, v in environment.items()], *command]
        # Files avoid pipe-buffer deadlocks and bound stdout/stderr via RLIMIT_FSIZE.
        with tempfile.TemporaryFile() as inp, tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            inp.write(data); inp.seek(0)
            started = time.monotonic()
            child = subprocess.Popen(command, cwd=directory, env=environment,
                                     stdin=inp, stdout=out, stderr=err, start_new_session=True,
                                     preexec_fn=lambda: limits(timeout, self.services))
            failure = None
            try:
                child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                failure = 'timeout'
            finally:
                try:
                    smoke.kill_group(child)
                except (OSError, ValueError, subprocess.SubprocessError) as error:
                    failure = f'cleanup: {error}'
                child.wait(timeout=2)
            out.seek(0); err.seek(0)
            stdout, stderr = out.read(LIMIT + 1), err.read(LIMIT + 1)
        if len(stdout) > LIMIT or len(stderr) > LIMIT:
            failure = 'output limit'
        return dict(argv=command, pid=child.pid, status=child.returncode, stdout=stdout, stderr=stderr,
                    failure=failure, seconds=round(time.monotonic() - started, 3))

    def invoke(self, name, utility, args, directory, mode, data=b'', stdout=b'',
               stderr=b'', status=0, env=None, check=None):
        if self.services:
            for child in directory.iterdir():
                if child.is_file() and not child.is_symlink():
                    os.chown(child, 10001, 10001)
        path = self.providers[utility]['path']
        if not path:
            self.record(name + '/' + mode, utility, False, phase='setup', reason='missing provider')
            return None
        if mode == 'direct':
            argv = [path, *args]
            input_data = data
        else:
            # Redirect utility input independently of the source input mode.
            input_path = directory / 'command-input'
            input_path.write_bytes(data); input_path.chmod(0o644)
            command = ('exec ' if mode == 'exec' else '') + shlex.join([utility, *args])
            command += ' < ' + shlex.quote(str(input_path)) + '\n'
            input_data = b''
            if mode in ('command', 'exec'):
                argv = [self.binary, '-c', command]
            elif mode == 'file':
                script = directory / 'script'
                script.write_text(command); script.chmod(0o644)
                argv = [self.binary, str(script)]
            else:
                argv = [self.binary]
                input_data = command.encode()
        actual = self.call(argv, directory, input_data, env)
        def match(want, got):
            if want == 'nonzero': return isinstance(got, int) and got > 0
            if isinstance(want, re.Pattern): return bool(want.fullmatch(got))
            return want == got
        ok = not actual['failure'] and all(match(w, actual[k]) for k, w in
                (('status', status), ('stdout', stdout), ('stderr', stderr)))
        extra = None
        if check:
            try:
                extra = check(actual)
                ok = ok and bool(extra)
            except (OSError, ValueError, AssertionError) as error:
                extra = str(error)
                ok = False
        self.record(name + '/' + mode, utility, ok, phase='assertion', actual=actual,
                    expected=dict(status=status, stdout=repr(stdout), stderr=repr(stderr)),
                    effects=extra)
        return actual

    def start(self, argv, directory, env=None):
        log = tempfile.TemporaryFile()
        child = subprocess.Popen(argv, cwd=directory, env={**self.environment, **(env or {})},
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True,
                                 preexec_fn=lambda: limits(120, self.services))
        self.daemons.append((child, log, list(map(str, argv))))
        return child

    def stop(self, target=None):
        for child, log, argv in list(reversed(self.daemons)):
            if target is not None and child is not target:
                continue
            error = None
            try:
                smoke.kill_group(child)
                child.wait(timeout=2)
            except (OSError, ValueError, subprocess.SubprocessError) as e:
                error = str(e)
            log.seek(0)
            utility = {'atd': 'at', 'cron': 'crontab', 'cupsd': 'lp', 'python3': 'logger'}[Path(argv[0]).name]
            self.record('service-process-cleanup/' + Path(argv[0]).name, utility, error is None,
                        phase='cleanup', argv=argv, status=child.poll(), error=error,
                        log=log.read(LIMIT))
            log.close()
            self.daemons.remove((child, log, argv))


def wait_for(predicate, seconds=8):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if predicate(): return True
        time.sleep(0.05)
    return bool(predicate())


def encoded(data, name='decoded', mode='640', mime=False):
    if mime:
        body = base64.encodebytes(data)
        return f'begin-base64 {mode} {name}\n'.encode() + body + b'====\n'
    body = b''.join(binascii.b2a_uu(data[n:n+45], backtick=True)
                    for n in range(0, len(data), 45))
    return f'begin {mode} {name}\n'.encode() + body + b'`\nend\n'


def encoding_cases(s):
    for mode in MODES:
        with s.directory() as d:
            for size in (0, 1, 2, 3, 44, 45, 46, 57, 58, 256, 8192):
                data = bytes(n % 256 for n in range(size))
                source = d / 'binary'; source.write_bytes(data); source.chmod(0o640)
                for mime in (False, True):
                    tag = ('base64' if mime else 'historical') + '-' + str(size)
                    # Line folding and the historical space/backtick spelling are
                    # implementation choices; compare the complete decoded oracle
                    # plus independently validated envelope, lengths and digits.
                    def verify(a, mime=mime, data=data):
                        lines = a['stdout'].splitlines()
                        assert lines[0] == (b'begin-base64 640 decoded' if mime else b'begin 640 decoded')
                        if mime:
                            assert lines[-1] == b'===='
                            assert all(0 < len(x) <= 76 for x in lines[1:-1])
                            assert b''.join(lines[1:-1]) == base64.b64encode(data)
                        else:
                            assert lines[-1] == b'end' and lines[-2] in (b' ', b'`')
                            chunks = []
                            for line in lines[1:-2]:
                                length = (line[0] - 32) & 63
                                assert 1 <= length <= 45
                                assert len(line) == 1 + 4 * ((length + 2) // 3)
                                assert all(32 <= c <= 96 for c in line)
                                chunks.append(binascii.a2b_uu(line))
                            assert b''.join(chunks) == data
                        return True
                    s.invoke('encode-' + tag, 'uuencode', (['-m'] if mime else []) + ['binary', 'decoded'],
                             d, mode, stdout=re.compile(rb'.*', re.S), check=verify)
                    for dest in ('decoded', '-', '/dev/stdout'):
                        stream = encoded(data, name=dest, mime=mime)
                        target = d / 'decoded'
                        if target.exists(): target.unlink()
                        def effect(a):
                            return target.read_bytes() == data and stat.S_IMODE(target.stat().st_mode) == 0o640
                        s.invoke('decode-' + tag + '-' + dest, 'uudecode', [], d, mode,
                                 data=stream, stdout=data if dest != 'decoded' else b'',
                                 check=effect if dest == 'decoded' else None)
            for mime in (False, True):
                stream = b'ignored preamble\n' + encoded(b'payload\n', mime=mime)
                (d / 'encoded').write_bytes(stream)
                s.invoke('decode-file-override-' + str(mime), 'uudecode', ['-o', '-', 'encoded'],
                         d, mode, stdout=b'payload\n')
                s.invoke('encode-stdin-' + str(mime), 'uuencode', (['-m'] if mime else []) + ['decoded'],
                         d, mode, data=b'abc', stdout=re.compile(rb'.*', re.S),
                         check=lambda a, mime=mime: a['stdout'].replace(b'`', b' ') ==
                         encoded(b'abc', mode='600', mime=mime).replace(b'`', b' '))
            for utility in ('uuencode', 'uudecode'):
                args = ['missing', 'decoded'] if utility == 'uuencode' else ['missing']
                s.invoke('missing-file', utility, args, d, mode, status='nonzero',
                         stderr=re.compile(rb'.+', re.S))
                s.invoke('invalid-option', utility, ['-@'], d, mode, status='nonzero',
                         stderr=re.compile(rb'.+', re.S))


def date_cases(s, fake=None):
    # Literal-only formats are safe on the native host and still verify output,
    # unused stdin and all dispatch paths; controlled values need libfaketime.
    for mode in MODES:
        with s.directory() as d:
            s.invoke('date-literal', 'date', ['+literal %% %n %t'], d, mode,
                     data=b'unused\n', stdout=b'literal % \n \t\n')
            s.invoke('date-invalid-option', 'date', ['-@'], d, mode, status='nonzero',
                     stderr=re.compile(rb'.+', re.S))
            if fake:
                env = dict(LD_PRELOAD=fake)
                s.invoke('date-default', 'date', [], d, mode, env=env,
                         stdout=b'Thu Feb 29 12:34:56 UTC 2024\n')
                s.invoke('date-conversions', 'date', ['+%a|%A|%b|%B|%c|%C|%d|%D|%e|%F|%g|%G|%h|%H|%I|%j|%m|%M|%p|%r|%R|%S|%T|%u|%U|%V|%w|%W|%x|%X|%y|%Y|%z|%Z'],
                         d, mode, env=env, stdout=b'Thu|Thursday|Feb|February|Thu Feb 29 12:34:56 2024|20|29|02/29/24|29|2024-02-29|24|2024|Feb|12|12|060|02|34|PM|12:34:56 PM|12:34|56|12:34:56|4|08|09|4|09|02/29/24|12:34:56|24|2024|+0000|UTC\n')
                utc = {**env, 'TZ': 'EST5'}
                s.invoke('date-zone', 'date', ['+%F %T %z'], d, mode, env=utc,
                         stdout=b'2024-02-29 07:34:56 -0500\n')
                s.invoke('date-u-overrides-zone', 'date', ['-u', '+%F %T %z'], d, mode, env=utc,
                         stdout=b'2024-02-29 12:34:56 +0000\n')


def logging_cases(s):
    with s.directory() as d:
        packets_file = d / 'packets.jsonl'
        receiver = s.start(['/usr/bin/python3', str(Path(__file__).with_name('host_service_syslog.py')), str(packets_file)], d)
        def packets():
            if not packets_file.exists(): return []
            # A final partial line is not a complete datagram record yet.
            return [bytes.fromhex(json.loads(line)) for line in packets_file.read_text().splitlines(keepends=True)
                    if line.endswith('\n')]
        try:
            assert wait_for(lambda: Path('/dev/log').exists())
            for mode in MODES:
                for suffix, args, data, messages, priority in (
                    ('operands', ['-t', 'csh078', 'one', 'two'], b'ignored\n', [b'one two'], 13),
                    ('stdin', ['-t', 'csh078'], b'one\ntwo\n', [b'one', b'two'], 13),
                    ('file', ['-t', 'csh078', '-f', 'messages'], b'ignored\n', [b'one', b'two'], 13),
                    ('pid', ['-i', '-t', 'csh078', 'pid'], b'', [b'pid'], 13),
                    ('file-operands', ['-f', 'messages', '-t', 'csh078', 'operand', 'wins'],
                     b'ignored\n', [b'operand wins'], 13),
                    ('file-dash-literal', ['-f', '-', '-t', 'csh078'], b'ignored stdin\n', [b'literal dash file'], 13),
                ):
                    (d / 'messages').write_bytes(b'one\ntwo\n')
                    (d / '-').write_bytes(b'literal dash file\n')
                    before = len(packets())
                    received = []
                    def verify(actual):
                        def collect():
                            received[:] = [p for p in packets()[before:] if b' csh078' in p]
                            return len(received) >= len(messages)
                        assert wait_for(collect)
                        assert len(received) == len(messages)
                        for packet, message in zip(received, messages):
                            pattern = rb'<' + str(priority).encode() + rb'>[A-Z][a-z]{2} [ 0-9][0-9] [0-9:]{8} csh078'
                            pattern += rb'\[[0-9]+\]' if suffix == 'pid' else rb'(?:\[[0-9]+\])?'
                            assert re.fullmatch(pattern + rb': ' + re.escape(message), packet), packet
                        return True
                    # util-linux diagnoses this combination but logs the operands,
                    # as required. '-' is a literal filename on this provider.
                    diagnostic = (b'logger: --file <file> and <message> are mutually exclusive, message is ignored\n'
                                  if suffix == 'file-operands' else b'')
                    s.invoke('logger-' + suffix, 'logger', args, d, mode, data=data,
                             stderr=diagnostic, check=verify)
                    s.results[-1]['packets'] = serial(received)
                for suffix, args in [('missing-file', ['-f', 'missing']),
                                     ('bad-priority', ['-p', 'not-a-facility.not-a-level']),
                                     ('missing-tag', ['-t'])]:
                    s.invoke('logger-' + suffix, 'logger', args, d, mode,
                             status='nonzero', stderr=re.compile(rb'.+', re.S))
            for facility, number in [('user', 1)] + [(f'local{i}', 16+i) for i in range(8)]:
                for level, severity in zip(('emerg', 'alert', 'crit', 'err', 'warning', 'notice', 'info', 'debug'), range(8)):
                    priority = 8 * number + severity
                    before = len(packets())
                    s.invoke('logger-priority-' + facility + '.' + level, 'logger',
                             ['-t', 'csh078', '-p', facility + '.' + level, 'priority'], d, 'direct',
                             check=lambda a, priority=priority: wait_for(lambda: any(re.fullmatch(
                                 rb'<' + str(priority).encode() + rb'>[^\n]+ csh078(?:\[[0-9]+\])?: priority', packet)
                                 for packet in packets()[before:])))
        finally:
            s.stop(receiver)
            Path('/dev/log').unlink(missing_ok=True)


def messages(user):
    path = Path('/var/mail') / user
    if not path.exists(): return []
    box = mailbox.mbox(path, create=False)
    try: return list(box)
    finally: box.close()


def mail_cases(s):
    Path('/home/cshell/.mailrc').write_text('set sendwait\n')
    os.chown('/home/cshell/.mailrc', 10001, 10001)
    for mode in MODES:
        with s.directory() as d:
            subject = 'CSH078 subject ' + mode
            body = ('first line\nsecond line ' + mode + '\n.\nlast line\n').encode()
            before = {u: len(messages(u)) for u in ('cshell', 'recipient')}
            def delivery(a):
                assert wait_for(lambda: all(len(messages(u)) == before[u] + 1 for u in before))
                for u in before:
                    m = messages(u)[-1]
                    assert str(m['Subject']) == subject
                    assert m.get_payload(decode=True) == body
                    assert {address.split('@')[0] for _, address in getaddresses(m.get_all('To', []))} == {'cshell', 'recipient'}
                    assert getaddresses(m.get_all('From', []))[0][1] == 'cshell@localhost'
                    assert parsedate_to_datetime(m['Date']).utcoffset() is not None
                    assert re.fullmatch(r'<[^<>\s]+@[^<>\s]+>', m['Message-ID'])
                return True
            s.invoke('mail-send-multiple-recipients', 'mailx', ['-s', subject, 'cshell', 'recipient'],
                     d, mode, data=body, check=delivery)
            before = len(messages('recipient'))
            s.invoke('mail-E-empty', 'mailx', ['-E', '-s', 'must-not-arrive', 'recipient'],
                     d, mode, check=lambda a: len(messages('recipient')) == before)
            s.invoke('mail-E-nonempty', 'mailx', ['-E', '-s', subject, 'recipient'],
                     d, mode, data=b'nonempty\n', check=lambda a: wait_for(
                         lambda: len(messages('recipient')) == before + 1) and
                         messages('recipient')[-1].get_payload(decode=True) == b'nonempty\n')
            before = len(messages('recipient'))
            body = b'no subject\nsecond literal line\n'
            s.invoke('mail-default-subject', 'mailx', ['recipient'], d, mode, data=body,
                     check=lambda a: wait_for(lambda: len(messages('recipient')) == before + 1)
                     and messages('recipient')[-1].get_payload(decode=True) == body)
            s.invoke('mail-missing-subject', 'mailx', ['-s'], d, mode, status='nonzero',
                     stderr=re.compile(rb'.+', re.S))


def scheduler_cases(s):
    pending = []
    # Daemon is deliberately stopped until all submissions have been inspected.
    for mode in MODES:
        with s.directory() as d:
            job = b'printf scheduled > result\n'
            (d / 'job').write_bytes(job)
            result = s.invoke('at-submit-file', 'at', ['-f', 'job', '-t', '203012311230'], d, mode,
                             stderr=re.compile(rb'(?:warning: commands will be executed using /bin/sh\n)?job [0-9]+ at Tue Dec 31 12:30:00 2030\n(?:Can\'t open /run/atd.pid to signal atd. No atd running\?\n)?', re.S))
            if result and result['status'] == 0:
                found = re.search(rb'job ([0-9]+) at ', result['stderr'])
                if found:
                    job_id = found[1].decode()
                    s.invoke('at-list-selected', 'at', ['-l', job_id], d, mode,
                             stdout=re.compile(job_id.encode() + rb'\s+Tue Dec 31 12:30:00 2030 a cshell\n'))
                    s.invoke('at-remove', 'at', ['-r', job_id], d, mode)
                    s.invoke('at-list-empty', 'at', ['-l'], d, mode)
            queue_jobs = {}
            for queue in ('a', 'c'):
                submitted = s.invoke('at-submit-queue-' + queue, 'at',
                                     ['-q', queue, '-t', '203012311230'], d, mode, data=job,
                                     stderr=re.compile(rb'(?:warning: commands will be executed using /bin/sh\n)?job [0-9]+ at Tue Dec 31 12:30:00 2030\n(?:Can\'t open /run/atd.pid to signal atd. No atd running\?\n)?'))
                if submitted and submitted['status'] == 0:
                    found = re.search(rb'job ([0-9]+) at ', submitted['stderr'])
                    if found:
                        queue_jobs[queue] = found[1].decode()
            if len(queue_jobs) == 2:
                for queue, job_id in queue_jobs.items():
                    s.invoke('at-list-queue-' + queue, 'at', ['-l', '-q', queue], d, mode,
                             stdout=re.compile(job_id.encode() + rb'\s+Tue Dec 31 12:30:00 2030 '
                                               + queue.encode() + rb' cshell\n'))
                s.invoke('at-remove-multiple', 'at', ['-r', *queue_jobs.values()], d, mode)
                s.invoke('at-queues-empty', 'at', ['-l'], d, mode)
            s.invoke('at-invalid-time', 'at', ['-t', 'invalid'], d, mode,
                     status='nonzero', stderr=re.compile(rb'.+', re.S))
            # No job is allowed to escape the private container. The kept roots
            # remain alive until daemon effects and cleanup have been checked.
    with s.directory() as root:
        for mode in MODES:
            for utility in ('at', 'batch'):
                d = root / (utility + '-' + mode); d.mkdir(); os.chown(d, 10001, 10001)
                token = utility + '-' + mode
                probe = d / 'context.py'
                probe.write_text('import json, os\nfrom pathlib import Path\n'
                                 'parent = os.getppid()\n'
                                 'fields = Path(f"/proc/{parent}/stat").read_text().rsplit(")", 1)[1].split()\n'
                                 'Path("context.json").write_text(json.dumps(dict(parent=parent, '
                                 'pgrp=int(fields[2]), session=int(fields[3]), tty=int(fields[4]), '
                                 'uid=os.getuid(), gid=os.getgid())))\n')
                code = ('printf "%s\\n" "$CSH078_VALUE" > result\npwd >> result\numask >> result\n'
                        'printf "' + token + '\\n"\nprintf "error-' + token + '\\n" >&2\n')
                code += '/usr/bin/python3 ' + shlex.quote(str(probe)) + '\n:\n'
                result = s.invoke(utility + '-submit-execution', utility,
                                  ['-m', 'now'] if utility == 'at' else [], d, mode,
                                  data=code.encode(), env={'CSH078_VALUE': token},
                                  stderr=re.compile(rb'(?:warning: commands will be executed using /bin/sh\n)?job [0-9]+ at [^\n]+\n(?:Can\'t open /run/atd.pid to signal atd. No atd running\?\n)?', re.S))
                pending.append((d, token, result))
        daemon = s.start(['/usr/sbin/atd', '-f', '-l', '1000000', '-b', '1'], root)
        for d, token, submission in pending:
            ok = wait_for(lambda: (d / 'result').exists() and len((d / 'result').read_bytes().splitlines()) == 3, 20)
            actual = (d / 'result').read_bytes() if (d / 'result').exists() else b''
            expected = (token + '\n' + str(d) + '\n0077\n').encode()
            s.record('scheduled-effects/' + token, token.split('-')[0], ok and actual == expected,
                     expected=expected, actual=actual)
            context_file = d / 'context.json'
            ready = wait_for(context_file.exists)
            context = json.loads(context_file.read_text()) if ready else {}
            # Compare with the submitting process group (call() starts a new
            # session), not the service daemon's group. POSIX separates the
            # job from its invoking environment, not from other daemon jobs.
            s.record('scheduled-process-context/' + token, token.split('-')[0],
                     ready and submission is not None and submission['status'] == 0
                     and not submission['failure'] and context.get('pgrp', 0) > 0
                     and context.get('pgrp') not in (os.getpgrp(), (submission or {}).get('pid'))
                     and context.get('tty') == 0 and context.get('uid') == 10001
                     and context.get('gid') == 10001, actual=context,
                     submitting_group=(submission or {}).get('pid'), observer_group=os.getpgrp())
            arrived = wait_for(lambda: any((token + '\n').encode() in (m.get_payload(decode=True) or b'') and
                                           ('error-' + token + '\n').encode() in (m.get_payload(decode=True) or b'')
                                           for m in messages('cshell')), 10)
            s.record('scheduled-mail/' + token, token.split('-')[0], arrived)
        # -m is required by the definition of batch even for a silent job.
        for utility in ('at', 'batch'):
            count = len(messages('cshell'))
            s.invoke(utility + '-silent-submit', utility, ['-m', 'now'] if utility == 'at' else [],
                     root, 'direct', data=b':\n', stderr=re.compile(rb'(?:warning: commands will be executed using /bin/sh\n)?job [0-9]+ at [^\n]+\n(?:Can\'t open /run/atd.pid to signal atd. No atd running\?\n)?', re.S))
            s.record('silent-completion-mail/' + utility, utility,
                     wait_for(lambda: len(messages('cshell')) == count + 1, 10))
        s.invoke('scheduler-queue-cleanup', 'at', ['-l'], root, 'direct')
        s.stop(daemon)


def cron_cases(s):
    with s.directory() as d:
        for mode in MODES:
            table = b'# retained comment\n\n0,30 0-23 * * 0-6 echo scheduled\n'
            (d / 'table').write_bytes(table)
            s.invoke('crontab-install-file', 'crontab', ['table'], d, mode)
            s.invoke('crontab-list-file', 'crontab', ['-l'], d, mode, stdout=table)
            replacement = b'# replacement\n* * * * * echo replacement\n'
            s.invoke('crontab-replace-stdin', 'crontab', [], d, mode, data=replacement)
            s.invoke('crontab-list-replacement', 'crontab', ['-l'], d, mode, stdout=replacement)
            s.invoke('crontab-missing-file', 'crontab', ['missing'], d, mode,
                     status='nonzero', stderr=re.compile(rb'.+', re.S))
            s.invoke('crontab-preserve-on-error', 'crontab', ['-l'], d, mode, stdout=replacement)
            s.invoke('crontab-remove', 'crontab', ['-r'], d, mode)
            s.invoke('crontab-no-table', 'crontab', ['-l'], d, mode, status='nonzero',
                     stderr=re.compile(rb'.+', re.S))
        # Real cron delivery on one minute boundary; bounded independently of the
        # command timeout. Never changes host time. All syntax uses the base grammar.
        table = ('* * * * * /usr/bin/env > ' + str(d / 'environment') + '\n'
                 '* * * * * /bin/cat > ' + str(d / 'percent') + '%one%two\n'
                 '* * * * * echo csh078-cron-mail\n')
        s.invoke('crontab-execution-submit', 'crontab', [], d, 'command', data=table.encode(),
                 env={'HOME': '/wrong', 'LOGNAME': 'wrong', 'PATH': s.search, 'SHELL': '/wrong'})
        daemon = s.start(['/usr/sbin/cron', '-f'], d)
        try:
            ready = wait_for(lambda: (d / 'environment').exists() and (d / 'percent').exists(), 75)
            actual = (d / 'environment').read_text() if (d / 'environment').exists() else ''
            environment = dict(line.split('=', 1) for line in actual.splitlines() if '=' in line)
            expected = {'HOME': '/home/cshell', 'LOGNAME': 'cshell', 'SHELL': '/bin/sh'}
            s.record('cron-environment', 'crontab', ready and all(environment.get(k) == v for k, v in expected.items())
                     and bool(environment.get('PATH')), actual=environment, expected=expected)
            data = (d / 'percent').read_bytes() if (d / 'percent').exists() else b''
            s.record('cron-percent-stdin', 'crontab', ready and data == b'one\ntwo\n', actual=data)
            s.record('cron-mail', 'crontab', wait_for(lambda: any(b'csh078-cron-mail\n' in
                     (m.get_payload(decode=True) or b'') for m in messages('cshell')), 10))
        finally:
            s.invoke('crontab-final-remove', 'crontab', ['-r'], d, 'direct')
            s.stop(daemon)


def print_cases(s):
    spool = Path('/tmp/csh078-print'); spool.mkdir(mode=0o777); spool.chmod(0o777)
    backend = Path('/usr/lib/cups/backend/csh078')
    backend.write_text('''#!/usr/bin/python3
import json, os, pathlib, sys
if len(sys.argv) == 1:
 print('direct csh078:/sink "CSH078" "Disposable byte sink"')
 sys.exit(0)
data = pathlib.Path(sys.argv[6]).read_bytes() if len(sys.argv) > 6 else sys.stdin.buffer.read()
root = pathlib.Path('/tmp/csh078-print')
key = sys.argv[1]
(root / (key + '.data')).write_bytes(data)
(root / (key + '.json')).write_text(json.dumps(dict(job=key, user=sys.argv[2], title=sys.argv[3], copies=int(sys.argv[4]), options=sys.argv[5], uri=os.environ.get('DEVICE_URI'))))
''')
    backend.chmod(0o755)
    Path('/run/cups').mkdir(exist_ok=True)
    conf = Path('/etc/cups/cupsd.conf')
    conf.write_text('''Listen /run/cups/cups.sock
Browsing Off
WebInterface No
DefaultAuthType Basic
PreserveJobHistory Yes
PreserveJobFiles Yes
<Location />
Order allow,deny
Allow all
</Location>
''')
    with s.directory() as d:
        daemon = s.start(['/usr/sbin/cupsd', '-f'], d)
        try:
            assert wait_for(lambda: Path('/run/cups/cups.sock').exists()), 'CUPS socket not ready'
            setup = s.call(['/usr/sbin/lpadmin', '-p', 'sink', '-E', '-v', 'csh078:/sink', '-m', 'raw'], d, user=False)
            assert setup['status'] == 0, setup
            setup = s.call(['/usr/sbin/lpadmin', '-p', 'other', '-E', '-v', 'csh078:/other', '-m', 'raw'], d, user=False)
            assert setup['status'] == 0 and not setup['failure'], setup
            setup = s.call(['/usr/sbin/lpadmin', '-d', 'sink'], d, user=False)
            assert setup['status'] == 0, setup
            for mode in MODES:
                for suffix, args, data in (
                    ('stdin', [], b'print stdin\n'),
                    ('dash', ['-'], b'print dash\n'),
                    ('file', ['-c', '-d', 'sink', '-n', '2', '-t', 'CSH078 title', '-o', 'raw', '-o', 'job-sheets=none', 'document'], b''),
                    ('silent', ['-s', 'document'], b''),
                ):
                    source = d / 'document'; source.write_bytes(b'print file\n')
                    before = set(spool.glob('*.json'))
                    if suffix == 'file':
                        paused = s.call(['/usr/sbin/cupsdisable', 'sink'], d, user=False)
                        assert paused['status'] == 0 and not paused['failure'], paused
                    expected = data if suffix in ('stdin', 'dash') else b'print file\n'
                    def effect(a):
                        # -c permits immediate modification after lp returns.
                        if suffix == 'file':
                            source.write_bytes(b'changed after submission\n')
                            resumed = s.call(['/usr/sbin/cupsenable', 'sink'], d, user=False)
                            assert resumed['status'] == 0 and not resumed['failure'], resumed
                        assert wait_for(lambda: bool(set(spool.glob('*.json')) - before)), 'backend did not receive job'
                        paths = set(spool.glob('*.json')) - before
                        assert len(paths) == 1
                        path = paths.pop(); metadata = json.loads(path.read_text())
                        assert path.with_suffix('.data').read_bytes() == expected
                        if suffix == 'file':
                            assert metadata['copies'] == 2 and metadata['title'] == 'CSH078 title'
                        s.results.append(dict(name='print-backend/' + mode + '/' + suffix,
                                              utility='lp', owner='CSH-078', verdict='PASS',
                                              source=SOURCE + 'lp.html', actual=metadata))
                        return True
                    s.invoke('lp-' + suffix, 'lp', args, d, mode, data=data,
                             stdout=b'' if suffix == 'silent' else re.compile(rb'request id is sink-[0-9]+ \(' + (b'0' if suffix in ('stdin', 'dash') else b'1') + rb' file\(s\)\)\n'),
                             env={'LPDEST': 'sink'}, check=effect)
                for suffix, args, environment, destination in (
                    ('option-over-env', ['-d', 'sink'], {'LPDEST': 'other', 'PRINTER': 'other'}, 'sink'),
                    ('lpdest-over-printer', [], {'LPDEST': 'sink', 'PRINTER': 'other'}, 'sink'),
                    ('printer-env', [], {'PRINTER': 'other'}, 'other'),
                    ('default-destination', [], {}, 'sink'),
                ):
                    before = set(spool.glob('*.json'))
                    def delivered(a):
                        assert wait_for(lambda: bool(set(spool.glob('*.json')) - before))
                        paths = set(spool.glob('*.json')) - before
                        assert len(paths) == 1
                        path = paths.pop()
                        metadata = json.loads(path.read_text())
                        assert metadata['uri'] == 'csh078:/' + destination
                        assert path.with_suffix('.data').read_bytes() == b'destination control\n'
                        return True
                    s.invoke('lp-' + suffix, 'lp', args, d, mode,
                             data=b'destination control\n', env=environment,
                             stdout=re.compile(rb'request id is ' + destination.encode() + rb'-[0-9]+ \(0 file\(s\)\)\n'),
                             check=delivered)
                s.invoke('lp-missing-file', 'lp', ['missing'], d, mode,
                         status='nonzero', stderr=re.compile(rb'.+', re.S), env={'LPDEST': 'sink'})
            # Drain/cancel owned jobs before stopping the private scheduler.
            cleanup = s.call(['/usr/bin/cancel', '-a'], d, user=False)
            s.record('print-queue-cleanup', 'lp', cleanup['status'] == 0 and not cleanup['failure'], actual=cleanup)
            for destination in ('sink', 'other'):
                removed = s.call(['/usr/sbin/lpadmin', '-x', destination], d, user=False)
                assert removed['status'] == 0 and not removed['failure'], removed
            for mode in MODES:
                s.invoke('lp-no-destination', 'lp', [], d, mode, data=b'no device\n',
                         status='nonzero', stderr=re.compile(rb'.+', re.S))
        finally:
            s.stop(daemon)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('--path', default=os.defpath)
    parser.add_argument('--services', action='store_true')
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    s = Suite(args.binary, args.path, args.services)
    record = dict(schema_version=1, ticket='CSH-078', completed=False, profile='disposable-services' if args.services else 'native-safe',
                  full_contract_qualified=False, platform=platform.platform(), uname=list(platform.uname()),
                  path=args.path, providers=s.providers, shell=dict(path=s.binary, sha256=sha(s.binary)),
                  source_identity=source_identity(), bounds=dict(command_seconds=TIMEOUT, output_bytes=LIMIT, descriptors=1024 if args.services else 64,
                  cron_seconds=75, fixture_bytes=8192), results=s.results)
    if platform.system() == 'Darwin':
        record['os_build'] = subprocess.check_output(['sw_vers'], text=True)
    contract_map = json.loads(Path(__file__).with_name('host_service_contracts.json').read_text())
    record['contract_map'] = contract_map
    try:
        if args.services:
            require_container()
            record['services'] = {p: dict(realpath=os.path.realpath(p), sha256=sha(p)) for p in
                                  ('/usr/sbin/atd', '/usr/sbin/cron', '/usr/sbin/cupsd',
                                   '/usr/sbin/exim4', '/usr/sbin/sendmail', '/bin/sh', '/usr/bin/python3')}
            record['packages'] = subprocess.check_output(['dpkg-query', '-W', '-f=${binary:Package}\t${Version}\n'], text=True)
            record['isolation'] = dict(network='loopback only', sys_time=False,
                                       mountinfo=Path('/proc/self/mountinfo').read_text(),
                                       status=Path('/proc/self/status').read_text())
        print('Running encoding and date witnesses', flush=True)
        encoding_cases(s)
        fake = Path('/work/build/tests/host_service_clock.so') if args.services else None
        if fake and not fake.is_file(): raise RuntimeError('test clock missing')
        if fake: record['clock_provider'] = dict(path=str(fake), sha256=sha(fake))
        date_cases(s, str(fake) if fake else None)
        if args.services:
            for name, function in [('logger', logging_cases), ('mail', mail_cases),
                                   ('scheduler', scheduler_cases), ('cron', cron_cases), ('print', print_cases)]:
                print('Running ' + name + ' witnesses', flush=True)
                try:
                    function(s)
                except (OSError, ValueError, AssertionError, RuntimeError, subprocess.SubprocessError) as e:
                    utility = {'mail': 'mailx', 'scheduler': 'at', 'cron': 'crontab', 'print': 'lp'}.get(name, name)
                    s.record(name + '-setup', utility, False, phase='setup', reason=str(e))
        else:
            record['unavailable_capabilities'] = ['No developer-host service invocation', 'No controlled native clock']
        # Every declared prefix must have actually run; a swallowed setup error
        # or accidental fixture deletion cannot leave a profile qualified.
        for row in contract_map['utilities']:
            if not args.services and row['utility'] not in ('date', 'uuencode', 'uudecode'):
                continue
            for prefix in row['case_prefixes']:
                if not args.services and prefix in ('date-default/', 'date-conversions/', 'date-zone/', 'date-u-overrides-zone/'):
                    continue
                if not any(r['utility'] == row['utility'] and r['name'].startswith(prefix) for r in s.results):
                    s.record('missing-witness/' + prefix, row['utility'], False, phase='setup', reason='declared witness not executed')
        record['completed'] = True
    except KeyboardInterrupt:
        s.record('profile-interrupted', 'date', False, phase='setup', reason='interrupted before completion')
    except (OSError, ValueError, AssertionError, RuntimeError, subprocess.SubprocessError) as e:
        s.record('profile-setup', 'date', False, phase='setup', reason=str(e))
    finally:
        s.stop()
        record['summary'] = {v: sum(r['verdict'] == v for r in s.results) for v in ('PASS', 'FAIL')}
        record['qualified_subset'] = record['completed'] and record['summary']['FAIL'] == 0
        args.record.parent.mkdir(parents=True, exist_ok=True)
        args.record.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record['summary']), flush=True)
    return int(record['summary']['FAIL'] != 0)


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
