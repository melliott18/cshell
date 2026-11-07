"""Check retained CSH-114 oracles, predecessor preservation and provenance."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import stat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREVIOUS = HERE.with_name('csh-113')
sys.path.insert(0, str(ROOT / 'tests'))
from host_filesystem_touch_objects import BASELINE, TARGET, cases
from host_utilities import serial, source_identity


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return {(r['id'], r['mode']) for r in report['cases']
            if not failures or r['verdict'] == 'FAIL'}


def stable_expected(row):
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


def verify():
    authored = {r['id']: r for r in cases()}
    assert len(authored) == 28
    source = json.loads((HERE / 'normative-source.json').read_text())
    mapping = json.loads((ROOT / 'tests/host_filesystem_contracts.json').read_text())
    entry = next(r for r in mapping['utilities'] if r['utility'] == 'touch')
    assert source['url'] == entry['source'] and source['sha256'] == entry['source_sha256']
    assert set(entry['csh114_assertions']) == set(authored)
    summary, comparisons, digests = {}, {}, set()
    required = ('profile', 'allocation', 'provider-audit', 'residual', 'isolated',
                'interactive', 'decisions', 'metadata', 'recursive', 'path-limits',
                'cwd', 'creation', 'output', 'cwd-logical', 'magic', 'calendar',
                'reference', 'datetime', 'timezone', 'day-rules', 'transition-times',
                'magic-strings', 'magic-messages', 'magic-types', 'magic-defaults',
                'link-bytes', 'omitted-who', 'parent-graphs', 'removal', 'link-graphs',
                'link-permissions', 'touch-permissions', 'touch-current', 'touch-objects', 'audit', 'stock-provider-audit')
    for platform in ('native', 'linux'):
        commands = json.loads((HERE / f'{platform}-commands.json').read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
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
            after = current[(row['id'], row['mode'])]
            for field in ('cwd_identity', 'creation_existing_identity', 'creation_preserved'):
                assert (field in row['expected']) == (field in after['expected'])
            assert stable_expected(row) == stable_expected(after), row['id']
        focused = read(HERE / f'{platform}-host-filesystem-touch-objects.json.gz')
        assert focused['totals'] == dict(PASS=112, FAIL=0)
        assert new['totals']['PASS'] - old['totals']['PASS'] == 112
        assert keys(new) - keys(old) == keys(focused)
        assert keys(focused) == {(name, mode) for name in authored
                                for mode in ('direct', 'string', 'file', 'stdin')}
        assert (focused['ticket'], focused['predecessor'], focused['selection']) == ('CSH-114', 'CSH-113', 'touch-objects')
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        manifest = read(HERE / f'{platform}-host-profile-manifest.json.gz')
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64
            if utility in new['providers']:
                assert provider['sha256'] == new['providers'][utility]['sha256'], utility
        provider = manifest['executables']['touch']
        assert focused['providers']['touch'] == new['providers']['touch']
        assert provider['sha256'] == focused['providers']['touch']['sha256'] and provider['override']
        assert provider['source']['version'] == 'GNU coreutils 9.7 + IANA tzcode 2025b'
        old_manifest = read(PREVIOUS / f'{platform}-host-profile-manifest.json.gz')
        assert provider['source'] == old_manifest['executables']['touch']['source']
        archive = ROOT / provider['source']['tzcode_archive']
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == provider['source']['tzcode_archive_sha256']
        assert (HERE / f'{platform}-host-tzcode-build.log.gz').is_file()
        for name, digest in old['source_identity']['files'].items():
            if name.startswith(('src/', 'include/', 'tools/host-profile/')):
                assert new['source_identity']['files'][name] == digest, name
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and row['errors'] == [] and row['cleanup']
            expected = serial(authored[row['id']])
            # ELOOP has different numeric values on the two measured kernels.
            if expected['touch_objects']['boundary'] == 'symlink-loop':
                expected['touch_objects']['errno'] = 40 if platform == 'linux' else 62
            assert row['expected'] == expected
            assert row['captured']['capture_errors'] == []
            assert row['actual']['stdout'] == {'hex': ''}
            failure = expected['status'] == 'nonzero'
            assert row['actual']['status'] > 0 if failure else row['actual']['status'] == 0
            assert bool(row['actual']['stderr']['hex']) == failure
            for name, effect in expected['effects'].items():
                actual = row['actual']['effects'][name]
                assert all(actual[key] == value for key, value in effect.items()), (row['id'], name)
            spec = expected['touch_objects']
            assert row['touch_exec'] == dict(
                phase='exec', provider=focused['providers']['touch']['path'],
                uid=focused['uid'], euid=focused['uid'])
            environment = row['touch_object_environment']
            observed = row['touch_object_observed']
            assert environment['uid'] == environment['euid'] == focused['uid'] != 0
            assert environment['errno'] == observed['errno'] == spec['errno']
            nonlinks = {n for n, e in expected['effects'].items() if e['type'] != 'link'}
            assert len(environment['probes']) == 2 * len(nonlinks)
            assert {p['path'] for p in environment['probes']} == nonlinks
            for probe in environment['probes']:
                assert probe['requested_ns'] == probe['observed_ns']
                assert probe['requested_ns'] in ([TARGET, TARGET], list(BASELINE))
            assert set(environment['before']) == set(observed['objects']) == set(expected['effects'])
            for name, after in observed['objects'].items():
                before = environment['before'][name]
                assert all(after[k] == before[k] for k in ('device', 'inode', 'mode', 'nlink', 'size'))
                if stat.S_ISLNK(before['mode']):
                    assert after['mtime_ns'] == before['mtime_ns']
                else:
                    assert (before['atime_ns'], before['mtime_ns']) == BASELINE
                    changed = name in ('first', 'last') or (not spec['errno'] and name in ('object', 'object-hard'))
                    stamps = tuple(spec['target_ns']) if changed else BASELINE
                    assert (after['atime_ns'], after['mtime_ns']) == stamps
            if spec['kind'] == 'fifo':
                objects = observed['objects']
                assert objects['object']['nlink'] == objects['object-hard']['nlink'] == 2
                assert objects['object']['inode'] == objects['object-hard']['inode']
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            before, after = read(PREVIOUS / name), read(HERE / name)
            assert keys(before, True) == keys(after, True), (platform, suffix)
            comparisons[platform][suffix] = dict(retained_failures=sorted(keys(before, True)), added_failures=[])
    assert digests == {source_identity()['sha256']}, 'evidence differs from current inputs'
    summary['source_identity_sha256'] = digests.pop()
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: 112 new assertions per platform, all predecessor oracles, stock failures, cleanup and provenance')


if __name__ == '__main__':
    verify()
