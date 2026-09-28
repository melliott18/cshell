#!/usr/bin/env python3
"""Check the retention diagnostic's process isolation with cheap pipe cases.

Uses production smoke capture. The helper rendezvous requires both worker
processes to participate; no scheduling delay is used as proof of concurrency.
"""

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SMOKE_WRAPPER = '''\
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import threading

spec = importlib.util.spec_from_file_location('production_smoke', {smoke_path!r})
actual = importlib.util.module_from_spec(spec)
spec.loader.exec_module(actual)
load_suite = actual.load_suite

def run_case(binary, case, timeout, output_limit):
    audit = {{'pid': os.getpid(), 'threads': threading.active_count(),
             'method': multiprocessing.get_start_method(),
             'timeout': timeout, 'output_limit': output_limit}}
    Path(case['env']['CSH_RETENTION_TRACE'] + '.worker.json').write_text(
        json.dumps(audit))
    assert audit['threads'] == 1, audit
    assert audit['method'] == 'spawn', audit
    return actual.run_case(binary, case, timeout, output_limit)
'''

HELPER = '''\
import os
from pathlib import Path
import time

trace = Path(os.environ['CSH_RETENTION_TRACE'])
index = int(trace.stem)
peer = trace.with_name(str(1 - index) + '.ready')
trace.with_suffix('.ready').write_text('ready\\n')
deadline = time.monotonic() + 10
while not peer.exists():
    if time.monotonic() >= deadline:
        raise RuntimeError('second diagnostic worker did not reach rendezvous')
    time.sleep(0.01)
trace.write_text('helper ready\\n')
print('helper passed')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument('--output', type=Path,
                        help='new directory for the fixture, results and report')
    args = parser.parse_args()
    repo = args.root.resolve()
    if args.output is None:
        output = Path(tempfile.mkdtemp(prefix='csh057-spawn-check-'))
    else:
        output = args.output.resolve()
        output.mkdir(parents=True, exist_ok=False)

    fixture_root = output / 'fixture'
    (fixture_root / 'tests/fixtures').mkdir(parents=True)
    (fixture_root / 'build/tests').mkdir(parents=True)
    shutil.copyfile(repo / 'tests/pty_harness.py', fixture_root / 'tests/pty_harness.py')
    (fixture_root / 'tests/smoke.py').write_text(
        SMOKE_WRAPPER.format(smoke_path=str(repo / 'tests/smoke.py')))
    # Run a cheap Python helper through the production pipe harness without
    # compiling or launching the actual 619-child retention fixture.
    (fixture_root / 'build/tests/jobs_lifecycle').symlink_to(Path(sys.executable).resolve())
    helper = fixture_root / 'helper.py'
    helper.write_text(HELPER)
    suite = {
        'version': 1, 'name': 'concurrent-runner-probe', 'kind': 'module',
        'cases': [{'name': 'cheap helper', 'stdin': '', 'args': [str(helper)],
                   'timeout': 60,
                   'expect': {'stdout': 'helper passed\n', 'stderr': '', 'status': 0}}],
    }
    case_path = fixture_root / 'tests/fixtures/job-retention.json'
    report = {'root': str(repo), 'output': str(output), 'runs': []}
    for label in ('pass', 'failure'):
        if label == 'failure':
            suite['cases'][0]['expect']['stdout'] = 'deliberate mismatch\n'
        case_path.write_text(json.dumps(suite))
        results = output / label
        command = [sys.executable,
                   str(repo / 'docs/evidence/csh-057-timeouts/diagnose_retention.py'),
                   str(fixture_root), str(results), '--workers', '2']
        completed = subprocess.run(command, check=True, text=True,
                                   capture_output=True, timeout=30)
        rows = [json.loads((results / f'{i}.json').read_text()) for i in range(2)]
        workers = [json.loads((results / f'{i}.progress.worker.json').read_text())
                   for i in range(2)]
        report['runs'].append({'label': label, 'command': command,
                               'returncode': completed.returncode,
                               'stdout': completed.stdout, 'stderr': completed.stderr,
                               'rows': rows, 'workers': workers})
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        assert len({worker['pid'] for worker in workers}) == 2, workers
        assert all(worker['threads'] == 1 and worker['method'] == 'spawn'
                   and worker['timeout'] == 60 and worker['output_limit'] == 65536
                   for worker in workers), workers
        assert [row['index'] for row in rows] == [0, 1], rows
        for row in rows:
            if label == 'pass':
                assert row['failures'] == [], row
            else:
                assert len(row['failures']) == 1, row
                assert row['failures'][0].startswith(
                    "stdout: expected b'deliberate mismatch\\n'"), row
        assert all((results / f'{i}.progress').read_text() == 'helper ready\n'
                   for i in range(2))
        printed_rows = [json.loads(line) for line in completed.stdout.splitlines()]
        assert sorted(printed_rows, key=lambda row: row['index']) == rows
        assert completed.stderr == '', completed.stderr

    report['result'] = 'passed'
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'result': 'passed', 'report': str(output / 'report.json'),
                      'successful_cases': 2, 'intentional_failure_cases': 2}))


if __name__ == '__main__':
    main()
