#!/usr/bin/env python3
"""Controlled terminal candidate; these observations do not test shell behavior."""

import fcntl
import json
import os
from pathlib import Path
import resource
import select
import signal
import struct
import sys
import termios
import time


def emit(text):
    os.write(1, text.encode("utf-8"))


def record_processes(path, child=None):
    if path:
        Path(path).write_text(json.dumps({"parent": os.getpid(), "child": child}))


def wait_forever():
    signal.signal(signal.SIGHUP, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(1)


def terminal():
    with open("/dev/tty", "rb", buffering=0) as controlling:
        attrs = termios.tcgetattr(controlling)
        rows, columns, _, _ = struct.unpack(
            "HHHH", fcntl.ioctl(controlling, termios.TIOCGWINSZ, b"\0" * 8))
        checks = {
            "canonical": bool(attrs[3] & termios.ICANON),
            "controlling": os.tcgetpgrp(controlling.fileno()) == os.getpgrp(),
            "echo": bool(attrs[3] & termios.ECHO),
            "foreground": os.tcgetpgrp(0) == os.getpid(),
            "output_postprocessed": bool(attrs[1] & termios.OPOST),
            "session_leader": os.getsid(0) == os.getpid(),
            "signals": bool(attrs[3] & termios.ISIG),
            "size": [rows, columns],
            "stdio_ttys": all(os.isatty(fd) for fd in (0, 1, 2)),
        }
    emit(json.dumps(checks, sort_keys=True) + "\n")


def job_control(marker):
    # A real foreground child group lets the terminal generate SIGTSTP. The
    # parent stays in the same session so the child's group is not orphaned.
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    read_end, write_end = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(write_end)
        os.setpgid(0, 0)
        signal.signal(signal.SIGTTOU, signal.SIG_DFL)
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        signal.signal(signal.SIGCONT, lambda *_: emit("continued\n"))
        os.read(read_end, 1)
        os.close(read_end)
        emit("child ready\n")
        # Darwin may restart a blocked canonical read before Python gets a
        # chance to run its SIGCONT handler. Periodic select returns provide
        # interpreter safe points while the kernel still owns stop/resume.
        while not select.select([0], [], [], 0.05)[0]:
            pass
        sys.stdin.readline()
        os._exit(0)
    os.close(read_end)
    os.setpgid(child, child)
    os.tcsetpgrp(0, child)
    record_processes(marker, child)
    os.write(write_end, b"x")
    os.close(write_end)
    _, status = os.waitpid(child, os.WUNTRACED)
    if os.WIFSTOPPED(status):
        emit("child stopped\n")
        os.waitpid(child, 0)
    else:
        raise RuntimeError("child exited before stopping")
    os.tcsetpgrp(0, os.getpgrp())
    emit("leader restored\n")
    sys.stdin.readline()


def fork_background(mode, marker):
    read_end, write_end = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(read_end)
        os.setpgid(0, 0)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.write(write_end, b"x")
        os.close(write_end)
        wait_forever()
    os.close(write_end)
    os.read(read_end, 1)
    os.close(read_end)
    record_processes(marker, child)
    emit("background ready\n")
    if mode == "fork-exit":
        # Keep the leader alive until the runner has observed this session.
        sys.stdin.readline()
        return
    wait_forever()


def leaderless_group(marker):
    """Leave a live foreground job whose original process-group leader exited."""
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)
    ready_read, ready_write = os.pipe()
    done_read, done_write = os.pipe()
    child = os.fork()
    if child == 0:
        os.close(ready_read)
        os.close(done_read)
        os.setpgid(0, 0)
        if os.fork() != 0:
            os._exit(0)

        def terminated(*_):
            emit("member terminated\n")
            os.write(done_write, b"x")
            os._exit(0)

        signal.signal(signal.SIGTERM, terminated)
        os.write(ready_write, str(os.getpid()).encode())
        os.close(ready_write)
        while True:
            signal.pause()
    os.close(ready_write)
    os.close(done_write)
    grandchild = int(os.read(ready_read, 64))
    os.close(ready_read)
    os.waitpid(child, 0)
    os.tcsetpgrp(0, child)
    if marker:
        Path(marker).write_text(json.dumps({"parent": os.getpid(), "grandchild": grandchild}))
    emit("group ready\n")
    os.read(done_read, 1)
    os.close(done_read)
    os.tcsetpgrp(0, os.getpgrp())


def main():
    mode = sys.argv[1]
    arguments = sys.argv[2:]
    marker = arguments[0] if arguments else None
    if mode == "terminal":
        terminal()
    elif mode == "exchange":
        emit("ready> ")
        line = sys.stdin.readline()
        emit("stdout:" + line)
        os.write(2, ("stderr:" + line).encode("utf-8"))
        if Path("seed.txt").exists():
            Path("result.txt").write_text(Path("seed.txt").read_text() + line)
        return int(arguments[0]) if arguments else 0
    elif mode == "signals":
        signal.signal(signal.SIGINT, lambda *_: emit("interrupt\n"))
        signal.signal(signal.SIGQUIT, lambda *_: emit("quit\n"))
        emit("signals ready\n")
        while sys.stdin.readline():
            pass
        emit("eof\n")
    elif mode == "job-control":
        job_control(marker)
    elif mode == "leaderless-group":
        leaderless_group(marker)
    elif mode == "hang":
        record_processes(marker)
        emit("hanging\n")
        wait_forever()
    elif mode in ("fork-hang", "fork-exit"):
        fork_background(mode, marker)
    elif mode == "flood":
        record_processes(marker)
        while True:
            os.write(1, b"o" * 1024)
            os.write(2, b"e" * 1024)
    elif mode == "exit":
        emit("finished\n")
        return int(arguments[0]) if arguments else 0
    elif mode == "paced":
        for _ in range(8):
            time.sleep(0.12)
            emit("tick\n")
    elif mode == "close-terminal":
        record_processes(marker)
        emit("closing\n")
        for descriptor in (0, 1, 2):
            os.close(descriptor)
        wait_forever()
    elif mode == "record-cwd":
        Path(arguments[0]).write_text(str(Path.cwd()))
        return int(arguments[1]) if len(arguments) > 1 else 0
    elif mode == "environment":
        cwd = Path.cwd()
        checks = {
            "allocator_setting": os.environ.get("MallocNanoZone") == "0",
            "locale": os.environ.get("LC_ALL") == "C",
            "override": os.environ.get("CSHELL_FIXTURE_VALUE") == "fixture value",
            "host_isolated": "CSHELL_HOST_SECRET" not in os.environ,
            "home_isolated": Path(os.environ["HOME"]).resolve().is_relative_to(cwd),
            "temporary_isolated": Path(os.environ["TMPDIR"]).resolve().is_relative_to(cwd),
        }
        emit(json.dumps(checks, sort_keys=True) + "\n")
    elif mode == "limits":
        checks = {
            "core": resource.getrlimit(resource.RLIMIT_CORE)[0] == 0,
            "cpu": 0 < resource.getrlimit(resource.RLIMIT_CPU)[0] <= 6,
            "file": 0 < resource.getrlimit(resource.RLIMIT_FSIZE)[0] <= 1048576,
            "descriptors": 0 < resource.getrlimit(resource.RLIMIT_NOFILE)[0] <= 64,
        }
        emit(json.dumps(checks, sort_keys=True) + "\n")
    else:
        raise ValueError("unknown PTY candidate mode: " + mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
