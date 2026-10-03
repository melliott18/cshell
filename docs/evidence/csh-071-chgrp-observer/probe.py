"""Observe slow owned chgrp sessions without changing their five-second limit."""
import argparse
import grp
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2))
    temporary.replace(path)


def observe(out):
    seen = set()
    samplers = []
    while not (out / 'stop').exists():
        now = time.monotonic()
        for proc, log, started in samplers[:]:
            if proc.poll() is not None or now - started > 2:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
                log.close()
                samplers.remove((proc, log, started))
        try:
            active = json.loads((out / 'active.json').read_text())
        except (OSError, ValueError):
            time.sleep(.02)
            continue
        pid = active['pid']
        if pid in seen or now - active['started'] < .25:
            time.sleep(.02)
            continue
        seen.add(pid)
        try:
            if os.getsid(pid) != pid:
                continue
            result = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,pgid=,stat=,wchan=,comm='],
                                    capture_output=True, text=True, timeout=.5)
            rows = [row for row in result.stdout.splitlines()
                    if len(row.split()) >= 6 and row.split()[2] == str(pid)]
            save(out / f'slow-{pid}.json', dict(active, observed_seconds=time.monotonic()-active['started'],
                                              ps_status=result.returncode, processes=rows))
            for row in rows:
                member = int(row.split()[0])
                if os.getsid(member) != pid or os.getpgid(member) != pid:
                    continue
                log = (out / f'sample-{pid}-{member}.log').open('w')
                proc = subprocess.Popen(['/usr/bin/sample', str(member), '1', '1', '-file',
                                         str(out / f'sample-{pid}-{member}.txt')], stdout=log, stderr=log)
                samplers.append((proc, log, time.monotonic()))
        except (OSError, subprocess.SubprocessError) as error:
            save(out / f'observer-error-{pid}.json', dict(error=str(error), active=active))
    for proc, log, started in samplers:
        if proc.poll() is None:
            proc.kill()
        proc.wait()
        log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observe', type=Path)
    parser.add_argument('--output', type=Path, default=Path('build/chgrp-stall-followup/replay'))
    parser.add_argument('--rounds', type=int, default=100)
    args = parser.parse_args()
    if args.observe:
        observe(args.observe)
        return
    root = Path.cwd()
    sys.path.insert(0, str(root / 'tests'))
    import smoke
    from host_permissions import run_case
    from host_permission_cases import case
    from host_utilities import inventory
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    observer = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--observe', str(out)])
    original = subprocess.Popen
    records = []
    current = {}

    class ObservedPopen(original):
        def __init__(self, *positional, **kwargs):
            started = time.monotonic()
            super().__init__(*positional, **kwargs)
            if kwargs.get('start_new_session'):
                save(out / 'active.json', dict(current, pid=self.pid, started=started,
                                              spawn_seconds=time.monotonic()-started))

    smoke.subprocess.Popen = ObservedPopen
    search = str(root / 'build/host-profile/bin') + ':' + os.defpath
    providers = inventory(search, names=('chgrp',))
    gid = os.getegid()
    try:
        for repeat in range(args.rounds):
            for operand in (grp.getgrgid(gid).gr_name, str(gid)):
                for shell, mode in [('cshell', 'direct'), ('cshell', 'string'), ('cshell', 'file'),
                                    ('cshell', 'stdin'), ('/bin/sh', 'string')]:
                    current.update(repeat=repeat, operand=operand, shell=shell, mode=mode)
                    expected = case('chgrp', 'observe-'+operand, [operand, 'subject', 'data'],
                                    metadata={p: {'uid': os.geteuid(), 'gid': gid} for p in ('subject', 'data')})
                    started = time.monotonic()
                    result = run_case(root / shell if shell == 'cshell' else Path(shell), providers,
                                      search, expected, mode, Path(tempfile.gettempdir()))
                    result.update(current, elapsed=time.monotonic()-started)
                    records.append(result)
                    save(out / 'results.json', records)
                    if result['verdict'] != 'PASS':
                        print('FAIL', current, result.get('actual'), flush=True)
                        return
            if repeat % 5 == 0:
                print('round', repeat+1, 'cases', len(records), 'max', max(r['elapsed'] for r in records), flush=True)
    finally:
        subprocess.Popen = original
        (out / 'stop').touch()
        try:
            observer.wait(timeout=5)
        except subprocess.TimeoutExpired:
            observer.kill()
            observer.wait()
        print('finished', len(records), 'cases;', len(list(out.glob('slow-*.json'))), 'slow snapshots', flush=True)


if __name__ == '__main__':
    main()
