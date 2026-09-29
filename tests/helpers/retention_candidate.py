"""Controlled trace producer and sampler for diagnostic ownership regressions."""
import json
import os
from pathlib import Path
import signal
import sys
import time


def emit(event, child=0):
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
    action = signal.getsignal(signal.SIGALRM)
    record = {"t": int(time.clock_gettime(time.CLOCK_MONOTONIC) * 1000000), "p": os.getpid(),
              "e": event, "n": 32, "r": 1, "i": 1, "c": child,
              "a": [int(signal.SIGALRM in mask),
                    int(signal.SIGALRM in signal.sigpending()),
                    0 if action == signal.SIG_DFL else 1 if action == signal.SIG_IGN else 2,
                    int(signal.getitimer(signal.ITIMER_REAL)[0] * 1000000)]}
    fd = os.open(os.environ["CSH_RETENTION_TRACE"], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, (json.dumps(record, separators=(",", ":")) + "\n").encode())
    finally:
        os.close(fd)


def candidate(mode):
    if mode == "missing":
        print("ok")
        return
    emit("start")
    if mode in ("success", "progress"):
        if mode == "progress":
            emit("round+")
            for _ in range(20):
                emit("run+")
                time.sleep(0.02)  # Intentional workload; event pairs prove progress.
                emit("run-")
            emit("round-")
        emit("finish")
        print("ok")
        return
    if mode == "spoof":
        emit("fork-parent", int(sys.argv[3]))
        emit("stall_wait+", int(sys.argv[3]))
    else:
        read, write = os.pipe()
        child = os.fork()
        if child == 0:
            os.close(read)
            emit("fork-child")
            os.write(write, b"r")
            os.close(write)
            while True:
                signal.pause()
        os.close(write)
        emit("fork-parent", child)
        assert os.read(read, 1) == b"r"
        os.close(read)
        emit("stall_wait+", child)
    while True:
        signal.pause()


def sampler(mode, target, output):
    path = Path(output)
    if mode == "hang":
        read, write = os.pipe()
        child = os.fork()
        if child == 0:
            os.close(read)
            os.setpgid(0, 0)
            os.write(write, b"r")
            os.close(write)
            while True:
                signal.pause()
        os.close(write)
        assert os.read(read, 1) == b"r"
        os.close(read)
        path.with_suffix(".pids.json").write_text(json.dumps([os.getpid(), child]))
        while True:
            signal.pause()
    if mode == "oversize":
        with path.open("wb", buffering=0) as stream:
            for _ in range(4096):
                stream.write(b"x" * 4096)
        return
    path.write_text(f"controlled sample target {target}\n")


if __name__ == "__main__":
    if sys.argv[1] == "sample":
        sampler(*sys.argv[2:])
    else:
        candidate(sys.argv[2])
