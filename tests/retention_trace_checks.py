"""Validate real alarm failure capture without changing the retention oracle."""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import retention_diagnostics as diagnostics


def assert_stopped(pid):
    deadline = time.monotonic() + 2
    while True:
        result = subprocess.run(["/bin/ps", "-o", "stat=", "-p", str(pid)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=max(0.05, deadline - time.monotonic()))
        state = result.stdout.strip()
        if not state or state.startswith(b"Z"):
            return
        assert time.monotonic() < deadline, (pid, state)
        time.sleep(0.01)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--output", type=Path, default=Path("build/retention-diagnostics-checks"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    records = []
    captured_roles = set()
    for blocked in (False, True):
        case = {"name": "diagnostic stalled child: " + ("blocked alarm" if blocked else "default alarm"),
                "stdin": "", "args": ["diagnostic-stall"],
                "expect": {"stdout": "", "stderr": "", "status": 0}}
        candidate = binary
        if blocked:
            candidate = Path(sys.executable)
            case["args"] = ["-c", "import os,signal,sys; signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGALRM}); os.execv(sys.argv[1],sys.argv[1:])",
                            str(binary), "diagnostic-stall"]
        result = diagnostics.run_case(candidate, case, args.output, timeout=6)
        assert result["diagnostic_failures"] == [], result
        assert result["watcher_cleanup_failures"] == [], result
        expected = f"status: expected 0, got {-signal.SIGKILL if blocked else -signal.SIGALRM}"
        assert expected in result["case_failures"], result
        assert any("timeout after 6s" in item for item in result["case_failures"]) == blocked, result
        assert result["duration_seconds"] < 10, result
        rows, info = diagnostics.read_trace(Path(result["artifacts"]["trace"]))
        assert not info["errors"] and not info["truncated"], info
        root = result["trace_summary"]["root_pid"]
        wait = next(row for row in rows if row["p"] == root and row["e"] == "stall_wait+")
        assert wait["a"][0] == int(blocked) and wait["a"][2] == 0, wait
        assert 0 < wait["a"][3] <= 5000000, wait
        assert any(row["e"] == "fork-child" and row["a"][3] == 0 for row in rows), rows
        assert result["watcher"]["trigger"] is not None, result
        attempts = result["watcher"]["attempts"]
        assert {item["role"] for item in attempts} == {"root", "child"}, result
        assert all(item["status"] not in ("starting", "sampling") for item in attempts), result
        for item in attempts:
            if item["status"] == "captured":
                stack = Path(item["output"]).read_text(errors="replace")
                assert "Call graph:" in stack, item
                captured_roles.add(item["role"])
        for pid in {row["p"] for row in rows} | {result["watcher"]["pid"]}:
            assert_stopped(pid)
        records.append({"name": case["name"], "verdict": "PASS", "result": result})
        print("PASS:", case["name"], "(expected failure retained)", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "checks.json").write_text(json.dumps(records, indent=2) + "\n")
    if sys.platform == "darwin":
        # Individual best-effort attempts may time out, but these controls must
        # actually demonstrate both stack roles across the two known stalls.
        assert captured_roles == {"root", "child"}, "macOS stack capture was not demonstrated; inspect retained attempts"
        print("PASS: real macOS root and child stack capture", flush=True)
    else:
        print("UNAVAILABLE: native stack sampler is macOS-only; timing/alarm and cleanup controls passed", flush=True)


if __name__ == "__main__":
    main()
