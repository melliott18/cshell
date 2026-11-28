"""Verify CSH-123 platform evidence, provenance and predecessor preservation."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_ls_output import cases
from host_filesystem_fault import marker_matches
import errno
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


def verify():
    authored = {r['id']: r for r in cases('Linux')}
    expected = {(name, mode) for name in authored for mode in ('direct', 'string', 'file', 'stdin')}
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    entry = next(u for u in mapping['utilities'] if u['utility'] == 'ls')
    assert hashlib.sha256((HERE / 'ls.html').read_bytes()).hexdigest() == entry['source_sha256']
    assert set(entry['csh123_assertions']) == set(authored)
    summary = {}
    previous = HERE.with_name('csh-122')
    for platform in ('native', 'linux'):
        authored = {r['id']: r for r in cases('Darwin' if platform == 'native' else 'Linux')}
        expected = {(name, mode) for name in authored for mode in ('direct', 'string', 'file', 'stdin')}
        count = 64 if platform == 'native' else 96
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        full_log = gzip.decompress((HERE / f'{platform}-command-0.log.gz').read_bytes()).decode()
        assert 'Ran 208 tests in ' in full_log and 'Ran 13 tests in ' in full_log
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
        old = read(previous / f'{platform}-host-filesystem-profile.json.gz')
        new = read(HERE / f'{platform}-host-filesystem-profile.json.gz')
        focused = read(HERE / f'{platform}-host-filesystem-ls-output.json.gz')
        assert keys(new) - keys(old) == keys(focused) == expected
        assert keys(old) <= keys(new)
        assert focused['totals'] == dict(PASS=count, FAIL=0)
        assert new['totals']['PASS'] == old['totals']['PASS'] + count
        assert focused['ticket'] == 'CSH-123' and focused['predecessor'] == 'CSH-122'
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
            assert row['actual']['status'] > 0
            assert row['actual']['stdout'] == {'hex': ''}
            assert bytes.fromhex(row['actual']['stderr']['hex'])
            env = row['ls_output_environment']
            assert env['before'] == row['ls_output_observed']
            assert env['uid'] == env['euid'] == focused['uid']
            action = authored[row['id']]['io_action']
            number = {'closed-output': errno.EBADF, 'broken-pipe': errno.EPIPE, 'enospc': errno.ENOSPC}[action]
            assert marker_matches(row['kernel_fault'], action, focused['providers']['ls']['path'], number)
            invocation = row['invocation']
            assert row['expected']['args'] == authored[row['id']]['args']
            if row['mode'] == 'direct':
                assert invocation['args'][-len(row['expected']['args']):] == row['expected']['args']
                assert focused['providers']['ls']['path'] in invocation['args']
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            assert keys(read(previous / name), True) == keys(read(HERE / name), True), name
        summary[platform] = dict(reports=reports, required_command_passed=True)
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print('PASS: 64 native / 96 Linux new assertions; predecessor expectations, stock failure identities, source/provider provenance and cleanup retained.')


if __name__ == '__main__':
    verify()
