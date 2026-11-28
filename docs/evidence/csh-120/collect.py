"""Retain reports and losslessly compress raw logs after validation completes."""
import gzip
from pathlib import Path
import shutil

here = Path(__file__).resolve().parent
root = here.parents[2]
for folder in ('csh120-validation', 'csh120-linux'):
    for path in (root / 'build' / folder).iterdir():
        if not path.is_file() or path.name == 'linux-image.json':
            continue
        if path.suffix == '.log':
            (here / (path.name + '.gz')).write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        elif path.suffix in ('.json', '.gz'):
            shutil.copyfile(path, here / path.name)
