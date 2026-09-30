"""Owned, deadline-bounded CSH-073 I/O/signal and disposable-capacity probes.

FIFO rendezvous proves the selected utility opened its input, not that its read
syscall returned EINTR. Linux wchan proves a blocked pipe write before signalling.
No sleep utility or unrelated process is used as a proxy for these contracts.
"""
import errno
import json
import os
from pathlib import Path
import selectors
import shlex
import signal
import subprocess
import tempfile
import time

import smoke
from host_utilities import serial


def receive(process, expected, deadline):
    data = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        while len(data) < len(expected):
            remaining = deadline - time.monotonic()
            if remaining <= 0 or not selector.select(remaining):
                raise TimeoutError('output handshake deadline; partial='+repr(bytes(data)))
            chunk = os.read(process.stdout.fileno(), len(expected)-len(data))
            if not chunk:
                raise RuntimeError('EOF before output handshake: ' + repr(bytes(data)))
            data.extend(chunk)
    if bytes(data) != expected:
        raise RuntimeError('unexpected handshake: ' + repr(bytes(data)))
    return bytes(data)


def collect(process, deadline):
    """Bound both output and time; communicate(timeout) alone bounds only time."""
    output = {'stdout': bytearray(), 'stderr': bytearray()}
    if process.stdin is not None and not process.stdin.closed:
        process.stdin.close()
        process.stdin = None
    with selectors.DefaultSelector() as selector:
        for name in output:
            stream = getattr(process, name)
            if stream is not None:
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('capture deadline; partial='+repr({name:bytes(data) for name,data in output.items()}))
            for key, _ in selector.select(min(remaining, .05)):
                data = os.read(key.fileobj.fileno(), 4096)
                if not data:
                    selector.unregister(key.fileobj)
                else:
                    output[key.data].extend(data)
                    if sum(map(len, output.values())) > 65536:
                        raise RuntimeError('capture exceeds 65536 bytes')
    process.wait(timeout=max(.01, deadline-time.monotonic()))
    return bytes(output['stdout']), bytes(output['stderr'])


def child_setup():
    smoke.child_limits(5, 65536)
    # Tool/CI launchers may ignore INT/QUIT. This probe selects default input
    # dispositions explicitly instead of accidentally testing inherited ignores.
    for sig in (signal.SIGINT, signal.SIGQUIT, signal.SIGHUP, signal.SIGTERM, signal.SIGPIPE):
        signal.signal(sig, signal.SIG_DFL)


def launch(binary, path, selected, args, mode, directory, **kw):
    argv = [selected] + args
    if mode == 'exec':
        argv = [str(binary), '-c', 'exec ' + shlex.join(argv)]
    return subprocess.Popen(argv, cwd=directory,
        env=dict(PATH=path, LC_ALL='C', HOME=str(directory)),
        start_new_session=True, preexec_fn=child_setup,
        stderr=subprocess.PIPE, **kw)


def finish(process):
    """Always reap our leader; group kill also contains a misbehaving provider."""
    if process is None:
        return True
    smoke.kill_group(process)
    process.wait(timeout=2)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream is not None:
            stream.close()
    try:
        os.kill(process.pid, 0)
    except ProcessLookupError:
        return True
    return False


def signal_case(binary, path, selected, tool, kind, mode, fixture_root):
    row = dict(id=tool+'/'+kind, mode=mode, verdict='FAIL',
               condition='U-040/other-interruptions', source='https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'+tool+'.html')
    row['expected'] = (dict(status=-signal.SIGTERM,stdout_hex='',stderr_hex='')
        if tool != 'ed' else dict(stdout_hex=(b'READY>READY>saved\nREADY>?\nREADY>saved\nREADY>' if kind=='interrupt-recovery' else b'READY>READY>saved\nREADY>').hex(),
                                 stderr_hex='',recovery='unchanged buffer' if kind=='interrupt-recovery' else 'ed.hup contains saved\n'))
    process = None
    writer = reader = None
    with tempfile.TemporaryDirectory(prefix='csh-stream-signal-',dir=fixture_root) as temporary:
        directory = Path(temporary)
        try:
            deadline = time.monotonic()+5
            if selected is None:
                raise FileNotFoundError('missing selected provider')
            if kind == 'read-termination':
                os.mkfifo(directory/'fifo')
                (directory/'other').write_bytes(b'x')
                args = ['fifo'] + (['other'] if tool == 'cmp' else [])
                process = launch(binary,path,selected,args,mode,directory,
                                 stdin=subprocess.DEVNULL,stdout=subprocess.PIPE)
                while writer is None:
                    try:
                        writer = os.open(directory/'fifo',os.O_WRONLY|os.O_NONBLOCK)
                    except OSError as error:
                        if error.errno != errno.ENXIO:
                            raise
                        if time.monotonic() >= deadline or process.poll() is not None:
                            raise TimeoutError('utility never opened owned FIFO')
                        time.sleep(.005)
                row['handshake'] = 'FIFO writer open succeeded; no bytes supplied; writer held open'
                process.send_signal(signal.SIGTERM)
                stdout, stderr = collect(process,deadline)
                ok = process.returncode == -signal.SIGTERM and stdout == stderr == b''
            elif kind == 'write-termination':
                reader, writer = os.pipe()
                os.set_blocking(writer,False)
                filled = 0
                try:
                    while True:
                        filled += os.write(writer,b'x'*4096)
                except BlockingIOError:
                    pass
                os.set_blocking(writer,True)
                (directory/'a').write_bytes(b'a'*32768)
                (directory/'b').write_bytes(b'b'*32768)
                args = ['-l','a','b'] if tool == 'cmp' else ['-c','32768','a'] if tool == 'head' else ['-u','a']
                process = launch(binary,path,selected,args,mode,directory,
                                 stdin=subprocess.DEVNULL,stdout=writer)
                from host_text_observer import observe_write
                try:
                    observation = observe_write(process,directory,deadline)
                except NotImplementedError as error:
                    row.update(verdict='UNAVAILABLE',reason=str(error))
                    return row
                row.update(handshake=observation['state'], blocked_write=observation,
                           pipe_prefill_bytes=filled)
                process.send_signal(signal.SIGTERM)
                _, stderr = collect(process,deadline)
                stdout = b''
                ok = process.returncode == -signal.SIGTERM and stderr == b''
            else:
                process = launch(binary,path,selected,['-s','-p','READY>'],mode,directory,
                                 stdin=subprocess.PIPE,stdout=subprocess.PIPE)
                stdout = receive(process,b'READY>',deadline)
                process.stdin.write(b'a\nsaved\n.\n')
                process.stdin.flush()
                stdout += receive(process,b'READY>',deadline)
                process.stdin.write(b'1p\n')
                process.stdin.flush()
                stdout += receive(process,b'saved\nREADY>',deadline)
                row['handshake'] = 'ed acknowledged changed buffer, completed print and emitted next command prompt'
                if Path('/proc/self/wchan').exists():
                    observed = ''
                    while 'pipe_read' not in observed:
                        if process.poll() is not None or time.monotonic() >= deadline:
                            raise TimeoutError('ed did not reach blocked input: '+observed)
                        observed = Path('/proc/'+str(process.pid)+'/wchan').read_text().strip()
                        time.sleep(.005)
                    row['blocked_input'] = observed
                if kind == 'interrupt-recovery':
                    process.send_signal(signal.SIGINT)
                    stdout += receive(process,b'?\nREADY>',deadline)
                    process.stdin.write(b'1p\nQ\n')
                    process.stdin.flush()
                    more,stderr = collect(process,deadline)
                    stdout += more
                    ok = stdout == b'READY>READY>saved\nREADY>?\nREADY>saved\nREADY>' and stderr == b'' and process.returncode in (0,1)
                else:
                    process.send_signal(signal.SIGHUP)
                    more,stderr = collect(process,deadline)
                    stdout += more
                    recovery = (directory/'ed.hup').read_bytes()
                    row['recovery_file'] = serial(recovery)
                    ok = stdout == b'READY>READY>saved\nREADY>' and stderr == b'' and recovery == b'saved\n' and process.returncode >= 0
            row.update(verdict='PASS' if ok else 'FAIL',phase='assertion',
                       actual=serial(dict(status=process.returncode,stdout=stdout,stderr=stderr)),pid=process.pid)
        except (OSError,RuntimeError,subprocess.SubprocessError) as error:
            row.update(error=str(error),phase='setup' if process is None else 'assertion')
            if process is not None:
                smoke.kill_group(process)
                output, diagnostic = process.communicate(timeout=2)
                row['failure_capture'] = serial(dict(status=process.returncode,stdout=output,stderr=diagnostic))
        finally:
            try:
                row['leader_reaped'] = finish(process)
                if not row['leader_reaped']:
                    row['verdict'] = 'FAIL'
            finally:
                for descriptor in (reader,writer):
                    if descriptor is not None:
                        os.close(descriptor)
    row['fixture_removed'] = not Path(temporary).exists()
    return row


def capacity_case(binary,path,selected,mode,root):
    row = dict(id='cat/filesystem-enospc',mode=mode,condition='U-040/cat-filesystem-limits',verdict='FAIL')
    process = None
    # Only use an explicitly supplied tiny disposable filesystem. Never fill /tmp
    # or the worktree. The caller supplies a dedicated <=2MiB Docker tmpfs.
    info = os.statvfs(root)
    if info.f_blocks*info.f_frsize > 2*1024*1024:
        return dict(row,verdict='UNAVAILABLE',reason='supplied filesystem exceeds 2 MiB safety ceiling')
    with tempfile.TemporaryDirectory(prefix='csh-capacity-',dir=root) as temporary:
        directory=Path(temporary)
        try:
            (directory/'input').write_bytes(b'x'*8192)
            with (directory/'output').open('wb') as output, (directory/'padding').open('wb',buffering=0) as padding:
                written=0
                try:
                    while written <= 2*1024*1024:
                        written += padding.write(b'p'*4096)
                    raise RuntimeError('filesystem did not reach bounded ENOSPC')
                except OSError as error:
                    if error.errno != errno.ENOSPC:
                        raise
                    row.update(padding_errno=error.errno,padding_bytes=written)
                process=launch(binary,path,selected,['input'],mode,directory,
                               stdin=subprocess.DEVNULL,stdout=output)
                _,err=collect(process,time.monotonic()+5)
                size=(directory/'output').stat().st_size
                row.update(verdict='PASS' if process.returncode>0 and err and size==0 else 'FAIL',
                           phase='assertion',actual=serial(dict(status=process.returncode,stderr=err,output_size=size)))
        except (OSError,RuntimeError,subprocess.SubprocessError) as error:
            row.update(error=str(error),phase='setup' if process is None else 'assertion')
            if process is not None:
                smoke.kill_group(process)
                output, diagnostic = process.communicate(timeout=2)
                row['failure_capture'] = serial(dict(status=process.returncode,stdout=output,stderr=diagnostic))
        finally:
            row['leader_reaped']=finish(process)
    row['fixture_removed']=not Path(temporary).exists()
    return row


def run_boundaries(binary,path,identity,fixture_root,capacity_root=None,audit=False):
    from host_text_interruptions import run_cases
    rows=run_cases(binary,path,identity,fixture_root)
    for mode in ('direct','exec'):
        for tool in ('cat','head','cmp','ed'):
            for kind in ((('interrupt-recovery','hangup-recovery') if audit else ('hangup-recovery',)) if tool=='ed' else ('read-termination','write-termination')):
                rows.append(signal_case(binary,path,identity[tool]['path'],tool,kind,mode,fixture_root))
        if capacity_root:
            rows.append(capacity_case(binary,path,identity['cat']['path'],mode,capacity_root))
        else:
            rows.append(dict(id='cat/filesystem-enospc',mode=mode,verdict='UNAVAILABLE',condition='U-040/cat-filesystem-limits',reason='No explicit disposable <=2 MiB filesystem supplied'))
    for row in rows:
        print(row['verdict']+': boundary: '+row['id']+' ('+row['mode']+')',flush=True)
        if row['verdict']=='FAIL':
            print(json.dumps(row),flush=True)
    return rows
