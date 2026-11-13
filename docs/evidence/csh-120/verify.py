"""Validate retained CSH-120 platform reports and predecessor expectations."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_ls_recursive import cases, output_matches
from host_utilities import source_identity, serial


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failed=False):
    return {(r['id'], r['mode']) for r in report['cases'] if not failed or r['verdict'] == 'FAIL'}


def verify():
    authored = {r['id']: r for r in cases()}
    expected = {(name, mode) for name in authored for mode in ('direct', 'string', 'file', 'stdin')}
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    entry = next(u for u in mapping['utilities'] if u['utility'] == 'ls')
    assert hashlib.sha256((HERE / 'ls.html').read_bytes()).hexdigest() == entry['source_sha256']
    assert set(entry['csh120_assertions']) == set(authored)
    summary = {}
    for platform in ('native', 'linux'):
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        setup = json.loads((HERE / f'{platform}-partial-setup.json').read_text())
        assert setup['passed'] == 4 and setup['failed'] == 0 and setup['uid'] != 0
        assert {r['mode'] for r in setup['cases']} == {'direct', 'string', 'file', 'stdin'}
        for row in setup['cases']:
            assert row['partial_setup'] == 'complete directories/files and first alias; second alias absent'
            assert row['record']['phase'] == 'setup' and row['record']['cleanup']
            assert row['record']['error'] == 'injected CSH-120 second-alias setup failure'
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
                assert report['totals'].get('FAIL', report['totals'].get('failed')) == 0, path
                assert report['totals'].get('gaps', 0) == 0, path
            reports[path.name] = report['totals']
        previous = HERE.with_name('csh-119')
        old = read(previous / f'{platform}-host-filesystem-profile.json.gz')
        new = read(HERE / f'{platform}-host-filesystem-profile.json.gz')
        focused = read(HERE / f'{platform}-host-filesystem-ls-recursive.json.gz')
        assert keys(new) - keys(old) == keys(focused) == expected
        assert keys(old) <= keys(new)
        assert focused['totals'] == dict(PASS=192, FAIL=0)
        assert new['totals']['PASS'] == old['totals']['PASS'] + 192
        assert focused['ticket'] == 'CSH-120' and focused['predecessor'] == 'CSH-119'
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        # Authored expected rows remain byte-for-byte unchanged except temporary paths.
        current = {(r['id'], r['mode']): r for r in new['cases']}
        def stable(row):
            result = dict(row['expected'])
            for field in ('cwd_identity', 'creation_existing_identity', 'creation_preserved'):
                value = result.pop(field, None)
                if value is not None:
                    if field == 'cwd_identity':
                        assert set(value) == {'device', 'inode'} and all(type(n) is int for n in value.values())
                    elif field == 'creation_preserved':
                        assert set(value) == {'existing', 'parent-alias', 'data', 'dangling'}
                        assert all(len(v) == 3 and all(type(n) is int for n in v) for v in value.values())
                    else:
                        assert len(value) == 2 and all(type(n) is int for n in value)
            return result
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
            env = row['ls_recursive_environment']
            assert env['before'] == row['ls_recursive_observed']
            assert env['uid'] == env['euid'] == focused['uid']
            assert output_matches(env, bytes.fromhex(row['actual']['stdout']['hex']))
            if row['mode'] == 'direct':
                assert row['executable'] == focused['providers']['ls']['path']
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            assert keys(read(previous / name), True) == keys(read(HERE / name), True), name
        summary[platform] = dict(reports=reports, required_command_passed=commands[0]['status'] == 0)
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS: bounded filesystem evidence; 192 new assertions per platform; predecessor expectations, stock failures, provenance and cleanup retained. Full host-profile command results are recorded separately in summary.json.')


if __name__ == '__main__':
    verify()
