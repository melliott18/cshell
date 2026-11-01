"""Verify CSH-108 parent graphs, predecessor expectations and exact provenance."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREVIOUS = HERE.with_name('csh-107')
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_creation import parent_graph_cases
from host_utilities import serial, source_identity


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return {(r['id'], r['mode']) for r in report['cases']
            if not failures or r['verdict'] == 'FAIL'}


def verify():
    authored = {r['id']: r for r in parent_graph_cases()}
    source = json.loads((HERE / 'normative-source.json').read_text())
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    mkdir = next(r for r in mapping['utilities'] if r['utility'] == 'mkdir')
    assert source['url'] == mkdir['source'] and source['sha256'] == mkdir['source_sha256']
    assert set(mkdir['csh108_assertions']) == set(authored)

    summary, comparisons, digests = {}, {}, set()
    required = ('profile', 'allocation', 'provider-audit', 'residual', 'isolated',
                'interactive', 'decisions', 'metadata', 'recursive', 'path-limits',
                'cwd', 'creation', 'output', 'cwd-logical', 'magic', 'calendar',
                'reference', 'datetime', 'timezone', 'day-rules', 'transition-times',
                'magic-strings', 'magic-messages', 'magic-types', 'magic-defaults',
                'link-bytes', 'omitted-who', 'parent-graphs', 'audit', 'stock-provider-audit')
    for platform in ('native', 'linux'):
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        supplement = json.loads((HERE / f'{platform}-supplement-commands.json').read_text())
        assert [r['status'] for r in supplement] == [0, 0, 0], supplement
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
        focused = read(HERE / f'{platform}-host-filesystem-parent-graphs.json.gz')
        assert focused['totals'] == dict(PASS=240, FAIL=0)
        assert new['totals']['PASS'] - old['totals']['PASS'] == 240
        assert keys(new) - keys(old) == keys(focused)
        assert keys(focused) == {(name, mode) for name in authored
                                for mode in ('direct', 'string', 'file', 'stdin')}
        assert (focused['ticket'], focused['predecessor'], focused['selection']) == ('CSH-108', 'CSH-107', 'parent-graphs')
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        manifest = read(HERE / f'{platform}-host-profile-manifest.json.gz')
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64
            if utility in new['providers']:
                assert provider['sha256'] == new['providers'][utility]['sha256'], utility
        for utility in ('mkdir',):
            provider = manifest['executables'][utility]
            assert focused['providers'][utility] == new['providers'][utility]
            assert provider['override']
            assert provider['source']['version'] == 'GNU coreutils 9.7'
            archive = ROOT / provider['source']['archive']
            assert provider['source']['archive_sha256'] == hashlib.sha256(archive.read_bytes()).hexdigest()
        # No vendor source/patch or shell C source was changed.
        for name, digest in old['source_identity']['files'].items():
            if name.startswith(('src/', 'include/', 'tools/host-profile/vendor/')):
                assert new['source_identity']['files'][name] == digest, name
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and row['errors'] == [] and row['cleanup']
            expected = serial(authored[row['id']])
            measured = dict(row['expected'])
            identity = measured.pop('creation_existing_identity')
            preserved = measured.pop('creation_preserved')
            assert set(preserved) == {'existing', 'parent-alias', 'data', 'dangling'}
            assert identity == preserved['existing'][:2]
            assert all(len(v) == 3 and all(type(n) is int for n in v) for v in preserved.values())
            assert measured == expected
            assert row['captured']['capture_errors'] == []
            assert row['actual']['stdout'] == {'hex': ''}
            failure = expected['parent_graph'].endswith('obstruction')
            assert row['actual']['status'] > 0 if failure else row['actual']['status'] == 0
            assert bool(row['actual']['stderr']['hex']) == failure
            for name, effect in expected['effects'].items():
                actual = row['actual']['effects'][name]
                assert all(actual[key] == value for key, value in effect.items()), (row['id'], name)
            probe = row['creation_environment']
            mask = expected['creation_mask']
            assert probe['phase'] == 'armed' and probe['requested_mask'] == probe['observed_mask'] == mask
            assert probe['directory_mode'] == 0o777 & ~mask and probe['fifo_mode'] == 0o666 & ~mask
            assert probe['uid'] == probe['euid'] == focused['uid']
            assert probe['provider'] == focused['providers'][expected['utility']]['path']
        for number, count in [(1, 14), (2, 5)]:
            checks = json.loads((HERE / f'{platform}-supplement-{number}.log').read_text())
            assert checks['passed'] == count and all(r['cleanup'] for r in checks['cases'])
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            before, after = read(PREVIOUS / name), read(HERE / name)
            assert keys(before, True) <= keys(after, True), (platform, suffix)
            added = keys(after, True) - keys(before, True)
            expected_added = {(name, mode) for name in authored
                              if name.startswith(('mkdir/parent-graph-077-copy-', 'mkdir/parent-graph-777-copy-'))
                              for mode in ('direct', 'string', 'file', 'stdin')}
            assert added == (expected_added if platform == 'native' and suffix == 'audit' else set()), added
            comparisons[platform][suffix] = dict(retained_failures=sorted(keys(before, True)), added_failures=sorted(added))
    assert digests == {source_identity()['sha256']}, 'evidence differs from current inputs'
    summary['source_identity_sha256'] = digests.pop()
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: exact new/previous expectations, retained stock failures, cleanup, provider/source identities')


if __name__ == '__main__':
    verify()
