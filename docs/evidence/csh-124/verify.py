"""Verify CSH-124 platform evidence, provenance and predecessor preservation."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_ls_utf8 import cases, output_matches, expected_entries, NONPRINT, PRINTABLE
from host_utilities import source_identity, serial


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failed=False):
    return {(r['id'], r['mode']) for r in report['cases'] if not failed or r['verdict'] == 'FAIL'}


def stable(row):
    result = dict(row['expected'])
    for field in ('cwd_identity', 'creation_existing_identity', 'creation_preserved'):
        result.pop(field, None)  # Kernel-generated identity, not an authored expectation.
    return result


def verify(platforms=('native', 'linux')):
    authored = {r['id']: r for r in cases()}
    expected = {(name, mode) for name in authored for mode in ('direct', 'string', 'file', 'stdin')}
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    entry = next(u for u in mapping['utilities'] if u['utility'] == 'ls')
    assert hashlib.sha256((HERE / 'ls.html').read_bytes()).hexdigest() == entry['source_sha256']
    assert set(entry['csh124_assertions']) == set(authored)
    summary = {}
    previous = HERE.with_name('csh-123')
    for platform in platforms:
        authored = {r['id']: r for r in cases()}
        expected = {(name, mode) for name in authored for mode in ('direct', 'string', 'file', 'stdin')}
        count = 192
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands[1:]] == [2, 1], commands
        assert commands[0]['status'] == 0 or (platform == 'native' and commands[0]['status'] == 2), commands
        full_log = gzip.decompress((HERE / f'{platform}-command-0.log.gz').read_bytes()).decode()
        assert 'Ran 214 tests in ' in full_log and 'Ran 13 tests in ' in full_log
        files = dict(source_identity()['files'])
        for header in ('host-test-provider.h', 'host-newgrp-provider.h'):
            files['build/' + header] = hashlib.sha256(gzip.decompress((HERE / f'{platform}-{header}.gz').read_bytes())).hexdigest()
        digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
        text_recheck = None
        if platform == 'native' and commands[0]['status'] == 2:
            initial = read(HERE / 'native-text-initial.json.gz')
            recheck = read(HERE / 'native-text-recheck.json.gz')
            assert initial['source_identity']['sha256'] == recheck['source_identity']['sha256'] == digest
            failed = [r for r in initial['cases'] if r['verdict'] == 'FAIL']
            assert {(r['id'], r['mode']) for r in failed} == {
                ('strings/offset-decimal', 'direct'), ('strings/offset-decimal', 'string')}
            assert initial['totals'] == {'pass': 864, 'fail': 2, 'unavailable': 2}
            for row in failed:
                assert row['actual']['status'] == -9 and row['fixture_removed']
                assert row['actual']['errors'] == ['timeout after 5s (no output received; 0 bytes captured; process group killed)']
            assert recheck['totals'] == {'pass': 866, 'fail': 0, 'unavailable': 2}
            assert json.loads((HERE / 'native-text-recheck-command.json').read_text())['status'] == 0
            assert initial['inventory'] == recheck['inventory']
            assert initial['limits'] == recheck['limits']
            assert {(r['id'], r['mode']): r.get('case') for r in initial['cases']} == {
                (r['id'], r['mode']): r.get('case') for r in recheck['cases']}
            assert {(r['id'], r['mode']) for r in initial['cases'] if r['verdict'] == 'UNAVAILABLE'} == {
                (r['id'], r['mode']) for r in recheck['cases'] if r['verdict'] == 'UNAVAILABLE'}
            continuation = json.loads((HERE / 'native-profile-continuation.json').read_text())
            assert [r['status'] for r in continuation] == [0, 0]
            assert [line for line in full_log.splitlines() if line.startswith('make: ***')] == ['make: *** [test-host-profile] Error 1']
            text_recheck = recheck['totals']
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
        focused = read(HERE / f'{platform}-host-filesystem-ls-utf8.json.gz')
        assert len(focused['cases']) == count
        assert keys(new) - keys(old) == keys(focused) == expected
        assert keys(old) <= keys(new)
        assert focused['totals'] == dict(PASS=count, FAIL=0)
        assert new['totals']['PASS'] == old['totals']['PASS'] + count
        assert focused['ticket'] == 'CSH-124' and focused['predecessor'] == 'CSH-123'
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
            assert row['actual']['status'] == 0
            assert row['actual']['stderr'] == {'hex': ''}
            env = row['ls_utf8_environment']
            assert env['entries'] == expected_entries(env['before'], authored[row['id']]['ls_utf8'])
            assert output_matches(env, bytes.fromhex(row['actual']['stdout']['hex']))
            assert env['before'] == row['ls_utf8_observed']
            assert env['uid'] == env['euid'] == focused['uid']
            probe = env['locale_probe']
            assert probe['collate'] == 'C'
            assert probe['ctype'] == focused['utf8_locale']
            assert probe['codeset'].lower().replace('-', '') == 'utf8'
            assert probe['printable'] == {str(ord(c)): c in PRINTABLE for c in NONPRINT + PRINTABLE}
            execution_env = row['invocation']['env']
            assert execution_env['LC_ALL'] == '' and execution_env['LC_COLLATE'] == 'C'
            assert execution_env['LC_CTYPE'] == focused['utf8_locale']
            invocation = row['invocation']
            assert row['expected']['args'] == authored[row['id']]['args']
            if row['mode'] == 'direct':
                assert invocation['args'] == row['expected']['args']
                assert row['executable'] == focused['providers']['ls']['path']
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            assert keys(read(previous / name), True) == keys(read(HERE / name), True), name
        summary[platform] = dict(reports=reports, required_command_passed=commands[0]['status'] == 0,
                                 text_recheck=text_recheck)
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS: 192 new assertions per platform (' + ', '.join(platforms) + '); predecessor expectations, stock failure identities, source/provider provenance and cleanup retained.')


if __name__ == '__main__':
    verify()
