"""Package local validation directories without rewriting behavioral reports."""
import gzip
import json
from pathlib import Path
import shutil
import sys

here = Path(__file__).resolve().parent
for argument in sys.argv[1:]:
    source = Path(argument)
    for path in source.iterdir():
        if not path.is_file():
            continue
        destination = here / ('development' if '-pre-final-' in path.name else '') / path.name
        destination.parent.mkdir(exist_ok=True)
        if path.suffix == '.log' and not path.name.endswith(('-supplement-1.log', '-supplement-2.log')):
            destination.with_suffix('.log.gz').write_bytes(gzip.compress(path.read_bytes(), mtime=0))
        elif path.name.endswith('-commands.json'):
            records = json.loads(path.read_text())
            for row in records:
                log = row.get('log', '')
                if log.endswith('.log') and not log.endswith(('-supplement-1.log', '-supplement-2.log')):
                    row['log'] = log + '.gz'
            destination.write_text(json.dumps(records,indent=2)+'\n')
        else:
            shutil.copyfile(path,destination)
