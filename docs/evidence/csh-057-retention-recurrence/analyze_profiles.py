"""Summarize retained local phase traces without rerunning the fixture."""
import gzip
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def summarize(name, trace, result):
    rows = [line.split() for line in gzip.decompress((ROOT / trace).read_bytes()).decode().splitlines()]
    phases = {}
    for phase, count in (("fork", 615), ("run", 576), ("reap", 576)):
        values = [float(row[-1]) for row in rows if row[0] == phase]
        assert len(values) == count, (name, phase, len(values))
        phases[phase] = {"count": len(values), "sum_seconds": sum(values), "max_seconds": max(values)}
    recorded = json.loads((ROOT / result).read_text())
    assert recorded["failures"] == [], recorded
    return {"name": name, "elapsed_seconds": recorded.get("seconds", recorded.get("elapsed")),
            "failures": recorded["failures"], "phases": phases}


def main():
    records = [summarize("serial", "serial.progress.gz", "asan-profile.json")]
    records += [summarize(f"concurrent-{i}", f"concurrent-{i}.progress.gz", f"concurrent-{i}.json")
                for i in range(4)]
    report = {"source": "60295934db1c971a2b3aac582f88b0f766eccce2", "patch": "profile.patch",
              "notes": ["fork is nested within run; do not add their sums",
                        "run/reap cover capacity fills only; fork covers all context_job forks",
                        "four live/format fixture forks are not instrumented",
                        "these successful local probes cannot establish hosted timeout cause"],
              "records": records}
    (ROOT / "profile-analysis.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
