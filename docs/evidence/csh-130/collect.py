"""Retain reports and losslessly compress raw logs after validation completes."""
import gzip
from pathlib import Path
import shutil
import sys
import json

here = Path(__file__).resolve().parent
root = here.parents[2]
if sys.argv[1:] == ['--initial-linux']:
    source = root / 'build/csh130-linux'
    commands = json.loads((source / 'linux-commands.json').read_text())
    assert [r['status'] for r in commands] == [2, 2, 1]
    initial = here / 'linux-initial'
    initial.mkdir(exist_ok=True)
    for name in ('linux-command-0.log', 'linux-command-0.json', 'linux-commands.json',
                 'linux-host-languages-profile-results.json.gz'):
        path = source / name
        if path.suffix == '.log':
            (initial / (name + '.gz')).write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        else:
            shutil.copyfile(path, initial / name)
    raise SystemExit(0)

for folder in ('csh130-validation', 'csh130-linux'):
    for path in (root / 'build' / folder).iterdir():
        if not path.is_file():
            continue
        if path.suffix == '.log':
            (here / (path.name + '.gz')).write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        elif path.suffix in ('.json', '.gz'):
            shutil.copyfile(path, here / path.name)
