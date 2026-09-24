#!/usr/bin/env python3
"""Controlled candidate executable for the behavioral runner's own tests."""

import json
import os
from pathlib import Path
import resource
import signal
import sys
import time


def record_processes(path, child=None):
    if path:
        Path(path).write_text(json.dumps({"parent": os.getpid(), "child": child}))


def wait_forever():
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(1)


def main():
    mode = sys.argv[1]
    arguments = sys.argv[2:]
    if mode == "echo":
        sys.stdout.buffer.write(sys.stdin.buffer.read())
        sys.stderr.write(arguments[0] if arguments else "")
        return int(arguments[1]) if len(arguments) > 1 else 0
    if mode == "backpressure":
        sys.stdout.buffer.write(b"prefix" * 22000)
        sys.stdout.buffer.flush()
        sys.stdout.buffer.write(sys.stdin.buffer.read())
        return 0
    if mode == "files":
        Path("result.txt").write_text(Path("seed/input.txt").read_text() + "processed\n")
        Path("artifacts/empty").mkdir(parents=True)
        Path("remove.txt").unlink()
        return 0
    if mode == "write":
        Path(arguments[0]).write_text(arguments[1])
        return 0
    if mode == "record-cwd":
        Path(arguments[0]).write_text(str(Path.cwd()))
        return int(arguments[1])
    if mode == "environment":
        cwd = Path.cwd()
        checks = {
            "allocator_setting": os.environ.get("MallocNanoZone") == "0",
            "locale": os.environ.get("LC_ALL") == "C",
            "override": os.environ.get("CSHELL_FIXTURE_VALUE") == "fixture value",
            "host_isolated": "CSHELL_HOST_SECRET" not in os.environ,
            "home_isolated": Path(os.environ["HOME"]).resolve().is_relative_to(cwd),
            "temporary_isolated": Path(os.environ["TMPDIR"]).resolve().is_relative_to(cwd),
        }
        print(json.dumps(checks, sort_keys=True))
        return 0
    if mode == "limits":
        limits = {
            "core": resource.getrlimit(resource.RLIMIT_CORE)[0] == 0,
            "cpu": 0 < resource.getrlimit(resource.RLIMIT_CPU)[0] <= 6,
            "file": 0 < resource.getrlimit(resource.RLIMIT_FSIZE)[0] <= 1048576,
            "descriptors": 0 < resource.getrlimit(resource.RLIMIT_NOFILE)[0] <= 64,
        }
        print(json.dumps(limits, sort_keys=True))
        return 0
    if mode == "prompt":
        print("Shell> hello")
        return 0
    if mode == "symlink":
        Path(arguments[0]).symlink_to(arguments[1])
        return 0
    if mode == "hang":
        record_processes(arguments[0] if arguments else None)
        wait_forever()
    if mode in ("fork-hang", "fork-exit"):
        # The child keeps inherited output descriptors and deliberately ignores
        # SIGTERM. Both a waiting and an exited parent must trigger cleanup.
        read_end, write_end = os.pipe()
        child = os.fork()
        if child == 0:
            os.close(read_end)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            os.write(write_end, b"ready")
            os.close(write_end)
            wait_forever()
        os.close(write_end)
        os.read(read_end, 5)
        os.close(read_end)
        record_processes(arguments[0], child)
        if mode == "fork-exit":
            return 0
        wait_forever()
    if mode == "flood":
        record_processes(arguments[0] if arguments else None)
        while True:
            os.write(1, b"o" * 1024)
            os.write(2, b"e" * 1024)
    raise ValueError("unknown candidate mode: " + mode)


if __name__ == "__main__":
    raise SystemExit(main())
