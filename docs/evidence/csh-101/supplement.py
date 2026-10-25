"""Rerun utility-dependent behavior under the changed opt-in provider profile."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

label = sys.argv[1]
output = Path('build/csh101-supplement')
output.mkdir(exist_ok=True)
env = dict(os.environ, PATH=str(Path('build/host-profile/bin').resolve()) + ':' + os.environ['PATH'])
commands = [
    ['make', 'test-runtime', 'test-runtime-pty', 'test-harness'],
    [sys.executable, 'docs/evidence/csh-101/sanitize.py', label],
]
records = []
for index, command in enumerate(commands):
    start = time.monotonic()
    log = output / (label + '-supplement-' + str(index) + '.log')
    with log.open('wb') as stream:
        result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT)
    records.append(dict(argv=command, path=env['PATH'], status=result.returncode,
                        seconds=time.monotonic()-start, log=log.name))
    (output / (label + '-supplement-commands.json')).write_text(json.dumps(records,indent=2)+'\n')
    print(label, index, result.returncode, flush=True)
raise SystemExit(any(r['status'] for r in records))
