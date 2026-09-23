#!/usr/bin/env python3
"""Bounded startup/external-command checks, not a POSIX conformance suite."""

import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile


CASES = (
    ("exit", "exit\n", ""),
    ("external command", "/bin/echo cshell-smoke-ok\nexit\n", "cshell-smoke-ok\n"),
    (
        "successive commands",
        "/bin/echo first second third\n/bin/echo fourth\nexit\n",
        "first second third\nfourth\n",
    ),
)
OUTPUT_LIMIT = 65536


def run_case(binary, name, script, expected, timeout):
    # Files bound the runner's memory even when a broken shell produces output
    # repeatedly. A fresh working directory isolates each case's side effects.
    with tempfile.TemporaryDirectory(prefix="cshell-smoke-") as directory:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(
                [str(binary)],
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                cwd=directory,
                start_new_session=True,
                env=dict(os.environ, LC_ALL="C"),
            )
            timed_out = False
            try:
                process.communicate(script.encode(), timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                # Kill the whole test process group, including launched commands.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
            stdout.seek(0)
            stderr.seek(0)
            output = stdout.read(OUTPUT_LIMIT + 1)
            errors = stderr.read(OUTPUT_LIMIT + 1)

    # The legacy loop prints prompts even with redirected stdin. Tolerate only
    # that known limitation here; CSH-003 adds strict non-interactive assertions.
    actual = output.replace(b"Shell> ", b"")
    passed = (
        not timed_out
        and process.returncode == 0
        and len(output) <= OUTPUT_LIMIT
        and actual == expected.encode()
        and errors == b""
    )
    print(f"{'PASS' if passed else 'FAIL'}: {name}")
    if not passed:
        print(f"  status={process.returncode}, timed_out={timed_out}")
        print(f"  stdout={output[:1000]!r}")
        print(f"  stderr={errors[:1000]!r}")
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="./cshell")
    parser.add_argument("--timeout", type=float, default=5.0, help="seconds per case")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    binary = Path(args.binary).resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"not an executable file: {binary}")
    results = []
    for name, script, expected in CASES:
        try:
            results.append(run_case(binary, name, script, expected, args.timeout))
        except OSError as error:
            print(f"FAIL: {name}: {error}")
            results.append(False)
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
