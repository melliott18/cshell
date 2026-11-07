"""Verify current CSH-105 identities, exact oracles and retained CSH-104 evidence."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.with_name('csh-104')
sys.path.insert(0, str(HERE.parents[2] / 'tests'))
from host_utilities import source_identity, serial
from host_filesystem_magic_defaults import cases


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return {(r['id'], r['mode']) for r in report['cases']
            if not failures or r['verdict'] == 'FAIL'}


def verify():
    summary, comparisons, digests = {}, {}, set()
    authored = {r['id']: r for r in cases()}
    required = ('profile', 'allocation', 'provider-audit', 'residual', 'isolated',
                'interactive', 'decisions', 'metadata', 'recursive', 'path-limits',
                'cwd', 'creation', 'output', 'cwd-logical', 'magic', 'calendar',
                'reference', 'datetime', 'timezone', 'day-rules', 'transition-times',
                'magic-strings', 'magic-messages', 'magic-types', 'magic-defaults', 'audit', 'stock-provider-audit')
    for platform in ('native', 'linux'):
        commands = json.loads((HERE / (platform + '-commands.json')).read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        supplemental = json.loads((HERE / (platform + '-supplement-commands.json')).read_text())
        assert [r['status'] for r in supplemental] == [0, 0, 0], supplemental
        for target in required:
            assert (HERE / f'{platform}-host-filesystem-{target}.json.gz').is_file(), target
        assert (HERE / f'{platform}-host-profile-results.json.gz').is_file()
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
        focused = read(HERE / f'{platform}-host-filesystem-magic-defaults.json.gz')
        assert focused['totals'] == dict(PASS=1120, FAIL=0)
        assert new['totals']['PASS'] - old['totals']['PASS'] == 1120
        assert keys(new) - keys(old) == keys(focused)
        assert keys(focused) == {(name, mode) for name in authored
                                for mode in ('direct', 'string', 'file', 'stdin')}
        assert focused['ticket'] == 'CSH-105' and focused['predecessor'] == 'CSH-104'
        assert focused['selection'] == 'magic-defaults'
        assert not focused['full_contracts_qualified'] and focused['uid'] != 0
        manifest = read(HERE / f'{platform}-host-profile-manifest.json.gz')
        assert manifest['executables']['file']['sha256'] == focused['providers']['file']['sha256']
        assert manifest['executables']['file']['override']
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64
            if utility in new['providers']:
                assert provider['sha256'] == new['providers'][utility]['sha256'], utility
        assert focused['providers']['file'] == new['providers']['file']
        source = manifest['executables']['file']['source']
        for key, path in [('archive_sha256', 'tools/host-profile/vendor/file/file-5.46.tar.gz'),
                          ('patch_sha256', 'tools/host-profile/vendor/file/message-formats.patch'),
                          ('build_script_sha256', 'tools/host-profile/build-file.sh')]:
            assert source[key] == hashlib.sha256((HERE.parents[2] / path).read_bytes()).hexdigest()
        safety = json.loads((HERE / (platform + '-supplement-1.log')).read_text())
        assert safety['passed'] == 14
        assert all(r['passed'] and r['cleanup'] for r in safety['cases'])
        type_checks = json.loads((HERE / (platform + '-supplement-2.log')).read_text())
        assert type_checks['passed'] == 5 and all(r['cleanup'] for r in type_checks['cases'])
        # The native-alias repair must not alter the vendor compiled database.
        old_manifest = read(PREVIOUS / f'{platform}-host-profile-manifest.json.gz')
        assert source['magic_database_sha256'] == old_manifest['executables']['file']['source']['magic_database_sha256']
        provider_commands = json.loads((HERE / (platform + '-provider-commands.json')).read_text())
        assert all(r['status'] == r['expected_status'] for r in provider_commands)
        for record in provider_commands:
            if record['name'] in ('sanitized-configure', 'sanitized-build'):
                assert '-fsanitize=address,undefined' in record['env']['CFLAGS']
                assert '-fsanitize=address,undefined' in record['env']['LDFLAGS']
        for selection, count in [('magic-defaults',1120), ('magic-types',1440), ('magic-messages',432), ('magic',184), ('magic-strings',364)]:
            report = read(HERE / f'{platform}-sanitized-{selection}.json.gz')
            assert report['totals'] == dict(PASS=count, FAIL=0)
            assert report['providers']['file']['sha256'] != manifest['executables']['file']['sha256']
            assert all(r['cleanup'] and not r['errors'] for r in report['cases'])
            digests.add(report['source_identity']['sha256'])
        for selection, totals in [('magic-defaults',dict(PASS=812,FAIL=308)),
                                  ('magic-types',dict(PASS=1352,FAIL=88)),
                                  ('magic-messages',dict(PASS=292,FAIL=140)),
                                  ('magic',dict(PASS=176,FAIL=8))]:
            report = read(HERE / f'{platform}-unpatched-{selection}.json.gz')
            assert report['totals'] == totals, (platform, selection, report['totals'])
            assert all(r['cleanup'] for r in report['cases'])
            digests.add(report['source_identity']['sha256'])
        checks = json.loads((HERE / f'{platform}-sanitized-format-checks.log').read_text())
        assert checks['passed'] == 14 and all(r['cleanup'] for r in checks['cases'])
        type_checks = json.loads((HERE / f'{platform}-sanitized-type-checks.log').read_text())
        assert type_checks['passed'] == 5 and all(r['cleanup'] for r in type_checks['cases'])
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and row['errors'] == [] and row['cleanup']
            expected = serial(authored[row['id']])
            assert row['expected'] == expected
            probe = row['magic_environment']
            assert probe['phase'] == 'armed'
            assert probe['sample_hex'] == expected['files']['sample']['hex']
            for field, value in expected['magic_environment'].items():
                assert probe[field] == value
            assert row['captured']['capture_errors'] == []
            assert row['actual']['stdout'] == expected['stdout']
            assert row['actual']['stderr'] == {'hex': ''} and row['actual']['status'] == 0
            for name, effect in expected['effects'].items():
                assert all(row['actual']['effects'][name][k] == v for k,v in effect.items())
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = f'{platform}-host-filesystem-{suffix}.json.gz'
            before, after = read(PREVIOUS / name), read(HERE / name)
            assert keys(before, True) <= keys(after, True), (platform, suffix)
            added = keys(after, True) - keys(before, True)
            assert added <= keys(focused), (platform, suffix, added)
            if suffix == 'audit':
                assert added
            else:
                assert not added
            comparisons[platform][suffix] = dict(unchanged_failures=sorted(keys(before, True)), added_numeric_failures=sorted(added))
    assert len(digests) == 1, digests
    digest = digests.pop()
    assert digest == source_identity()['sha256'], 'evidence differs from current build/test inputs'
    summary['source_identity_sha256'] = digest
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: exact new/previous expectations, stock failures, cleanup and provider/source identities')


if __name__ == '__main__':
    verify()
