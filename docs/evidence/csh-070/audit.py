#!/usr/bin/env python3
"""Verify retained CSH-070 evidence; this is accounting, not new qualification."""
import gzip
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    path = HERE / name
    with gzip.open(path, 'rt') if path.suffix == '.gz' else path.open() as stream:
        return json.load(stream)


def main():
    artifacts = read('artifacts.json')
    for name, expected in artifacts.items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == expected, name
    digests = set()
    for name, count in [('native-focused.json.gz', 351), ('linux-focused.json.gz', 356),
                        ('native-sanitize.json.gz', 346)]:
        record = read(name)
        assert record['totals'] == {'PASS': count, 'FAIL': 0}, name
        assert record['temporary_directory_removed'], name
        digests.add(record['source_identity']['sha256'])
        for case in record['cases']:
            if 'trials' not in case:
                continue
            assert case['smallest_e2big'] == case['largest_success'] + 1
            assert len(case['trials']) <= case['max_trials']
            assert case['trials'][-2]['size'] == case['largest_success']
            assert case['trials'][-1]['size'] == case['smallest_e2big']
            for trial in case['trials']:
                if trial['errno'] is None:
                    assert trial['status'] == 0 and not trial['stderr_hex']
                    assert trial['stdout_sha256'] == trial['expected_stdout_sha256']
                else:
                    assert trial['errno'] == 7 and trial['status'] is None
    assert len(digests) == 1, digests
    for host in ('native', 'linux'):
        record = read(host + '-profile.json.gz')
        assert record['totals'] == dict(passed=1162, failed=0, gaps=0)
        assert record['source_identity']['sha256'] in digests
        residuals = {r['condition']: r for r in record['limitations']}
        for condition in ('U-035/locale-catalogs', 'U-035/other-locales', 'U-035/format-allocation-limits',
                          'U-035/full-format', 'U-036/alternative-policies', 'U-036/argument-limits'):
            assert residuals[condition]['owner'] == 'CSH-079'
            assert residuals[condition]['current_qualification']['ticket'] == 'CSH-070'
    before = read('linux-before.json')
    assert [(r['verdict'], r['actual']['status']) for r in before['cases']] == [
        ('FAIL', 0), ('FAIL', 0), ('FAIL', -11), ('FAIL', 0)]
    assert read('native-attempt-3.json.gz')['totals']['FAIL'] == 4
    assert read('native-profile-attempt-4.json.gz')['totals']['failed'] == 1
    print('PASS: identities, strict subset assertions, thresholds, failures and residual ownership')


if __name__ == '__main__':
    main()
