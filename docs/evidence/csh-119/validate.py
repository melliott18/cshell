"""Run selected contracts and retain stock failures as separate evidence."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import time

label = sys.argv[1]
output = Path('build/csh119-validation')
output.mkdir(exist_ok=True)
targets = [
    'test-host-inventory', 'test-host-profile', 'test-host-filesystem-allocation',
    'test-host-filesystem-provider-audit', 'test-host-filesystem-residual',
    'test-host-filesystem-isolated', 'test-host-filesystem-interactive',
    'test-host-filesystem-decisions', 'test-host-filesystem-metadata',
    'test-host-filesystem-recursive', 'test-host-filesystem-path-limits',
    'test-host-filesystem-cwd', 'test-host-filesystem-creation',
    'test-host-filesystem-output', 'test-host-filesystem-cwd-logical',
    'test-host-filesystem-magic', 'test-host-filesystem-calendar', 'test-host-filesystem-reference', 'test-host-filesystem-datetime', 'test-host-filesystem-timezone', 'test-host-filesystem-day-rules', 'test-host-filesystem-transition-times', 'test-host-filesystem-magic-strings', 'test-host-filesystem-magic-messages', 'test-host-filesystem-magic-types', 'test-host-filesystem-magic-defaults', 'test-host-filesystem-link-bytes', 'test-host-filesystem-omitted-who', 'test-host-filesystem-parent-graphs', 'test-host-filesystem-removal', 'test-host-filesystem-link-graphs', 'test-host-filesystem-link-permissions', 'test-host-filesystem-touch-permissions', 'test-host-filesystem-touch-current', 'test-host-filesystem-touch-objects', 'test-host-filesystem-ls-blocks', 'test-host-filesystem-ls-totals', 'test-host-filesystem-ls-identity', 'test-host-filesystem-ls-sockets', 'test-host-filesystem-ls-visibility',
]
commands = [
    ['make', *targets],
    ['make', 'test-host-filesystem-audit'],
    [sys.executable, 'tests/host_filesystem.py', './cshell', '--extended-only',
     '--provider-audit', '--record', 'build/tests/host-filesystem-stock-provider-audit.json'],
]
def execute(item):
    number, command = item
    start = time.monotonic()
    log = output / f'{label}-command-{number}.log'
    print('Starting', label, number, flush=True)
    with log.open('wb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    record = dict(argv=command, status=result.returncode,
                  seconds=time.monotonic() - start, log=log.name)
    (output / f'{label}-command-{number}.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Finished', label, number, result.returncode, flush=True)
    return record


# Existing harness startup deadlines require sequential validation.
records = [execute(item) for item in enumerate(commands)]
(output / f'{label}-commands.json').write_text(json.dumps(records, indent=2) + '\n')

for path in Path('build/tests').glob('*.json'):
    if path.name.startswith(('host-filesystem-', 'host-profile-')):
        (output / (label + '-' + path.name + '.gz')).write_bytes(
            gzip.compress(path.read_bytes(), mtime=0))
for name in ('build/host-test-provider.h', 'build/host-newgrp-provider.h', 'build/host-profile/manifest.json', 'build/host-coreutils-build/configure.log',
             'build/host-coreutils-build/build.log', 'build/host-coreutils-build/creation.log', 'build/host-coreutils-build/ln.log', 'build/host-coreutils-build/ls.log', 'build/host-pax-build/build.log', 'build/host-tzcode/build.log', 'build/host-file-build/configure.log', 'build/host-file-build/build.log'):
    path = Path(name)
    prefix = '' if path.parent.name == 'build' else path.parent.name + '-'
    (output / (label + '-' + prefix + path.name + '.gz')).write_bytes(
        gzip.compress(path.read_bytes(), mtime=0))

raise SystemExit(0 if [record['status'] for record in records] == [0, 2, 1] else 1)
