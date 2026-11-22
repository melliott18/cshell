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


class EdCapture:
    """Keep both output descriptors until their individual EOF boundaries."""
    def __init__(self, stdout_fd, stderr_fd):
        self.stdout = bytearray()
        self.stderr = bytearray()
        self.events = []
        self.phase = 'setup'
        self.selector = selectors.DefaultSelector()
        try:
            for fd, name in ((stdout_fd, 'stdout'), (stderr_fd, 'stderr')):
                os.set_blocking(fd, False)
                self.selector.register(fd, selectors.EVENT_READ, name)
        except BaseException:
            self.selector.close()
            raise

    def event(self, **event):
        # A one-byte producer must not turn bounded output into an unbounded log.
        if len(self.events) < 512:
            self.events.append(dict(phase=self.phase, **event))

    def read(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError('ed readiness/response bound exceeded')
        ready = self.selector.select(remaining)
        self.event(event='ready', streams=[key.data for key, _ in ready])
        for key, _ in ready:
            try:
                block = os.read(key.fd, 4096)
            except BlockingIOError:
                continue
            self.event(event='data' if block else 'eof', stream=key.data, size=len(block))
            if not block:
                self.selector.unregister(key.fd)
                continue
            room = 65536 - len(self.stdout) - len(self.stderr)
            getattr(self, key.data).extend(block[:room])
            if len(block) > room:
                raise RuntimeError('ed output bound exceeded')

    def read_until(self, wanted):
        deadline = time.monotonic() + 2
        start_out, start_err = len(self.stdout), len(self.stderr)
        while wanted not in self.stdout[start_out:] and wanted not in self.stderr[start_err:]:
            if not self.selector.get_map():
                raise RuntimeError('ed exited before response: ' + repr(bytes(self.stdout)))
            self.read(deadline)

    def drain(self):
        deadline = time.monotonic() + 2
        while self.selector.get_map():
            self.read(deadline)

    def close(self):
        self.selector.close()


def ed_signal(argv, action):
    # Inherit smoke.capture's process group/resource bounds: its cleanup also
    # catches ed shell escapes and helper descendants after any failure.
    master = slave = child = capture = None
    complete = False
    phase = 'setup'
    try:
        if action == 'int':
            master, slave = pty.openpty()
            attrs = termios.tcgetattr(slave)
            attrs[3] &= ~termios.ECHO
            attrs[1] &= ~termios.OPOST
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
        # Only input needs terminal semantics. A pipe preserves final stdout
        # even if the child exits before its last response is consumed; Darwin
        # can discard queued PTY output when the last slave descriptor closes.
        child = subprocess.Popen(argv, stdin=slave if slave is not None else subprocess.PIPE,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        if slave is not None:
            os.close(slave)
            slave = None
        read_fd = child.stdout.fileno()
        write_fd = master if master is not None else child.stdin.fileno()
        capture = EdCapture(read_fd, child.stderr.fileno())
        observed, diagnostics = capture.stdout, capture.stderr
        os.set_blocking(write_fd, False)

        def send(data):
            deadline = time.monotonic() + 2
            while data:
                try:
                    written = os.write(write_fd, data)
                    if not written:
                        raise RuntimeError('ed input closed before command')
                    data = data[written:]
                except BlockingIOError:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise RuntimeError('ed command write bound exceeded')
                    with selectors.DefaultSelector() as sel:
                        sel.register(write_fd, selectors.EVENT_WRITE)
                        sel.select(remaining)

        capture.phase = phase = 'initial-response'
        ready_command = shlex.join([sys.executable, str(Path(__file__).resolve()), 'ready'])
        send(b'a\nrecovered\n.\n1p\n!' + ready_command.encode() + b'\n' +
             (b'P\n' if action == 'int' else b''))
        capture.read_until(b'recovered\n')
        # The shell escape proves the print returned; the later prompt proves
        # system() has returned and restored SIGINT before we deliver it.
        capture.phase = phase = 'readiness'
        ready_deadline = time.monotonic() + 2
        while not Path('ready').exists():
            if time.monotonic() >= ready_deadline:
                raise RuntimeError('ed did not reach the post-print readiness command')
            time.sleep(0.005)
        if action == 'int' and not observed.endswith(b'*'):
            capture.read_until(b'*')
        if action == 'hup-home':
            Path('ed.hup').mkdir()
        sent = signal.SIGINT if action == 'int' else signal.SIGHUP
        capture.phase = phase = 'signal-response'
        child.send_signal(sent)
        if action == 'int':
            capture.read_until(b'?\n*')
            capture.phase = phase = 'final-response'
            send(b'P\n1p\nw saved\nq\n')
            capture.read_until(b'recovered\n')
        # Drain both output pipes under the same bounds. A pre-drain wait can
        # deadlock if a broken provider fills stderr. Trailing bytes remain in
        # the oracle.
        capture.phase = phase = 'final-drain'
        capture.drain()
        child.wait(timeout=2)
        err = bytes(diagnostics)
        if action == 'int':
            ok=(bytes(observed)==b'recovered\n*?\n*recovered\n' and not err
                and child.returncode >= 0 and Path('saved').read_bytes()==b'recovered\n')
        else:
            recovery=Path('.home/ed.hup' if action=='hup-home' else 'ed.hup')
            ok=(bytes(observed)==b'recovered\n' and (action=='hup-home' or not err) and child.returncode >= 0
                and recovery.read_bytes()==b'recovered\n')
        # Retain the status; signal death never qualifies as recovery.
        if not ok:
            raise RuntimeError('ed signal assertion failed')
        complete = True
    finally:
        try:
            if child is not None:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=1)
        finally:
            if capture is not None:
                capture.close()
            if child is not None:
                for stream in (child.stdin, child.stdout, child.stderr):
                    if stream is not None:
                        stream.close()
            for fd in (slave, master):
                if fd is not None:
                    os.close(fd)
            result = dict(argv=argv, action=action, phase=phase,
                          signal=('SIGINT' if action == 'int' else 'SIGHUP'),
                          status=child.returncode if child is not None else None,
                          stdout=bytes(capture.stdout).hex() if capture else '',
                          stderr=bytes(capture.stderr).hex() if capture else '',
                          reaped=child is not None and child.returncode is not None,
                          incomplete=not complete, events=capture.events if capture else [],
                          files={str(p):p.read_bytes().hex() for p in
                                 (Path('saved'),Path('ed.hup'),Path('.home/ed.hup')) if p.is_file()})
            Path('signal.json').write_text(json.dumps(result,indent=2)+'\n')
    print('recovered and reaped')


if __name__ == '__main__':
    if sys.argv[1]=='terminal-exec':
        # Keep the controlling terminal, replace only the selected descriptors,
        # and exec in place so the harness retains session/leader ownership.
        terminal, source = sys.argv[2:4]
        with open(source, 'rb') as stream:
            os.dup2(stream.fileno(), 0)
        with open('other-output', 'wb') as stream:
            os.dup2(stream.fileno(), 2 if terminal == 'stdout' else 1)
        os.execv(sys.argv[4], sys.argv[4:])
    elif sys.argv[1]=='argv':
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
