#!/usr/bin/env python3
"""Run isolated, bounded fixtures; passing a suite is not POSIX conformance."""

import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import resource
import selectors
import stat
import subprocess
import sys
import tempfile
import time

import pty_harness


DEFAULT_SUITE = Path(__file__).resolve().parent.parent / "build" / "tests" / "runtime.json"
# The combined evidence grids exceed 1 MiB with long worktree helper paths.
# Keep input parsing bounded independently of child output/file-size limits.
SUITE_LIMIT = 2 * 1024 * 1024
DIAGNOSTIC_LIMIT = 1000


def positive_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value > 0
    except OverflowError:
        return False


def fields(value, required, optional, context):
    if not isinstance(value, dict):
        raise ValueError(f"{context}: expected an object")
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    if missing or unknown:
        raise ValueError(f"{context}: missing fields {sorted(missing)}, unknown fields {sorted(unknown)}")


def fixture_path(value):
    if not isinstance(value, str) or not value or "\0" in value:
        raise ValueError("fixture paths must be nonempty strings without NUL")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"fixture path must stay inside its case directory: {value!r}")
    if path.parts[0] in (".home", ".tmp"):
        raise ValueError(f"fixture path is reserved for isolation: {value!r}")


def load_suite(path):
    with path.open("rb") as source:
        raw = source.read(SUITE_LIMIT + 1)
    if len(raw) > SUITE_LIMIT:
        raise ValueError(f"suite exceeds {SUITE_LIMIT} bytes")
    suite = json.loads(raw)
    fields(suite, ("version", "name", "kind", "cases"), (), "suite")
    if type(suite["version"]) is not int or suite["version"] != 1:
        raise ValueError("suite version must be 1")
    if not isinstance(suite["name"], str) or not suite["name"].strip():
        raise ValueError("suite name must be a nonempty string")
    if suite["kind"] not in ("replacement", "module", "self"):
        raise ValueError("suite kind must be replacement, module, or self")
    if not isinstance(suite["cases"], list) or not suite["cases"]:
        raise ValueError("suite cases must be a nonempty array")
    names = set()
    for case in suite["cases"]:
        fields(case, ("name", "expect"),
               ("stdin", "transport", "steps", "args", "env", "setup", "platforms", "skip_reason", "timeout", "output_limit"), "case")
        name = case["name"]
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError("case names must be nonempty unique strings")
        names.add(name)
        transport = case.get("transport", "pipe")
        if transport not in ("pipe", "pty"):
            raise ValueError(f"{name}: transport must be pipe or pty")
        if transport == "pipe":
            if not isinstance(case.get("stdin"), str):
                raise ValueError(f"{name}: stdin must be a string")
            if "steps" in case:
                raise ValueError(f"{name}: steps require transport pty")
        else:
            if "stdin" in case:
                raise ValueError(f"{name}: PTY cases use steps and exact output, not stdin")
            validate_steps(case.get("steps"), name)
        args = case.get("args", [])
        if not isinstance(args, list) or any(not isinstance(a, str) or "\0" in a for a in args):
            raise ValueError(f"{name}: args must be strings without NUL")
        env = case.get("env", {})
        if not isinstance(env, dict) or any(
            not isinstance(k, str) or not k or "=" in k or "\0" in k
            or not isinstance(v, str) or "\0" in v for k, v in env.items()
        ):
            raise ValueError(f"{name}: env must map valid variable names to strings")
        if set(env) & {"HOME", "TMPDIR"}:
            raise ValueError(f"{name}: HOME and TMPDIR are reserved for isolation")
        setup = case.get("setup", {})
        if not isinstance(setup, dict):
            raise ValueError(f"{name}: setup must map paths to UTF-8 contents")
        for target, content in setup.items():
            fixture_path(target)
            if not isinstance(content, str):
                raise ValueError(f"{name}: setup contents must be strings")
        expected = case["expect"]
        streams = ("output",) if transport == "pty" else ("stdout", "stderr")
        fields(expected, (*streams, "status"), ("files",), f"{name}: expect")
        if any(not isinstance(expected[k], str) for k in streams):
            raise ValueError(f"{name}: expected {'/'.join(streams)} must be strings")
        if type(expected["status"]) is not int:
            raise ValueError(f"{name}: expected status must be an integer")
        files = expected.get("files", {})
        if not isinstance(files, dict):
            raise ValueError(f"{name}: files must be an object")
        for target, assertion in files.items():
            fixture_path(target)
            fields(assertion, ("type",), ("content",), f"{name}: file {target}")
            kind = assertion["type"]
            if kind not in ("file", "directory", "absent"):
                raise ValueError(f"{name}: invalid file type for {target}")
            if kind == "file" and not isinstance(assertion.get("content"), str):
                raise ValueError(f"{name}: file {target} needs string content")
            if kind != "file" and "content" in assertion:
                raise ValueError(f"{name}: only file assertions accept content")
        if "timeout" in case and not positive_number(case["timeout"]):
            raise ValueError(f"{name}: timeout must be finite and positive")
        if "output_limit" in case and (type(case["output_limit"]) is not int or case["output_limit"] <= 0):
            raise ValueError(f"{name}: output_limit must be a positive integer")
        if "platforms" in case:
            platforms = case["platforms"]
            if not isinstance(platforms, list) or not platforms or any(p not in ("darwin", "linux") for p in platforms):
                raise ValueError(f"{name}: platforms must be a nonempty list of darwin/linux")
            if not isinstance(case.get("skip_reason"), str) or not case["skip_reason"].strip():
                raise ValueError(f"{name}: platform restrictions require skip_reason")
        elif "skip_reason" in case:
            raise ValueError(f"{name}: skip_reason requires platforms")
    return suite


def validate_steps(steps, name):
    if not isinstance(steps, list):
        raise ValueError(f"{name}: PTY steps must be an array")
    for index, step in enumerate(steps, 1):
        if not isinstance(step, dict) or len(step) != 1:
            raise ValueError(f"{name}: PTY step {index} must contain exactly one action")
        action, value = next(iter(step.items()))
        choices = {"control": pty_harness.CONTROLS, "signal": pty_harness.SIGNALS,
                   "foreground": ("leader", "other")}
        if action not in ("expect", "send", *choices):
            raise ValueError(f"{name}: unknown PTY step action {action!r}")
        if not isinstance(value, str) or (action == "expect" and not value):
            raise ValueError(f"{name}: PTY {action} must be a string (expect must be nonempty)")
        if action in choices and value not in choices[action]:
            raise ValueError(f"{name}: invalid PTY {action}: {value!r}")


def child_limits(timeout, output_limit, file_size_limit=None):
    """Run only in the forked child of this single-threaded POSIX runner."""
    for kind, limit in (
        (resource.RLIMIT_CORE, 0),
        (resource.RLIMIT_CPU, math.ceil(timeout) + 1),
        (resource.RLIMIT_FSIZE, file_size_limit if file_size_limit is not None
         else max(1024 * 1024, output_limit)),
        (resource.RLIMIT_NOFILE, 64),
    ):
        soft, hard = resource.getrlimit(kind)
        existing = [n for n in (soft, hard) if n != resource.RLIM_INFINITY]
        bound = min([limit] + existing)
        resource.setrlimit(kind, (bound, bound))
    os.umask(0o077)


def kill_group(process, deadline=None):
    if deadline is None:
        deadline = time.monotonic() + 1.0
    pty_harness.kill_group(process.pid, process.pid, deadline)


def capture(binary, case, directory, timeout, output_limit, file_size_limit=None):
    environment = {
        "PATH": os.environ.get("CSH_TEST_PATH", os.defpath), "LANG": "C", "LC_ALL": "C",
        "HOME": str(directory / ".home"), "TMPDIR": str(directory / ".tmp"),
    }
    if "MallocNanoZone" in os.environ:
        environment["MallocNanoZone"] = os.environ["MallocNanoZone"]
    environment.update(case.get("env", {}))
    for target in (".home", ".tmp"):
        (directory / target).mkdir()
    if case.get("transport") == "pty":
        return pty_harness.capture(binary, case, directory, timeout, output_limit,
                                   environment, child_limits)
    data = case["stdin"].encode("utf-8")
    output = {"stdout": bytearray(), "stderr": bytearray()}
    failures = []
    deadline = time.monotonic() + timeout
    process = subprocess.Popen(
        [str(binary)] + case.get("args", []), cwd=directory, env=environment,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True,
        preexec_fn=lambda: child_limits(timeout, output_limit, file_size_limit),
    )
    try:
        with selectors.DefaultSelector() as selector:
            for stream, name in ((process.stdout, "stdout"), (process.stderr, "stderr")):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            if data:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            else:
                process.stdin.close()
            written = 0
            captured = 0
            exited = False
            while selector.get_map() or process.poll() is None:
                if not exited and process.poll() is not None:
                    # Even a successful leader may leave children holding pipes
                    # or modifying the case directory. Clean up before assertions.
                    kill_group(process)
                    exited = True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    failures.append(f"timeout after {timeout:g}s (process group killed)")
                    break
                for key, _ in selector.select(min(remaining, 0.05)):
                    stream, name = key.fileobj, key.data
                    if name == "stdin":
                        try:
                            written += os.write(stream.fileno(), data[written:written + 65536])
                        except BrokenPipeError:
                            written = len(data)
                        except BlockingIOError:
                            continue
                        if written == len(data):
                            selector.unregister(stream)
                            stream.close()
                    else:
                        try:
                            chunk = os.read(stream.fileno(), min(65536, output_limit - captured + 1))
                        except BlockingIOError:
                            continue
                        if not chunk:
                            selector.unregister(stream)
                            stream.close()
                            continue
                        available = output_limit - captured
                        output[name].extend(chunk[:available])
                        captured += min(len(chunk), available)
                        if len(chunk) > available:
                            failures.append(f"output limit exceeded ({output_limit} bytes combined stdout/stderr; process group killed)")
                            break
                if failures:
                    break
    finally:
        # Also runs on interruption, I/O errors, and normal completion.
        cleanup_deadline = time.monotonic() + 1.0
        try:
            kill_group(process, cleanup_deadline)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            failures.append(f"pipe cleanup failed: {error}")
            # A snapshot/group failure must not prevent trying to stop and reap
            # the leader. Keep the original failure even if this fallback works.
            try:
                process.kill()
            except OSError as error:
                failures.append(f"pipe cleanup could not kill leader: {error}")
        finally:
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()
            try:
                process.wait(timeout=max(0, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                failures.append("pipe cleanup could not reap leader within 1s")
    return process.returncode, output, failures


def safe_target(directory, relative):
    target = directory
    for part in PurePosixPath(relative).parts:
        target = target / part
        if target.is_symlink():
            raise ValueError(f"file {relative!r}: symlinks are not followed")
    return target


def compare_file(directory, relative, assertion):
    try:
        target = safe_target(directory, relative)
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            mode = None
        kind = assertion["type"]
        if kind == "absent":
            return None if mode is None else f"file {relative!r}: expected absent"
        if mode is None:
            return f"file {relative!r}: expected {kind}, found absent"
        if kind == "directory":
            return None if stat.S_ISDIR(mode) else f"file {relative!r}: expected directory"
        if not stat.S_ISREG(mode):
            return f"file {relative!r}: expected regular file"
        expected = assertion["content"].encode("utf-8")
        # Neither a huge file nor a FIFO/device can cause unbounded reads.
        with target.open("rb") as source:
            actual = source.read(len(expected) + 1)
        if actual != expected:
            return f"file {relative!r}: expected {expected[:DIAGNOSTIC_LIMIT]!r}, got {actual[:DIAGNOSTIC_LIMIT]!r}"
    except (OSError, ValueError) as error:
        return str(error)
    return None


def run_case(binary, case, timeout, output_limit):
    timeout = min(timeout, case.get("timeout", timeout))
    output_limit = min(output_limit, case.get("output_limit", output_limit))
    with tempfile.TemporaryDirectory(prefix="cshell-fixture-") as temporary:
        directory = Path(temporary)
        for relative, content in case.get("setup", {}).items():
            target = directory / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content.encode("utf-8"))
        status, output, failures = capture(binary, case, directory, timeout, output_limit)
        expected = case["expect"]
        if status != expected["status"]:
            failures.append(f"status: expected {expected['status']}, got {status}")
        for name in output:
            actual = bytes(output[name])
            wanted = expected[name].encode("utf-8")
            if actual != wanted:
                failures.append(f"{name}: expected {wanted[:DIAGNOSTIC_LIMIT]!r} ({len(wanted)} bytes), got {actual[:DIAGNOSTIC_LIMIT]!r} ({len(actual)} captured bytes)")
        for relative, assertion in expected.get("files", {}).items():
            failure = compare_file(directory, relative, assertion)
            if failure:
                failures.append(failure)
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="./cshell")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--case", help="run one case by exact name")
    parser.add_argument("--timeout", type=float, default=5.0, help="maximum seconds per case")
    parser.add_argument("--output-limit", type=int, default=65536, help="maximum combined stdout/stderr bytes per case")
    args = parser.parse_args()
    if not positive_number(args.timeout):
        parser.error("--timeout must be a finite positive number")
    if args.output_limit <= 0:
        parser.error("--output-limit must be a positive integer")
    binary = Path(args.binary).resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"not an executable file: {binary}")
    try:
        suite = load_suite(args.suite)
    except (OSError, ValueError) as error:
        parser.error(f"{args.suite}: {error}")
    cases = [c for c in suite["cases"] if args.case is None or c["name"] == args.case]
    if not cases:
        parser.error(f"unknown case: {args.case!r}")
    print(f"Suite: {suite['name']} [{suite['kind']}] candidate={binary}", flush=True)
    passed = failed = skipped = 0
    for case in cases:
        if sys.platform not in case.get("platforms", [sys.platform]):
            print(f"SKIP: {case['name']}: {case['skip_reason']} (platform={sys.platform})", flush=True)
            skipped += 1
            continue
        try:
            failures = run_case(binary, case, args.timeout, args.output_limit)
        except pty_harness.PtyUnavailable as error:
            print(f"SKIP: {case['name']}: {error}", flush=True)
            skipped += 1
            continue
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            failures = [str(error)]
        if failures:
            failed += 1
            print(f"FAIL: {case['name']}", flush=True)
            for failure in failures:
                print(f"  {failure}", flush=True)
        else:
            passed += 1
            print(f"PASS: {case['name']}", flush=True)
    print(f"Result: {passed} passed, {failed} failed, {skipped} skipped", flush=True)
    if not passed and not failed:
        print("FAIL: no cases ran on this platform", flush=True)
    return 1 if failed or not passed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
