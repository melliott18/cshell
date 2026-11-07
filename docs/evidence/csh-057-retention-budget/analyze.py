#!/usr/bin/env python3
"""Recompute the hosted retention diagnosis from local, original artifacts.

No network, subprocess execution, archive extraction, or fixture execution.
Print deterministic JSON to stdout; compare it with analysis.json.
"""
import collections
import hashlib
import json
from pathlib import Path
import tarfile


HERE = Path(__file__).resolve().parent
PROVENANCE = json.loads((HERE / "provenance.json").read_text())


def seconds(microseconds):
    return round(microseconds / 1000000, 6)


def read_case(record):
    path = HERE / record["archive"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == record["archive_sha256"]
    with tarfile.open(path, "r:gz") as archive:
        members = {}
        for member in archive.getmembers():
            assert member.isfile()
            source = archive.extractfile(member)
            assert source is not None
            members[member.name] = source.read()
    prefix = record["case_directory"] + "/"
    documents = {name: json.loads(members[prefix + name]) for name in (
        "result.json", "metadata.json", "capture-start.json", "watcher.json")}
    raw_trace = members[prefix + "trace.jsonl"]
    assert raw_trace.endswith(b"\n")
    rows = [json.loads(line) for line in raw_trace.splitlines()]
    assert rows[0]["e"] == "start"
    root = rows[0]["p"]
    parent = [row for row in rows if row["p"] == root]
    assert all(a["t"] <= b["t"] for a, b in zip(parent, parent[1:]))
    result, metadata, watcher = (documents[name] for name in (
        "result.json", "metadata.json", "watcher.json"))
    assert not result["diagnostic_failures"]
    assert not result["watcher_cleanup_failures"]
    assert not result["trace_summary"]["errors"]
    assert not result["trace_summary"]["truncated"]
    assert not result["trace_summary"]["partial_final_record"]
    assert result["trace_summary"]["events"] == len(rows)
    assert metadata["deadline_seconds"] == 60
    assert metadata["ci_identity"]["GITHUB_RUN_ID"] == str(record["run_id"])

    pending, intervals = {}, collections.defaultdict(list)
    for row in parent:
        event = row["e"]
        if event.endswith("+"):
            phase = event[:-1]
            assert phase not in pending, (phase, row)
            pending[phase] = row
        elif event.endswith("-") or event == "fork-parent":
            phase = "fork" if event == "fork-parent" else event[:-1]
            begin = pending.pop(phase)
            intervals[phase].append((begin, row))
    timings = {}
    for phase, pairs in sorted(intervals.items()):
        longest = max(pairs, key=lambda pair: pair[1]["t"] - pair[0]["t"])
        timings[phase] = {
            "completed": len(pairs),
            "sum_seconds": seconds(sum(end["t"] - begin["t"] for begin, end in pairs)),
            "max_seconds": seconds(longest[1]["t"] - longest[0]["t"]),
            "max_context": {key: longest[1][key] for key in ("n", "r", "i")},
        }
    # These two phases are sequential, not nested. Fork is nested inside run
    # (or foreground/overflow/helper work) and MUST NOT be added to this total.
    work = sorted(intervals["run"] + intervals["reap"], key=lambda pair: pair[0]["t"])
    assert all(a[1]["t"] <= b[0]["t"] for a, b in zip(work, work[1:]))
    fill_reaps = [row for row in parent if row["e"] == "reap-"
                  and row["r"] in (1, 2) and 1 <= row["i"] <= row["n"]]
    starts = [row for row in parent if row["e"] == "run+"]
    completed_reaps = [row for row in parent if row["e"] == "reap-"]
    alarm_states = sorted({tuple(row["a"][:3]) for row in rows})
    assert alarm_states == [(0, 0, 0)]
    assert all(all(value >= 0 for value in row["a"]) for row in rows)
    assert all(0 < row["a"][3] <= 5000000 for row in starts)
    forked = {row["c"]: row for row in parent if row["e"] == "fork-parent"}
    entered = {row["p"] for row in rows if row["e"] == "fork-child"}
    assert all(pid > 0 for pid in forked)
    capture_start = documents["capture-start.json"]["monotonic_us"]
    last_reap = completed_reaps[-1]
    job = json.loads((HERE / record["job_record"]).read_text())
    assert job["id"] == record["job_id"] and job["run_id"] == record["run_id"]
    checks = json.loads(members["retention-diagnostics-checks/checks.json"])
    assert all(check["verdict"] == "PASS" for check in checks)
    return {
        "run_id": record["run_id"], "job_id": record["job_id"],
        "job_url": record["job_url"], "job_conclusion": job["conclusion"],
        "checkout": metadata["ci_identity"]["GITHUB_SHA"],
        "binary_sha256": metadata["binary_sha256"],
        "uname": metadata["uname"],
        "capture_duration_seconds": result["capture_duration_seconds"],
        "case_failures": result["case_failures"],
        "diagnostic_failures": result["diagnostic_failures"],
        "watcher_cleanup_failures": result["watcher_cleanup_failures"],
        "events": len(rows), "event_counts": dict(sorted(collections.Counter(
            row["e"] for row in rows).items())),
        "root_finished": result["trace_summary"]["root_finished"],
        "successful_parent_forks": len(forked),
        "completed_capacity_fills": len(fill_reaps),
        "child_entry_records": len(entered),
        "forks_without_child_entry_record": [forked[pid] for pid in sorted(set(forked) - entered)],
        "alarm_states": [list(state) for state in alarm_states],
        "alarm_state_fields": ["blocked", "pending", "disposition_0_default"],
        "phase_timings": timings,
        "nonoverlapping_run_reap_sum_seconds": seconds(sum(
            end["t"] - begin["t"] for begin, end in work)),
        "maximum_root_event_gap_seconds": seconds(max(
            b["t"] - a["t"] for a, b in zip(parent, parent[1:]))),
        "last_event": parent[-1], "last_completed_reap": last_reap,
        "last_event_after_root_start_seconds": seconds(parent[-1]["t"] - parent[0]["t"]),
        "last_event_after_capture_start_seconds": seconds(parent[-1]["t"] - capture_start),
        "last_reap_after_root_start_seconds": seconds(last_reap["t"] - parent[0]["t"]),
        "last_reap_after_capture_start_seconds": seconds(last_reap["t"] - capture_start),
        "capture_start_reference": documents["capture-start.json"]["reference"],
        "unfinished_phases": pending,
        "watcher": watcher,
        "diagnostic_controls": [{"name": check["name"], "verdict": check["verdict"],
                                 "case_failures": check["result"]["case_failures"]}
                                for check in checks],
        "original_member_sha256": {name: hashlib.sha256(data).hexdigest()
                                   for name, data in sorted(members.items())},
    }


def main():
    cases = {name: read_case(record) for name, record in PROVENANCE["inputs"].items()}
    comparison = json.loads((HERE / PROVENANCE["comparison_record"]).read_text())
    assert not comparison["files"]
    assert comparison["base_commit"]["sha"] == cases["failed"]["checkout"]
    peer_commit = next(commit for commit in comparison["commits"]
                       if commit["sha"] == cases["peer"]["checkout"])
    tree = comparison["base_commit"]["commit"]["tree"]["sha"]
    assert peer_commit["commit"]["tree"]["sha"] == tree
    failed, peer = cases["failed"], cases["peer"]
    assert failed["case_failures"] and not failed["root_finished"]
    assert failed["successful_parent_forks"] == 578
    assert failed["completed_capacity_fills"] == 573
    assert failed["maximum_root_event_gap_seconds"] < 0.2
    assert failed["last_event_after_capture_start_seconds"] > 59.99
    assert not peer["case_failures"] and peer["root_finished"]
    assert peer["successful_parent_forks"] == 619 and peer["completed_capacity_fills"] == 576
    print(json.dumps({"same_source_tree": tree, "source_files_changed": [],
                      "cases": cases}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
