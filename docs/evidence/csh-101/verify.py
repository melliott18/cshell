"""Check retained CSH-101 evidence against CSH-100 without executing utilities."""
import gzip
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.with_name('csh-100')
sys.path.insert(0, str(HERE.parents[2] / 'tests'))
from host_utilities import source_identity, serial
from host_filesystem_transition_times import cases


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def keys(report, failures=False):
    return sorted((r['id'], r['mode']) for r in report['cases']
                  if not failures or r['verdict'] == 'FAIL')


def verify():
    summary, comparisons, digests = {}, {}, set()
    authored = {r['id']: r for r in cases()}
    for platform in ('native', 'linux'):
        supplements = json.loads((HERE / (platform + '-supplement-commands.json')).read_text())
        assert [r['status'] for r in supplements] == [0, 0], supplements
        sanitizer = read(HERE / (platform + '-sanitizer.json.gz'))
        assert sanitizer['totals'] == dict(PASS=384, FAIL=0)
        assert all(r['cleanup'] and r['verdict'] == 'PASS' for r in sanitizer['cases'])
        assert len(sanitizer['binary_sha256']) == 64
        assert keys(sanitizer) == sorted((case_id, mode) for case_id in authored
                                        for mode in ('direct', 'string', 'file', 'stdin'))
        link = sanitizer['build_commands'][1]
        instrumented = link[link.index('-o') + 1]
        for row in sanitizer['cases']:
            assert row['invocation']['env']['PATH'].split(':')[0] == str(Path(instrumented).parent)
            if row['mode'] == 'direct':
                assert row['executable'] == instrumented
        digests.add(sanitizer['source_identity']['sha256'])
        commands = json.loads((HERE / (platform + '-commands.json')).read_text())
        assert [r['status'] for r in commands] == [0, 2, 1], commands
        for target in ('profile', 'allocation', 'provider-audit', 'residual',
                       'isolated', 'interactive', 'decisions', 'metadata', 'recursive',
                       'path-limits', 'cwd', 'creation', 'output', 'cwd-logical',
                       'magic', 'calendar', 'reference', 'datetime', 'timezone', 'day-rules', 'transition-times', 'audit', 'stock-provider-audit'):
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
        current = {(r['id'], r['mode']): r for r in new['cases']}
        for row in old['cases']:
            # These two pre-exec device/inode observations are necessarily new
            # for each disposable fixture. Preserve their presence and type;
            # compare every authored expectation exactly, including all effects.
            before = dict(row['expected'])
            after = dict(current[(row['id'], row['mode'])]['expected'])
            for field in ('cwd_identity', 'creation_existing_identity'):
                assert (field in before) == (field in after), (row['id'], field)
                if field in before:
                    for value in (before.pop(field), after.pop(field)):
                        if field == 'cwd_identity':
                            assert set(value) == {'device', 'inode'}
                            assert all(type(v) is int for v in value.values())
                        else:
                            assert len(value) == 2 and all(type(v) is int for v in value)
            assert before == after, row['id']
        assert new['totals']['PASS'] - old['totals']['PASS'] == 384
        focused = read(HERE / (platform + '-host-filesystem-transition-times.json.gz'))
        assert focused['totals'] == dict(PASS=384, FAIL=0)
        assert focused['ticket'] == 'CSH-101' and focused['predecessor'] == 'CSH-100'
        assert focused['selection'] == 'transition-times'
        assert len(focused['providers']['touch']['sha256']) == 64
        assert set(keys(new)) - set(keys(old)) == set(keys(focused))
        assert not focused['full_contracts_qualified']
        manifest = read(HERE / (platform + '-host-profile-manifest.json.gz'))
        assert manifest['executables']['touch']['sha256'] == focused['providers']['touch']['sha256']
        provider_source = manifest['executables']['touch']['source']
        assert provider_source['version'] == 'GNU coreutils 9.7 + IANA tzcode 2025b'
        assert provider_source['tzcode_archive_sha256'] == '05f8fedb3525ee70d49c87d3fae78a8a0dbae4fe87aa565c65cda9948ae135ec'
        assert provider_source['coreutils_archive_sha256'] == 'e8bb26ad0293f9b5a1fc43fb42ba970e312c66ce92c1b0b16713d7500db251bf'
        from hashlib import sha256
        assert provider_source['build_script_sha256'] == sha256((HERE.parents[2] / 'tools/host-profile/build-touch.sh').read_bytes()).hexdigest()
        assert new['providers']['touch'] == focused['providers']['touch']
        for utility, provider in manifest['executables'].items():
            assert len(provider['sha256']) == 64, utility
            if utility in new['providers']:
                assert new['providers'][utility]['sha256'] == provider['sha256'], utility
        for name in ('host-coreutils-build-configure.log', 'host-coreutils-build-build.log',
                     'host-pax-build-build.log', 'host-tzcode-build.log'):
            assert gzip.decompress((HERE / (platform + '-' + name + '.gz')).read_bytes())
        assert keys(focused) == sorted((case_id, mode) for case_id in authored
                                       for mode in ('direct', 'string', 'file', 'stdin'))
        for row in focused['cases']:
            assert row['verdict'] == 'PASS' and row['errors'] == [], row['id']
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
        assert len({r['id'] for r in focused['cases']}) == 96
        comparisons[platform] = {}
        for suffix in ('audit', 'stock-provider-audit'):
            name = platform + '-host-filesystem-' + suffix + '.json.gz'
            old, new = read(PREVIOUS / name), read(HERE / name)
            before, after = keys(old, True), keys(new, True)
            added = sorted(set(after) - set(before))
            assert set(before) <= set(after), (platform, suffix, before, after)
            expected_added = sorted((case_id, mode) for case_id in authored
                if ('previous-day-start-after' in case_id or 'next-day-end-before' in case_id)
                for mode in ('direct', 'string', 'file', 'stdin')) if platform == 'native' and suffix == 'audit' else []
            assert added == expected_added, (platform, suffix, added)
            for row in new['cases']:
                if (row['id'], row['mode']) in added:
                    assert row['phase'] == 'assertion' and row['errors'] == ['effect mismatch: target']
                    assert row['actual']['status'] == 0
                    assert row['actual']['stdout'] == row['actual']['stderr'] == {'hex': ''}
                    target = row['expected']['datetime_environment']['target_ns']
                    for field in ('atime_ns', 'mtime_ns'):
                        expected_value = row['expected']['effects']['target'][field]
                        assert row['actual']['effects']['target'][field] == expected_value + (1800*10**9 if expected_value == target else 0)

            comparisons[platform][suffix] = dict(prior_failures_preserved=True,
                                                 prior_failures=before, new_failures=added)

    assert len(digests) == 1, digests
    summary['source_identity_sha256'] = digests.pop()
    assert summary['source_identity_sha256'] == source_identity()['sha256']
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    (HERE / 'stock-failure-comparison.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    print('PASS: selected results, prior assertions, stock failures, cleanup and source identities')


if __name__ == '__main__':
    verify()
