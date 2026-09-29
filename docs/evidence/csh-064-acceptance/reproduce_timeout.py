"""Reproduce the nested timeout in a disposable Linux root container only.

The supplied checkout is read-only. All files and processes here are private.
Exit zero means the defect was reproduced and the surviving utility was killed;
it is NOT a passing timeout-cleanup assertion.
"""
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import sys
import tempfile
import time

if platform.system() != 'Linux' or os.geteuid() != 0:
    raise SystemExit('requires a disposable Linux root container')
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'tests'))
from host_platform_probe import command
from host_utilities import source_identity

result = dict(source_identity=source_identity(), platform=platform.platform(),
              python=sys.version, expected='selected utility is terminated before timeout returns',
              verdict='UNOBSERVED', cleanup='no utility launched')
pid = None
with tempfile.TemporaryDirectory(prefix='csh064-review-') as temporary:
    directory = Path(temporary)
    directory.chmod(0o755)
    target = directory / 'owned'
    target.write_bytes(b'private')
    os.chown(target, 10001, 10002)
    target.chmod(0o400)
    pidfile = directory / 'pid'
    pidfile.touch(mode=0o666)
    pidfile.chmod(0o666)
    slow = directory / 'slow-chmod'
    slow.write_text('#!' + sys.executable + '\nimport os,time\nfrom pathlib import Path\n'
                    + 'Path(' + repr(str(pidfile)) + ').write_text(str(os.getpid()))\n'
                    + 'time.sleep(30)\n')
    slow.chmod(0o755)
    result['selected_fixture'] = dict(path=str(slow), sha256=hashlib.sha256(slow.read_bytes()).hexdigest(),
                                      sleep_seconds=30, identity=10002)
    try:
        start = time.monotonic()
        result['command'] = command([sys.executable, str(root / 'tests/host_platform_probe.py'),
                                     '_chmod-child', '10002', str(target), str(slow)])
        result['elapsed_seconds'] = round(time.monotonic() - start, 3)
        pid = int(pidfile.read_text())
        status = Path(f'/proc/{pid}/status')
        lines = status.read_text().splitlines() if status.exists() else []
        state = next((line for line in lines if line.startswith('State:')), 'absent')
        result['utility_after_timeout'] = dict(pid=pid, state=state,
            credentials=[line for line in lines if line.startswith(('Uid:', 'Gid:', 'Groups:', 'CapEff:'))])
        alive = state != 'absent' and not state.startswith('State:\tZ')
        result['utility_alive_after_timeout'] = alive
        result['verdict'] = 'FAIL' if alive else 'PASS'
    finally:
        if pid is None and pidfile.read_text().strip():
            pid = int(pidfile.read_text())
        if pid is not None:
            try:
                os.kill(pid, signal.SIGKILL)
                result['cleanup'] = 'review sent SIGKILL to its surviving utility; container init reaps it'
            except ProcessLookupError:
                result['cleanup'] = 'utility already exited'
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['verdict'] == 'FAIL' else 1)
