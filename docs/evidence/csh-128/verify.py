"""Verify CSH-128 evidence without weakening predecessor or stock assertions."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_ls_dates import cases, output_matches, age_is_interior, date_fields
from host_utilities import source_identity, serial


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failed=False):
    return {(r['id'], r['mode']) for r in report['cases'] if not failed or r['verdict'] == 'FAIL'}


def stable(row):
    result = dict(row['expected'])
    for field in ('cwd_identity', 'creation_existing_identity', 'creation_preserved'):
        result.pop(field, None)
    return result


def verify(platforms=('native', 'linux')):
    authored = {r['id']: r for r in cases()}
    expected = {(name, mode) for name in authored for mode in ('direct', 'string', 'file', 'stdin')}
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    entry = next(u for u in mapping['utilities'] if u['utility'] == 'ls')
    assert hashlib.sha256((HERE / 'ls.html').read_bytes()).hexdigest() == entry['source_sha256']
    assert set(entry['csh128_assertions']) == set(authored)
    summary = {}
    previous = HERE.with_name('csh-127')
    for platform in platforms:
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        log = gzip.decompress((HERE / f'{platform}-command-0.log.gz').read_bytes()).decode()
        assert 'Ran 239 tests in ' in log and 'Ran 13 tests in ' in log
        files = dict(source_identity()['files'])
        for header in ('host-test-provider.h', 'host-newgrp-provider.h'):
            files['build/' + header] = hashlib.sha256(gzip.decompress((HERE / f'{platform}-{header}.gz').read_bytes())).hexdigest()
        digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        reports = {}
        for path in HERE.glob(platform + '-host-*.json.gz'):
            report = read(path)
            if 'source_identity' not in report:
                continue
            assert report['source_identity']['sha256'] == digest, path
            if 'filesystem' in path.name:
                assert all(r['cleanup'] for r in report['cases']), path
            if not path.name.endswith(('-filesystem-audit.json.gz', '-stock-provider-audit.json.gz')):
                assert report['totals'].get('FAIL', report['totals'].get('failed', report['totals'].get('fail'))) == 0, path
                assert report['totals'].get('gaps', 0) == 0, path
            reports[path.name] = report['totals']
        old = read(previous / f'{platform}-host-filesystem-profile.json.gz')
        new = read(HERE / f'{platform}-host-filesystem-profile.json.gz')
        focused = read(HERE / f'{platform}-host-filesystem-ls-dates.json.gz')
        assert keys(new) - keys(old) == keys(focused) == expected
        assert keys(old) <= keys(new)
        assert focused['totals'] == dict(PASS=240, FAIL=0)
        assert new['totals']['PASS'] == old['totals']['PASS'] + 240
        assert focused['ticket'] == 'CSH-128' and focused['predecessor'] == 'CSH-127'
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        current = {(r['id'], r['mode']): r for r in new['cases']}
        for row in old['cases']:
            assert stable(row) == stable(current[(row['id'], row['mode'])]), row['id']
        manifest = read(HERE / f'{platform}-host-profile-manifest.json.gz')
        for utility, provider in manifest['executables'].items():
            if utility in new['providers']:
                assert provider['sha256'] == new['providers'][utility]['sha256'], utility
        for name, sha in old['source_identity']['files'].items():
            if name.startswith(('src/', 'include/', 'tools/')):
                assert new['source_identity']['files'][name] == sha, name
        assert focused['providers']['ls'] == new['providers']['ls']
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and not row['errors'] and row['cleanup']
            assert row['expected'] == serial(authored[row['id']])
            assert row['actual']['status'] == 0 and row['actual']['stderr'] == {'hex': ''}
            env = row['ls_dates_environment']
            assert env['spec'] == authored[row['id']]['ls_dates']
            assert output_matches(env, bytes.fromhex(row['actual']['stdout']['hex']))
            for name, info in env['before'].items():
                assert all(row['ls_dates_observed']['measurements'][name][k] == v for k, v in info.items() if k != 'atime_ns')
            assert env['uid'] == env['euid'] == focused['uid']
            assert row['invocation']['env']['LC_ALL'] == 'C'
            assert row['invocation']['env']['TZ'] == authored[row['id']]['env']['TZ']
            assert env['owner'] and env['group']
            info = env['before'][env['spec']['kind']]
            assert info['mtime_ns'] == env['seconds'] * 10**9
            assert env['date_fields'] == [s.decode('ascii') for s in date_fields(env['spec'], env['seconds'])]
            assert age_is_interior(env['spec']['age'], env['seconds'], env['clock_before'])
            assert age_is_interior(env['spec']['age'], env['seconds'], row['ls_dates_observed']['clock_after'])
            for name, ctime in env['ctimes'].items():
                assert row['ls_dates_observed']['measurements'][name]['ctime_ns'] == ctime
            if row['mode'] == 'direct':
                assert row['invocation']['args'] == row['expected']['args']
                assert row['executable'] == focused['providers']['ls']['path']
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            old_report, new_report = read(previous / name), read(HERE / name)
            added = keys(new_report) - keys(old_report)
            assert added == (expected if suffix == 'audit' else set()), name
            old_failed, new_failed = keys(old_report, True), keys(new_report, True)
            assert old_failed <= new_failed, name
            extra = new_failed - old_failed
            assert not extra, (name, extra)
            for row in new_report['cases']:
                if row['id'] in authored:
                    assert row['verdict'] == 'PASS' and not row['errors'] and row['cleanup']
                    assert row['expected'] == serial(authored[row['id']])
            # Every existing stock case retains its expectation and verdict.
            by_key = {(r['id'], r['mode']): r for r in new_report['cases']}
            for row in old_report['cases']:
                other = by_key[(row['id'], row['mode'])]
                assert stable(row) == stable(other) and row['verdict'] == other['verdict']
        summary[platform] = dict(reports=reports, required_command_passed=True)
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS: 240 new assertions per platform; predecessor expectations, stock failure identities, source/provider provenance and cleanup retained.')


if __name__ == '__main__':
    verify()
