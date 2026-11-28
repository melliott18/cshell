"""Manually rerun the complete required command after retained CSH-129 failure.

Run only after validate.py finishes and its reports are saved under linux-initial.
This does not alter fixture expectations or add a harness retry policy.
"""
import gzip
import json
from pathlib import Path
import subprocess
import time

output = Path('build/csh130-validation')
records_path = output / 'linux-commands.json'
records = json.loads(records_path.read_text())
assert [r['status'] for r in records] == [2, 2, 1], records
start = time.monotonic()
with (output / 'linux-command-0.log').open('wb') as stream:
    result = subprocess.run(records[0]['argv'], stdout=stream, stderr=subprocess.STDOUT)
records[0].update(status=result.returncode, seconds=time.monotonic() - start)
(output / 'linux-command-0.json').write_text(json.dumps(records[0], indent=2) + '\n')
records_path.write_text(json.dumps(records, indent=2) + '\n')
for path in Path('build/tests').glob('*.json'):
    if path.name.startswith(('host-filesystem-', 'host-profile-', 'host-languages-')):
        (output / ('linux-' + path.name + '.gz')).write_bytes(gzip.compress(path.read_bytes(), mtime=0))
print('Complete required-command rerun:', result.returncode, flush=True)
raise SystemExit(result.returncode)
