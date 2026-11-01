"""Run selected contracts and retain stock failures as separate evidence."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import time

label = sys.argv[1]
output = Path('build/csh108-validation')
output.mkdir(exist_ok=True)
targets = [
    'test-host-inventory', 'test-host-profile', 'test-host-filesystem-allocation',
    'test-host-filesystem-provider-audit', 'test-host-filesystem-residual',
    'test-host-filesystem-isolated', 'test-host-filesystem-interactive',
    'test-host-filesystem-decisions', 'test-host-filesystem-metadata',
    'test-host-filesystem-recursive', 'test-host-filesystem-path-limits',
    'test-host-filesystem-cwd', 'test-host-filesystem-creation',
    'test-host-filesystem-output', 'test-host-filesystem-cwd-logical',
    'test-host-filesystem-magic', 'test-host-filesystem-calendar', 'test-host-filesystem-reference', 'test-host-filesystem-datetime', 'test-host-filesystem-timezone', 'test-host-filesystem-day-rules', 'test-host-filesystem-transition-times', 'test-host-filesystem-magic-strings', 'test-host-filesystem-magic-messages', 'test-host-filesystem-magic-types', 'test-host-filesystem-magic-defaults', 'test-host-filesystem-link-bytes', 'test-host-filesystem-omitted-who', 'test-host-filesystem-parent-graphs',
]
commands = [
    ['make', *targets],
    ['make', 'test-host-filesystem-audit'],
    [sys.executable, 'tests/host_filesystem.py', './cshell', '--extended-only',
     '--provider-audit', '--record', 'build/tests/host-filesystem-stock-provider-audit.json'],
]
records = []
for number, command in enumerate(commands):
    start = time.monotonic()
    log = output / f'{label}-command-{number}.log'
    print('Starting', label, number, flush=True)
    with log.open('wb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    records.append(dict(argv=command, status=result.returncode,
                        seconds=time.monotonic() - start, log=log.name))
    (output / f'{label}-commands.json').write_text(json.dumps(records, indent=2) + '\n')
    print('Finished', label, number, result.returncode, flush=True)

for path in Path('build/tests').glob('*.json'):
    if path.name.startswith(('host-filesystem-', 'host-profile-')):
        (output / (label + '-' + path.name + '.gz')).write_bytes(
            gzip.compress(path.read_bytes(), mtime=0))
for name in ('build/host-profile/manifest.json', 'build/host-coreutils-build/configure.log',
             'build/host-coreutils-build/build.log', 'build/host-coreutils-build/creation.log', 'build/host-pax-build/build.log', 'build/host-tzcode/build.log', 'build/host-file-build/configure.log', 'build/host-file-build/build.log'):
    path = Path(name)
    (output / (label + '-' + path.parent.name + '-' + path.name + '.gz')).write_bytes(
        gzip.compress(path.read_bytes(), mtime=0))

raise SystemExit(0 if [record['status'] for record in records] == [0, 2, 1] else 1)
