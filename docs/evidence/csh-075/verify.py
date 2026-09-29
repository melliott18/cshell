#!/usr/bin/env python3
"""Check CSH-075 retained accounting; does not requalify host providers."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]


def read(name):
    with gzip.open(ROOT / name) as stream:
        return json.load(stream)


def main():
    manifest = json.loads((ROOT / 'artifacts.json').read_text())
    for name, digest in manifest.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    summary = json.loads((ROOT / 'runs.json').read_text())
    for name, row in summary.items():
        if not name.endswith('.json.gz'):
            continue
        result = read(name)
        assert result['totals'] == row['totals'], name
        assert result['source_identity']['sha256'] == row['source_sha256'], name
    for system, name, failed in (
            ('darwin', 'native-full.json.gz', {'getconf/issue8-environment', 'timeout/foreground', 'timeout/preserve'}),
            ('linux', 'docker-full.json.gz', {'getconf/issue8-environment', 'timeout/foreground', 'timeout/preserve', 'renice/relative-increment'})):
        result = read(name)
        actual = {(r['id'], r.get('mode')) for r in result['cases'] if r['verdict'] != 'PASS'}
        assert actual == {(case, mode) for case in failed for mode in ('direct', 'string', 'file', 'stdin')}, name
        subset = json.loads((REPO / 'tests' / ('host_execution_subset_' + system + '.json')).read_text())
        passing = {(r['id'], r.get('mode')) for r in result['cases'] if r['verdict'] == 'PASS'}
        assert {(case, mode) for case in subset for mode in ('direct', 'string', 'file', 'stdin')} <= passing, name
    print('PASS: retained identities, counts, strict failures, subset coverage and artifact hashes')


if __name__ == '__main__':
    main()
