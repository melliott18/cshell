#!/usr/bin/env python3
"""Check signals ignored before a non-interactive shell starts."""
import os
from pathlib import Path
import signal
import subprocess
import sys


def run(binary, script, expected, ignored):
    def ignore_on_entry():
        signal.signal(ignored, signal.SIG_IGN)

    process = subprocess.Popen([str(binary), "-c", script],
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, preexec_fn=ignore_on_entry,
                               start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise AssertionError("ignored-signal case timed out")
    actual = (process.returncode, stdout, stderr)
    assert actual == (0, expected, b""), actual


def main():
    binary = Path(sys.argv[1]).resolve()
    run(binary, "trap 'echo caught' INT; kill -s INT $$; echo alive",
        b"alive\n", signal.SIGINT)
    run(binary, "/bin/sh -c 'kill -INT $$; echo external'; echo alive",
        b"external\nalive\n", signal.SIGINT)
    run(binary, "trap 'echo caught' CHLD; /usr/bin/true & wait; echo alive",
        b"alive\n", signal.SIGCHLD)
    print("ignored-entry signal checks passed (3 cases)")


if __name__ == "__main__":
    main()
