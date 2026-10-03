"""Portable owned SIGINT, SIGPIPE, stop/resume and tee -i witnesses."""
import errno
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

import smoke
from host_text_boundaries import collect, finish, launch, receive
from host_utilities import serial


def definitions():
    for tool in ('cat', 'head', 'cmp'):
        for behavior in ('fifo-int', 'pipe-broken', 'fifo-stop-resume'):
            yield tool, behavior
    for behavior in ('int-default', 'int-ignore'):
        yield 'tee', behavior


def fifo_writer(process, path, deadline):
    while True:
        try:
            return os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError as error:
            if error.errno != errno.ENXIO:
                raise
            if process.poll() is not None or time.monotonic() >= deadline:
                raise TimeoutError('selected utility never opened FIFO')
            time.sleep(.005)


def stopped(process, deadline):
    while time.monotonic() < deadline:
        pid, status = os.waitpid(process.pid, os.WNOHANG | os.WUNTRACED)
        if pid:
            if not os.WIFSTOPPED(status) or os.WSTOPSIG(status) != signal.SIGSTOP:
                if os.WIFEXITED(status) or os.WIFSIGNALED(status):
                    process.returncode = os.waitstatus_to_exitcode(status)
                raise RuntimeError('provider exited instead of stopping')
            return dict(pid=pid, signal=os.WSTOPSIG(status))
        time.sleep(.005)
    raise TimeoutError('owned provider never entered stopped state')


def run_case(binary, path, selected, tool, behavior, mode, fixture_root):
    row = dict(id=tool+'/'+behavior, mode=mode, category='interruptions',
               source='https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'+tool+'.html',
               verdict='FAIL', expected={})
    process = None
    descriptors = []
    with tempfile.TemporaryDirectory(prefix='csh-interruption-', dir=fixture_root) as temporary:
        directory = Path(temporary)
        try:
            deadline = time.monotonic()+5
            if not selected:
                raise FileNotFoundError('missing provider: '+tool)
            if behavior.startswith('fifo-'):
                payload = b'one\ntwo\n'
                os.mkfifo(directory/'fifo')
                (directory/'expected').write_bytes(payload)
                args = ['-s', 'fifo', 'expected'] if tool == 'cmp' else ['-n', '2', 'fifo'] if tool == 'head' else ['-u', 'fifo']
                process = launch(binary, path, selected, args, mode, directory,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
                writer = fifo_writer(process, directory/'fifo', deadline)
                descriptors.append(writer)
                row['handshake'] = 'selected utility opened FIFO; parent holds writer'
                if behavior == 'fifo-int':
                    expected_status, expected_output = -signal.SIGINT, b''
                    process.send_signal(signal.SIGINT)
                else:
                    process.send_signal(signal.SIGSTOP)
                    row['observed_stop'] = stopped(process, deadline)
                    if os.write(writer, payload) != len(payload):
                        raise RuntimeError('short fixture FIFO write')
                    os.close(writer)
                    descriptors.remove(writer)
                    process.send_signal(signal.SIGCONT)
                    expected_status, expected_output = 0, b'' if tool == 'cmp' else payload
                    row['supplied_input'] = serial(payload)
                output, diagnostic = collect(process, deadline)
            elif behavior == 'pipe-broken':
                reader, writer = os.pipe()
                os.close(reader)  # before launch: no reader, no readiness race
                descriptors.append(writer)
                (directory/'a').write_bytes(b'a'*32768)
                (directory/'b').write_bytes(b'b'*32768)
                args = ['-l', 'a', 'b'] if tool == 'cmp' else ['-c', '32768', 'a'] if tool == 'head' else ['-u', 'a']
                process = launch(binary, path, selected, args, mode, directory,
                                 stdin=subprocess.DEVNULL, stdout=writer)
                row['handshake'] = 'private output pipe has no read descriptors before provider exec'
                output, diagnostic = collect(process, deadline)
                expected_status, expected_output = -signal.SIGPIPE, b''
            else:
                args = (['-i'] if behavior == 'int-ignore' else []) + ['copy']
                process = launch(binary, path, selected, args, mode, directory,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                process.stdin.write(b'ready\n')
                process.stdin.flush()
                first = receive(process, b'ready\n', deadline)
                while not (directory/'copy').exists() or (directory/'copy').read_bytes() != b'ready\n':
                    if process.poll() is not None or time.monotonic() >= deadline:
                        raise TimeoutError('tee did not copy ready marker to its output file')
                    time.sleep(.005)
                row['handshake'] = 'tee copied ready marker to both stdout and file before SIGINT'
                process.send_signal(signal.SIGINT)
                if behavior == 'int-ignore':
                    # No sleep is used as proof of survival: the second exact
                    # marker and matching output file prove continued copying.
                    process.stdin.write(b'after\n')
                    process.stdin.flush()
                    first += receive(process, b'after\n', deadline)
                    expected_status, expected_output = 0, b'ready\nafter\n'
                else:
                    expected_status, expected_output = -signal.SIGINT, b'ready\n'
                rest, diagnostic = collect(process, deadline)
                output = first+rest
                actual_file = (directory/'copy').read_bytes()
                row['copy'] = serial(actual_file)
                if actual_file != expected_output:
                    raise RuntimeError('tee file differs from independently expected copied markers')
            row['expected'] = serial(dict(status=expected_status, stdout=expected_output, stderr=b''))
            row['actual'] = serial(dict(status=process.returncode, stdout=output, stderr=diagnostic))
            row['verdict'] = 'PASS' if (process.returncode, output, diagnostic) == (expected_status, expected_output, b'') else 'FAIL'
            row['phase'] = 'assertion'
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            row.update(error=str(error), phase='setup' if process is None else 'assertion')
            if process is not None:
                smoke.kill_group(process)
                stdout, stderr = process.communicate(timeout=2)
                row['failure_capture'] = serial(dict(status=process.returncode, stdout=stdout, stderr=stderr))
        finally:
            try:
                row['leader_reaped'] = finish(process)
                if not row['leader_reaped']:
                    row['verdict'] = 'FAIL'
            finally:
                for descriptor in descriptors:
                    os.close(descriptor)
    row['fixture_removed'] = not Path(temporary).exists()
    if not row['fixture_removed']:
        row['verdict'] = 'FAIL'
    return row


def run_cases(binary, path, identity, fixture_root):
    return [run_case(binary, path, identity[tool]['path'], tool, behavior, mode, fixture_root)
            for mode in ('direct', 'exec') for tool, behavior in definitions()]
