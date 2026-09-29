#!/usr/bin/env python3
"""Owned argument/exit witness and synchronized ed signal driver for CSH-074."""
import json
import os
from pathlib import Path
import selectors
import pty
import termios
import signal
import shlex
import subprocess
import sys
import time


def ed_signal(argv, action):
    # Inherit the outer smoke.capture process group and resource bounds. Killing
    # that group on timeout also catches ed shell escapes and helper descendants.
    master = slave = None
    if action == 'int':
        master, slave = pty.openpty()
        attrs = termios.tcgetattr(slave)
        attrs[3] &= ~termios.ECHO
        attrs[1] &= ~termios.OPOST
        termios.tcsetattr(slave, termios.TCSANOW, attrs)
    child = subprocess.Popen(argv, stdin=slave if slave is not None else subprocess.PIPE,
                             stdout=slave if slave is not None else subprocess.PIPE,
                             stderr=subprocess.PIPE)
    if slave is not None:
        os.close(slave)
    read_fd = master if master is not None else child.stdout.fileno()
    write_fd = master if master is not None else child.stdin.fileno()
    def send(data):
        os.write(write_fd, data)
    observed = bytearray()
    diagnostics = bytearray()
    def read_until(wanted):
        deadline = time.monotonic() + 2
        start_out, start_err = len(observed), len(diagnostics)
        with selectors.DefaultSelector() as sel:
            sel.register(read_fd, selectors.EVENT_READ, observed)
            sel.register(child.stderr, selectors.EVENT_READ, diagnostics)
            while not ((len(observed) > start_out and observed.endswith(wanted)) or
                       (len(diagnostics) > start_err and diagnostics.endswith(wanted))):
                if len(observed) + len(diagnostics) > 65536 or time.monotonic() >= deadline:
                    raise RuntimeError('ed readiness/response bound exceeded: '+repr(bytes(observed)))
                for key, _ in sel.select(max(0, deadline-time.monotonic())):
                    block = os.read(key.fd, 4096)
                    if not block:
                        raise RuntimeError('ed exited before response: '+repr(bytes(observed)))
                    key.data.extend(block)
    try:
        ready_command = shlex.join([sys.executable, str(Path(__file__).resolve()), 'ready'])
        send(b'a\nrecovered\n.\n1p\n!' + ready_command.encode() + b'\n')
        read_until(b'recovered\n')
        # Seeing bytes in the pipe does not prove ed's stdio operation returned.
        # A later shell escape proves the print command completed before a signal
        # can interrupt it and make exit flush the same stdio buffer a second time.
        ready_deadline = time.monotonic() + 2
        while not Path('ready').exists():
            if time.monotonic() >= ready_deadline:
                raise RuntimeError('ed did not reach the post-print readiness command')
            time.sleep(0.005)  # Handler and modified buffer are ready.
        if action == 'hup-home':
            Path('ed.hup').mkdir()  # Deterministic cwd write failure, even as root.
        sent = signal.SIGINT if action == 'int' else signal.SIGHUP
        child.send_signal(sent)
        if action == 'int':
            read_until(b'?\n')
            send(b'1p\nw saved\nq\n')
            read_until(b'recovered\n')
        # Keep stdin open until ed acknowledges SIGINT / exits on SIGHUP.
        child.wait(timeout=2)
        out, err = child.communicate()
        observed.extend(out or b'')
        diagnostics.extend(err)
        err = bytes(diagnostics)
        result=dict(argv=argv, signal=sent.name, status=child.returncode,
                    stdout=bytes(observed).hex(), stderr=err.hex(), reaped=True,
                    files={str(p):p.read_bytes().hex() for p in
                           (Path('saved'),Path('ed.hup'),Path('.home/ed.hup')) if p.is_file()})
        Path('signal.json').write_text(json.dumps(result,indent=2)+'\n')
        if action == 'int':
            ok=(bytes(observed)==b'recovered\n?\nrecovered\n' and not err
                and child.returncode >= 0 and Path('saved').read_bytes()==b'recovered\n')
        else:
            recovery=Path('.home/ed.hup' if action=='hup-home' else 'ed.hup')
            ok=(bytes(observed)==b'recovered\n' and (action=='hup-home' or not err) and child.returncode >= 0
                and recovery.read_bytes()==b'recovered\n')
        # HUP/INT exit statuses are retained, but no exact status is specified for
        # these asynchronous paths. Signal death is never accepted as recovery.
        if not ok:
            raise RuntimeError('ed signal assertion failed: '+json.dumps(result))
        print('recovered and reaped')
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=1)
        if not Path('signal.json').exists():
            Path('signal.json').write_text(json.dumps(dict(argv=argv, action=action,
                status=child.returncode, stdout=bytes(observed).hex(),
                stderr=bytes(diagnostics).hex(), reaped=True,
                incomplete=True), indent=2) + '\n')
        for stream in (child.stdin,child.stdout,child.stderr):
            if stream is not None:
                stream.close()
        if master is not None:
            os.close(master)


if __name__ == '__main__':
    if sys.argv[1]=='argv':
        print(json.dumps(sys.argv[2:],ensure_ascii=True))
    elif sys.argv[1]=='ready':
        Path('ready').write_bytes(b'ready\n')
    elif sys.argv[1]=='exit':
        with open('calls','ab') as stream:
            stream.write((' '.join(sys.argv[3:])+'\n').encode())
        sys.exit(int(sys.argv[2]))
    elif sys.argv[1]=='ed-signal':
        ed_signal(sys.argv[3:],sys.argv[2])
    else:
        raise SystemExit('unknown helper action')
