"""Repeat the unchanged 32-cycle PTY case with complete failure diagnostics."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path.cwd() / "tests"))
import smoke

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--rounds", type=int, default=100)
args = parser.parse_args()
assert 0 < args.rounds <= 1000
smoke.DIAGNOSTIC_LIMIT = 65536
case = next(case for case in smoke.load_suite(Path("build/tests/jobs-pty.json"))["cases"]
            if case["name"] == "repeated background resumes preserve prompt and terminal")
for iteration in range(args.rounds):
    failures = smoke.run_case(Path("cshell").resolve(), case, 5, 65536)
    print(f"Round {iteration + 1}: " + ("FAIL" if failures else "PASS"), flush=True)
    if failures:
        print("\n".join(failures), flush=True)
        raise SystemExit(1)
print(f"{args.rounds} exact PTY repetitions passed ({args.rounds * 32} resume cycles)")
