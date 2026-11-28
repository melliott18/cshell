#!/usr/bin/env python3
"""Force stderr EOF ahead of the real ed's queued final stdout response.

No provider bytes or statuses are fabricated. Wait for the editor to exit only
after the final commands, then order the already-ready descriptors stderr first.
The same probe can load the pre-fix helper to retain a deterministic failure.
On Darwin that helper can also lose unread output when its PTY slave closes.
"""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
from unittest.mock import patch


def probe(helper, argv):
    spec = importlib.util.spec_from_file_location('signal_helper', helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    real_selector, real_write = selectors.DefaultSelector, os.write
    real_read, real_close, real_popen = os.read, os.close, subprocess.Popen
    state = dict(events=[], final=False)
    child = None
    master = None

    def popen(*args, **kwargs):
        nonlocal child
        child = real_popen(*args, **kwargs)
        return child

    def write(fd, data):
        nonlocal master
        if data == b'P\n1p\nw saved\nq\n':
            master = fd
            state['final'] = True
        return real_write(fd, data)

    class OrderedSelector(real_selector):
        def select(self, timeout=None):
            if state['final']:
                child.wait(timeout=2)
                events = super().select(timeout)
                events.sort(key=lambda event: event[0].fd != child.stderr.fileno())
                state['events'].append(dict(event='ready', fds=[
                    'stderr' if key.fd == child.stderr.fileno() else 'stdout'
                    for key, _ in events]))
                return events
            return super().select(timeout)

    def read(fd, size):
        block = real_read(fd, size)
        if state['final']:
            state['events'].append(dict(event='read', stream=(
                'stderr' if fd == child.stderr.fileno() else 'stdout'), data=block.hex()))
        return block

    def close(fd):
        # Preserve the unread final stdout after the old helper fails. This is
        # evidence only, never input to the helper or its acceptance assertion.
        if fd == master:
            os.set_blocking(fd, False)
            try:
                state['unread_stdout'] = real_read(fd, 65536).hex()
            except OSError as error:
                state['unread_errno'] = error.errno
        return real_close(fd)

    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix='csh129-order-') as temporary:
        directory = Path(temporary)
        os.chdir(directory)
        Path('original').write_bytes(b'')
        try:
            with patch.object(module.selectors, 'DefaultSelector', OrderedSelector), \
                 patch.object(module.subprocess, 'Popen', popen), \
                 patch.object(module.os, 'write', write), \
                 patch.object(module.os, 'read', read), \
                 patch.object(module.os, 'close', close), redirect_stdout(io.StringIO()):
                try:
                    module.ed_signal(argv, 'int')
                    state['outcome'] = 'PASS'
                except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                    state.update(outcome='FAIL', error=str(error))
            state['signal'] = json.loads(Path('signal.json').read_text())
            state['files'] = {str(p): p.read_bytes().hex() for p in
                              (Path('saved'), Path('original')) if p.is_file()}
            state['reaped'] = child is not None and child.poll() is not None
        finally:
            os.chdir(previous)
    state['fixture_removed'] = not directory.exists()
    return state


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--helper', type=Path, default=Path(__file__).with_name('host_language_helper.py'))
    parser.add_argument('--ed', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    result = probe(args.helper.resolve(), [str(args.ed.resolve()), '-s', 'original'])
    args.record.write_text(json.dumps(result, indent=2) + '\n')
    print(result['outcome'])
    raise SystemExit(result['outcome'] != 'PASS')
