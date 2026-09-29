"""Audit complete CSH-064 records without treating retained failures as passes."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root.parents[2] / 'tests'))
from host_capability_limits import RESIDUAL
from host_utilities import source_identity, sanitizer_diagnostic

source = source_identity()['sha256']
conditions = {row[0] for row in RESIDUAL}
expected = {
    'native': (1162, {}),
    'linux-normal': (2281, {}),
    'linux-unequal': (2077, {'assertion': 204}),
    'linux-namespace': (2269, {'setup': 12}),
    'linux-namespace-unequal': (2065, {'setup': 12, 'assertion': 204}),
    'linux-tmpfs': (1183, {'setup': 1098}),
    'linux-bind': (1162, {'setup': 1110, 'assertion': 9}),
}
summary = {}
for name, (passed, phases) in expected.items():
    record = json.loads(gzip.decompress((root / (name + '.json.gz')).read_bytes()))
    assert record['source_identity']['sha256'] == source, name
    failures = [row for row in record['cases'] if row['verdict'] == 'FAIL']
    assert record['totals'] == dict(passed=passed, failed=sum(phases.values()), gaps=0), name
    assert Counter(row['verdict'] for row in record['cases']) == Counter(
        {key: value for key, value in dict(PASS=passed, FAIL=sum(phases.values())).items() if value}), name
    assert Counter(row.get('phase', 'assertion') for row in failures) == phases, name
    limitations = {row['condition']: row for row in record['limitations']}
    assert len(limitations) == len(record['limitations']), name
    assert conditions <= limitations.keys(), name
    for row in limitations.values():
        assert row['owner'] == 'CSH-064' and row['executable']['sha256'], (name, row)
        assert all(row[key] for key in ('reason', 'source', 'environment', 'implementation_owner')), (name, row)
        assert row['environment']['credential_namespace'] == record['credential_namespace'], name
        assert 'verdict' not in row, name
    for row in failures:
        assert not row['case'].get('gap'), (name, row)
        if row.get('phase') == 'setup':
            assert row['filesystem'] == record['filesystem'], (name, row)
            assert all(row[key] for key in ('source', 'reason', 'owner')), (name, row)
            if 'namespace' in name:
                assert 'private' in row['name'] and row['actual']['errno'] == 1, (name, row)
    if 'unequal' in name:
        predicates = [row for row in failures if row.get('phase') != 'setup']
        assert len(predicates) == 204
        assert sum(row['case']['status'] == 0 for row in predicates) == 132
        assert all('operation' not in row['name'] for row in predicates)
    if 'namespace' in name:
        ns = record['credential_namespace']
        assert list(map(int, ns['uid_map'].split())) == [0, 0, 1, 1, 20001, 65535]
        assert ns['uid_map'] == ns['gid_map'] and ns['setgroups'] == 'allow'
    for row in record['cases']:
        streams = {key: bytes.fromhex(row['actual'][key]['hex']) for key in ('stdout', 'stderr')
                   if isinstance(row.get('actual', {}).get(key), dict)}
        assert not sanitizer_diagnostic(streams), (name, row['name'])
    summary[name] = dict(totals=record['totals'], failure_phases=phases, limitations=len(limitations))
for name, totals in [('overlay', dict(passed=8, failed=0)), ('bind', dict(passed=3, failed=5))]:
    probe = json.loads((root / (name + '-probe.json')).read_text())
    assert probe['source_identity']['sha256'] == source, name
    assert probe['totals'] == totals, name
    assert len(probe['cases']) == 8, name
    if name == 'bind':
        rows = {row['name']: row for row in probe['cases']}
        assert probe['filesystem']['mount']['type'] == 'fakeowner'
        assert rows['socket stat type']['actual']['errno'] == 22
        assert rows['socket actual transfer']['verdict'] == 'PASS'
        for method in ('syscall', 'utility'):
            row = rows[f'chmod {method} uid=10002']
            assert row['verdict'] == 'FAIL'
            child = row['actual']['child']
            assert child['credentials']['euid'] == 10002
            assert not int(child['credentials']['capabilities']['CapEff'], 16)
            assert child['after']['mode'] == '0o100600'
prerequisites = json.loads((root / 'prerequisites.json').read_text())
assert {row['condition'] for row in prerequisites['residuals']} == conditions
assert all(row['required_capability'] and row['owner'] == 'CSH-064' for row in prerequisites['residuals'])
commands = {row['name']: row for row in json.loads((root / 'commands.json').read_text())}
for name in ('normal', 'native-profile', 'native-integration', 'linux-integration', 'namespace-integration', 'overlay-probe'):
    assert commands[name]['status'] == 0, name
for name in ('unequal', 'namespace', 'namespace-unequal', 'tmpfs', 'bind', 'bind-probe'):
    assert commands[name]['status'] == 1, name
for name, digest in json.loads((root / 'artifacts.json').read_text()).items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
print(json.dumps(dict(source_sha256=source, residual_conditions=len(conditions), records=summary), indent=2))
