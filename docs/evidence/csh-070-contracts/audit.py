#!/usr/bin/env python3
"""Check strict contract records and preserve failed-oracle accounting."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    with gzip.open(HERE / name, 'rt') as source:
        return json.load(source)


def main():
    for name, digest in json.loads((HERE / 'artifacts.json').read_text()).items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    normal, sanitized = read('native-contracts.json.gz'), read('native-sanitize.json.gz')
    for record, count in [(normal, 589), (sanitized, 537)]:
        assert record['totals'] == dict(PASS=count, FAIL=0)
        assert record['source_identity'] == record['final_source_identity']
        assert record['cases'][-1]['name'] == 'qualification input stability'
        assert record['temporary_directory_removed']
    assert normal['source_identity'] == sanitized['source_identity']
    io = [case for case in normal['cases'] if 'ignored_signals' in case.get('invocation', {})]
    assert len(io) == 52
    for case in io:
        assert case['verdict'] == 'PASS' and case['invocation']['reaped']
        assert not case['invocation']['errors']
        assert case['actual'] == case['expected']
    failed = read('native-attempt-1.json.gz')
    assert failed['totals'] == dict(PASS=523, FAIL=30)
    assert all(case['name'].startswith('catalog fallback ') for case in failed['cases'] if case['verdict'] == 'FAIL')
    print('PASS: exact native contracts, stable inputs, bounded cleanup and retained oracle failure')


if __name__ == '__main__':
    main()
