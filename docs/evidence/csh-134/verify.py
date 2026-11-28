"""Verify CSH-134 evidence without weakening predecessor or stock assertions."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_ls_time_links import cases, output_matches, LINKS, FILES, TIMES, DAY
from host_filesystem_metadata import STAMP
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
    assert set(entry['csh134_assertions']) == set(authored)
    summary = {}
    previous = HERE.with_name('csh-133')
    if 'linux' in platforms:
        capacity = json.loads((HERE / 'linux-report-capacity.json').read_text())
        assert all(capacity[path]['capacity_bytes'] == 512 * 1024 * 1024
                   for path in ('/tmp', '/work/build/tests'))
    for platform in platforms:
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        command_statuses = [r['status'] for r in commands]
        observer_retry = platform == 'native' and command_statuses[0] == 2
        assert command_statuses == ([2, 2, 1] if observer_retry else [0, 2, 1]), commands
        if observer_retry:
            recovery = json.loads((HERE / 'native-recovery-commands.json').read_text())
            assert len(recovery) == 3 and all(r['status'] == 0 for r in recovery)
            original = read(HERE / 'native-text-observer-failure.json.gz')
            retried = read(HERE / 'native-host-text-results.json.gz')
            assert original['totals'] == {'pass': 865, 'fail': 1, 'unavailable': 2}
            assert retried['totals'] == {'pass': 866, 'fail': 0, 'unavailable': 2}
            failed = [r for r in original['cases'] if r['verdict'] == 'FAIL']
            assert len(failed) == 1
            failure = failed[0]
            assert (failure['id'], failure['mode']) == ('cmp/write-termination', 'exec')
            assert failure['error'].startswith('Darwin sample failed:')
            assert failure['leader_reaped'] and failure['fixture_removed']
            assert original['source_identity'] == retried['source_identity']
            assert original['inventory'] == retried['inventory']
            assert original['limits'] == retried['limits']
            assert original['binary_sha256'] == retried['binary_sha256']
            retry_rows = {(r['id'], r['mode']): r for r in retried['cases']}
            assert len(retry_rows) == len(original['cases'])
            for row in original['cases']:
                other = retry_rows[(row['id'], row['mode'])]
                assert row.get('expected') == other.get('expected')
                assert other['verdict'] == ('PASS' if row is failure else row['verdict'])
        log = gzip.decompress((HERE / f'{platform}-command-0.log.gz').read_bytes()).decode()
        assert 'Ran 268 tests in ' in log and 'Ran 13 tests in ' in log
        if observer_retry:
            assert log.count('make: ***') == 1 and '[test-host-profile] Error 1' in log
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
        focused = read(HERE / f'{platform}-host-filesystem-ls-time-links.json.gz')
        assert keys(new) - keys(old) == keys(focused) == expected
        assert keys(old) <= keys(new)
        assert focused['totals'] == dict(PASS=288, FAIL=0)
        assert new['totals']['PASS'] == old['totals']['PASS'] + 288
        assert focused['ticket'] == 'CSH-134' and focused['predecessor'] == 'CSH-133'
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
        assert new['providers']['ls']['sha256'] == old['providers']['ls']['sha256']
        assert focused['limits'] == old['limits']
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and not row['errors'] and row['cleanup']
            assert row['expected'] == serial(authored[row['id']])
            assert row['actual']['status'] == 0 and row['actual']['stderr'] == {'hex': ''}
            env = row['ls_time_links_environment']
            assert env['spec'] == authored[row['id']]['ls_time_links']
            assert output_matches(env, bytes.fromhex(row['actual']['stdout']['hex']))
            assert row['ls_time_links_observed'] == env['before']
            assert env['uid'] == env['euid'] == focused['uid']
            assert row['invocation']['env']['LC_ALL'] == 'C'
            assert row['invocation']['env']['TZ'] == 'UTC0'
            assert env['owners'] and env['groups'] and env['unit_bytes'] == 1024
            for key, times in env['timestamps'].items():
                assert times == {clock + '_ns': STAMP + TIMES[clock][key] * DAY
                                 for clock in ('mtime', 'atime')}
            for name, content in FILES.items():
                info = env['before']['targets/' + name]
                assert info['size'] == len(content)
                key = 'targets/' + name
                assert info['mtime_ns'] == STAMP + TIMES['mtime'][key] * DAY
                assert info['atime_ns'] == STAMP + TIMES['atime'][key] * DAY
            for name, target in LINKS.items():
                info = env['before']['links/' + name]
                assert info['size'] == len(target)
                key = 'links/' + name
                assert info['mtime_ns'] == STAMP + TIMES['mtime'][key] * DAY
                referent = env['before']['targets/' + target.rsplit('/', 1)[1]]
                assert env['referents'][name] == {k: referent[k] for k in ('device', 'inode', 'size')}
                assert info['inode'] != referent['inode']
            assert env['entries'] == dict(links=sorted(LINKS), targets=sorted(FILES))
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
            expected_failures = ({(r['id'], mode) for r in authored.values()
                                  if r['ls_time_links']['graph'] == 'operands'
                                  and r['ls_time_links']['follow'] == 'H'
                                  for mode in ('direct', 'string', 'file', 'stdin')}
                                 if platform == 'native' and suffix == 'audit' else set())
            assert extra == expected_failures, (name, extra)
            for row in new_report['cases']:
                if row['id'] in authored:
                    failed = (row['id'], row['mode']) in expected_failures
                    assert row['verdict'] == ('FAIL' if failed else 'PASS') and row['cleanup']
                    assert row['errors'] == (['stdout mismatch'] if failed else [])
                    assert row['expected'] == serial(authored[row['id']])
            # Every existing stock case retains its expectation and verdict.
            by_key = {(r['id'], r['mode']): r for r in new_report['cases']}
            for row in old_report['cases']:
                other = by_key[(row['id'], row['mode'])]
                assert stable(row) == stable(other) and row['verdict'] == other['verdict']
        summary[platform] = dict(reports=reports, required_command_passed=commands[0]['status'] == 0,
                                 required_recipes_completed=True,
                                 observer_retry=observer_retry)
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS: 288 new assertions per platform; predecessor expectations, stock failure identities, source/provider provenance and cleanup retained.')


if __name__ == '__main__':
    verify()
