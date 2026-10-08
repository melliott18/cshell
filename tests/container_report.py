#!/usr/bin/env python3
"""Run existing Make suites and report their aggregate outcomes for Pipeline."""

import argparse
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET


SUITES = ("test", "test-pty", "test-harness")


def run_suites(output, suites=SUITES, command=("make",)):
    """One JUnit testcase per Make target; logs contain individual assertions.

    Stop on the first failed suite. Reports are written after every completed
    suite; a killed/incomplete run cannot manufacture a passing testcase.
    """
    output.mkdir(parents=True, exist_ok=True)
    report = output / "junit.xml"
    # Never leave a previous successful report behind after a new failed run.
    report.unlink(missing_ok=True)
    root = ET.Element("testsuite", name="cshell container suites")
    failed = 0
    elapsed = 0.0
    for target in suites:
        log = output / (target + ".log")
        print(f"Running make {target}; log: {log}", flush=True)
        start = time.monotonic()
        error = None
        with log.open("wb") as stream:
            try:
                result = subprocess.run([*command, target], stdout=stream,
                                        stderr=subprocess.STDOUT, check=False)
                if result.returncode:
                    error = f"make {target} exited {result.returncode}; see {log.name}"
            except OSError as exc:
                error = f"could not run make {target}: {exc}"
                stream.write(error.encode("utf-8", errors="replace"))
        duration = time.monotonic() - start
        elapsed += duration
        case = ET.SubElement(root, "testcase", classname="cshell.make",
                             name=target, time=f"{duration:.6f}")
        ET.SubElement(case, "system-out").text = f"Full output: {log.name}"
        if error:
            failed += 1
            ET.SubElement(case, "failure", message=error).text = error
        root.set("tests", str(len(root)))
        root.set("failures", str(failed))
        root.set("errors", "0")
        root.set("skipped", "0")
        root.set("time", f"{elapsed:.6f}")
        temporary = report.with_suffix(".xml.tmp")
        ET.ElementTree(root).write(temporary, encoding="utf-8", xml_declaration=True)
        temporary.replace(report)
        print(error or f"PASS: make {target} ({duration:.1f}s)", flush=True)
        if error:
            return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("test-results"))
    args = parser.parse_args()
    return run_suites(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
