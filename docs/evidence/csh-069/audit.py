#!/usr/bin/env python3
"""Verify immutable historical records and every CSH-069 validation attempt."""
import gzip
import hashlib
import json
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((EVIDENCE / name).read_text())


original = json.loads((ROOT / 'docs/evidence/csh-012/closure-5b56328/defect-dispositions.json').read_text())
assert [entry['id'] for entry in original['records']] == [f'H{i:02}' for i in range(1, 12)]
for entry in original['records']:
    for item in entry['evidence']:
        path = ROOT / item['path']
        assert digest(path) == item['sha256'], path
        assert path.stat().st_size == item['bytes'], path

before = read('native-before.json')
assert before['returncode'] == -6
assert 'errno=10 (No child processes)' in before['stderr']
assert digest(EVIDENCE / 'before_fixture.c') == before['inputs']['tests/context_fixture.c']
for name, status in (
    ('docker-before-build', 0), ('docker-before', -6),
    ('native-regression', 0), ('docker-regression', 0),
    ('native-sanitizer', 0), ('docker-sanitizer', 2),
    ('docker-sanitizer-build-limit-fixed', 0),
):
    record = read(name + '.json')
    log = EVIDENCE / (name + '.log.gz')
    assert record['returncode'] == status, name
    assert digest(log) == record['log_sha256'], name
    output = gzip.decompress(log.read_bytes()).decode()
    if name == 'docker-before':
        assert 'errno=10 (No child processes)' in output
    elif name == 'docker-sanitizer':
        assert 'File size limit exceeded' in output
        assert 'context fixtures passed' not in output
    elif name != 'docker-before-build':
        assert 'context fixtures passed (60 behavior cases, API, forced schedule and fault checks)' in output
        # These are exact fixed-source validation records, not just summaries.
        for path, expected in record['inputs'].items():
            assert digest(ROOT / path) == expected, (name, path)
    if name.endswith('regression'):
        assert 'execution fixtures passed (61 behavior cases, API and fault checks)' in output
        assert 'pipeline fixtures passed (52 behavior cases, API and fault checks)' in output

failed = read('docker-sanitizer.json')
fixed = read('docker-sanitizer-build-limit-fixed.json')
assert failed['inputs'] == fixed['inputs']
assert digest(EVIDENCE / 'record-initial.py') == failed['evidence_inputs']['record.py']
assert digest(EVIDENCE / 'record.py') == fixed['evidence_inputs']['record.py']
assert fixed['environment']['ASAN_OPTIONS'] == 'detect_leaks=1:halt_on_error=1'
for path, expected in read('artifacts.json').items():
    assert digest(EVIDENCE / path) == expected, path
print('H01–H11 original records and all CSH-069 attempts verified')
