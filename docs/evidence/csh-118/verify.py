"""Verify CSH-118 retained evidence without weakening predecessor assertions."""
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREVIOUS = HERE.with_name('csh-117')
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_ls_sockets import cases, output_matches, expected_entries
from host_utilities import serial, source_identity

spec = importlib.util.spec_from_file_location('predecessor_verifier', PREVIOUS / 'verify.py')
predecessor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(predecessor)


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return {(r['id'], r['mode']) for r in report['cases']
            if not failures or r['verdict'] == 'FAIL'}


def verify(platforms=('native', 'linux')):
    assert platforms and set(platforms) <= {'native', 'linux'}
    authored = {r['id']: r for r in cases()}
    assert len(authored) == 36
    expected_keys = {(name, mode) for name in authored for mode in ('direct', 'string', 'file', 'stdin')}
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    entry = next(r for r in mapping['utilities'] if r['utility'] == 'ls')
    source = json.loads((HERE / 'normative-source.json').read_text())
    assert source['url'] == entry['source'] and source['sha256'] == entry['source_sha256']
    assert hashlib.sha256(gzip.decompress((HERE / 'ls.html.gz').read_bytes())).hexdigest() == source['sha256']
    assert set(entry['csh118_assertions']) == set(authored)
    required = ('profile', 'allocation', 'provider-audit', 'residual', 'isolated',
                'interactive', 'decisions', 'metadata', 'recursive', 'path-limits',
                'cwd', 'creation', 'output', 'cwd-logical', 'magic', 'calendar',
                'reference', 'datetime', 'timezone', 'day-rules', 'transition-times',
                'magic-strings', 'magic-messages', 'magic-types', 'magic-defaults',
                'link-bytes', 'omitted-who', 'parent-graphs', 'removal', 'link-graphs',
                'link-permissions', 'touch-permissions', 'touch-current', 'touch-objects',
                'ls-blocks', 'ls-totals', 'ls-identity', 'ls-sockets', 'audit', 'stock-provider-audit')
    current_source = source_identity()['files']
    summary, comparisons, digests = {}, {}, {}
    for platform in platforms:
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        for target in required:
            assert (HERE / f'{platform}-host-filesystem-{target}.json.gz').is_file(), target
        expected_source = dict(current_source)
        for header in ('host-test-provider.h', 'host-newgrp-provider.h'):
            content = gzip.decompress((HERE / f'{platform}-{header}.gz').read_bytes())
            expected_source['build/' + header] = hashlib.sha256(content).hexdigest()
        digest = hashlib.sha256(json.dumps(expected_source, sort_keys=True).encode()).hexdigest()
        digests[platform] = digest
        summary[platform] = {}
        for path in sorted(HERE.glob(platform + '-host-*.json.gz')):
            report = read(path)
            if 'source_identity' not in report:
                continue
            assert report['source_identity']['sha256'] == digest, path
            summary[platform][path.name] = report['totals']
            if 'filesystem' in path.name:
                assert all(r['cleanup'] for r in report['cases']), path
            if not path.name.endswith(('-filesystem-audit.json.gz', '-stock-provider-audit.json.gz')):
                assert report['totals'].get('FAIL', report['totals'].get('failed')) == 0, path
        old = read(PREVIOUS / f'{platform}-host-filesystem-profile.json.gz')
        new = read(HERE / f'{platform}-host-filesystem-profile.json.gz')
        focused = read(HERE / f'{platform}-host-filesystem-ls-sockets.json.gz')
        current = {(r['id'], r['mode']): r for r in new['cases']}
        assert keys(old) <= keys(new)
        for row in old['cases']:
            after = current[(row['id'], row['mode'])]
            assert predecessor.predecessor.predecessor.predecessor.stable_expected(row) == predecessor.predecessor.predecessor.predecessor.stable_expected(after), row['id']
        assert focused['totals'] == dict(PASS=144, FAIL=0)
        assert new['totals']['PASS'] - old['totals']['PASS'] == 144
        assert keys(new) - keys(old) == keys(focused) == expected_keys
        assert (focused['ticket'], focused['predecessor'], focused['selection']) == ('CSH-118', 'CSH-117', 'ls-sockets')
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        manifest = read(HERE / f'{platform}-host-profile-manifest.json.gz')
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64
            if utility in new['providers']:
                assert provider['sha256'] == new['providers'][utility]['sha256'], utility
        old_manifest = read(PREVIOUS / f'{platform}-host-profile-manifest.json.gz')
        for name, sha in old['source_identity']['files'].items():
            if name.startswith('tools/'):
                assert new['source_identity']['files'][name] == sha, name
        provider = manifest['executables']['ls']
        assert provider['source'] == old_manifest['executables']['ls']['source']
        assert focused['providers']['ls'] == new['providers']['ls']
        assert provider['override'] and provider['sha256'] == focused['providers']['ls']['sha256']
        assert provider['source']['version'] == 'GNU coreutils 9.7'
        assert provider['source']['build_targets'] == ['src/ls']
        archive = ROOT / provider['source']['archive']
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == provider['source']['archive_sha256']
        assert (HERE / f'{platform}-host-coreutils-build-ls.log.gz').is_file()
        # Providers are unchanged from CSH-117.
        # The shell implementation itself must remain unchanged in this ticket.
        baseline = json.loads((HERE / 'baseline-source.json').read_text())
        for name, sha in baseline.items():
            assert new['source_identity']['files'][name] == sha, name
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and row['errors'] == [] and row['cleanup']
            assert row['expected'] == serial(authored[row['id']])
            assert row['captured']['capture_errors'] == []
            assert row['actual']['status'] == 0 and row['actual']['stderr'] == {'hex': ''}
            env = row['ls_socket_environment']
            assert env['binding'] == dict(status=0, stdout=b'bound-and-closed\n'.hex(), stderr='',
                                          endpoints=['stream', 'datagram'], closed_before_exec=True)
            assert env['before'] == row['ls_socket_observed']
            assert env['uid'] == env['euid'] == focused['uid'] != 0
            spec = authored[row['id']]['ls_sockets']
            assert env['entries'] == serial(expected_entries(env['before'], spec))
            assert output_matches(env, bytes.fromhex(row['actual']['stdout']['hex']))
            if row['mode'] == 'direct':
                assert row['executable'] == focused['providers']['ls']['path']
            assert row['invocation']['env']['PATH'] == focused['path']
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            before, after = read(PREVIOUS / name), read(HERE / name)
            added = ({(name, mode) for name, mode in expected_keys
                      if name in {'ls/sockets-plain-inode-H-operands', 'ls/sockets-p-inode-H-operands',
                                  'ls/sockets-F-name-H-operands', 'ls/sockets-F-inode-H-operands'}}
                     if platform == 'native' and suffix == 'audit' else set())
            assert keys(after, True) == keys(before, True) | added, (platform, suffix)
            for row in after['cases']:
                if (row['id'], row['mode']) in added:
                    assert row['errors'] == ['stdout mismatch'] and row['cleanup']
                    assert row['actual']['status'] == 0 and row['actual']['stderr'] == {'hex': ''}
                    assert row['ls_socket_environment']['before'] == row['ls_socket_observed']
                    assert row['expected'] == serial(authored[row['id']])
            comparisons[platform][suffix] = dict(retained_failures=sorted(keys(before, True)), added_failures=sorted(added))
    summary['source_identity_sha256'] = digests
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: 144 new assertions per platform, all predecessor oracles, stock failures, cleanup and provenance')


if __name__ == '__main__':
    verify(tuple(sys.argv[1:]) or ('native', 'linux'))
