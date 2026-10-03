"""Controlled aggregate-cost witness using a separately delayed fixture binary.

Apply controlled-delay.patch only in a temporary checkout, then build with
ASan/UBSan. This script preserves the production oracle, child count and alarms.
It expects the old 60s cap to fail and the new default 120s cap to pass.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
import retention_diagnostics as diagnostics
import smoke


def check_progress(result):
    rows, info = diagnostics.read_trace(Path(result["artifacts"]["trace"]))
    assert not info["errors"], info
    assert all(row["a"][:3] == [0, 0, 0] for row in rows), rows
    root = result["trace_summary"]["root_pid"]
    parent = [row for row in rows if row["p"] == root]
    assert max(b["t"] - a["t"] for a, b in zip(parent, parent[1:])) < 2000000
    start = json.loads((Path(result["artifacts"]["directory"]) / "capture-start.json").read_text())
    assert parent[-1]["t"] - start["monotonic_us"] > 58000000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    case = smoke.load_suite(ROOT / "tests/fixtures/job-retention.json")["cases"][0]
    before = diagnostics.run_case(args.binary, case, args.output / "before",
                                  timeout=60, total_threshold=57)
    assert any("timeout after 60s" in x for x in before["case_failures"]), before
    assert "status: expected 0, got -9" in before["case_failures"], before
    assert before["diagnostic_failures"] == [], before
    assert before["watcher_cleanup_failures"] == [], before
    check_progress(before)
    print("PASS: controlled old-budget timeout retained", flush=True)
    after = diagnostics.run_case(args.binary, case, args.output / "after")
    assert after["failures"] == [], after
    assert 60 < after["capture_duration_seconds"] < 120, after
    rows, _ = diagnostics.read_trace(Path(after["artifacts"]["trace"]))
    root = after["trace_summary"]["root_pid"]
    assert sum(row["e"] == "fork-parent" and row["c"] > 0 and row["p"] == root
               for row in rows) == 619
    assert all(row["a"][:3] == [0, 0, 0] for row in rows), rows
    check_progress(after)
    summary = {"before": before, "after": after}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("PASS: all 619 children and exact assertions finish beyond 60s under the new budget", flush=True)


if __name__ == "__main__":
    main()
