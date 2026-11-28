"""Rerun the failed text recipe and the two language recipes it prevented.

Preserve the original Darwin observer failure. No test expectation, provider,
limit or source is changed; successful prerequisites are not repeated.
"""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

output = Path('build/csh134-validation')
initial = Path('build/tests/host-text-results.json')
(output / 'native-text-observer-failure.json.gz').write_bytes(
    gzip.compress(initial.read_bytes(), mtime=0))
search_path = str(Path('build/host-profile/bin').resolve()) + ':' + os.confstr('CS_PATH')
commands = [
    [sys.executable, 'tests/host_text.py', './cshell', '--path', search_path,
     '--boundaries', '--record', 'build/tests/host-text-results.json'],
    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_host_languages.py'],
    [sys.executable, 'tests/host_languages.py', './cshell', '--path', search_path,
     '--ed-faults', 'build/tests/host_ed_faults', '--record', 'build/tests/host-languages-profile-results.json'],
]
records = []
for number, argv in enumerate(commands):
    start = time.monotonic()
    log = output / f'native-recovery-{number}.log'
    with log.open('wb') as stream:
        result = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
    record = dict(argv=argv, status=result.returncode, seconds=time.monotonic()-start, log=log.name)
    records.append(record)
    print(number, result.returncode, flush=True)
    (output / 'native-recovery-commands.json').write_text(json.dumps(records, indent=2)+'\n')
    if result.returncode:
        raise SystemExit(result.returncode)
for name in ('host-text-results.json', 'host-languages-profile-results.json'):
    path = Path('build/tests') / name
    json.loads(path.read_text())
    (output / ('native-' + name + '.gz')).write_bytes(gzip.compress(path.read_bytes(), mtime=0))
