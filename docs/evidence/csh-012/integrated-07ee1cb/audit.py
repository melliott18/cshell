"""Check inventory consistency and retained bytes, not POSIX conformance.

Run from any directory; stdout is the JSON report. This deliberately does not
rewrite old manifests or infer a passing requirement from a completed ticket.
"""
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DOCS = ROOT / "docs"
EXCLUDED = {"U-018", "U-021", "U-022", "U-025", "U-028",
            "O-003", "O-008", "O-010", "O-011", "O-015",
            *(f"O-{i:03}" for i in range(20, 26))}
rows = {}
forward = set()
for filename in ("posix-matrix.md", "posix-utilities.md"):
    for line in (DOCS / filename).read_text().splitlines():
        match = re.match(r'\| <a id="([a-z]+-\d{3})"></a>([A-Z]+-\d{3}) \|', line)
        if not match:
            continue
        anchor, rid = match.groups()
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line)[1:-1]]
        assert len(cells) == 7, rid
        owners = sorted(set(re.findall(r"\[(CSH-\d+)\]", cells[4])))
        assert rid not in rows and owners, rid
        rows[rid] = dict(matrix=f"{filename}#{anchor}", owners=owners,
                         applicable=rid not in EXCLUDED, evidence=cells[6])
        forward.update((owner, rid) for owner in owners)
        if rid in EXCLUDED:
            assert "inapplicable" in line.lower(), rid

reverse = set()
for line in (DOCS / "posix-owners.md").read_text().splitlines():
    if not line.startswith("| [CSH-"):
        continue
    cells = line.split("|")
    owner = re.search(r"CSH-\d+", cells[1]).group()
    reverse.update((owner, rid.upper()) for rid in re.findall(
        r"\(posix-(?:matrix|utilities)\.md#([a-z]+-\d{3})\)", cells[2]))
assert len(rows) == 131 and len(EXCLUDED) == 16
assert forward == reverse, (sorted(forward - reverse), sorted(reverse - forward))

tickets = {}
for p in sorted((DOCS / "tickets").glob("CSH-*.md")):
    content = p.read_text()
    status = re.search(r"^- Status: (.+)$", content, re.M)
    if status:
        tickets[p.name[:7]] = dict(path=str(p.relative_to(ROOT)), status=status[1])
allocations = {}
for number in range(46, 53):
    owner = f"CSH-{number:03}"
    ids = sorted(rid for candidate, rid in forward if candidate == owner)
    if number == 52:
        ids.remove("U-026")  # Shared external-host portion, not a second allocation.
    allocations[owner] = dict(status=tickets[owner]["status"], ids=ids)
allocated = [rid for item in allocations.values() for rid in item["ids"]]
assert len(allocated) == len(set(allocated)) == 115
assert set(allocated) == set(rows) - EXCLUDED

inventories = {}
mismatches = []
exact_matches = 0
drift = {entry["path"]: entry for entry in json.loads((HERE / "document-drift.json").read_text())}
explained = []
paths = sorted((DOCS / "evidence").rglob("artifacts.json"))
paths += [DOCS / "evidence" / name / "inventory.json" for name in
          ("csh-057-timeouts", "csh-057-retention-review")]
for manifest in paths:
    if HERE in manifest.parents:
        continue
    data = json.loads(manifest.read_text())
    entries = data.get("sha256", data.get("artifacts", data))
    assert isinstance(entries, dict), manifest
    for name, entry in entries.items():
        expected = entry if isinstance(entry, str) else entry["sha256"]
        path = manifest.parent / name
        if not path.is_file():
            mismatches.append(dict(manifest=str(manifest.relative_to(ROOT)), file=name,
                                   reason="missing"))
            continue
        payload = path.read_bytes()
        relative = str(path.relative_to(ROOT))
        if relative in drift:
            record = drift[relative]
            old = subprocess.check_output(["git", "show", record["historical_revision"] + ":" + relative], cwd=ROOT)
            assert hashlib.sha256(old).hexdigest() == expected == record["expected_sha256"], relative
            assert hashlib.sha256(payload).hexdigest() == record["current_sha256"], relative
            assert len(old) == entry["bytes"] == record["historical_bytes"], relative
            assert len(payload) == record["current_bytes"], relative
            explained.append(relative)
            continue
        previous_mismatches = len(mismatches)
        if hashlib.sha256(payload).hexdigest() != expected:
            mismatches.append(dict(manifest=str(manifest.relative_to(ROOT)), file=name,
                                   reason="sha256 mismatch"))
        if isinstance(entry, dict):
            if "bytes" in entry and len(payload) != entry["bytes"]:
                mismatches.append(dict(file=str(path.relative_to(ROOT)), reason="byte count"))
            if "uncompressed_sha256" in entry:
                assert hashlib.sha256(gzip.decompress(payload)).hexdigest() == entry["uncompressed_sha256"], path
        if len(mismatches) == previous_mismatches:
            exact_matches += 1
    inventories[str(manifest.relative_to(ROOT))] = len(entries)

report = dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              source_revision=subprocess.check_output(["git", "rev-parse", "HEAD"],
                                                       cwd=ROOT, text=True).strip(),
              requirement_count=len(rows), applicable_count=len(allocated),
              excluded_ids=sorted(EXCLUDED), forward_reverse_pairs=len(forward),
              ownership_matches=True, primary_allocations=allocations,
              ticket_statuses=tickets, requirements=rows,
              artifact_inventories=inventories,
              artifact_entries=sum(inventories.values()),
              exact_manifest_matches=exact_matches,
              explained_document_drift=explained, unexplained_mismatches=mismatches)
print(json.dumps(report, indent=2))
raise SystemExit(bool(mismatches))
