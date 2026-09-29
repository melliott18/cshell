"""Reproduce the bounded native reconciliation in a clean source archive."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

REVISION = "07ee1cb26ffcec0470977d03789ce0ebb156603a"
REPO = Path(__file__).resolve().parents[4]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, help="Empty directory for new results")
args = parser.parse_args()
OUTPUT = args.output or Path(tempfile.mkdtemp(prefix="csh012-results-"))
OUTPUT.mkdir(parents=True, exist_ok=True)
if any(OUTPUT.iterdir()):
    raise SystemExit("Output directory must be empty; preserve retained evidence")
print("New results:", OUTPUT.resolve(), flush=True)
source = Path(tempfile.mkdtemp(prefix="csh012-reconciliation-"))
archive = subprocess.check_output(["git", "archive", REVISION], cwd=REPO)
subprocess.run(["tar", "-xf", "-", "-C", str(source)], input=archive, check=True)
runs = []

def run(name, argv, env=None):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = subprocess.run(argv, cwd=source, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    (OUTPUT / (name + ".log.gz")).write_bytes(gzip.compress(result.stdout, mtime=0))
    runs.append(dict(command=argv, cwd=str(source), status=result.returncode,
                     start_utc=start,
                     end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     log=name + ".log.gz",
                     environment_overrides={"CSH_TEST_PATH": env["CSH_TEST_PATH"]} if env else {}))
    (OUTPUT / "runs.json").write_text(json.dumps(runs, indent=2) + "\n")
    print(name, result.returncode, flush=True)
    return result.returncode

if run("build", ["make", "-j4"]):
    raise SystemExit(1)
run("execution", ["make", "test-execution-evidence"])
run("jobs-signals", ["make", "test-jobs-signals"])
profile_status = run("host-profile", ["make", "test-host-profile"])
profile = source / "build/tests/host-profile-results.json"
if profile.exists():
    (OUTPUT / "native-host-profile.json.gz").write_bytes(gzip.compress(profile.read_bytes(), mtime=0))
if not profile_status:
    env = dict(os.environ, CSH_TEST_PATH=str(source / "build/host-profile/bin") + ":" +
               subprocess.check_output(["getconf", "PATH"], text=True).strip())
    run("profile-runtime", ["make", "test-runtime", "test-pty"], env)
run("harness", ["make", "test-harness"])
identity = json.loads(subprocess.check_output(
    ["python3", "docs/evidence/csh-058/identity.py"], cwd=source,
    env=dict(os.environ, EVIDENCE_REVISION=REVISION)))
identity["built_executables"] = {
    str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
    for p in sorted((source / "build").rglob("*"))
    if p.is_file() and os.access(p, os.X_OK)
}
(OUTPUT / "native-identity.json").write_text(json.dumps(identity, indent=2) + "\n")
print("Retained clean archive:", source, flush=True)
raise SystemExit(any(row["status"] for row in runs))
