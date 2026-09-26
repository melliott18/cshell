#!/usr/bin/env python3
"""Check signals ignored before a non-interactive shell starts."""
import os
from pathlib import Path
import signal
import subprocess
import sys


def run(binary, script, expected, ignored, interactive=False):
    def ignore_on_entry():
        signal.signal(ignored, signal.SIG_IGN)

    process = subprocess.Popen([str(binary), "-ic" if interactive else "-c", script],
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
    run(binary, "trap -p INT; trap - INT; trap -p INT; trap",
        b"trap -- '' INT\ntrap -- '' INT\ntrap -- '' INT\n", signal.SIGINT)
    run(binary, "trap 'echo caught' QUIT; kill -s QUIT $$; echo alive",
        b"alive\n", signal.SIGQUIT)
    for name in ("TERM", "QUIT", "TSTP", "TTIN", "TTOU"):
        number = getattr(signal, "SIG" + name)
        run(binary, f"trap 'echo caught' {name}; kill -s {name} $$; "
            f"trap - {name}; kill -s {name} $$; echo alive", b"alive\n", number)
        run(binary, f"trap 'echo caught' {name}; kill -s {name} $$; "
            f"trap - {name}; kill -s {name} $$; echo alive", b"caught\nalive\n", number, True)
        run(binary, f"/bin/sh -c 'kill -{name} $$; echo child'", b"child\n", number)
    print("ignored-entry signal checks passed (20 cases)")


if __name__ == "__main__":
    main()
