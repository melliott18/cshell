"""Check retained observations without treating non-reproduction as a fix."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(name):
    return json.loads(gzip.decompress((ROOT / (name + '.json.gz')).read_bytes()))

identity = read('identity')
old = json.loads(gzip.decompress((ROOT.parent / 'csh-071-chgrp-timeout/identity.json.gz').read_bytes()))
assert identity['binary_sha256'] == old['binary_sha256']
assert identity['chgrp_sha256'] == old['provider']['sha256']
for path, digest in identity['probe_files'].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
for name in ('replay', 'early'):
    rows = read(name)
    assert len(rows) == 1000
    assert all(r['verdict'] == 'PASS' and r['cleanup'] and r['process']['reaped']
               and r['process']['returncode'] == 0 for r in rows)
    assert sum(r['shell'] == '/bin/sh' for r in rows) == 200
    assert {r['mode'] for r in rows} == {'direct', 'string', 'file', 'stdin'}
    assert {r['operand'] for r in rows} == {'staff', '20'}
control = read('observer-control')
assert json.loads(control['control.json'])['reaped']
assert any(name.endswith('.txt') and 'Call graph:' in text for name, text in control.items())
for name, count in [('harness', 31), ('linux-harness', 31), ('permissions-harness', 6)]:
    log = gzip.decompress((ROOT / (name + '.log.gz')).read_bytes()).decode()
    assert f'Ran {count} tests' in log and '\nOK\n' in log and 'FAILED' not in log
baseline = gzip.decompress((ROOT / 'baseline-regression.log.gz').read_bytes()).decode()
assert "KeyError: 'timeout_group'" in baseline and 'FAILED' in baseline
print('PASS: 2,000 strict replays, same binaries, observer control and group diagnostics regression')
