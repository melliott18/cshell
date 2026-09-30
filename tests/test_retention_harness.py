"""Failure and cleanup controls for the separate retention observer."""
import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import pty_harness
import retention_diagnostics as diagnostics


HELPER = Path(__file__).resolve().parent / "helpers/retention_candidate.py"


class RetentionDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="retention-observer-check-")
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name)

    def case(self, mode="stall", extra=()):
        return {"name": "controlled retention observer " + mode, "stdin": "",
                "args": [str(HELPER), "candidate", mode, *extra],
                "expect": {"stdout": "ok\n", "stderr": "", "status": 0}}

    def run_case(self, case, sample="normal", **kwargs):
        command = ([sys.executable, str(HELPER), "sample", sample, "{pid}", "{output}"]
                   if sample is not None else [str(self.output / "missing-sampler"), "{pid}"])
        options = dict(timeout=1.0, operation_threshold=0.1, total_threshold=0.4,
                       sample_timeout=0.2, sample_limit=4096, sampler_command=command)
        options.update(kwargs)
        result = diagnostics.run_case(Path(sys.executable), case, self.output, **options)
        self.assertEqual(result["watcher_cleanup_failures"], [], result)
        self.assertLess(result["duration_seconds"], 5.0, result)
        return result

    def assert_not_running(self, pid):
        deadline = time.monotonic() + 2.0
        while True:
            result = subprocess.run(["/bin/ps", "-o", "stat=", "-p", str(pid)],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    timeout=max(0.05, deadline - time.monotonic()))
            state = result.stdout.strip()
            if not state or state.startswith(b"Z"):
                return
            if time.monotonic() >= deadline:
                self.fail(f"diagnostic-owned process {pid} still running: {state!r}")
            time.sleep(0.01)

    def assert_failed_and_clean(self, result):
        self.assertTrue(any("timeout after 1s" in item for item in result["case_failures"]), result)
        self.assertEqual(result["diagnostic_failures"], [], result)
        rows, info = diagnostics.read_trace(Path(result["artifacts"]["trace"]))
        self.assertEqual(info["errors"], [])
        pids = {row["p"] for row in rows}
        pids.add(result["watcher"]["pid"])
        for pid in pids:
            self.assert_not_running(pid)

    def test_success_preserves_oracle_and_input(self):
        case = self.case("success")
        original = copy.deepcopy(case)
        result = self.run_case(case)
        self.assertEqual(result["failures"], [], result)
        self.assertEqual(case, original)
        self.assertTrue(result["trace_summary"]["root_finished"])
        self.assertEqual(result["watcher"]["attempts"], [])

    def test_timeout_samples_owned_root_and_child_without_extending_case(self):
        result = self.run_case(self.case())
        self.assert_failed_and_clean(result)
        attempts = result["watcher"]["attempts"]
        self.assertEqual({item["role"] for item in attempts}, {"root", "child"}, result)
        for item in attempts:
            self.assertEqual(item["status"], "captured", result)
            self.assertIn(str(item["target_pid"]), Path(item["output"]).read_text())

    def test_slow_round_with_progress_does_not_look_like_a_stalled_operation(self):
        # Exercise the real watcher with a controlled clock and trace. A short
        # wall-clock subprocess deadline confounds scheduler delay with a
        # stalled operation, which is precisely what this test must distinguish.
        now = [1000000]
        rounds = [0]
        trace = self.output / "trace.jsonl"

        def emit(event):
            with trace.open("a") as stream:
                stream.write(json.dumps({"e": event, "p": 123, "t": now[0]}) + "\n")

        for event in ("start", "round+", "run+"):
            emit(event)

        def progress(_delay):
            now[0] += 50000
            rounds[0] += 1
            emit("run-")
            if rounds[0] == 20:
                emit("round-")
                emit("finish")
            else:
                emit("run+")

        config = self.output / "config.json"
        config.write_text(json.dumps(dict(directory=str(self.output),
            watch_deadline_us=20000000, parent_pid=os.getppid(),
            operation_threshold=0.1, total_threshold=10, sample_timeout=0.2)))
        with mock.patch.object(diagnostics, "monotonic_us", side_effect=lambda: now[0]), \
             mock.patch.object(diagnostics.time, "sleep", side_effect=progress), \
             mock.patch.object(diagnostics, "in_session", return_value=True), \
             mock.patch.object(diagnostics.os, "getpgrp", return_value=-1), \
             mock.patch.object(diagnostics, "sample_targets") as sample:
            self.assertEqual(diagnostics.watch(config), 0)
        sample.assert_not_called()
        self.assertEqual(rounds[0], 20)
        report = json.loads((self.output / "watcher.json").read_text())
        self.assertEqual(report["status"], "completed-before-sampling")

    def test_missing_sampler_retains_original_timeout(self):
        result = self.run_case(self.case(), sample=None)
        self.assert_failed_and_clean(result)
        self.assertTrue(result["watcher"]["attempts"], result)
        self.assertTrue(all(item["status"] == "unavailable"
                            for item in result["watcher"]["attempts"]), result)

    def test_hung_sampler_and_its_descendants_are_stopped(self):
        result = self.run_case(self.case(), sample="hang")
        self.assert_failed_and_clean(result)
        self.assertTrue(all(item["status"] == "timeout"
                            for item in result["watcher"]["attempts"]), result)
        markers = list(Path(result["artifacts"]["directory"]).glob("*.pids.json"))
        self.assertEqual(len(markers), 2, result)
        for marker in markers:
            for pid in json.loads(marker.read_text()):
                self.assert_not_running(pid)

    def test_sampler_disk_and_console_output_are_bounded(self):
        result = self.run_case(self.case(), sample="oversize")
        self.assert_failed_and_clean(result)
        for item in result["watcher"]["attempts"]:
            self.assertEqual(item["status"], "truncated", result)
            self.assertLessEqual(item["output_bytes"] + item["console_bytes"], 4096)

    def test_outside_process_is_never_sampled_or_killed(self):
        unrelated = subprocess.Popen(["/bin/sleep", "30"], start_new_session=True)
        try:
            result = self.run_case(self.case("spoof", [str(unrelated.pid)]))
            self.assert_failed_and_clean(result)
            self.assertIsNone(unrelated.poll())
            self.assertEqual([item["role"] for item in result["watcher"]["attempts"]], ["root"])
        finally:
            unrelated.kill()
            unrelated.wait(timeout=1)

    def test_missing_trace_is_an_explicit_diagnostic_failure(self):
        result = self.run_case(self.case("missing"))
        self.assertEqual(result["case_failures"], [])
        self.assertTrue(result["diagnostic_failures"], result)
        self.assert_not_running(result["watcher"]["pid"])


if __name__ == "__main__":
    unittest.main()
