#!/usr/bin/env python3
"""Strict test-only provider call-site faults; separate from kernel evidence."""
import argparse
import json
import os
from pathlib import Path
import platform
import tempfile

from host_filesystem import run_case
from host_filesystem_cases import case
from host_utilities import sha, source_identity


def scenarios():
    yield 'readlink', 'short', ['link'], b'data\n', {}
    yield 'readlink', 'growth', ['longlink'], b'x' * 600 + b'\n', {}
    yield 'realpath', 'existing', ['-e', 'data'], 'resolved-data', {}
    yield 'realpath', 'missing', ['-E', 'absent'], 'resolved-absent', {}
    yield 'realpath', 'relative-link', ['-E', 'dirlink/../absent'], 'resolved-tree/absent', {}
    # Absolute symlink branch is tested using an independently authored /-rooted
    # path back into the fixture, supplied dynamically by setup.
    yield 'realpath', 'absolute-link', ['-E', 'absolute-link'], 'resolved-absent', {'absolute_link': True}


def run(binary, provider, fixture_root, sanitizer=False):
    records = []
    with tempfile.TemporaryDirectory(prefix='csh-path-fault-bin-', dir=fixture_root) as temp:
        directory = Path(temp)
        for utility in ('readlink', 'realpath'):
            (directory / utility).symlink_to(provider)
        providers = {utility: {'path': str(directory / utility)} for utility in ('readlink', 'realpath')}
        search = str(directory) + os.pathsep + os.defpath
        for utility, name, args, output, extra in scenarios():
            for mode in ('direct', 'string', 'file', 'stdin'):
                baseline = case(utility, 'allocation-' + name + '-control', args, out=output,
                                env={'CSH_PATH_FAIL_AT': '0'}, **extra)
                # Read the baseline call count from the same checked marker path;
                # the expected count is checked separately before generating faults.
                baseline['allocation_probe'] = True
                control = run_case(binary, providers, search, baseline, mode, fixture_root, None, sanitizer=sanitizer)
                marker = control.get('allocation_fault', {})
                if not isinstance(marker, dict):
                    marker = {}
                count = marker.get('calls', 0)
                if marker.get('requested') != 0 or marker.get('triggered') != 0 or not isinstance(count, int) or not 1 <= count <= 128:
                    control['verdict'] = 'FAIL'
                    control.setdefault('errors', []).append('invalid allocation baseline')
                records.append(control)
                if control['verdict'] != 'PASS':
                    continue
                for index in range(1, count + 2):
                    hit = index <= count
                    row = case(utility, 'allocation-' + name + '-' + str(index), args,
                               out=b'' if hit else output, status='nonzero' if hit else 0,
                               err='nonempty' if hit else b'', env={'CSH_PATH_FAIL_AT': str(index)},
                               allocation_fault={'requested': index, 'calls_min': index if hit else count,
                                                 'calls_max': count, 'triggered': int(hit)}, **extra)
                    record = run_case(binary, providers, search, row, mode, fixture_root, None, sanitizer=sanitizer)
                    records.append(record)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('binary', type=Path)
    parser.add_argument('provider', type=Path)
    parser.add_argument('--record', type=Path, required=True)
    parser.add_argument('--sanitizer', action='store_true')
    args = parser.parse_args()
    records = run(args.binary.resolve(), args.provider.resolve(), Path(tempfile.gettempdir()), args.sanitizer)
    for row in records:
        print(row['verdict'] + ': ' + row['id'] + ' (' + row['mode'] + ')', flush=True)
        if row['verdict'] != 'PASS':
            print(json.dumps(row), flush=True)
    totals = {key: sum(r['verdict'] == key for r in records) for key in ('PASS', 'FAIL')}
    result = dict(ticket='CSH-080', scope='test-only malloc/strdup/getcwd/realpath call-site ENOMEM; not libc-internal or kernel faults',
                  platform=platform.platform(), source_identity=source_identity(), binary_sha256=sha(args.binary),
                  provider=str(args.provider.resolve()), provider_sha256=sha(args.provider), totals=totals, cases=records)
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(totals))
    return int(bool(totals['FAIL']))


if __name__ == '__main__':
    raise SystemExit(main())
