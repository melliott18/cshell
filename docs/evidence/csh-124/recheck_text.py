"""Record a separate unchanged text-profile run; never replace the initial run."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

output = Path('build/csh124-validation')
report = output / 'native-text-recheck.json'
command = [sys.executable, 'tests/host_text.py', './cshell', '--path',
           str(Path('build/host-profile/bin').resolve()) + ':' + os.defpath,
           '--boundaries', '--record', str(report)]
start = time.monotonic()
with (output / 'native-text-recheck.log').open('wb') as stream:
    result = subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT)
(output / 'native-text-recheck-command.json').write_text(json.dumps(
    dict(argv=command, status=result.returncode, seconds=time.monotonic() - start), indent=2) + '\n')
report.with_suffix('.json.gz').write_bytes(gzip.compress(report.read_bytes(), mtime=0))
report.unlink()
raise SystemExit(result.returncode)
