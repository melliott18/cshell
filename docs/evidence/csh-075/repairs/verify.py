#!/usr/bin/env python3
"""Check retained repair evidence; does not run or qualify host utilities."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(name):
    return json.loads(gzip.decompress((ROOT / name).read_bytes()))


def main():
    artifacts = json.loads((ROOT / 'artifacts.json').read_text())
    for name, digest in artifacts.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    for name, summary in json.loads((ROOT / 'runs.json').read_text()).items():
        result = read(name)
        assert result['totals'] == summary['totals'], name
        assert result['source_identity']['sha256'] == summary['source_sha256'], name
        rows = result['cases']
        assert sum(row['verdict'] == 'PASS' for row in rows) == result['totals']['passed'], name
        assert sum(row['verdict'] == 'FAIL' for row in rows) == result['totals']['failed'], name
    for system in ('native', 'linux'):
        result = read(system + '-full.json.gz')
        failed = {(row['id'], row.get('mode')) for row in result['cases'] if row['verdict'] != 'PASS'}
        assert failed == {('getconf/issue8-environment', mode)
                          for mode in ('direct', 'string', 'file', 'stdin')}
        build = json.loads((ROOT / (system + '-timeout-build.json')).read_text())
        assert result['inventory']['timeout']['sha256'] == build['executable_sha256']
        for log, digest in build['logs'].items():
            content = gzip.decompress((ROOT / (system + '-timeout-' + log + '.gz')).read_bytes())
            assert hashlib.sha256(content).hexdigest() == digest
        for name, total in (('subset', 274), ('edges', 80), ('priority-final', 18)):
            passing = read(system + '-' + name + '.json.gz')
            assert passing['totals'] == dict(passed=total, failed=0)
        subset = read(system + '-subset.json.gz')
        assert subset['omitted'] == ['getconf/issue8-environment']
    original = read('upstream-timeout.json.gz')
    assert {row['id'] for row in original['cases'] if row['verdict'] == 'FAIL'} == {
        'timeout/preserve', 'timeout/foreground-preserve'}
    print('PASS: hashes, counts, provider builds, strict getconf failures and repaired subsets')


if __name__ == '__main__':
    main()
