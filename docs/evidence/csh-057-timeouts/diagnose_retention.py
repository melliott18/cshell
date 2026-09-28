"""Run instrumented retention fixtures with unchanged 60-second deadlines."""
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat
from pathlib import Path
import argparse
import json
import multiprocessing
import sys
import time


def run(index, root, output):
    # smoke.capture uses preexec_fn, which must run from a single-threaded
    # process. Each spawned worker imports the runner independently.
    sys.path.insert(0, str(root / 'tests'))
    import smoke
    case = smoke.load_suite(root / 'tests/fixtures/job-retention.json')['cases'][0]
    case['env'] = {'CSH_RETENTION_TRACE': str(output / f'{index}.progress')}
    started = time.monotonic()
    failures = smoke.run_case(root / 'build/tests/jobs_lifecycle', case, 60, 65536)
    result = {'index': index, 'elapsed': time.monotonic() - started, 'failures': failures}
    (output / f'{index}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=2)
    args = parser.parse_args()
    args.root = args.root.resolve()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    # Explicit spawn also avoids inheriting any parent threads on platforms
    # where the multiprocessing default still uses fork.
    with ProcessPoolExecutor(max_workers=args.workers,
                             mp_context=multiprocessing.get_context('spawn')) as pool:
        list(pool.map(run, range(args.workers), repeat(args.root), repeat(args.output)))


if __name__ == '__main__':
    main()
