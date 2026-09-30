"""Observe an owned blocked writer without changing its signal/I/O behavior."""
import hashlib
from pathlib import Path
import re
import subprocess
import time


def sampled_write(report, pid):
    """Require the owned PID and repeated syscall frames in the call graph."""
    if not re.search(r'^Process:.*\['+str(pid)+r'\]$', report, re.M):
        return False
    graph = report.partition('Call graph:')[2].partition('Total number in stack')[0]
    return any(int(count) >= 2 for count in re.findall(
        r'^\s+(\d+) (?:__)?write(?:v)?(?:_nocancel)?\s+\(in libsystem_kernel\.dylib\)',
        graph, re.M))


def observe_write(process, directory, deadline):
    wchan = Path('/proc/'+str(process.pid)+'/wchan')
    if Path('/proc/self/wchan').exists():
        observed = ''
        while 'pipe_write' not in observed:
            if process.poll() is not None or time.monotonic() >= deadline:
                raise TimeoutError('selected provider did not reach blocked pipe_write: '+observed)
            observed = wchan.read_text().strip()
            time.sleep(.005)
        return dict(observer='Linux /proc/PID/wchan', state=observed)
    sampler = Path('/usr/bin/sample')
    if not sampler.exists():
        raise NotImplementedError('No Linux wchan or Darwin sample observer supplied')
    output = directory/'blocked-write.sample'
    attempt = subprocess.run([str(sampler), str(process.pid), '1', '-file', str(output)],
        capture_output=True, timeout=max(.01,min(4,deadline-time.monotonic())))
    if attempt.returncode:
        raise RuntimeError('Darwin sample failed: '+attempt.stderr.decode(errors='replace'))
    with output.open('rb') as stream:
        data = stream.read(262145)
    if len(data) > 262144:
        raise RuntimeError('Darwin sample exceeds 262144-byte capture ceiling')
    report = data.decode('utf-8',errors='replace')
    if process.poll() is not None or not sampled_write(report,process.pid):
        raise RuntimeError('Darwin sample did not observe the owned process blocked in write')
    return dict(observer=str(sampler), observer_sha256=hashlib.sha256(sampler.read_bytes()).hexdigest(),
                state='sampled write in libsystem_kernel; private pipe held full with no drains',
                sample=report, sample_sha256=hashlib.sha256(data).hexdigest())
