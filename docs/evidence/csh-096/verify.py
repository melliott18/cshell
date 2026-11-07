"""Check retained CSH-096 evidence against CSH-095 without executing utilities."""
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.with_name('csh-095')
sys.path.insert(0, str(HERE.parents[2] / 'tests'))
from host_utilities import source_identity


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return sorted((r['id'], r['mode']) for r in report['cases']
                  if not failures or r['verdict'] == 'FAIL')


def verify():
    summary, comparisons, digests = {}, {}, set()
    for platform in ('native', 'linux'):
        commands = json.loads((HERE / (platform + '-commands.json')).read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        for target in ('profile', 'allocation', 'provider-audit', 'residual',
                       'isolated', 'interactive', 'decisions', 'metadata', 'recursive',
                       'path-limits', 'cwd', 'creation', 'output', 'cwd-logical',
                       'magic', 'calendar', 'audit', 'stock-provider-audit'):
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
        assert new['totals']['PASS'] - old['totals']['PASS'] == 160
        focused = read(HERE / (platform + '-host-filesystem-calendar.json.gz'))
        assert focused['totals'] == dict(PASS=160, FAIL=0)
        assert set(keys(new)) - set(keys(old)) == set(keys(focused))
        for row in focused['cases']:
            probe = row['calendar_environment']
            assert probe['phase'] == 'armed'
            assert probe['timezone'] == 'UTC0'
            assert len(probe['probes']) == 2
            assert all(p['requested_ns'] == p['observed_ns'] for p in probe['probes'])
            assert probe['probes'][0]['requested_ns'] == [probe['target_ns']] * 2
            assert probe['probes'][1]['requested_ns'] == probe['baseline_ns']
            assert len({(p['device'], p['inode']) for p in probe['probes']}) == 1
            assert row['actual']['stdout'] == row['actual']['stderr'] == {'hex': ''}
            assert row['actual']['status'] == 0
            actual = row['actual']['effects']['target']
            assert all(actual[k] == v for k, v in row['expected']['effects']['target'].items())
            assert focused['uid'] != 0
        assert {r['mode'] for r in focused['cases']} == {'direct', 'string', 'file', 'stdin'}
        assert len({r['id'] for r in focused['cases']}) == 40
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
