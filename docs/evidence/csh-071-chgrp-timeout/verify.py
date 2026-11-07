"""Audit focused replays without claiming the historical stall is resolved."""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(name):
    with gzip.open(ROOT / (name + '.json.gz'), 'rt') as stream:
        return json.load(stream)

identity = read('identity')
assert identity['original_binary_matches'] and identity['original_chgrp_matches']
for name, expected in [('before-probe', 80), ('probe', 320)]:
    rows = read(name)
    assert len(rows) == expected
    assert all(c['verdict'] == 'PASS' and c['cleanup'] for c in rows)
    assert {c['mode'] for c in rows} == {'direct', 'string', 'file', 'stdin'}
    if name == 'probe':
        assert all(c['process']['reaped'] and c['process']['returncode'] == 0 for c in rows)
data = read('permissions')
assert data['totals'] == {'pass': 980, 'fail': 0}
assert all(c['cleanup'] and c['process']['reaped'] for c in data['cases'])
for name in ('harness', 'linux-harness'):
    with gzip.open(ROOT / (name + '.log.gz'), 'rt') as stream:
        log = stream.read()
    assert 'Ran 88 tests' in log and 'Ran 6 tests' in log and 'FAILED' not in log
with gzip.open(ROOT / 'baseline-regression.log.gz', 'rt') as stream:
    assert 'pipe cleanup could not reap leader within 1s' in stream.read()
print('PASS: same binaries, strict replays, reaped leaders and cleanup regression')
