"""Independently recompute saved assertion verdicts at the reviewed checkout."""
import gzip
import json
from pathlib import Path
import sys
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / 'tests'))
from host_utilities import matches_case


def decode(value):
    if isinstance(value, dict):
        if set(value) == {'hex'}:
            return bytes.fromhex(value['hex'])
        return {key: decode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode(item) for item in value]
    return value


count = 0
records = {}
for path in sorted((root / 'docs/evidence/csh-064').glob('*.json.gz')):
    record = decode(json.loads(gzip.decompress(path.read_bytes())))
    for row in record['cases']:
        if row.get('phase') == 'setup':
            continue
        actual, case = row['actual'], row['case']
        passed = (not actual['errors'] and matches_case(case, actual['status'], actual)
                  and actual['files'] == case.get('files', {}))
        assert (row['verdict'] == 'PASS') == passed, (path.name, row['name'])
        count += 1
    records[path.name] = record['totals']
print(json.dumps(dict(assertions_recomputed=count, records=records), indent=2))
