"""Observe the unchanged PTY case; snapshots occur only after a failed deadline."""
from pathlib import Path
import argparse
import inspect
import json
import os
import subprocess
import sys
import tempfile
import termios
import select
import signal
import time

parser = argparse.ArgumentParser()
parser.add_argument('--root', type=Path, default=Path.cwd())
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--delay-us', default='0')
parser.add_argument('--both', action='store_true')
parser.add_argument('--rounds', type=int, default=100)
args = parser.parse_args()
args.root = args.root.resolve()
args.output = args.output.resolve()
args.output.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(args.root / 'tests'))
import smoke
import pty_harness
smoke.DIAGNOSTIC_LIMIT = 65536
trace = {}

def mark(index, size):
    trace['events'].append([time.monotonic() - trace['start'], index, size])

# Only add in-memory timestamps when a scripted step advances. Candidate,
# inputs, expectations, deadlines, selector waits and cleanup remain unchanged.
source = inspect.getsource(pty_harness._interact)
source = source.replace('index += 1', 'index += 1; mark(index, len(output))')
def note_write(master, pending, sent):
    modes=termios.tcgetattr(master)
    trace.setdefault('writes',[]).append({'elapsed':time.monotonic()-trace['start'],
        'data':pending[sent:].decode(errors='replace'),'foreground':os.tcgetpgrp(master),
        'lflag':modes[3],'intr':repr(modes[6][termios.VINTR]),'susp':repr(modes[6][termios.VSUSP])})
source = source.replace('sent += os.write(master, pending[sent:sent + 65536])',
    'note_write(master, pending, sent); sent += os.write(master, pending[sent:sent + 65536])')
namespace = dict(pty_harness.__dict__, mark=mark, note_write=note_write)
exec(compile(source, 'diagnostic_interact', 'exec'), namespace)
original_interact = namespace['_interact']

def interact(process, master, steps, output, failures, deadline, timeout, output_limit):
    trace.update(start=deadline-timeout, events=[], pid=process.pid)
    original_interact(process, master, steps, output, failures, deadline, timeout, output_limit)
    trace['case_elapsed'] = time.monotonic() - trace['start']
    trace['deadline_failures'] = list(failures)
    if not any('timeout' in f for f in failures):
        return
    trace['bytes_at_deadline'] = len(output)
    trace['output_at_deadline'] = bytes(output).decode(errors='replace')
    trace['foreground'] = os.tcgetpgrp(master)
    try:
        members = pty_harness.session_members(process.pid, time.monotonic()+1)
        trace['members'] = members
        pids = sorted({process.pid, *(pid for pid, _ in members)})
        columns = 'pid=,ppid=,pgid=,stat=,wchan=,time=,sig=,sigmask=,jobc=,tpgid='
        trace['ps'] = subprocess.run(['/bin/ps','-p',','.join(map(str,pids)),'-o',columns],
            text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1).stdout
        trace['termios_at_deadline'] = repr(termios.tcgetattr(master))
        # Keep the original failure. These are post-deadline observations,
        # never additional time in which the fixture can be accepted.
        for kind in ('second-control', 'direct-signal'):
            if kind=='second-control':
                os.write(master,b'\x03')
            else:
                if os.tcgetpgrp(master)!=trace['foreground']:
                    break
                os.killpg(trace['foreground'],signal.SIGINT)
            ready,_,_=select.select([master],[],[],0.25)
            extra=bytearray()
            if ready:
                while pty_harness._read(master,extra,[],65536): pass
            trace[kind]={'elapsed':time.monotonic()-trace['start'],
                'output':bytes(extra).decode(errors='replace'),'foreground':os.tcgetpgrp(master)}
        extra = bytearray()
        while pty_harness._read(master,extra,[],65536):
            pass
        trace['output_after_snapshot'] = bytes(extra).decode(errors='replace')
        trace['post_snapshot_elapsed'] = time.monotonic()-trace['start']
    except (OSError,subprocess.SubprocessError) as error:
        trace['snapshot_error'] = str(error)

pty_harness._interact = interact
case = {'name': 'minimal redundant SIGCONT' if args.both else 'minimal necessary SIGCONT',
        'transport': 'pty', 'args': ['1' if args.both else '0',str(args.root/'build/tests/jobs_helper'), args.delay_us],
        'steps': [{'expect': 'ready\n'}, {'control': 'Z'}, {'expect': 'foreground\n'}, {'control':'C'}, {'expect':'interrupted\n'}] * 64,
        'expect': {'output': 'ready\nforeground\ninterrupted\n' * 64, 'status': 0}}
with (args.output/'rounds.jsonl').open('w') as log:
    for iteration in range(args.rounds):
        trace.clear(); trace['round']=iteration+1
        started=time.monotonic()
        failures=smoke.run_case(args.root/'build/tests/resume_race',case,5,65536)
        trace['total_elapsed']=time.monotonic()-started
        trace['failures']=failures
        log.write(json.dumps(trace)+'\n');log.flush()
        print('round',iteration+1,'FAIL' if failures else 'PASS',round(trace['case_elapsed'],3),flush=True)
        if failures:
            raise SystemExit(1)
