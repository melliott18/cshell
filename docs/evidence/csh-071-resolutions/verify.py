"""Audit strict passing scopes and retain failed setup/cleanup evidence."""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(name):
    with gzip.open(ROOT / (name + '.json.gz'), 'rt') as stream:
        return json.load(stream)

for name, count in [('native-chmod', 124), ('native-chmod-asan', 124),
                    ('linux-chmod', 124), ('linux-newgrp', 24),
                    ('linux-newgrp-asan', 24), ('linux-permissions', 1072),
                    ('ci-linux-chmod-qualification', 124), ('ci-linux-newgrp-qualification', 24),
                    ('ci-linux-controlled-qualification', 22), ('ci-linux-ordinary-qualification', 16)]:
    data = read(name)
    assert data['totals'] == {'pass': count, 'fail': 0}, name
    assert all(c['verdict'] == 'PASS' and c['cleanup'] for c in data['cases']), name
    assert not data['missing_providers'], name

for name in ('linux-profile', 'mapped-nodes-qualification', 'mapped-final-qualification'):
    data = read(name)
    assert data['totals'] == {'passed': 2281, 'failed': 0, 'gaps': 0}, name
    assert all(c['verdict'] == 'PASS' for c in data['cases']), name
    if name.startswith('mapped'):
        ns = data['credential_namespace']
        for key in ('uid_map', 'gid_map'):
            assert [line.split() for line in ns[key].splitlines()] == [['0', '0', '1'], ['1', '20001', '65535']]
        assert ns['setgroups'] == 'allow'
        nodes = [c['controlled_fixture']['supplied_device'] for c in data['cases']
                 if (c.get('controlled_fixture') or {}).get('kind') in ('block', 'character')]
        assert len(nodes) == 12 and all(n['stat_only'] for n in nodes)

data = read('mapped-qualification')
assert data['totals'] == {'passed': 2269, 'failed': 12, 'gaps': 0}
assert all(c['phase'] == 'setup' and c['actual']['errno'] == 1
           for c in data['cases'] if c['verdict'] != 'PASS')
assert read('native-permissions')['totals'] == {'pass': 979, 'fail': 1}
data = read('darwin-account-groups-failure')
assert data['totals'] == {'pass': 0, 'fail': 240}
assert all(c['actual']['errors'] == ['credential setup differs from requested IDs'] for c in data['cases'])
assert read('ci-linux-unequal-acl-qualification')['totals'] == {'passed': 2260, 'failed': 0, 'gaps': 0}
ci = json.loads((ROOT / 'ci-run.json').read_text())
assert any(j['name'] == 'permissions (ubuntu-24.04)' and j['conclusion'] == 'success' for j in ci['jobs'])
print('PASS: selected repairs, mapped credentials, supplied nodes and retained failures')
