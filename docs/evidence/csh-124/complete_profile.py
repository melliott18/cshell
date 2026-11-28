"""Run the two host-profile recipes skipped after the recorded text failure."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

output = Path('build/csh124-validation')
commands = [
    [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_host_languages.py'],
    [sys.executable, 'tests/host_languages.py', './cshell', '--path',
     str(Path('build/host-profile/bin').resolve()) + ':' + os.defpath,
     '--ed-faults', 'build/tests/host_ed_faults', '--record',
     str(output / 'native-host-languages-profile-results.json')],
]
records = []
for index, command in enumerate(commands):
    start = time.monotonic()
    log = output / f'native-profile-continuation-{index}.log'
    with log.open('wb') as stream:
        result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
    records.append(dict(argv=command, status=result.returncode,
                        seconds=time.monotonic() - start, log=log.name))
(output / 'native-profile-continuation.json').write_text(json.dumps(records, indent=2) + '\n')
report = output / 'native-host-languages-profile-results.json'
report.with_suffix('.json.gz').write_bytes(gzip.compress(report.read_bytes(), mtime=0))
report.unlink()
raise SystemExit(any(r['status'] for r in records))
