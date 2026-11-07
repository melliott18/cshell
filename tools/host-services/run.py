#!/usr/bin/env python3
"""Run the service image without networks, mounts, or host clock capabilities."""
import argparse
import hashlib
import json
import signal
from pathlib import Path
import subprocess
import time
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='cshell-services:local')
    parser.add_argument('--output', type=Path, default=Path('build/tests/host-services'))
    parser.add_argument('--timeout', type=int, default=300)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 600: parser.error('timeout must be 1..600 seconds')
    args.output.mkdir(parents=True, exist_ok=True)
    name = 'cshell-services-' + uuid.uuid4().hex
    command = ['docker', 'create', '--name', name, '--init', '--network', 'none',
               '--cap-drop', 'SYS_TIME', '--cap-drop', 'SYS_ADMIN', '--cap-drop', 'NET_ADMIN',
               '--pids-limit', '128', '--memory', '768m', '--hostname', 'csh078', args.image]
    record = dict(command=command, timeout_seconds=args.timeout, failures=[])
    created = False
    process = None
    started = time.monotonic()
    try:
        record['image'] = json.loads(subprocess.check_output(['docker', 'image', 'inspect', args.image], timeout=10))[0]
        # Use the inspected immutable image, even if a tag changes concurrently.
        command[-1] = record['image']['Id']
        # The daemon can create the object even if its response times out.
        # This unpredictable unique name is ours to clean up after any attempt.
        created = True
        record['container'] = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT, timeout=15).strip()
        with (args.output / 'run.log').open('wb') as log:
            process = subprocess.Popen(['docker', 'start', '-a', name], stdout=log, stderr=subprocess.STDOUT)
            try:
                record['attach_status'] = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                record['failures'].append('outer service deadline exceeded')
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait(timeout=5)
        state = json.loads(subprocess.check_output(['docker', 'inspect', name], timeout=10))[0]
        if state['State']['Running']:
            subprocess.run(['docker', 'stop', '--time', '3', name], check=True, capture_output=True, timeout=10)
            state = json.loads(subprocess.check_output(['docker', 'inspect', name], timeout=10))[0]
        record['state'] = state['State']
        if state['State']['ExitCode'] != 0:
            record['failures'].append('service profile returned nonzero')
        copy = subprocess.run(['docker', 'cp', name + ':/work/build/tests/host-services.json',
                               str(args.output / 'results.json')], capture_output=True, text=True, timeout=15)
        if copy.returncode:
            record['failures'].append('missing qualification record: ' + copy.stderr)
        else:
            result = json.loads((args.output / 'results.json').read_text())
            if not result.get('qualified_subset'):
                record['failures'].append('qualification record is not passing')
    except KeyboardInterrupt:
        record['failures'].append('launcher interrupted')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        record['failures'].append(str(error))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(timeout=5)
        if created:
            try:
                cleanup = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, text=True, timeout=15)
                record['cleanup'] = dict(status=cleanup.returncode, stdout=cleanup.stdout, stderr=cleanup.stderr)
                if cleanup.returncode:
                    record['failures'].append('container removal failed')
                else:
                    listed = subprocess.check_output(['docker', 'ps', '-aq', '--filter', 'name=^/' + name + '$'], timeout=10)
                    if listed.strip(): record['failures'].append('owned container still exists')
            except (OSError, subprocess.SubprocessError) as error:
                record['failures'].append('cleanup: ' + str(error))
        record['seconds'] = round(time.monotonic() - started, 3)
        record['artifacts'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in args.output.iterdir() if p.name in ('run.log', 'results.json')}
        (args.output / 'launcher.json').write_text(json.dumps(record, indent=2) + '\n')
    for error in record['failures']: print('FAIL:', error)
    print('Service evidence:', args.output)
    return int(bool(record['failures']))


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    raise SystemExit(main())
