"""Run every unchanged generated runtime fixture in four bounded harnesses."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

root = Path('/evidence')
source = Path('build/tests/runtime.json')
suite = json.loads(source.read_text())
cases = suite['cases']
assert len({case['name'] for case in cases}) == len(cases)
manifest = {'suite_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'case_count': len(cases), 'batches': []}
children = []
started = time.monotonic()
for index in range(4):
    selected = cases[index::4]
    batch = dict(suite, cases=selected)
    path = Path(f'build/tests/csh057-runtime-batch-{index}.json')
    path.write_text(json.dumps(batch))
    assert json.loads(path.read_text())['cases'] == selected
    log = (root / f'docker-sanitizer-runtime-{index}.log').open('w')
    argv = [sys.executable, 'tests/smoke.py', './cshell', '--suite', str(path)]
    process = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
    children.append((process, log))
    manifest['batches'].append({'index': index, 'argv': argv,
        'case_names': [case['name'] for case in selected],
        'suite_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
# Every fixture retains smoke.py's five-second execution and bounded cleanup.
# This whole-run budget is additional; the dedicated container is the final
# cleanup boundary if an outer runner fails, never an unrelated host session.
for index, (process, log) in enumerate(children):
    try:
        status = process.wait(timeout=max(1, 1200 - (time.monotonic() - started)))
    except subprocess.TimeoutExpired:
        status = 'timeout'
    log.close()
    manifest['batches'][index]['exit_status'] = status
manifest['elapsed_seconds'] = time.monotonic() - started
assert sum(len(batch['case_names']) for batch in manifest['batches']) == len(cases)
assert set().union(*(set(batch['case_names']) for batch in manifest['batches'])) == {case['name'] for case in cases}
(root / 'docker-sanitizer-runtime-batches.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps({k: v for k, v in manifest.items() if k != 'batches'}), flush=True)
print('batch exit statuses:', [batch['exit_status'] for batch in manifest['batches']], flush=True)
raise SystemExit(any(batch['exit_status'] != 0 for batch in manifest['batches']))
