#!/usr/bin/env python3
"""Record one bounded attempt, preserving failure and exact input identities."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tests'))
from execute import bounded_run

parser = argparse.ArgumentParser()
parser.add_argument('--name', required=True)
parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
parser.add_argument('--fixture', action='store_true')
parser.add_argument('command', nargs=argparse.REMAINDER)
args = parser.parse_args()
if args.command[0] == '--':
    args.command.pop(0)


def hashes(paths):
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths) if p.is_file() and '__pycache__' not in str(p)}


inputs = [Path('Makefile'), Path('Dockerfile')]
for directory in ('src', 'include', 'tests'):
    inputs.extend(Path(directory).rglob('*'))
record = {
    'base': 'f07568223c02f488924e8599bf9b9f1013b03164',
    'platform': platform.platform(), 'python': sys.version,
    'compiler': subprocess.check_output(['cc', '--version'], text=True),
    'inputs': hashes([ROOT / p for p in inputs]),
    'command': args.command, 'timeout_seconds': 20 if args.fixture else 600,
    'environment': {key: os.environ[key] for key in
                    ('ASAN_OPTIONS', 'UBSAN_OPTIONS') if key in os.environ},
    'evidence_inputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in Path(__file__).resolve().parent.iterdir()
                        if p.suffix in ('.c', '.mk', '.py', '.patch')},
}
command = args.command
if args.fixture:
    command = [str(ROOT / p) for p in command]
with tempfile.TemporaryDirectory(prefix='csh069-') as temporary:
    try:
        result = bounded_run(command, cwd=temporary if args.fixture else ROOT,
                             env=dict(os.environ), timeout=record['timeout_seconds'])
        record.update(returncode=result.returncode)
        output = result.stdout + result.stderr
    except AssertionError as error:
        record.update(returncode=None, harness_error=str(error))
        output = str(error).encode()
record['binaries'] = hashes([ROOT / 'cshell', *(ROOT / 'build/tests').glob('context*'),
                             ROOT / 'build/tests/execute_helper'])
log = args.output / (args.name + '.log.gz')
log.write_bytes(gzip.compress(output, mtime=0))
record['log_sha256'] = hashlib.sha256(log.read_bytes()).hexdigest()
(args.output / (args.name + '.json')).write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps({'attempt': args.name, 'returncode': record['returncode'],
                  'output_tail': output.decode(errors='replace')[-2000:]}))
sys.exit(0 if record['returncode'] == 0 else 1)
