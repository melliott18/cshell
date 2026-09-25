#!/usr/bin/env python3
"""Bounded replacement input/invocation API checks; no commands are executed."""

import argparse
import errno
import json
import math
import os
from pathlib import Path
import pty
import signal
import subprocess
import tempfile


OUTPUT_LIMIT = 2 * 1024 * 1024


class Fixture:
    def __init__(self, binary, directory, timeout):
        self.binary = binary
        self.directory = directory
        self.timeout = timeout

    def run(self, *arguments, data=b"", stdin_tty=False, stderr_tty=False):
        master = slave = None
        if stdin_tty or stderr_tty:
            master, slave = pty.openpty()
        try:
            with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
                process = subprocess.Popen(
                    [str(self.binary), *map(str, arguments)],
                    stdin=slave if stdin_tty else subprocess.PIPE,
                    stdout=stdout,
                    stderr=slave if stderr_tty else stderr,
                    cwd=self.directory,
                    start_new_session=True,
                    env=dict(os.environ, LC_ALL="C"),
                )
                if slave is not None:
                    os.close(slave)
                    slave = None
                try:
                    process.communicate(None if stdin_tty else data, timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.communicate()
                    raise AssertionError(f"subprocess exceeded {self.timeout}s") from None
                stdout.seek(0)
                stderr.seek(0)
                output = stdout.read(OUTPUT_LIMIT + 1)
                errors = stderr.read(OUTPUT_LIMIT + 1)
                if master is not None:
                    os.set_blocking(master, False)
                    while len(errors) <= OUTPUT_LIMIT:
                        try:
                            chunk = os.read(master, 65536)
                        except OSError as error:
                            if error.errno in (errno.EIO, errno.EAGAIN):
                                break
                            raise
                        if not chunk:
                            break
                        errors += chunk
                assert len(output) <= OUTPUT_LIMIT, "stdout exceeded output limit"
                assert len(errors) <= OUTPUT_LIMIT, "stderr exceeded output limit"
                assert process.returncode == 0, (
                    f"fixture status {process.returncode}, stderr={errors[:1000]!r}"
                )
                assert errors == b"", f"unexpected stderr: {errors[:1000]!r}"
                return output
        finally:
            if slave is not None:
                os.close(slave)
            if master is not None:
                os.close(master)

    def json(self, *arguments, **kwargs):
        output = self.run(*arguments, **kwargs)
        try:
            return json.loads(output)
        except ValueError:
            raise AssertionError(f"invalid JSON, extra output, or banner: {output[:1000]!r}") from None


def expected_lines(data):
    lines = []
    offset, line_number, column = 0, 1, 1
    while data:
        end = data.find(b"\n")
        length = len(data) if end < 0 else end + 1
        physical_line, data = data[:length], data[length:]
        start = [offset, line_number, column]
        offset += length
        if physical_line.endswith(b"\n"):
            line_number += 1
            column = 1
        else:
            column += length
        lines.append({
            "data": physical_line.decode("latin1"),
            "start": start,
            "end": [offset, line_number, column],
        })
    return lines, [offset, line_number, column]


def check_input(result, data):
    lines, final_position = expected_lines(data)
    assert result["lines"] == lines, "physical bytes or source positions differ"
    assert result["position"] == final_position, "final source position differs"
    assert result["eof_repeats"] == 3, "EOF was not repeatedly checked"


def check_invocation(result, mode, arg0, arguments, interactive=False, prompt=False):
    assert "error" not in result, result
    assert result["mode"] == mode, result
    assert result["arg0"] == arg0, result
    assert result["arguments"] == arguments, result
    assert result["interactive"] is interactive, result
    assert result["primary"] == ("primary> " if prompt else None), result
    assert result["secondary"] == ("more> " if prompt else None), result


def check_error(result, status, system_errno=None, argument_index=None):
    assert result.get("error"), result
    assert result["status"] == status, result
    if system_errno is not None:
        assert result["errno"] == system_errno, result
    if argument_index is not None:
        assert result["argument_index"] == argument_index, result


def cases(fixture, directory):
    source_data = (
        ("empty", b""),
        ("newline", b"\n"),
        ("final unterminated line", b"echo final"),
        ("multiple physical lines", b"first\n\nthird\nlast"),
        ("multiline shell text", b"echo 'first\nsecond'\nnext \\\ncontinued\n"),
    )
    for name, data in source_data:
        for kind in ("string", "file", "fd"):
            def check_source(kind=kind, data=data):
                if kind == "string":
                    result = fixture.json(kind, data.decode())
                    assert result["source"] == "fixture-string"
                elif kind == "file":
                    source = directory / "source"
                    source.write_bytes(data)
                    result = fixture.json(kind, source)
                    assert result["source"] == str(source)
                else:
                    result = fixture.json(kind, data=data)
                    assert result["source"] == "fixture-stdin"
                check_input(result, data)
            yield f"{kind}: {name}", check_source

    def check_binary_file():
        data = b"before\x00after\xff\n\x00final"
        source = directory / "binary"
        source.write_bytes(data)
        check_input(fixture.json("file", source), data)
    yield "file: embedded NUL and high byte", check_binary_file

    def check_long_line():
        data = b"x" * 200000 + b"\nfinal"
        source = directory / "long"
        source.write_bytes(data)
        check_input(fixture.json("file", source), data)
        check_input(fixture.json("fd", data=data), data)
    yield "file/fd: 200KB physical line", check_long_line

    yield "owned string/name/file lifetime", lambda: expect_bytes(fixture.run("ownership"), b"ok\n")
    yield "descriptor ownership, CLOEXEC, blocking, and no read-ahead", lambda: expect_bytes(
        fixture.run("fd-contract"), b"ok\n"
    )

    command = "first\nsecond"
    script = directory / "script"
    script.write_bytes(b"script\nlast")
    dash_script = directory / "-script"
    dash_script.write_bytes(b"dash script\n")
    mappings = (
        ("-c default arg0", ["-c", command], "string", "fixture-shell", [], command.encode()),
        ("-c operands", ["-c", command, "alias", "one", "-two", ""], "string", "alias", ["one", "-two", ""], command.encode()),
        ("-c empty command", ["-c", "", "", "arg"], "string", "", ["arg"], b""),
        ("-s operands", ["-s", "one", "-two", ""], "stdin", "fixture-shell", ["one", "-two", ""], b"redirected\n"),
        ("stdin default", [], "stdin", "fixture-shell", [], b"redirected\n"),
        ("script operands", [script, "one", "-two"], "file", str(script), ["one", "-two"], script.read_bytes()),
        ("-- option delimiter", ["--", "-script", "one"], "file", "-script", ["one"], dash_script.read_bytes()),
        ("lone - delimiter", ["-", "-script", "one"], "file", "-script", ["one"], dash_script.read_bytes()),
        ("-c -- delimiter", ["-c", "--", "-command", "alias"], "string", "alias", [], b"-command"),
        ("-s -- delimiter", ["-s", "--", "-arg"], "stdin", "fixture-shell", ["-arg"], b"redirected\n"),
    )
    for name, arguments, mode, arg0, positional, data in mappings:
        def check_mapping(arguments=arguments, mode=mode, arg0=arg0, positional=positional, data=data):
            result = fixture.json("invoke-owned", *arguments, data=data)
            check_invocation(result, mode, arg0, positional)
            check_input(result, data)
        yield f"invocation: {name} with copied operands", check_mapping

    errors = (
        ("missing command", ["-c"], 0),
        ("missing grouped command", ["-ic"], 0),
        ("unknown option", ["-z"], 1),
        ("unknown shell option", ["-z"], 1),
        ("long option", ["--invalid"], 1),
        ("plus option", ["+i"], 1),
        ("conflicting grouped modes", ["-cs", "text"], 1),
        ("conflicting modes", ["-s", "-c", "text"], 2),
    )
    for name, arguments, index in errors:
        yield f"invocation error: {name}", lambda arguments=arguments, index=index: check_error(
            fixture.json("invoke", *arguments), 2, 0, index
        )

    missing = directory / "missing"
    yield "missing source file", lambda: check_error(fixture.json("file", missing), 127, errno.ENOENT)
    yield "missing script diagnostic", lambda: check_error(fixture.json("invoke", missing), 127, errno.ENOENT, 1)
    yield "directory source rejected", lambda: check_error(fixture.json("file", directory), 1, errno.EISDIR)
    yield "directory script diagnostic", lambda: check_error(fixture.json("invoke", directory), 1, errno.EISDIR, 1)
    if os.geteuid() != 0:
        unreadable = directory / "unreadable"
        unreadable.write_bytes(b"secret\n")
        unreadable.chmod(0)
        yield "unreadable source file", lambda: check_error(fixture.json("file", unreadable), 1, errno.EACCES)
        yield "unreadable script diagnostic", lambda: check_error(fixture.json("invoke", unreadable), 1, errno.EACCES, 1)

    for stdin_tty, stderr_tty in ((False, False), (True, False), (False, True), (True, True)):
        for arguments in ([], ["-s", "first", "second"]):
            def check_auto(stdin_tty=stdin_tty, stderr_tty=stderr_tty, arguments=arguments):
                result = fixture.json("meta", *arguments, stdin_tty=stdin_tty, stderr_tty=stderr_tty)
                interactive = stdin_tty and stderr_tty
                check_invocation(result, "stdin", "fixture-shell", arguments[1:], interactive, interactive)
            yield f"automatic interactive stdin={stdin_tty} stderr={stderr_tty} argv={arguments}", check_auto

    explicit = (
        (["-i"], "stdin", "fixture-shell", [], True),
        (["-is", "arg"], "stdin", "fixture-shell", ["arg"], True),
        (["-ic", command, "alias"], "string", "alias", [], False),
        (["-ci", command], "string", "fixture-shell", [], False),
        (["-i", script, "arg"], "file", str(script), ["arg"], False),
    )
    for arguments, mode, arg0, positional, prompt in explicit:
        yield f"explicit interactive {arguments}", lambda arguments=arguments, mode=mode, arg0=arg0, positional=positional, prompt=prompt: check_invocation(
            fixture.json("meta", *arguments), mode, arg0, positional, True, prompt
        )
    for arguments, mode, arg0 in ((["-c", command], "string", "fixture-shell"), ([script], "file", str(script))):
        yield f"terminal descriptors do not auto-enable {mode}", lambda arguments=arguments, mode=mode, arg0=arg0: check_invocation(
            fixture.json("meta", *arguments, stdin_tty=True, stderr_tty=True), mode, arg0, []
        )
    for arguments in (["-c", command], [script], ["-s"], ["-i"]):
        yield f"API has no banner or prompt output {arguments}", lambda arguments=arguments: expect_bytes(
            fixture.run("quiet", *arguments), b""
        )


def expect_bytes(actual, expected):
    assert actual == expected, f"unexpected output: {actual[:1000]!r}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="build/tests/input_fixture")
    parser.add_argument("--fault-binary", type=Path)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    binary = Path(args.binary).resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"not an executable file: {binary}")
    failed = 0
    total = 0
    with tempfile.TemporaryDirectory(prefix="cshell-input-") as temporary:
        directory = Path(temporary)
        fixture = Fixture(binary, directory, args.timeout)
        checks = list(cases(fixture, directory))
        if args.fault_binary is not None:
            fault_fixture = Fixture(args.fault_binary.resolve(), directory, args.timeout)
            checks.append(("injected allocation/read failures", lambda: fault_fixture.run()))
        if os.geteuid() == 0:
            print("SKIP: unreadable-file permissions require an unprivileged test user")
        for name, check in checks:
            total += 1
            try:
                check()
            except (AssertionError, OSError, KeyError) as error:
                failed += 1
                print(f"FAIL: {name}: {error}")
            else:
                print(f"PASS: {name}")
    print(f"{total - failed}/{total} input/invocation checks passed")
    return int(failed != 0)


if __name__ == "__main__":
    raise SystemExit(main())
