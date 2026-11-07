#!/usr/bin/env python3
"""Check retained qualification and cleanup assertions without rerunning stress."""
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
index = json.loads((ROOT / 'inventory.json').read_text())
archive = ROOT / 'runs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == index['archive_sha256']
with tarfile.open(archive, 'r:gz') as bundle:
    def read(name):
        data = bundle.extractfile('runs/' + name).read()
        assert hashlib.sha256(data).hexdigest() == index['files'][name]
        return data

    for name in index['files']:
        read(name)
    summary = json.loads((ROOT / 'validation.json').read_text())
    for name, total in [('native-verified', 693), ('native-sanitizer-verified', 602),
                        ('linux-verified-normal', 698), ('linux-verified-sanitizer', 698)]:
        result = json.loads(read(name + '.json'))
        assert result['totals'] == {'PASS': total, 'FAIL': 0}
        assert result['source_identity']['sha256'] == summary['final_build_test_input_sha256']
        assert result['source_identity'] == result['final_source_identity']
        assert result['temporary_directory_removed']
        assert all(case['verdict'] == 'PASS' for case in result['cases'])
        if name != 'native-sanitizer-verified':
            added = [case for case in result['cases'] if case['name'].startswith('CSH-079 ')]
            assert len(added) == 99
            for case in added:
                if 'reaped' in case['invocation']:
                    owned = case['invocation']
                    assert owned['reaped'] and owned['pid_disappeared'] and not owned['errors']
            for case in result['cases']:
                if case['name'].startswith('echo threshold'):
                    assert all(t['reaped'] and t['pid_disappeared'] for t in case['trials'])
    for name in ('native-profile-verified', 'linux-verified-profile', 'linux-verified-sanitizer-profile'):
        result = json.loads(read(name + '.json'))
        assert result['totals'] == {'passed': 1162, 'failed': 0, 'gaps': 0}
    assert json.loads(read('native-attempt-1.json'))['totals'] == {'PASS': 683, 'FAIL': 5}
    diagnostic_name = next(name for name in index['files']
                           if name.startswith('hosted-attempt-1/') and name.endswith('host-formatted-disposable.json'))
    diagnostic = json.loads(read(diagnostic_name))
    assert diagnostic['status'] == 'FAIL' and len(diagnostic['cases']) == 5
    assert all(case['verdict'] == 'PASS' for case in diagnostic['cases'][:4])
    failure = diagnostic['cases'][-1]
    assert failure['verdict'] == 'FAIL' and failure['stack_soft'] == 1048576
    assert failure['trials'][-1]['status'] == -11
    assert all(t['reaped'] and t['pid_disappeared'] for case in diagnostic['cases'] for t in case['trials'])
    assert not read('remaining-container-ids.txt').strip()
    for name in ('linux-verified-container-before-removal.json', 'linux-qualified-integration-state.json'):
        state = json.loads(read(name))[0]['State']
        assert not state['Running'] and state['Pid'] == 0 and state['ExitCode'] == 0
    for name in ('native-integration.log', 'linux-verified-normal.log', 'linux-qualified-integration.log'):
        log = read(name).decode()
        for count in (3950, 30, 33):
            assert f'Result: {count} passed, 0 failed, 0 skipped' in log
print('PASS: strict profiles, retained failed diagnostic, and owned-process/container cleanup')
