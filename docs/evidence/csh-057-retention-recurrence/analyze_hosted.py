#!/usr/bin/env python3
"""Read the retained hosted logs and source identities; emit analysis as JSON.

No probes, builds, checkout changes or GitHub writes are performed. Source
comparison uses local Git for the prior revision and GitHub's read-only compare
API for the synthetic PR merge, which may not exist in the local object store.

Reproduce from this checkout:
    python3 docs/evidence/csh-057-retention-recurrence/analyze_hosted.py
"""

import argparse
import ast
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess


PRIOR_SOURCE = 'faf2e9525dfe2c2c2cba4598a1d63d49552fc1d7'
UNMODIFIED_PATHS = (
    'src/jobs.c', 'tests/jobs_lifecycle.c', 'tests/fixtures/job-retention.json',
    'tests/smoke.py', 'tests/pty_harness.py',
)
ANSI = re.compile(r'\x1b\[[0-9;]*m')
TIMESTAMP = re.compile(r'^(\d{4}-\d\d-\d\dT\S+Z) (.*)$')
CHECKPOINT = re.compile(r'retention capacity=(\d+) round=(\d+) completed=(\d+)')


def command(arguments, repository):
    return subprocess.check_output(arguments, cwd=repository, text=True)


def git(arguments, repository):
    return command(['git', *arguments], repository).strip()


def log_rows(path):
    rows = []
    for number, line in enumerate(gzip.open(path, 'rt'), 1):
        match = TIMESTAMP.match(ANSI.sub('', line.rstrip('\n')))
        if match:
            rows.append({'line': number, 'timestamp': match[1], 'text': match[2]})
    return rows


def interval(start, end):
    return round((datetime.fromisoformat(end.replace('Z', '+00:00')) -
                  datetime.fromisoformat(start.replace('Z', '+00:00'))).total_seconds(), 6)


def evidence(row):
    return {key: row[key] for key in ('line', 'timestamp', 'text')}


def parse_log(path, run_id, job_id):
    rows = log_rows(path)
    source_index = next(i for i, row in enumerate(rows)
                        if 'git log -1 --format=%H' in row['text'])
    source = rows[source_index + 1]['text']
    assert re.fullmatch(r'[0-9a-f]{40}', source), source
    os_index = next(i for i, row in enumerate(rows)
                    if row['text'] == '##[group]Operating System')
    image_index = next(i for i, row in enumerate(rows)
                       if row['text'].startswith('Image: '))
    asan_index = next(i for i, row in enumerate(rows)
                      if row['text'].startswith('make -j2 test test-pty test-host-profile '))
    options = {}
    for row in rows[asan_index:asan_index + 20]:
        match = re.match(r'\s+(CC|ASAN_OPTIONS|MallocNanoZone|UBSAN_OPTIONS): (.*)', row['text'])
        if match:
            options[match[1]] = match[2]

    cases = []
    for index, row in enumerate(rows):
        if not row['text'].startswith('Suite: job-retention [module]'):
            continue
        end = next(i for i in range(index + 1, len(rows))
                   if re.match(r'(PASS|FAIL): CSH-057 bounded CHILD_MAX retention and eviction',
                               rows[i]['text']))
        outcome = rows[end]['text'].split(':', 1)[0]
        case = {'build': 'ASan/UBSan' if index > asan_index else 'normal',
                'outcome': outcome,
                'suite_start': evidence(row), 'case_result': evidence(rows[end]),
                'github_log_timestamp_interval_seconds': interval(row['timestamp'], rows[end]['timestamp'])}
        if outcome == 'FAIL':
            tail = rows[end + 1:end + 10]
            timeout = next(item for item in tail if 'timeout after ' in item['text'])
            match = re.search(r'timeout after ([\d.]+)s \(last output at ([\d.]+)s; '
                              r'no output for ([\d.]+)s; (\d+) bytes captured; process group killed\)',
                              timeout['text'])
            assert match, timeout
            status = next(item for item in tail if 'status: expected ' in item['text'])
            status_match = re.search(r'status: expected (-?\d+), got (-?\d+)', status['text'])
            output = next(item for item in tail if 'stdout: expected ' in item['text'])
            output_match = re.search(r'stdout: expected (b.*) \((\d+) bytes\), got '
                                     r'(b.*) \((\d+) captured bytes\)$', output['text'])
            assert output_match, output
            expected = ast.literal_eval(output_match[1])
            captured = ast.literal_eval(output_match[3])
            assert isinstance(expected, bytes) and isinstance(captured, bytes)
            assert len(expected) == int(output_match[2])
            assert len(captured) == int(output_match[4]) == int(match[4])
            checkpoints = [tuple(map(int, item)) for item in CHECKPOINT.findall(captured.decode())]
            completed = {}
            for capacity, round_number, count in checkpoints:
                completed[(capacity, round_number)] = max(completed.get((capacity, round_number), 0), count)
            assert expected.startswith(captured)
            case['failure'] = {
                'timeout_diagnostic': evidence(timeout), 'status_diagnostic': evidence(status),
                'stdout_diagnostic': evidence(output),
                'runner_deadline_seconds': float(match[1]),
                'runner_last_output_seconds_since_capture_start': float(match[2]),
                'runner_seconds_without_output': float(match[3]),
                'expected_status': int(status_match[1]), 'actual_status': int(status_match[2]),
                'expected_stdout_bytes': len(expected), 'captured_stdout_bytes': len(captured),
                'expected_stdout': expected.decode(), 'captured_stdout': captured.decode(),
                'captured_is_exact_expected_prefix': True,
                'last_checkpoint': {'capacity': checkpoints[-1][0], 'round': checkpoints[-1][1],
                                    'completed': checkpoints[-1][2]},
                'completed_fill_children_lower_bound': sum(completed.values()),
                'completed_by_capacity_round': [
                    {'capacity': capacity, 'round': round_number, 'completed': count}
                    for (capacity, round_number), count in completed.items()],
                'not_reached_in_captured_output': ['retention live records', 'retention formatting',
                                                   'retention complete'],
            }
        cases.append(case)
    assert len(cases) == 2, cases
    return {
        'artifact': path.name, 'artifact_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'run': run_id, 'job': job_id,
        'url': f'https://github.com/melliott18/cshell/actions/runs/{run_id}/job/{job_id}',
        'checkout_commit': source, 'checkout_evidence': evidence(rows[source_index + 1]),
        'environment': {'os': rows[os_index + 1]['text'], 'version': rows[os_index + 2]['text'],
                        'build': rows[os_index + 3]['text'],
                        'runner_image': rows[image_index]['text'].split(': ', 1)[1],
                        'runner_image_version': rows[image_index + 1]['text'].split(': ', 1)[1]},
        'sanitizer_invocation': evidence(rows[asan_index]),
        'sanitizer_options': options, 'make_parallel_job_limit': 2, 'retention_cases': cases,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--repository', type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    directory, repository = args.directory.resolve(), args.repository.resolve()
    identity = json.loads((directory / 'identity.json').read_text())
    failure = parse_log(directory / 'hosted-failure.log.gz', identity['failure_run'], identity['failure_job'])
    peer = parse_log(directory / 'hosted-peer.log.gz', identity['peer_run'], identity['peer_job'])
    failed_source, peer_source = failure['checkout_commit'], peer['checkout_commit']
    assert failed_source == identity['failed_source']
    endpoint = f'repos/melliott18/cshell/compare/{failed_source}...{peer_source}'
    comparison = json.loads(command(['gh', 'api', endpoint], repository))
    peer_commit = next(commit for commit in comparison['commits'] if commit['sha'] == peer_source)
    comparison_record = {
        'api_endpoint': endpoint, 'base_commit': comparison['base_commit']['sha'],
        'base_tree': comparison['base_commit']['commit']['tree']['sha'],
        'peer_commit': peer_source, 'peer_tree': peer_commit['commit']['tree']['sha'],
        'ahead_by': comparison['ahead_by'], 'behind_by': comparison['behind_by'],
        'changed_files': [item['filename'] for item in comparison['files']],
    }
    comparison_record['identical_tracked_source_trees'] = comparison_record['base_tree'] == comparison_record['peer_tree']
    unchanged = []
    for path in UNMODIFIED_PATHS:
        before = git(['rev-parse', f'{PRIOR_SOURCE}:{path}'], repository)
        after = git(['rev-parse', f'{failed_source}:{path}'], repository)
        assert before == after, path
        unchanged.append({'path': path, 'prior_blob': before, 'failed_blob': after, 'unchanged': True})
    changed_runtime = git(['diff', '--name-only', PRIOR_SOURCE, failed_source, '--', 'src', 'include'], repository).splitlines()
    assertion = failure['retention_cases'][1]['failure']
    assert assertion['completed_fill_children_lower_bound'] == 448
    analysis = {
        'logs': [failure, peer], 'source_comparison_failure_to_peer': comparison_record,
        'source_review': {
            'prior_green_integration_commit': PRIOR_SOURCE, 'failed_commit': failed_source,
            'unchanged_relevant_files': unchanged, 'changed_runtime_paths': changed_runtime,
            'review': 'CSH-066 changes shallow parse/execute/expand cost through native-stack checks, '
                      'getrlimit, thread-local bound caching and iterative execution-plan ownership. '
                      'It does not change jobs.c, the retention fixture, or pipe/PTY capture. '
                      'A source diff alone does not quantify throughput effects or establish causation.'},
        'interpretation': {
            'established': [
                'The failing sanitizer case hit the outer 60-second deadline and the runner reported '
                'killing its group; the resulting leader status was -9.',
                'All captured bytes are the exact required prefix. By its final checkpoint, at least '
                '448 capacity-fill children completed their run/reap assertions: 32 + 32 + 256 + 128.',
                'The runner received its last output at 58.721 seconds and reported 1.282 seconds '
                'without output at timeout. This is evidence of observed progress near the outer bound.',
                'The peer passed on a distinct checkout commit with an identical tracked source tree.'],
            'supported_diagnosis': 'The aggregate outer case deadline expired after substantial '
                                   'completed work. The record does not demonstrate a five-second '
                                   'operation stall or establish why the hosted work took this long.',
            'limits': [
                'GitHub suite-start/result timestamp differences include logging and runner overhead; '
                'they are not internal per-operation timings.',
                'Last-output time measures receipt by the runner, not the exact child completion time. '
                'Checkpoints occur every 64 fills and do not record each intervening duration.',
                'The record cannot rule out earlier or late stalls, scheduling delays or progress after the '
                'last checkpoint, and it does not contain timeout-time stacks or inherited alarm state.',
                'make -j2 establishes a permitted concurrent test configuration, not actual machine '
                'load or a measured cause of slowing.',
                'The new recurrence does not retrospectively prove the cause of the earlier failure '
                'with empty fully buffered stdout. The peer pass does not erase either failure.'],
        },
    }
    print(json.dumps(analysis, indent=2))


if __name__ == '__main__':
    main()
