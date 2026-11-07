"""Run the unchanged terminal-fault oracle for the controlled Mach receiver."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
import smoke

case = smoke.load_suite(ROOT / "tests/fixtures/jobs-fault-pty.json")["cases"][0]
started = time.monotonic()
failures = smoke.run_case(Path(sys.argv[1]).resolve(), case, 5, 65536)
result = {"binary": sys.argv[1], "case": case,
          "seconds": time.monotonic() - started, "failures": failures}
Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result), flush=True)
sys.exit(bool(failures))
