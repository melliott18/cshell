#!/usr/bin/env python3
"""Linux-root regression for the actual nested credential/utility probe path."""
import argparse
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import tempfile
import time

from host_platform_probe import command
from host_utilities import source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != 'Linux' or os.geteuid() != 0:
        parser.error('requires disposable Linux root; no accounts are modified')
    rows = []
    for kind in ('slow', 'forked', 'normal'):
        pids = []
        with tempfile.TemporaryDirectory(prefix='csh-probe-timeout-') as temporary:
            directory = Path(temporary)
            directory.chmod(0o755)
            target = directory / 'owned'
            target.write_bytes(b'private')
            os.chown(target, 10001, 10002)
            target.chmod(0o400)
            pidfile = directory / 'pids'
            pidfile.touch()
            pidfile.chmod(0o666)
            utility = directory / 'selected-chmod'
            script = ('#!' + sys.executable + '\nimport json,os,time\n'
                      'from pathlib import Path\n'
                      'path=Path(' + repr(str(pidfile)) + ')\n'
                      'pids=[os.getpid()]\n')
            if kind == 'forked':
                script += ('child=os.fork()\n'
                           'if child == 0:\n'
                           ' time.sleep(30)\n'
                           ' os._exit(0)\n'
                           'pids.append(child)\n')
            script += ('path.write_text(json.dumps(dict(pids=pids,uid=os.getuid(),euid=os.geteuid(),'
                       'gid=os.getgid(),egid=os.getegid(),groups=os.getgroups())))\n')
            script += 'time.sleep(30)\n' if kind != 'normal' else 'print("control")\n'
            utility.write_text(script)
            utility.chmod(0o755)
            # A child outside the probe's process group must not be signalled/reaped.
            unrelated = subprocess.Popen(['/bin/sleep', '30'])
            try:
                started = time.monotonic()
                result = command([sys.executable, str(Path(__file__).with_name('host_platform_probe.py').resolve()),
                                  '_chmod-child', '10002', str(target), str(utility)])
                elapsed = time.monotonic() - started
                measured = json.loads(pidfile.read_text())
                pids = measured['pids']
                remaining = [pid for pid in pids if Path(f'/proc/{pid}').exists()]
                correct_ids = all(measured[key] == 10002 for key in ('uid', 'euid', 'gid', 'egid')) and not measured['groups']
                if kind == 'normal':
                    child = json.loads(bytes.fromhex(result['stdout']['hex']))
                    outcome = result['status'] == 0 and child['utility']['stdout'] == {'hex': b'control\n'.hex()}
                else:
                    outcome = result.get('timeout_seconds') == 5 and result['status'] is None
                ok = (outcome and correct_ids and not remaining and unrelated.poll() is None
                      and elapsed < 8 and not result.get('cleanup_errors'))
                rows.append(dict(name=kind, verdict='PASS' if ok else 'FAIL',
                                 elapsed_seconds=round(elapsed,3), command=result,
                                 measured=measured, remaining_pids=remaining,
                                 unrelated_alive=unrelated.poll() is None))
            finally:
                # Also clean up when this test is run against the defective source.
                if not pids and pidfile.read_text():
                    pids = json.loads(pidfile.read_text())['pids']
                for pid in pids:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                unrelated.kill()
                unrelated.wait(timeout=1)
    result = dict(source_identity=source_identity(), platform=platform.platform(),
                  cases=rows, totals=dict(passed=sum(r['verdict']=='PASS' for r in rows),
                                         failed=sum(r['verdict']=='FAIL' for r in rows)))
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result['totals']))
    return int(bool(result['totals']['failed']))


if __name__ == '__main__':
    raise SystemExit(main())
