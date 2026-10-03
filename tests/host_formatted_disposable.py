#!/usr/bin/env python3
"""Investigate low-stack exec only on a disposable GitHub-hosted Darwin OS.

The ordinary threshold entry point rejects this configuration. This diagnostic
requires both explicit opt-in and hosted-runner identity, checkpoints results,
and stops after the first failed configuration instead of accumulating stuck
processes. Never invoke with fabricated runner variables on a personal host.
"""
import argparse
import json
import os
from pathlib import Path
import platform

from host_echo_threshold import threshold
from host_utilities import sha, source_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disposable-darwin', action='store_true', required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    if not (platform.system() == 'Darwin' and os.environ.get('GITHUB_ACTIONS') == 'true' and
            os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and os.environ.get('RUNNER_OS') == 'macOS'):
        parser.error('requires a disposable GitHub-hosted macOS runner; do not spoof its environment')
    root = Path(__file__).resolve().parents[1]
    provider = root / 'build/host-echo-literal'
    record = dict(platform=platform.platform(), uname=list(platform.uname()), mac_version=platform.mac_ver(),
                  provider=dict(path=str(provider), sha256=sha(provider)), source_identity=source_identity(),
                  runner={key: os.environ.get(key) for key in ('GITHUB_SHA', 'GITHUB_RUN_ID', 'RUNNER_ARCH',
                                                               'RUNNER_OS', 'RUNNER_ENVIRONMENT')},
                  reset_capability='Ephemeral GitHub-hosted runner; job teardown owns OS disposal',
                  status='in-progress', cases=[])
    args.record.parent.mkdir(parents=True, exist_ok=True)

    def save():
        temporary = args.record.with_suffix('.tmp')
        temporary.write_text(json.dumps(record, indent=2) + '\n')
        temporary.replace(args.record)

    save()
    for stack in (8 * 1024 * 1024, 1024 * 1024):
        for padding in (0, 4096):
            for shape in ('single', 'aggregate'):
                record['active_configuration'] = dict(stack=stack, padding=padding, shape=shape)
                save()
                result = threshold(provider, shape, padding, stack, disposable_darwin=True)
                record['cases'].append(result)
                del record['active_configuration']
                record['status'] = 'PASS' if result['verdict'] == 'PASS' else 'FAIL'
                save()
                if result['verdict'] != 'PASS':
                    print('FAIL: retained diagnostic; stop additional low-stack trials')
                    return 1
    record['status'] = 'PASS'
    save()
    print('PASS: eight bounded configurations; all launched children reaped and absent')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
