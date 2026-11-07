"""Owned live-stream checks: output must arrive before input EOF or termination."""
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time

from host_text_boundaries import collect, finish, launch, receive
from host_text_interruptions import fifo_writer
from host_utilities import serial


def definitions():
    return [('cat', 'unbuffered-live'), ('tee', 'unbuffered-live'),
            ('tee', 'unbuffered-append'), ('tail', 'follow-regular'),
            ('tail', 'follow-renamed-descriptor'), ('tail', 'follow-named-fifo'),
            ('tail', 'follow-stdin-pipe')]


def run_case(binary, path, selected, tool, behavior, mode, root, timeout=8):
    row = dict(id=tool+'/'+behavior, mode=mode, category='streaming', verdict='FAIL',
               source='https://pubs.opengroup.org/onlinepubs/9799919799/utilities/'+tool+'.html',
               phases=[], expected=dict(stdout_hex=b'A\0B\nlast'.hex()))
    process, writer = None, None
    with tempfile.TemporaryDirectory(prefix='csh-live-stream-', dir=root) as temporary:
        directory = Path(temporary)
        try:
            if not selected:
                raise FileNotFoundError('missing provider: '+tool)
            deadline = time.monotonic()+timeout
            chunks = [b'A', b'\0B\n', b'last']
            expected = b''.join(chunks)
            if tool in ('cat', 'tee'):
                copies = ('one', 'two') if tool == 'tee' else ()
                prefix = b'previous\n' if behavior.endswith('append') else b''
                for name in copies:
                    (directory/name).write_bytes(b'previous\n')
                args = ['-u'] if tool == 'cat' else (['-a'] if prefix else [])+list(copies)
                process = launch(binary, path, selected, args, mode, directory,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                output = b''
                for chunk in chunks:
                    process.stdin.write(chunk); process.stdin.flush()
                    output += receive(process, chunk, deadline)
                    # stdout can precede a file write. Require every copy to
                    # catch up while input remains open, before sending more.
                    for name in copies:
                        while (directory/name).read_bytes() != prefix+output:
                            if time.monotonic() >= deadline or process.poll() is not None:
                                raise TimeoutError('copy did not arrive before input EOF')
                            time.sleep(.005)
                    row['phases'].append(dict(input_open=not process.stdin.closed,
                                              output_hex=output.hex(), copies_verified=list(copies)))
                rest, err = collect(process, deadline)
                status = 0
            elif behavior == 'follow-stdin-pipe':
                process = launch(binary, path, selected, ['-f', '-c', '+1'], mode, directory,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                process.stdin.write(expected); process.stdin.flush()
                output, err = collect(process, deadline)
                rest, status = b'', 0
                row['phases'].append(dict(stdin_pipe_closed=True, follows=False))
            else:
                filename = directory/'data'
                if behavior == 'follow-named-fifo':
                    os.mkfifo(filename)
                else:
                    filename.write_bytes(chunks[0])
                process = launch(binary, path, selected, ['-f', '-c', '+1', 'data'], mode, directory,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
                if behavior == 'follow-named-fifo':
                    writer = fifo_writer(process, filename, deadline)
                    os.write(writer, chunks[0])
                    os.close(writer); writer = None
                output = receive(process, chunks[0], deadline)
                if behavior == 'follow-renamed-descriptor':
                    filename.rename(directory/'retained')
                    filename.write_bytes(b'wrong replacement\n')
                    filename = directory/'retained'
                for chunk in chunks[1:]:
                    if behavior == 'follow-named-fifo':
                        writer = fifo_writer(process, filename, deadline)
                        os.write(writer, chunk)
                        os.close(writer); writer = None
                    else:
                        with filename.open('ab', buffering=0) as stream:
                            stream.write(chunk)
                    output += receive(process, chunk, deadline)
                    row['phases'].append(dict(provider_alive=process.poll() is None, output_hex=output.hex()))
                process.send_signal(signal.SIGTERM)
                rest, err = collect(process, deadline)
                status = -signal.SIGTERM
            row.update(actual=serial(dict(status=process.returncode, stdout=output+rest, stderr=err)),
                       expected=dict(status=status, stdout_hex=expected.hex(), stderr_hex=''),
                       verdict='PASS' if process.returncode == status and output+rest == expected and not err else 'FAIL')
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            row.update(error=str(error), phase='setup' if process is None else 'assertion')
        finally:
            if writer is not None:
                os.close(writer)
            row['leader_reaped'] = finish(process)
    row['fixture_removed'] = not Path(temporary).exists()
    if not row['leader_reaped'] or not row['fixture_removed']:
        row['verdict'] = 'FAIL'
    return row


def run_cases(binary, path, identity, root):
    return [run_case(binary, path, identity[tool]['path'], tool, behavior, mode, root)
            for tool, behavior in definitions() for mode in ('direct', 'exec')]
