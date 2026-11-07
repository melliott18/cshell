"""Refresh inventory and any early reports predating the final ledger/test edit."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, 'tests')
from host_utilities import source_identity
label = sys.argv[1]
output = Path('build/csh106-validation')
records = (json.loads((output / f'{label}-refresh-commands.json').read_text())
           if '--resume' in sys.argv else [])

def run(command, name, expected_status=0):
    start = time.monotonic()
    log = output / f'{label}-refresh-{name}.log'
    with log.open('wb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    records.append(dict(argv=command, status=result.returncode, expected_status=expected_status, seconds=time.monotonic()-start, log=log.name))
    (output / f'{label}-refresh-commands.json').write_text(json.dumps(records, indent=2)+'\n')
    if result.returncode != expected_status:
        raise SystemExit(1)

if '--resume' not in sys.argv:
    run(['make', 'test-host-inventory'], 'inventory')
else:
    assert records and records[0]['status'] == 0
digest = source_identity()['sha256']
for name, command in [
    ('host-filesystem-allocation', ['make', 'test-host-filesystem-allocation']),
    ('host-profile-results', [sys.executable, 'tests/host_utilities.py', './cshell',
                             'build/tests/host_utility_helper', '--path',
                             str(Path('build/host-profile/bin').resolve()) + ':' + os.defpath,
                             '--strict-gaps', '--boundaries', '--printf-faults',
                             'build/tests/host_printf_faults', '--record',
                             'build/tests/host-profile-results.json']),
]:
    path = Path('build/tests') / (name + '.json')
    if json.loads(path.read_text())['source_identity']['sha256'] != digest:
        # Keep the report and its earlier source identity as development evidence.
        old = output / f'{label}-pre-final-{name}.json.gz'
        old.write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        run(command, name)
# Some focused reports can finish before the final ledger edit too. Refresh
# only those with a stale source digest; retain their previous reports verbatim.
for path in sorted(Path('build/tests').glob('host-filesystem-*.json')):
    if json.loads(path.read_text())['source_identity']['sha256'] == digest:
        continue
    (output / f'{label}-pre-final-{path.name}.gz').write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    suffix = path.stem.removeprefix('host-filesystem-')
    if suffix == 'stock-provider-audit':
        command = [sys.executable, 'tests/host_filesystem.py', './cshell', '--extended-only',
                   '--provider-audit', '--record', str(path)]
        status = 1
    else:
        command = ['make', 'test-host-profile' if suffix == 'profile' else 'test-host-filesystem-' + suffix]
        status = 2 if suffix == 'audit' else 0
    run(command, suffix, status)
for path in Path('build/tests').glob('*.json'):
    if path.name.startswith(('host-filesystem-', 'host-profile-')):
        data = json.loads(path.read_text())
        assert data['source_identity']['sha256'] == digest, path
        (output / (label + '-' + path.name + '.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
print('PASS: final inventory and source identities')
