"""Check retained CSH-094 evidence against CSH-093 without executing utilities."""
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.with_name('csh-093')


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
        assert new['totals']['PASS'] - old['totals']['PASS'] == 48
        focused = read(HERE / (platform + '-host-filesystem-cwd-logical.json.gz'))
        assert focused['totals'] == dict(PASS=48, FAIL=0)
        assert set(keys(new)) - set(keys(old)) == set(keys(focused))
        for row in focused['cases']:
            probe = row['cwd_environment']
            assert probe['phase'] == 'armed' and probe['before'] == probe['after']
            assert probe['pwd'] == probe['pwd_after']
            assert probe['pwd_identity'] != probe['after']
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
