"""Verify CSH-109 removal graphs, predecessor expectations and exact provenance."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREVIOUS = HERE.with_name('csh-108')
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_removal import cases as removal_cases
from host_utilities import serial, source_identity


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return {(r['id'], r['mode']) for r in report['cases']
            if not failures or r['verdict'] == 'FAIL'}


def verify():
    authored = {r['id']: r for r in removal_cases()}
    source = json.loads((HERE / 'normative-source.json').read_text())
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    rmdir = next(r for r in mapping['utilities'] if r['utility'] == 'rmdir')
    assert source['url'] == rmdir['source'] and source['sha256'] == rmdir['source_sha256']
    assert set(rmdir['csh109_assertions']) == set(authored)

    summary, comparisons, digests = {}, {}, set()
    required = ('profile', 'allocation', 'provider-audit', 'residual', 'isolated',
                'interactive', 'decisions', 'metadata', 'recursive', 'path-limits',
                'cwd', 'creation', 'output', 'cwd-logical', 'magic', 'calendar',
                'reference', 'datetime', 'timezone', 'day-rules', 'transition-times',
                'magic-strings', 'magic-messages', 'magic-types', 'magic-defaults',
                'link-bytes', 'omitted-who', 'parent-graphs', 'removal', 'audit', 'stock-provider-audit')
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
        # Supplemental runtime/format checks preceded the fixture-only ordering
        # correction. Require identical binaries/providers and all their inputs.
        earlier_dir = HERE / 'development' / ('native-pre-correction' if platform == 'native'
                                              else 'csh109-linux-pre-review')
        earlier = read(earlier_dir / f'{platform}-host-filesystem-profile.json.gz')
        changed = {name for name, digest in earlier['source_identity']['files'].items()
                   if new['source_identity']['files'].get(name) != digest}
        assert changed == {'tests/host_filesystem_removal.py', 'tests/host_contracts.json',
                           'tests/host_filesystem_contracts.json', 'tests/host_filesystem_residuals.json'}
        assert earlier['binary_sha256'] == new['binary_sha256']
        assert earlier['providers'] == new['providers']
        current = {(r['id'], r['mode']): r for r in new['cases']}
        assert keys(old) <= keys(new)
        for row in old['cases']:
            before, after = dict(row['expected']), dict(current[(row['id'], row['mode'])]['expected'])
            for field in ('cwd_identity', 'creation_existing_identity', 'creation_preserved'):
                assert (field in before) == (field in after)
                if field in before:
                    for value in (before.pop(field), after.pop(field)):
                        if field == 'cwd_identity':
                            assert set(value) == {'device', 'inode'}
                            assert all(type(v) is int for v in value.values())
                        elif field == 'creation_preserved':
                            assert set(value) == {'existing', 'parent-alias', 'data', 'dangling'}
                            assert all(len(v) == 3 and all(type(n) is int for n in v) for v in value.values())
                        else:
                            assert len(value) == 2 and all(type(v) is int for v in value)
            assert before == after, row['id']
        focused = read(HERE / f'{platform}-host-filesystem-removal.json.gz')
        assert focused['totals'] == dict(PASS=76, FAIL=0)
        assert new['totals']['PASS'] - old['totals']['PASS'] == 76
        assert keys(new) - keys(old) == keys(focused)
        assert keys(focused) == {(name, mode) for name in authored
                                for mode in ('direct', 'string', 'file', 'stdin')}
        assert (focused['ticket'], focused['predecessor'], focused['selection']) == ('CSH-109', 'CSH-108', 'removal')
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        manifest = read(HERE / f'{platform}-host-profile-manifest.json.gz')
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64
            if utility in new['providers']:
                assert provider['sha256'] == new['providers'][utility]['sha256'], utility
        provider = manifest['executables']['rmdir']
        assert focused['providers']['rmdir'] == new['providers']['rmdir']
        assert provider['sha256'] == focused['providers']['rmdir']['sha256']
        assert not provider['override']
        # No vendor source/patch or shell C source was changed.
        for name, digest in old['source_identity']['files'].items():
            if name.startswith(('src/', 'include/', 'tools/host-profile/vendor/')):
                assert new['source_identity']['files'][name] == digest, name
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and row['errors'] == [] and row['cleanup']
            expected = serial(authored[row['id']])
            assert row['expected'] == expected
            assert row['captured']['capture_errors'] == []
            assert row['actual']['stdout'] == {'hex': ''}
            failure = expected['status'] == 'nonzero'
            assert row['actual']['status'] > 0 if failure else row['actual']['status'] == 0
            assert bool(row['actual']['stderr']['hex']) == failure
            for name, effect in expected['effects'].items():
                actual = row['actual']['effects'][name]
                assert all(actual[key] == value for key, value in effect.items()), (row['id'], name)
            environment = row['removal_environment']
            assert environment['uid'] == environment['euid'] == focused['uid'] != 0
            assert set(environment['objects']) == set(expected['removal_graph'])
            for name, identity in environment['objects'].items():
                assert set(identity) == {'device', 'inode', 'mode'}
                assert all(type(n) is int for n in identity.values())
                if expected['effects'][name]['type'] != 'absent':
                    assert row['removal_observed'][name] == identity
            if expected['removal_denial']:
                probe = environment['denial']
                assert probe['phase'] == 'armed' and probe['errno'] == 13
                assert probe['kind'] == expected['removal_denial']
                assert probe['mode'] == (0o500 if probe['kind'] == 'write' else 0)
                assert row['removal_observed']['armed_mode'] == probe['mode']
                assert probe['uid'] == probe['euid'] == focused['uid']
        for number, count in [(1, 14), (2, 5)]:
            checks = json.loads((HERE / f'{platform}-supplement-{number}.log').read_text())
            assert checks['passed'] == count and all(r['cleanup'] for r in checks['cases'])
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            before, after = read(PREVIOUS / name), read(HERE / name)
            assert keys(before, True) <= keys(after, True), (platform, suffix)
            added = keys(after, True) - keys(before, True)
            assert added == set(), added
            comparisons[platform][suffix] = dict(retained_failures=sorted(keys(before, True)), added_failures=sorted(added))
    assert digests == {source_identity()['sha256']}, 'evidence differs from current inputs'
    summary['source_identity_sha256'] = digests.pop()
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: exact new/previous expectations, retained stock failures, cleanup, provider/source identities')


if __name__ == '__main__':
    verify()
