#!/usr/bin/env python3
"""Verify qualified subsets independently of the deliberately failed records."""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
counts = {'native-acl': 496, 'native-asan': 496, 'native-permissions': 980,
          'ci-linux-controlled-qualification': 22, 'ci-linux-ordinary-qualification': 16}
for name, passed in counts.items():
    with gzip.open(ROOT / (name + '.json.gz'), 'rt') as stream:
        report = json.load(stream)
    assert report['totals'] == {'pass': passed, 'fail': 0}, name
    assert all(row['verdict'] == 'PASS' and row['cleanup'] for row in report['cases']), name
    assert not report['missing_providers'], name
    for row in report['cases']:
        if row['case'].get('credentials'):
            assert row['identity']['root_regain_denied'], row['name']
for name, passed in [('native-profile', 1162), ('ci-linux-unequal-acl-qualification', 2260)]:
    with gzip.open(ROOT / (name + '.json.gz'), 'rt') as stream:
        report = json.load(stream)
    assert report['totals'] == {'passed': passed, 'failed': 0, 'gaps': 0}, name
    assert all(row['verdict'] == 'PASS' for row in report['cases']), name
ci = json.loads((ROOT / 'ci-run.json').read_text())
assert any(job['name'] == 'permissions (ubuntu-24.04)' and job['conclusion'] == 'success'
           for job in ci['jobs'])
print('PASS: native/ASan/CI strict scopes, identities, effects and fixture cleanup')
