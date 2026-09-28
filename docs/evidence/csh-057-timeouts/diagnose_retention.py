"""Run instrumented retention fixtures with unchanged 60-second deadlines."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import json
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument('root', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--workers', type=int, default=2)
args = parser.parse_args()
args.root = args.root.resolve()
args.output = args.output.resolve()
args.output.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(args.root / 'tests'))
import smoke

def run(index):
    case = smoke.load_suite(args.root / 'tests/fixtures/job-retention.json')['cases'][0]
    case['env'] = {'CSH_RETENTION_TRACE': str(args.output / f'{index}.progress')}
    started = time.monotonic()
    failures = smoke.run_case(args.root / 'build/tests/jobs_lifecycle', case, 60, 65536)
    result = {'index': index, 'elapsed': time.monotonic() - started, 'failures': failures}
    (args.output / f'{index}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)

with ThreadPoolExecutor(max_workers=args.workers) as pool:
    list(pool.map(run, range(args.workers)))
