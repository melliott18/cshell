"""Verify exact CSH-106 oracles, unchanged CSH-105 expectations and provenance."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREVIOUS = HERE.with_name('csh-105')
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_link_bytes import cases
from host_utilities import serial, source_identity


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return {(r['id'], r['mode']) for r in report['cases']
            if not failures or r['verdict'] == 'FAIL'}


def verify():
    authored = {r['id']: r for r in cases()}
    summary, comparisons, digests = {}, {}, set()
    required = ('profile', 'allocation', 'provider-audit', 'residual', 'isolated',
                'interactive', 'decisions', 'metadata', 'recursive', 'path-limits',
                'cwd', 'creation', 'output', 'cwd-logical', 'magic', 'calendar',
                'reference', 'datetime', 'timezone', 'day-rules', 'transition-times',
                'magic-strings', 'magic-messages', 'magic-types', 'magic-defaults',
                'link-bytes', 'audit', 'stock-provider-audit')
    for platform in ('native', 'linux'):
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        supplemental = json.loads((HERE / f'{platform}-supplement-commands.json').read_text())
        assert [r['status'] for r in supplemental[:3]] == [0, 0, 0], supplemental
        if supplemental[3]['status'] != 0:
            recovery = json.loads((HERE / f'{platform}-refresh-recovery.json').read_text())
            assert recovery['status'] == 0 and recovery['source_identity_sha256'] == source_identity()['sha256']
        refresh = json.loads((HERE / f'{platform}-refresh-commands.json').read_text())
        assert refresh and all(r['status'] == r.get('expected_status', 0) for r in refresh)
        for target in required:
            assert (HERE / f'{platform}-host-filesystem-{target}.json.gz').is_file(), target
        summary[platform] = {}
        for path in sorted(HERE.glob(platform + '-host-*.json.gz')):
            report = read(path)
            if 'source_identity' not in report:
                continue
            digests.add(report['source_identity']['sha256'])
            summary[platform][path.name] = report['totals']
            if 'filesystem' in path.name:
                assert all(r['cleanup'] for r in report['cases']), path
            if not path.name.endswith(('-filesystem-audit.json.gz', '-stock-provider-audit.json.gz')):
                assert report['totals'].get('FAIL', report['totals'].get('failed')) == 0, path
        old = read(PREVIOUS / f'{platform}-host-filesystem-profile.json.gz')
        new = read(HERE / f'{platform}-host-filesystem-profile.json.gz')
        current = {(r['id'], r['mode']): r for r in new['cases']}
        assert keys(old) <= keys(new)
        for row in old['cases']:
            before, after = dict(row['expected']), dict(current[(row['id'], row['mode'])]['expected'])
            for field in ('cwd_identity', 'creation_existing_identity'):
                assert (field in before) == (field in after)
                if field in before:
                    for value in (before.pop(field), after.pop(field)):
                        if field == 'cwd_identity':
                            assert set(value) == {'device', 'inode'}
                            assert all(type(v) is int for v in value.values())
                        else:
                            assert len(value) == 2 and all(type(v) is int for v in value)
            assert before == after, row['id']
        focused = read(HERE / f'{platform}-host-filesystem-link-bytes.json.gz')
        assert focused['totals'] == dict(PASS=4352, FAIL=0)
        assert new['totals']['PASS'] - old['totals']['PASS'] == 4352
        assert keys(new) - keys(old) == keys(focused)
        assert keys(focused) == {(name, mode) for name in authored
                                for mode in ('direct', 'string', 'file', 'stdin')}
        assert (focused['ticket'], focused['predecessor'], focused['selection']) == ('CSH-106', 'CSH-105', 'link-bytes')
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        assert focused['utf8_locale']
        manifest = read(HERE / f'{platform}-host-profile-manifest.json.gz')
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64
            if utility in new['providers']:
                assert provider['sha256'] == new['providers'][utility]['sha256'], utility
        assert focused['providers']['readlink'] == new['providers']['readlink']
        assert manifest['executables']['readlink']['override']
        # None of the provider source/patch inputs changed in this increment.
        for name, digest in old['source_identity']['files'].items():
            if name.startswith('tools/') and not name.endswith('README.md'):
                assert new['source_identity']['files'][name] == digest, name
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and row['errors'] == [] and row['cleanup']
            expected = serial(authored[row['id']])
            assert row['expected'] == expected
            assert row['captured']['capture_errors'] == []
            assert row['actual']['stdout'] == expected['stdout']
            assert row['actual']['stderr'] == {'hex': ''} and row['actual']['status'] == 0
            probe = row['link_environment']
            assert probe['phase'] == 'armed'
            assert probe['before']['target_hex'] == expected['byte_link']['hex']
            assert probe['before']['size'] == len(bytes.fromhex(expected['byte_link']['hex']))
            assert row['link_observed'] == probe['before']
        for number, count in [(1, 14), (2, 5)]:
            checks = json.loads((HERE / f'{platform}-supplement-{number}.log').read_text())
            assert checks['passed'] == count and all(r['cleanup'] for r in checks['cases'])
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            before, after = read(PREVIOUS / name), read(HERE / name)
            assert keys(before, True) <= keys(after, True), (platform, suffix)
            added = keys(after, True) - keys(before, True)
            assert added <= keys(focused), (platform, suffix, added)
            expected_added = {(f'readlink/link-bytes-newlines-{locale}', mode)
                              for locale in ('c', 'utf8')
                              for mode in ('direct', 'string', 'file', 'stdin')}
            assert added == (expected_added if platform == 'native' and suffix == 'audit' else set())
            comparisons[platform][suffix] = dict(retained_failures=sorted(keys(before, True)), added_failures=sorted(added))
    assert digests == {source_identity()['sha256']}, 'evidence differs from current inputs'
    summary['source_identity_sha256'] = digests.pop()
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: exact new/previous expectations, retained stock failures, cleanup, provider/source identities')


if __name__ == '__main__':
    verify()
