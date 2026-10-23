"""Check retained CSH-099 evidence against CSH-098 without executing utilities."""
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.with_name('csh-098')
sys.path.insert(0, str(HERE.parents[2] / 'tests'))
from host_utilities import source_identity, serial
from host_filesystem_timezone import cases


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return sorted((r['id'], r['mode']) for r in report['cases']
                  if not failures or r['verdict'] == 'FAIL')


def verify():
    summary, comparisons, digests = {}, {}, set()
    authored = {r['id']: r for r in cases()}
    for platform in ('native', 'linux'):
        commands = json.loads((HERE / (platform + '-commands.json')).read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        for target in ('profile', 'allocation', 'provider-audit', 'residual',
                       'isolated', 'interactive', 'decisions', 'metadata', 'recursive',
                       'path-limits', 'cwd', 'creation', 'output', 'cwd-logical',
                       'magic', 'calendar', 'reference', 'datetime', 'timezone', 'audit', 'stock-provider-audit'):
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
            if not path.name.endswith(('-audit.json.gz', '-stock-provider-audit.json.gz')):
                assert report['totals'].get('FAIL', report['totals'].get('failed')) == 0, path
            # Selected provider-audit is also mandatory, despite its audit name.
            if path.name.endswith('-filesystem-provider-audit.json.gz'):
                assert report['totals']['FAIL'] == 0, path
        name = platform + '-host-filesystem-profile.json.gz'
        old, new = read(PREVIOUS / name), read(HERE / name)
        assert set(keys(old)) <= set(keys(new))
        assert new['totals']['PASS'] - old['totals']['PASS'] == 416
        focused = read(HERE / (platform + '-host-filesystem-timezone.json.gz'))
        assert focused['totals'] == dict(PASS=416, FAIL=0)
        assert focused['ticket'] == 'CSH-099' and focused['predecessor'] == 'CSH-098'
        assert focused['selection'] == 'timezone'
        assert len(focused['providers']['touch']['sha256']) == 64
        assert set(keys(new)) - set(keys(old)) == set(keys(focused))
        assert not focused['full_contracts_qualified']
        manifest = read(HERE / (platform + '-host-profile-manifest.json.gz'))
        assert manifest['executables']['touch']['sha256'] == focused['providers']['touch']['sha256']
        assert new['providers']['touch'] == focused['providers']['touch']
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64, utility
            if utility in new['providers']:
                assert new['providers'][utility]['sha256'] == provider['sha256'], utility
        for name in ('host-coreutils-build-configure.log', 'host-coreutils-build-build.log',
                     'host-pax-build-build.log'):
            assert gzip.decompress((HERE / (platform + '-' + name + '.gz')).read_bytes())
        assert {r['id'] for r in focused['cases']} == set(authored)
        for row in focused['cases']:
            probe = row['datetime_environment']
            assert probe['phase'] == 'armed'
            assert len(probe['probes']) == 2
            assert all(p['requested_ns'] == p['observed_ns'] for p in probe['probes'])
            assert [p['requested_ns'] for p in probe['probes']] == [
                [probe['target_ns'], probe['target_ns']], probe['baseline_ns']]
            assert probe['before'] == row['datetime_observed']
            assert all((p['device'], p['inode']) ==
                       (probe['before']['device'], probe['before']['inode']) for p in probe['probes'])
            assert row['invocation']['env']['TZ'] == probe['timezone']
            expected = authored[row['id']]
            assert row['expected']['args'] == expected['args']
            assert row['invocation']['env']['TZ'] == expected['env']['TZ']
            assert probe['scope'] == expected['datetime_environment']['scope']
            assert probe['target_ns'] == expected['datetime_environment']['target_ns']
            assert row['expected']['effects'] == serial(expected['effects'])
            assert row['captured']['capture_errors'] == []
            assert row['actual']['stdout'] == row['actual']['stderr'] == {'hex': ''}
            assert row['actual']['status'] == 0
            for name, expected in row['expected']['effects'].items():
                actual = row['actual']['effects'][name]
                assert all(actual[k] == value for k, value in expected.items())
            assert focused['uid'] != 0
        assert {r['mode'] for r in focused['cases']} == {'direct', 'string', 'file', 'stdin'}
        assert len({r['id'] for r in focused['cases']}) == 104
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = platform + '-host-filesystem-' + suffix + '.json.gz'
            old, new = read(PREVIOUS / name), read(HERE / name)
            before, after = keys(old, True), keys(new, True)
            assert before == after, (platform, suffix, before, after)
            comparisons[platform][suffix] = dict(unchanged=True, failures=after)
    assert len(digests) == 1, digests
    summary['source_identity_sha256'] = digests.pop()
    assert summary['source_identity_sha256'] == source_identity()['sha256']
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: selected results, prior assertions, stock failures, cleanup and source identities')


if __name__ == '__main__':
    verify()
