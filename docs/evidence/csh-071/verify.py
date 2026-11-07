#!/usr/bin/env python3
"""Verify retained passing/failed scopes without rewriting historical evidence."""
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from host_contract_inventory import load_contracts, validate


def read(name):
    with gzip.open(HERE / (name + '.json.gz'), 'rt') as stream:
        return json.load(stream)


expected = {
    'docker-permissions': {'pass': 988, 'fail': 0},
    'docker-controlled-permissions': {'pass': 1072, 'fail': 0},
    'docker-profile': {'passed': 1162, 'failed': 0, 'gaps': 0},
    'docker-controlled-profile': {'passed': 2281, 'failed': 0, 'gaps': 0},
    'native-existing-profile': {'passed': 1162, 'failed': 0, 'gaps': 0},
    'native-final-permissions': {'pass': 968, 'fail': 12},
    'docker-newgrp': {'pass': 12, 'fail': 8},
    'docker-chmod-X': {'pass': 0, 'fail': 4},
    'docker-adapter-sanitizer-test': {'pass': 20, 'fail': 0},
    'docker-adapter-sanitizer-bracket': {'pass': 20, 'fail': 0},
    'docker-adapter-sanitizer-error': {'pass': 4, 'fail': 0},
}
for name, totals in expected.items():
    record = read(name)
    assert record['totals'] == totals, name
    if 'providers' in record:
        assert all(row['path'] and row['sha256'] for row in record['providers'].values()), name
        assert all(case['cleanup'] for case in record['cases']), name
        assert not record['missing_providers'], name
        if totals.get('fail') == 0:
            assert all(case['verdict'] == 'PASS' for case in record['cases']), name
native = read('native-final-permissions')
for case in native['cases']:
    if case['verdict'] == 'FAIL':
        assert any('timeout after 5s' in error for error in case['actual']['errors']), case
assert not validate(load_contracts())
assert '- Status: in-progress' in (ROOT / 'docs/tickets/CSH-071-host-permissions-identities.md').read_text()
print('PASS: selected profiles, strict failed scopes, cleanup records, providers and open ownership')
