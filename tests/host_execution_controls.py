"""Disposable Linux credential and virtual-duration controls for CSH-075."""
import errno
import json
import os
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import tempfile

import smoke
from host_utilities import serial, sha


def duration_total(text):
    """Allow any chunking, but require normalized nonnegative timespecs."""
    try:
        calls = [tuple(map(int, line.split())) for line in text.splitlines()] if text else []
        if not calls or not all(len(call) == 2 and call[0] >= 0 and 0 <= call[1] < 10**9 for call in calls):
            return None
        return sum(sec * 10**9 + ns for sec, ns in calls)
    except ValueError:
        return None


def clock_cases(binary, providers, library, search_path):
    rows = []
    for seconds in (1, 2147483647, 2147483648, 4294967295):
        for mode in ('direct', 'shell'):
            with tempfile.TemporaryDirectory(prefix='csh-clock-') as temporary:
                directory = Path(temporary)
                record = directory / 'clock'
                target = providers['sleep']['path'] if mode == 'direct' else binary
                args = [str(seconds)] if mode == 'direct' else ['-c', 'sleep ' + shlex.quote(str(seconds))]
                fixture = dict(args=args, stdin='', env={'PATH': search_path,
                    'LD_PRELOAD': str(library), 'CSH_CLOCK_RECORD': str(record)})
                try:
                    status, output, errors = smoke.capture(target, fixture, directory, 3, 65536)
                    observed = record.read_text() if record.exists() else None
                    total = duration_total(observed)
                    ok = status == 0 and not any(output.values()) and not errors and total == seconds * 10**9
                    rows.append(dict(id=f'sleep/virtual-duration-{seconds}', mode=mode,
                                     verdict='PASS' if ok else 'FAIL', phase='assertion',
                                     expected_nanoseconds=seconds * 10**9, observed=observed, total_nanoseconds=total,
                                     actual=serial(dict(status=status, **output, errors=errors)),
                                     clock_library=dict(path=str(library), sha256=sha(library))))
                except (OSError, subprocess.SubprocessError) as error:
                    rows.append(dict(id=f'sleep/virtual-duration-{seconds}', mode=mode,
                                     verdict='FAIL', phase='setup', reason=str(error)))
    return rows


def credential_cases(binary, helper, providers, search_path):
    """All signals name a still-owned PID. No UID/group-wide signalling occurs."""
    rows = []
    for same_user in (True, False):
        for mode in ('direct', 'shell'):
            process = None
            with tempfile.TemporaryDirectory(prefix='csh-credentials-') as temporary:
                directory = Path(temporary)
                directory.chmod(0o755)
                row = dict(id='kill/credential-' + ('allow' if same_user else 'deny'),
                           mode=mode, verdict='FAIL', phase='setup')
                try:
                    def target_ids():
                        os.setgroups([])
                        os.setgid(60001)
                        os.setuid(60001)
                    process = subprocess.Popen([str(helper), 'park'], stdout=subprocess.PIPE,
                                               stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                                               start_new_session=True, preexec_fn=target_ids)
                    with selectors.DefaultSelector() as selector:
                        selector.register(process.stdout, selectors.EVENT_READ)
                        if not selector.select(2) or process.stdout.readline() != b'ready\n':
                            raise RuntimeError('owned credential child did not become ready')
                    status_text = Path(f'/proc/{process.pid}/status').read_text()
                    credentials = {line.split(':')[0]: line.split(':')[1].split()
                                   for line in status_text.splitlines() if line.startswith(('Uid:', 'Gid:', 'Groups:', 'CapEff:'))}
                    if (credentials['Uid'] != ['60001'] * 4 or credentials['Gid'] != ['60001'] * 4
                            or credentials['Groups'] or int(credentials['CapEff'][0], 16)):
                        raise RuntimeError('target identity/capability check failed')
                    uid = 60001 if same_user else 60002
                    command = [providers['kill']['path'], '-s', '0', str(process.pid)] if mode == 'direct' else [str(binary), '-c', f'kill -s 0 {process.pid}']
                    fixture = dict(args=['drop-exec', str(uid)] + command, stdin='', env={'PATH': search_path})
                    status, output, errors = smoke.capture(helper, fixture, directory, 5, 65536)
                    caller = json.loads((directory / 'caller.json').read_text())
                    actual_ids = caller == dict(uid=uid, euid=uid, gid=uid, egid=uid, groups=0)
                    ok = actual_ids and process.poll() is None and not errors and not output['stdout']
                    ok &= (status == 0 and not output['stderr']) if same_user else (status > 0 and bool(output['stderr']))
                    row.update(verdict='PASS' if ok else 'FAIL', phase='assertion', target_credentials=credentials,
                               caller=caller, actual=serial(dict(status=status, **output, errors=errors)))
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                    row.update(reason=str(error))
                finally:
                    if process is not None:
                        if process.poll() is None:
                            process.kill()
                        process.wait(timeout=2)
                        process.stdout.close()
                        row['owned_cleanup'] = dict(pid=process.pid, reaped=True)
                rows.append(row)
    with tempfile.TemporaryDirectory(prefix='csh-process-limit-') as temporary:
        status, output, errors = smoke.capture(helper, dict(args=['fork-limit'], stdin=''),
                                               Path(temporary), 5, 65536)
        try:
            actual = json.loads(bytes(output['stdout']))
            ok = (status == 0 and not output['stderr'] and not errors and actual['fork_rejected']
                  and actual['uid'] == actual['euid'] == 60003 and actual['errno'] == errno.EAGAIN)
        except (ValueError, KeyError):
            ok = False
        rows.append(dict(id='kill/disposable-process-limit', verdict='PASS' if ok else 'FAIL',
                         phase='capability', actual=serial(dict(status=status, **output, errors=errors)),
                         boundary='child RLIMIT_NPROC=0, no process flood; not a utility fault injection'))
    return rows
