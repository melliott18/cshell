"""Verify retained qualification records against the current source inventory."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parents[2] / 'tests'))
from host_capability_limits import RESIDUAL
from host_utilities import sanitizer_diagnostic, source_identity

expected_source = source_identity()['sha256']
conditions = {row[0] for row in RESIDUAL}
summary = {}
for path in sorted(root.glob('*.json.gz')):
    record = json.loads(gzip.decompress(path.read_bytes()))
    assert record['source_identity']['sha256'] == expected_source, path
    counts = Counter(case['verdict'] for case in record['cases'])
    assert record['totals'] == dict(passed=counts['PASS'], failed=counts['FAIL'], gaps=counts['GAP']), path
    assert counts['GAP'] == 0, path
    residuals = {row['condition']: row for row in record['limitations']}
    assert len(residuals) == len(record['limitations']), path
    assert conditions <= residuals.keys(), path
    for row in residuals.values():
        assert all(row[field] for field in ('source', 'environment', 'reason', 'implementation_owner')), (path, row)
        assert row['owner'] == 'CSH-064' and row['executable']['sha256'], (path, row)
        assert 'verdict' not in row, (path, row)
    failures = [case for case in record['cases'] if case['verdict'] == 'FAIL']
    phases = Counter(case.get('phase', 'assertion') for case in failures)
    if 'unequal' in path.name:
        assert counts['FAIL'] == 204 and phases == {'assertion': 204}, path
        assert sum(case['case']['status'] == 0 for case in failures) == 132, path
        assert all('operation' not in case['name'] for case in failures), path
    elif 'tmpfs' in path.name:
        assert phases == {'setup': 1098}, path
    elif 'bind' in path.name:
        assert phases == {'setup': 1110, 'assertion': 9}, path
    else:
        assert not failures, path
    for case in failures:
        assert not case['case'].get('gap'), (path, case['name'])
        if case.get('phase') == 'setup':
            assert case['filesystem'] == record['filesystem'], (path, case['name'])
            assert all(case[field] for field in ('reason', 'source', 'owner')), (path, case['name'])
    for case in record['cases']:
        streams = {key: bytes.fromhex(case['actual'][key]['hex']) for key in ('stdout', 'stderr')
                   if isinstance(case.get('actual', {}).get(key), dict)}
        assert not sanitizer_diagnostic(streams), (path, case['name'])
    summary[path.name] = dict(totals=record['totals'], failure_phases=dict(phases),
                             limitations=len(residuals), filesystem=record['filesystem'])
manifest = root / 'artifacts.json'
if manifest.exists():
    for name, digest in json.loads(manifest.read_text()).items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
print(json.dumps(dict(source_sha256=expected_source, residual_conditions=len(conditions),
                      records=summary), indent=2))
