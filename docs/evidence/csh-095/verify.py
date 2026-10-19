"""Check retained CSH-095 evidence against CSH-094 without executing utilities."""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.with_name('csh-094')


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
        assert new['totals']['PASS'] - old['totals']['PASS'] == 184
        focused = read(HERE / (platform + '-host-filesystem-magic.json.gz'))
        assert focused['totals'] == dict(PASS=184, FAIL=0)
        assert set(keys(new)) - set(keys(old)) == set(keys(focused))
        for row in focused['cases']:
            probe = row['magic_environment']
            assert probe['phase'] == 'armed'
            assert probe['sample_hex'] == row['expected']['files']['sample']['hex']
            assert row['actual']['stdout'] == row['expected']['stdout']
            assert row['actual']['stderr'] == {'hex': ''}
            assert row['actual']['status'] == 0
            for name in ('sample', 'magic'):
                assert row['actual']['effects'][name]['content'] == row['expected']['files'][name]
            assert probe['c_bytes'] == {'byte': 1, 'short': 2}
            assert focused['uid'] != 0
        assert {r['mode'] for r in focused['cases']} == {'direct', 'string', 'file', 'stdin'}
        assert len({r['id'] for r in focused['cases']}) == 46
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = platform + '-host-filesystem-' + suffix + '.json.gz'
            old, new = read(PREVIOUS / name), read(HERE / name)
            before, after = keys(old, True), keys(new, True)
            assert before == after, (platform, suffix, before, after)
            comparisons[platform][suffix] = dict(unchanged=True, failures=after)
    assert len(digests) == 1, digests
    summary['source_identity_sha256'] = digests.pop()
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: selected results, prior assertions, stock failures, cleanup and source identities')


if __name__ == '__main__':
    verify()
