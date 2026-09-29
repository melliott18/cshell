"""Verify scoped CSH-064 cleanup acceptance without waiving platform failures."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parents[2] / 'tests'))
from host_utilities import source_identity
source = source_identity()
before = json.loads((root / 'timeout-before.json').read_text())
after = json.loads((root / 'timeout-after.json').read_text())
assert before['totals'] == dict(passed=1, failed=2)
assert after['totals'] == dict(passed=3, failed=0)
assert [r['verdict'] for r in before['cases']] == ['FAIL', 'FAIL', 'PASS']
assert all(r['remaining_pids'] for r in before['cases'][:2])
assert before['source_identity']['files']['tests/host_probe_timeout.py'] == source['files']['tests/host_probe_timeout.py']
assert before['source_identity']['files']['tests/host_platform_probe.py'] != source['files']['tests/host_platform_probe.py']
assert after['source_identity']['sha256'] == source['sha256']
for row in after['cases']:
    assert row['verdict'] == 'PASS' and not row['remaining_pids'] and row['unrelated_alive']
    assert row['elapsed_seconds'] < 8 and not row['command'].get('cleanup_errors')
    assert not row['measured']['groups']
    assert all(row['measured'][key] == 10002 for key in ('uid','euid','gid','egid'))
    if row['name'] != 'normal':
        assert row['command']['status'] is None and row['command']['timeout_seconds'] == 5
compatibility = json.loads((root / 'timeout-python311.json').read_text())
assert compatibility['totals'] == dict(passed=3, failed=0)
assert compatibility['source_identity']['sha256'] == source['sha256']
assert all(not row['remaining_pids'] and row['unrelated_alive'] for row in compatibility['cases'])
for name, totals in [('overlay', dict(passed=8, failed=0)), ('bind', dict(passed=3, failed=5))]:
    record = json.loads((root / (name + '.json')).read_text())
    assert record['totals'] == totals
    assert record['source_identity']['sha256'] == source['sha256']
    assert sum(c['verdict'] == 'FAIL' for c in record['cases']) == totals['failed']
for host in ('native', 'linux'):
    record = json.loads((root / (host + '-identity.json')).read_text())
    assert record['source_identity']['sha256'] == source['sha256']
    log = gzip.decompress((root / (host + '-integration.log.gz')).read_bytes()).decode()
    for passed in (3905, 30, 32):
        assert f'Result: {passed} passed, 0 failed, 0 skipped' in log
    assert log.count('Result: 1 passed, 0 failed, 0 skipped') == 2
    assert 'Ran 86 tests' in log and '\nOK\n' in log
    assert 'FAIL:' not in log and '\nFAILED' not in log
for name, digest in json.loads((root / 'artifacts.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
print(json.dumps(dict(source_sha256=source['sha256'], acceptance='scoped cleanup gate satisfied',
                      regression_before=before['totals'], regression_after=after['totals']), indent=2))
