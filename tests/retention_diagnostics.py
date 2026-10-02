#!/usr/bin/env python3
"""Observe the unchanged retention case from an independent, bounded process.

The fixture's JSONL side channel is separate from its exact stdout oracle.
Sampling is diagnostic evidence, never a reason to reset the case deadline.
"""

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import selectors
import signal
import subprocess
import sys
import tempfile
import time

import pty_harness
import smoke


TRACE_LIMIT = 1024 * 1024
DEFAULT_SUITE = Path(__file__).resolve().parent / "fixtures/job-retention.json"
# Container phases intentionally span many completed children. They must never
# consume the one stack snapshot merely because cumulative work exceeds the operation threshold.
OPERATION_PHASES = frozenset(("fork", "run", "reap", "fg", "overflow", "wait",
                              "wait_all", "live_stop", "cancel", "cleanup", "stall_wait"))


def monotonic_us():
    # Use the fixture's CLOCK_MONOTONIC clock, including its epoch, explicitly.
    return time.clock_gettime(time.CLOCK_MONOTONIC) * 1000000


def save_json(path, value):
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def read_json(path):
    return json.loads(path.read_text())


def read_trace(path):
    try:
        with path.open("rb") as stream:
            raw = stream.read(TRACE_LIMIT + 1)
    except FileNotFoundError:
        return [], {"bytes": 0, "truncated": False, "partial_final_record": False,
                    "errors": []}
    info = {"bytes": len(raw), "truncated": len(raw) > TRACE_LIMIT,
            "partial_final_record": bool(raw and not raw.endswith(b"\n")), "errors": []}
    rows = []
    last = {}
    lines = raw[:TRACE_LIMIT].splitlines(keepends=True)
    for number, line in enumerate(lines, 1):
        if not line.endswith(b"\n"):
            continue
        try:
            row = json.loads(line)
            if row.get("e") == "truncated":
                info["truncated"] = True
                continue
            assert isinstance(row, dict)
            assert isinstance(row.get("e"), str)
            assert type(row.get("p")) is int and row["p"] > 0
            assert type(row.get("t")) in (int, float) and math.isfinite(row["t"])
            assert row["t"] >= 0
            assert row["t"] >= last.get(row["p"], 0)
            alarm = row.get("a")
            assert isinstance(alarm, list) and len(alarm) == 4
            assert all(type(value) is int for value in alarm)
            assert alarm[0] in (-1, 0, 1) and alarm[1] in (-1, 0, 1)
            assert alarm[2] in (-1, 0, 1, 2) and alarm[3] >= -1
            last[row["p"]] = row["t"]
            rows.append(row)
        except (ValueError, TypeError, AttributeError, AssertionError) as error:
            info["errors"].append(f"invalid trace record {number}: {type(error).__name__}")
    return rows, info


def summarize_trace(path):
    rows, summary = read_trace(path)
    starts = [row for row in rows if row["e"] == "start"]
    root = starts[0]["p"] if starts else None
    summary.update({"events": len(rows), "root_pid": root,
                    "root_finished": any(row["p"] == root and row["e"] in ("finish", "end") for row in rows),
                    "first_time_us": rows[0]["t"] if rows else None,
                    "last_time_us": max((row["t"] for row in rows), default=None),
                    "alarm_states": [list(state) for state in sorted({tuple(row["a"][:3]) for row in rows})],
                    "alarm_query_failures": sum(any(value < 0 for value in row["a"]) for row in rows)})
    if len(starts) != 1:
        summary["errors"].append(f"expected one root start record, found {len(starts)}")
    return summary


def sample_limits(limit):
    # The watcher is itself single-threaded. This preexec_fn never runs in the
    # smoke process or a thread pool. Descendants inherit the same file bound.
    os.setpgid(0, 0)  # Separate sampler group, still inside the watcher session.
    soft, hard = resource.getrlimit(resource.RLIMIT_FSIZE)
    finite = [value for value in (soft, hard) if value != resource.RLIM_INFINITY]
    bound = min([limit] + finite)
    resource.setrlimit(resource.RLIMIT_FSIZE, (bound, bound))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def in_session(pid, root):
    try:
        return pid > 0 and os.getsid(pid) == root
    except OSError:
        return False


def cleanup_owned_groups(session, deadline, exclude_leader=False):
    """Bound one session snapshot and kill only groups proven to belong to it."""
    failures = []
    groups = set() if exclude_leader else {session}
    try:
        groups.update(group for _, group in pty_harness.session_members(session, deadline)
                      if not exclude_leader or group != session)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        failures.append(f"watcher session snapshot failed: {error}")
    for group in sorted(groups, key=lambda group: group == session):
        try:
            if pty_harness.owned_group(group, session, deadline):
                pty_harness.kill_group(group, session, deadline)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            failures.append(f"watcher group {group} cleanup failed: {error}")
    return failures


def sample_targets(config, targets, report, report_path):
    """Start at most two samplers together within one bounded time window."""
    limit = config["sample_limit"]
    deadline = time.monotonic() + config["sample_timeout"]
    running = []
    with selectors.DefaultSelector() as selector:
        for role, pid in targets:
            output = Path(config["directory"]) / f"stack-{role}-{pid}.txt"
            console = output.with_suffix(".console.txt")
            attempt = {"role": role, "target_pid": pid, "status": "starting",
                       "output": str(output), "console": str(console),
                       "returncode": None, "seconds": 0.0, "truncated": False}
            report["attempts"].append(attempt)
            save_json(report_path, report)
            if not in_session(pid, report["root_pid"]):
                attempt["status"] = "target-unavailable"
                save_json(report_path, report)
                continue
            command = config.get("sampler_command")
            if command is None:
                if sys.platform != "darwin":
                    attempt["status"] = "unavailable"
                    attempt["reason"] = f"no supported stack sampler for {sys.platform}"
                    save_json(report_path, report)
                    continue
                command = ["/usr/bin/sample", "{pid}", "1", "1", "-mayDie", "-file", "{output}"]
            command = [part.replace("{pid}", str(pid)).replace("{output}", str(output))
                       for part in command]
            attempt["command"] = command
            started = time.monotonic()
            try:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           preexec_fn=lambda: sample_limits(limit))
            except (OSError, subprocess.SubprocessError) as error:
                attempt.update(status="unavailable", reason=str(error))
                save_json(report_path, report)
                continue
            os.set_blocking(process.stdout.fileno(), False)
            item = {"process": process, "attempt": attempt, "started": started,
                    "bytes": bytearray(), "pipe_open": True}
            running.append(item)
            attempt["status"] = "sampling"
            selector.register(process.stdout, selectors.EVENT_READ, item)
            save_json(report_path, report)
        while running:
            now = time.monotonic()
            for key, _ in selector.select(max(0, min(0.02, deadline - now))):
                item = key.data
                try:
                    chunk = os.read(key.fileobj.fileno(), 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    item["pipe_open"] = False
                else:
                    room = limit - len(item["bytes"])
                    item["bytes"].extend(chunk[:room])
                    if len(chunk) > room:
                        item["attempt"]["truncated"] = True
            for item in list(running):
                process, attempt = item["process"], item["attempt"]
                try:
                    file_bytes = Path(attempt["output"]).stat().st_size
                except FileNotFoundError:
                    file_bytes = 0
                if file_bytes >= limit or file_bytes + len(item["bytes"]) > limit:
                    attempt["truncated"] = True
                expired = time.monotonic() >= deadline
                done = process.poll() is not None and not item["pipe_open"]
                if not (done or expired or attempt["truncated"]):
                    continue
                # Kill this sampler's original group even if its leader has
                # exited while a descendant retains the output pipe.
                if expired or attempt["truncated"]:
                    try:
                        if pty_harness.owned_group(process.pid, os.getpid(), deadline):
                            os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    except (OSError, ValueError, subprocess.SubprocessError) as error:
                        attempt["kill_error"] = str(error)
                if process.poll() is None:
                    process.kill()
                # Never spend a second sampling budget on final reap. Parent
                # group cleanup independently kills any remaining descendants.
                try:
                    process.wait(timeout=max(0, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    pass
                if item["pipe_open"]:
                    selector.unregister(process.stdout)
                    process.stdout.close()
                attempt["returncode"] = process.returncode
                attempt["seconds"] = time.monotonic() - item["started"]
                file_room = max(0, limit - len(item["bytes"]))
                if file_bytes > file_room:
                    with Path(attempt["output"]).open("r+b") as stream:
                        stream.truncate(file_room)
                    attempt["truncated"] = True
                    file_bytes = file_room
                Path(attempt["console"]).write_bytes(item["bytes"])
                attempt["output_bytes"] = file_bytes
                attempt["console_bytes"] = len(item["bytes"])
                if attempt["truncated"] or process.returncode == -signal.SIGXFSZ:
                    attempt["status"] = "truncated"
                elif expired and not done:
                    attempt["status"] = "timeout"
                elif process.returncode != 0:
                    attempt["status"] = "failed"
                elif file_bytes == 0:
                    attempt["status"] = "empty"
                else:
                    attempt["status"] = "captured"
                running.remove(item)
                save_json(report_path, report)
    report["status"] = "sampled"
    save_json(report_path, report)


def watch(config_path):
    config = read_json(config_path)
    directory = Path(config["directory"])
    trace = directory / "trace.jsonl"
    report_path = directory / "watcher.json"
    report = {"status": "watching", "pid": os.getpid(), "root_pid": None,
              "trigger": None, "attempts": []}
    save_json(report_path, report)
    active, children = {}, []
    start = None
    latest_alarm = None
    capture_start = None
    offset = 0
    pending = b""
    try:
        while True:
            if monotonic_us() >= config["watch_deadline_us"] or os.getppid() != config["parent_pid"]:
                report["status"] = "watch-lifetime-ended"
                report["reason"] = "absolute deadline or parent exit"
                save_json(report_path, report)
                return 1
            if capture_start is None:
                try:
                    capture_start = read_json(directory / "capture-start.json")["monotonic_us"]
                except FileNotFoundError:
                    pass
            # Read each event once. Re-parsing an ever-growing trace on every
            # poll would introduce material observer load into this timing test.
            chunk = b""
            try:
                with trace.open("rb") as source:
                    source.seek(offset)
                    chunk = source.read(max(0, TRACE_LIMIT + 1 - offset))
            except FileNotFoundError:
                pass
            offset += len(chunk)
            pending += chunk
            lines = pending.split(b"\n")
            pending = lines.pop()
            ended = False
            for line in lines:
                try:
                    row = json.loads(line)
                    event = row["e"]
                    if event == "start" and start is None:
                        if not in_session(row["p"], row["p"]):
                            continue
                        start = row
                        report["root_pid"] = row["p"]
                    if start is None or row.get("p") != start["p"]:
                        continue
                    if isinstance(row.get("a"), list) and len(row["a"]) == 4:
                        latest_alarm = row
                    if event.endswith("+") and event[:-1] in OPERATION_PHASES:
                        active[event[:-1]] = row
                    elif event.endswith("-"):
                        active.pop(event[:-1], None)
                        if event == "reap-" and row.get("c") in children:
                            children.remove(row["c"])
                    elif event == "fork-parent":
                        active.pop("fork", None)
                        if row.get("c", 0) > 0:
                            children.append(row["c"])
                    elif event in ("finish", "end"):
                        ended = True
                except (ValueError, TypeError, KeyError, AttributeError):
                    # Main validates the complete retained trace and reports
                    # malformed/truncated timing independently of case success.
                    continue
            if ended:
                report["status"] = "completed-before-sampling"
                save_json(report_path, report)
                return 0
            if start is not None:
                root = start["p"]
                now = monotonic_us()
                age = (now - (capture_start if capture_start is not None else start["t"])) / 1000000
                oldest = min(active.values(), key=lambda row: row["t"], default=None)
                operation_age = (now - oldest["t"]) / 1000000 if oldest else 0
                alarm_remaining = None
                if latest_alarm is not None and latest_alarm["a"][3] > 0:
                    alarm_remaining = (latest_alarm["t"] + latest_alarm["a"][3] - now) / 1000000
                alarm_due = alarm_remaining is not None and alarm_remaining <= config["sample_timeout"] + 0.2
                if operation_age >= config["operation_threshold"] or age >= config["total_threshold"] or alarm_due:
                    reason = ("operation-age" if operation_age >= config["operation_threshold"] else
                              "case-age" if age >= config["total_threshold"] else "alarm-deadline")
                    report["trigger"] = {"reason": reason,
                                         "observed_monotonic_us": now, "case_age_seconds": age,
                                         "operation_age_seconds": operation_age,
                                         "projected_alarm_remaining_seconds": alarm_remaining,
                                         "alarm_record": latest_alarm,
                                         "operation": oldest}
                    targets = [("root", root)]
                    child = next((pid for pid in reversed(children) if in_session(pid, root)), None)
                    if child is not None:
                        targets.append(("child", child))
                    sample_targets(config, targets, report, report_path)
                    return 0
            time.sleep(0.02)
    except BaseException as error:
        report.update(status="error", error=f"{type(error).__name__}: {error}")
        save_json(report_path, report)
        return 1
    finally:
        # Main always cleans this group too, but a watcher outliving a killed
        # main process must not leave a sampler or its descendants behind.
        # The internal entry point is required to be its own session leader.
        if os.getpgrp() == os.getpid() and os.getsid(0) == os.getpid():
            try:
                report.setdefault("cleanup_failures", []).extend(
                    cleanup_owned_groups(os.getpid(), time.monotonic() + 0.5, exclude_leader=True))
                report["self_cleanup"] = "owned session descendants, then SIGKILL to watcher group"
                save_json(report_path, report)
            finally:
                os.killpg(os.getpid(), signal.SIGKILL)


def run_case(binary, case, output, timeout=60, output_limit=65536, *,
             operation_threshold=2.0, total_threshold=57.0, sample_timeout=2.5,
             sample_limit=1048576, sampler_command=None):
    """Run one exact fixture; overrides are Python-only for controlled tests."""
    for name, value in (("timeout", timeout), ("operation_threshold", operation_threshold),
                        ("total_threshold", total_threshold), ("sample_timeout", sample_timeout)):
        if not smoke.positive_number(value):
            raise ValueError(f"{name} must be finite and positive")
    if type(sample_limit) is not int or sample_limit <= 0:
        raise ValueError("sample_limit must be a positive integer")
    if sampler_command is not None and (not isinstance(sampler_command, (tuple, list)) or
                                        not sampler_command or any(not isinstance(part, str) for part in sampler_command)):
        raise ValueError("sampler_command must be a nonempty string sequence")
    binary = Path(binary).resolve()
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="retention-", dir=output))
    paths = {name: str(directory / filename) for name, filename in
             (("trace", "trace.jsonl"), ("metadata", "metadata.json"),
              ("result", "result.json"), ("watcher", "watcher.json"))}
    paths["directory"] = str(directory)
    selected = copy.deepcopy(case)
    selected.setdefault("env", {})["CSH_RETENTION_TRACE"] = paths["trace"]
    metadata = {"binary": str(binary), "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                "platform": sys.platform, "uname": list(os.uname()), "python": sys.version,
                "case": selected, "deadline_seconds": min(timeout, case.get("timeout", timeout)),
                "output_limit": min(output_limit, case.get("output_limit", output_limit)),
                "watcher_cleanup_limit_seconds": 1.0,
                "ci_identity": {name: os.environ[name] for name in
                                ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_JOB", "GITHUB_RUN_ATTEMPT")
                                if name in os.environ},
                "forwarded_environment": {name: os.environ[name] for name in ("MallocNanoZone",)
                                          if name in os.environ},
                "sanitizer_environment_note": "smoke does not inherit ASAN_OPTIONS or UBSAN_OPTIONS; explicit case env is retained above",
                "clock": "CLOCK_MONOTONIC; trace timestamps in microseconds"}
    save_json(Path(paths["metadata"]), metadata)
    config = {"directory": str(directory), "parent_pid": os.getpid(),
              "watch_deadline_us": monotonic_us() + (metadata["deadline_seconds"] + 5.0) * 1000000,
              "operation_threshold": operation_threshold,
              "total_threshold": total_threshold, "sample_timeout": sample_timeout,
              "sample_limit": sample_limit, "sampler_command": sampler_command}
    config_path = directory / "watcher-config.json"
    save_json(config_path, config)
    watcher = None
    case_failures, diagnostic_failures, cleanup_failures = [], [], []
    started = time.monotonic()
    capture_started = None
    capture_duration = None
    watcher_returncode = None
    try:
        with (directory / "watcher-process.log").open("wb") as log:
            watcher = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
                                        "--watch", str(config_path)],
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                       start_new_session=True)
        ready_deadline = time.monotonic() + 2.0
        while not Path(paths["watcher"]).exists() and watcher.poll() is None and time.monotonic() < ready_deadline:
            time.sleep(0.01)
        if not Path(paths["watcher"]).exists():
            diagnostic_failures.append("diagnostic watcher did not initialize within 2s")
        capture_started = time.monotonic()
        save_json(directory / "capture-start.json", {"monotonic_us": monotonic_us(),
                  "reference": "immediately before smoke.run_case; includes fixture setup"})
        case_failures = smoke.run_case(binary, selected, timeout, output_limit)
        capture_duration = time.monotonic() - capture_started
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        case_failures.append(f"retention capture failed: {type(error).__name__}: {error}")
    finally:
        if watcher is not None:
            cleanup_deadline = time.monotonic() + 1.0
            cleanup_failures.extend(cleanup_owned_groups(watcher.pid, cleanup_deadline))
            # The group kill is attempted even when the bounded snapshot fails.
            try:
                watcher.kill()
            except OSError:
                pass
            try:
                watcher.wait(timeout=max(0, cleanup_deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                cleanup_failures.append("diagnostic watcher could not be reaped within 1s")
            watcher_returncode = watcher.returncode
    summary = summarize_trace(Path(paths["trace"]))
    diagnostic_failures.extend(summary["errors"])
    if summary["truncated"]:
        diagnostic_failures.append("required retention timing trace was truncated")
    if summary["partial_final_record"]:
        diagnostic_failures.append("required retention timing trace ended with a partial record")
    if summary["alarm_query_failures"]:
        diagnostic_failures.append("retention alarm-state query failed")
    if not case_failures and not summary["root_finished"]:
        diagnostic_failures.append("successful retention case omitted its final timing record")
    try:
        watcher_report = read_json(Path(paths["watcher"]))
    except (OSError, ValueError) as error:
        watcher_report = {"status": "unavailable", "error": str(error), "attempts": []}
        diagnostic_failures.append("diagnostic watcher report unavailable")
    cleanup_failures.extend(watcher_report.get("cleanup_failures", []))
    if watcher_report.get("status") == "error":
        diagnostic_failures.append("diagnostic watcher failed: " + watcher_report.get("error", "unknown error"))
    for attempt in watcher_report.get("attempts", []):
        if attempt.get("status") in ("starting", "sampling"):
            attempt["status"] = "interrupted-by-case-cleanup"
    watcher_report["cleanup_returncode"] = watcher_returncode
    save_json(Path(paths["watcher"]), watcher_report)
    result = {"case": case["name"], "failures": case_failures + diagnostic_failures + cleanup_failures,
              "case_failures": case_failures, "diagnostic_failures": diagnostic_failures,
              "watcher_cleanup_failures": cleanup_failures, "artifacts": paths,
              "duration_seconds": time.monotonic() - started,
              "capture_duration_seconds": capture_duration, "trace_summary": summary,
              "watcher": watcher_report}
    save_json(Path(paths["result"]), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="./build/tests/jobs_lifecycle")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output", type=Path, default=Path("build/retention-diagnostics"))
    parser.add_argument("--watch", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.watch:
        return watch(args.watch)
    binary = Path(args.binary).resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"not an executable file: {binary}")
    suite = smoke.load_suite(args.suite)
    print(f"Suite: {suite['name']} [{suite['kind']}] candidate={binary}", flush=True)
    passed = failed = 0
    for case in suite["cases"]:
        result = run_case(binary, case, args.output)
        if result["failures"]:
            failed += 1
            print(f"FAIL: {case['name']}", flush=True)
            for failure in result["failures"]:
                print(f"  {failure}", flush=True)
        else:
            passed += 1
            print(f"PASS: {case['name']}", flush=True)
        print(f"  retention diagnostics: {result['artifacts']['directory']}", flush=True)
    print(f"Result: {passed} passed, {failed} failed, 0 skipped", flush=True)
    return int(bool(failed) or not passed)


if __name__ == "__main__":
    raise SystemExit(main())
