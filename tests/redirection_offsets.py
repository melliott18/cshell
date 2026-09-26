#!/usr/bin/env python3
"""CSH-043: sparse redirections at a controlled, exact write boundary."""
import argparse
import os
from pathlib import Path
import platform
import resource
import shlex
import signal
import subprocess
import sys
import tempfile

import smoke

LIMIT = (1 << 31) + 4096
DISK_LIMIT = 1024 * 1024


def sparse(path, size):
    # Seek and write one byte, never fill the hole or read the entire file.
    with path.open("wb") as stream:
        stream.write(b"H")
        stream.seek(size - 1)
        stream.write(b"Q")
    assert path.stat().st_blocks * 512 <= DISK_LIMIT, "file is not sparse"


def cases(helper, append_bypasses_limit):
    h = shlex.quote(str(helper))
    # name, script, initial size, final size, last byte, stdout, stderr, status
    yield ("append last permitted byte", f"{h} write Q >>data", LIMIT - 1,
           LIMIT, b"Q", "", "", 0)
    # Match this filesystem's independently measured open(O_APPEND)/write rule.
    bypass = append_bypasses_limit
    yield ("fresh append at resource limit", f"trap '' XFSZ; {h} write X >>data",
           LIMIT, LIMIT + int(bypass), b"X" if bypass else b"Q", "",
           "" if bypass else "offset-helper: write: EFBIG\n", 0 if bypass else 23)
    yield ("positioned first rejected byte",
           f"trap '' XFSZ; exec 3<>data; {h} seek; {h} write Q >&3; {h} write X >&3",
           LIMIT - 1, LIMIT, b"Q", "", "offset-helper: write: EFBIG\n", 23)
    yield ("positioned failure with default SIGXFSZ",
           f"exec 3<>data; {h} seek; {h} write Q >&3; {h} write X >&3",
           LIMIT - 1, LIMIT, b"Q", "", "", 128 + signal.SIGXFSZ)
    yield ("positioned partial write",
           f"trap '' XFSZ; exec 3<>data; {h} seek; {h} write QX >&3", LIMIT - 1,
           LIMIT, b"Q", "", "offset-helper: write: EFBIG\n", 23)
    yield ("open at limit without writing", ": >>data", LIMIT,
           LIMIT, b"Q", "", "", 0)
    yield ("read at limit", f"{h} read <data", LIMIT, LIMIT, b"Q",
           "read boundary byte and EOF\n", "", 0)
    # External seek and writes share the open file description with the shell;
    # duplicating fd 3 must neither reset its offset nor create a lower limit.
    yield ("read-write duplicated offset",
           f"exec 3<>data; {h} seek; {h} write Q >&3", LIMIT - 1,
           LIMIT, b"Q", "", "", 0)
    yield ("duplicated write boundary and restoration",
           f"trap '' XFSZ; exec 3<>data; {h} seek; {h} write Q >&3; "
           f"{h} write X >&3; result=$?; printf 'status=%s\\n' \"$result\"",
           LIMIT - 1, LIMIT, b"Q", "status=23\n",
           "offset-helper: write: EFBIG\n", 0)
    yield ("builtin write failure and restoration",
           f"trap '' XFSZ; exec 3<>data; {h} seek; {h} write Q >&3; pwd >&3; result=$?; "
           "printf 'status=%s\\n' \"$result\"", LIMIT, LIMIT, b"Q",
           "status=1\n", "cshell: pwd: cannot write output\n", 0)
    yield ("truncate permits output again", f"{h} write Q >data",
           LIMIT, 1, b"Q", "", "", 0)
    yield ("native seek boundary via redirection", f"{h} boundary 3<>data",
           LIMIT, LIMIT, b"Q", "seek boundary and unchanged file verified\n", "", 0)


def run(binary, spec, mode):
    name, script, initial, final, tail, stdout, stderr, wanted_status = spec
    with tempfile.TemporaryDirectory(prefix="cshell-offset-") as temporary:
        directory = Path(temporary)
        path = directory / "data"
        sparse(path, initial)
        args, source = [], ""
        if mode == "string":
            args = ["-c", script]
        elif mode == "file":
            (directory / "script").write_text(script + "\n")
            args = ["script"]
        else:
            source = script + "\n"
        status, output, failures = smoke.capture(
            binary, {"args": args, "stdin": source}, directory, 5, 65536, LIMIT)
        if status != wanted_status:
            failures.append(f"status: expected {wanted_status}, got {status}")
        for stream, expected in (("stdout", stdout), ("stderr", stderr)):
            if bytes(output[stream]) != expected.encode():
                failures.append(f"{stream}: expected {expected!r}, got {bytes(output[stream])!r}")
        stat = path.stat()
        if stat.st_size != final:
            failures.append(f"file size: expected {final}, got {stat.st_size}")
        if stat.st_blocks * 512 > DISK_LIMIT:
            failures.append("allocated file storage exceeded 1 MiB")
        with path.open("rb") as stream:
            if stream.read(1) != (b"Q" if final == 1 else b"H"):
                failures.append("unexpected first byte (truncated or overwritten)")
            stream.seek(final - 1)
            if stream.read(2) != tail:
                failures.append("unexpected boundary byte or data beyond boundary")
        print(f"{'FAIL' if failures else 'PASS'}: {name} ({mode})", flush=True)
        for failure in failures:
            print(" ", failure, flush=True)
        return bool(failures)


def native_append_profile(helper):
    # A direct syscall control keeps host quirks out of the shell oracle. Only
    # these two exact outcomes are accepted; any other result is a failure.
    with tempfile.TemporaryDirectory(prefix="cshell-offset-control-") as temporary:
        directory = Path(temporary)
        path = directory / "data"
        sparse(path, LIMIT)
        status, output, failures = smoke.capture(
            helper, {"args": ["native-append", "X"], "stdin": ""},
            directory, 5, 65536, LIMIT)
        assert not failures, failures
        observed = (status, bytes(output["stdout"]), bytes(output["stderr"]),
                    path.stat().st_size)
        enforced = (23, b"", b"offset-helper: write: EFBIG\n", LIMIT)
        bypassed = (0, b"", b"", LIMIT + 1)
        assert observed in (enforced, bypassed), observed
        bypass = observed == bypassed
        with path.open("rb") as stream:
            assert stream.read(1) == b"H"
            stream.seek(LIMIT - 1)
            assert stream.read(3) == (b"QX" if bypass else b"Q")
        assert path.stat().st_blocks * 512 <= DISK_LIMIT
        print("Native fresh O_APPEND at RLIMIT_FSIZE: " +
              ("one-byte write succeeds" if bypass else "EFBIG"), flush=True)
        return bypass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("helper", type=Path)
    args = parser.parse_args()
    binary, helper = args.binary.resolve(), args.helper.resolve()
    print(f"Platform: {platform.platform()}; libc: {platform.libc_ver()}; "
          f"Python: {platform.python_version()}", flush=True)
    print(f"RLIMIT_FSIZE inherited={resource.getrlimit(resource.RLIMIT_FSIZE)}, "
          f"selected soft=hard={LIMIT}; disk cap={DISK_LIMIT}", flush=True)
    # FILESIZEBITS is filesystem metadata, not an exact byte-size guarantee.
    with tempfile.TemporaryDirectory(prefix="cshell-offset-info-") as temporary:
        path = Path(temporary) / "data"
        path.touch()
        subprocess.run([str(helper), "info", str(path)], check=True, timeout=5,
                       env={**os.environ, "LC_ALL": "C"})
        assert path.stat().st_size == 0 and path.stat().st_blocks == 0
    failed = total = 0
    append_profile = native_append_profile(helper)
    for spec in cases(helper, append_profile):
        for mode in ("string", "file", "stdin"):
            total += 1
            failed += run(binary, spec, mode)
    print(f"Result: {total - failed} passed, {failed} failed, 0 skipped", flush=True)
    return bool(failed)


if __name__ == "__main__":
    sys.exit(main())
