#!/usr/bin/env python3
"""CLI integration tests for the runner, independent of shell correctness."""

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


TESTS = Path(__file__).resolve().parent
RUNNER = TESTS / "smoke.py"
CANDIDATE = TESTS / "helpers" / "candidate.py"
FIXTURES = TESTS / "fixtures" / "self"


def case(name="self test", mode="echo", **changes):
    value = {
        "name": name,
        "stdin": "",
        "args": [mode],
        "expect": {"stdout": "", "stderr": "", "status": 0},
    }
    value.update(changes)
    return value


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cshell-runner-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def run_suite(self, cases=None, *, fixture=None, kind="self", extra=(), env=None,
                  document=None):
        if fixture is None:
            fixture = self.directory / "suite.json"
            if document is None:
                document = {"version": 1, "name": "runner test", "kind": kind,
                            "cases": cases}
            fixture.write_text(json.dumps(document))
        return subprocess.run(
            [sys.executable, str(RUNNER), str(CANDIDATE), "--suite", str(fixture),
             *extra],
            cwd=self.directory,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
            check=False,
        )

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout)

    def assert_failure(self, result, *details):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        for detail in details:
            self.assertIn(detail.lower(), result.stdout.lower(), result.stdout)

    def process_record(self, marker):
        self.assertTrue(marker.exists(), "candidate did not reach process setup")
        return json.loads(marker.read_text())

    def kill_recorded_group(self, marker):
        if marker.exists():
            record = json.loads(marker.read_text())
            try:
                os.killpg(record["parent"], signal.SIGKILL)
            except ProcessLookupError:
                pass

    def assert_not_running(self, pid):
        # On minimal container images an orphan can briefly remain a zombie
        # until PID 1 reaps it; a zombie cannot execute or retain open pipes.
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if sys.platform.startswith("linux"):
                try:
                    # /proc is available in the Docker test image; procps need
                    # not be installed only for this assertion.
                    status = Path(f"/proc/{pid}/stat").read_text()
                    state = status.rsplit(")", 1)[1].strip().split()[0]
                except FileNotFoundError:
                    state = ""
            else:
                result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, check=False, timeout=2)
                state = result.stdout.strip()
            if not state or state.startswith("Z"):
                return
            time.sleep(0.02)
        self.fail(f"candidate process {pid} is still running ({state})")

    def test_passing_fixtures_cover_streams_status_args_files_and_isolation(self):
        self.assert_success(self.run_suite(fixture=FIXTURES / "passing.json"))

    def test_intentional_failures_have_actionable_diagnostics(self):
        expectations = {
            "mismatched stdout": ("stdout", "actual stdout", "expected stdout"),
            "mismatched stderr": ("stderr", "actual stderr", "expected stderr"),
            "mismatched status": ("status", "7", "0"),
            "missing file": ("missing.txt",),
            "mismatched file content": ("result.txt", "actual contents", "expected contents"),
            "hanging candidate": ("time",),
            "excessive output": ("output", "limit"),
        }
        for name, details in expectations.items():
            with self.subTest(name=name):
                result = self.run_suite(fixture=FIXTURES / "failing.json",
                                        extra=("--case", name))
                self.assert_failure(result, name, *details)

    def test_environment_isolated_and_explicit_overrides_applied(self):
        expected = {"locale": True, "override": True, "host_isolated": True,
                    "home_isolated": True, "temporary_isolated": True}
        item = case(mode="environment", env={"CSHELL_FIXTURE_VALUE": "fixture value"})
        item["expect"]["stdout"] = json.dumps(expected, sort_keys=True) + "\n"
        parent_environment = dict(os.environ, CSHELL_HOST_SECRET="must not leak")
        self.assert_success(self.run_suite([item], env=parent_environment))

    def test_child_resource_limits_are_bounded(self):
        item = case(mode="limits")
        item["expect"]["stdout"] = json.dumps(
            {"core": True, "cpu": True, "file": True, "descriptors": True},
            sort_keys=True) + "\n"
        self.assert_success(self.run_suite([item]))

    def test_large_stdin_and_output_backpressure_do_not_deadlock(self):
        script = "input\n" * 33000
        item = case(mode="backpressure", stdin=script)
        item["expect"]["stdout"] = "prefix" * 22000 + script
        self.assert_success(self.run_suite([item], extra=("--output-limit", "524288")))

    def test_timeout_handles_candidate_that_does_not_read_large_stdin(self):
        marker = self.directory / "processes.json"
        self.addCleanup(self.kill_recorded_group, marker)
        item = case(mode="hang", args=["hang", str(marker)], stdin="x" * 200000,
                    timeout=5)
        started = time.monotonic()
        result = self.run_suite([item], extra=("--timeout", "0.3"))
        self.assert_failure(result, "self test", "time")
        self.assertLess(time.monotonic() - started, 3, result.stdout)
        self.assert_not_running(self.process_record(marker)["parent"])

    def test_timeout_kills_same_group_descendants(self):
        marker = self.directory / "processes.json"
        self.addCleanup(self.kill_recorded_group, marker)
        item = case(mode="fork-hang", args=["fork-hang", str(marker)], timeout=0.3)
        result = self.run_suite([item])
        self.assert_failure(result, "time")
        record = self.process_record(marker)
        self.assert_not_running(record["parent"])
        self.assert_not_running(record["child"])

    def test_cleanup_kills_descendant_after_successful_parent_exit(self):
        marker = self.directory / "processes.json"
        self.addCleanup(self.kill_recorded_group, marker)
        item = case(mode="fork-exit", args=["fork-exit", str(marker)], timeout=1)
        started = time.monotonic()
        self.assert_success(self.run_suite([item]))
        self.assertLess(time.monotonic() - started, 3)
        record = self.process_record(marker)
        self.assert_not_running(record["parent"])
        self.assert_not_running(record["child"])

    def test_output_flood_fails_promptly_with_bounded_diagnostics(self):
        marker = self.directory / "processes.json"
        self.addCleanup(self.kill_recorded_group, marker)
        item = case(mode="flood", args=["flood", str(marker)], output_limit=1000000)
        started = time.monotonic()
        result = self.run_suite([item], extra=("--output-limit", "4096"))
        self.assert_failure(result, "output", "limit")
        self.assertLess(time.monotonic() - started, 3, result.stdout)
        self.assertLess(len(result.stdout), 20000, "diagnostics must truncate captured output")
        self.assert_not_running(self.process_record(marker)["parent"])

    def test_output_limit_combines_stdout_and_stderr(self):
        item = case(stdin="a" * 3000, args=["echo", "b" * 3000])
        item["expect"].update(stdout="a" * 3000, stderr="b" * 3000)
        self.assert_failure(self.run_suite([item], extra=("--output-limit", "4096")),
                            "output", "limit")

    def test_temporary_directory_removed_after_success_and_failure(self):
        for status in (0, 7):
            with self.subTest(status=status):
                marker = self.directory / f"cwd-{status}"
                result = self.run_suite([case(args=["record-cwd", str(marker), str(status)])])
                if status == 0:
                    self.assert_success(result)
                else:
                    self.assert_failure(result, "status")
                self.assertFalse(Path(marker.read_text()).exists())

    def test_file_type_mismatches_are_reported(self):
        expectations = (
            {"type": "directory"},
            {"type": "absent"},
        )
        for expected in expectations:
            with self.subTest(expected=expected):
                item = case(args=["write", "result.txt", "content"])
                item["expect"]["files"] = {"result.txt": expected}
                self.assert_failure(self.run_suite([item]), "result.txt")

    def test_filesystem_assertions_do_not_follow_symlinks(self):
        outside = self.directory / "outside.txt"
        outside.write_text("outside content")
        item = case(args=["symlink", "result.txt", str(outside)])
        item["expect"]["files"] = {
            "result.txt": {"type": "file", "content": "outside content"}}
        self.assert_failure(self.run_suite([item]), "result.txt")

    def test_platform_skip_is_explicit_and_does_not_launch_candidate(self):
        other = "darwin" if sys.platform.startswith("linux") else "linux"
        item = case(mode="invalid-mode-must-not-run", platforms=[other],
                    skip_reason="requires the other supported platform")
        result = self.run_suite([item, case(name="supported")])
        self.assert_success(result)
        self.assertIn("skip", result.stdout.lower())
        self.assertIn(item["skip_reason"], result.stdout)

    def test_all_skipped_suite_fails_to_avoid_an_empty_success(self):
        other = "darwin" if sys.platform.startswith("linux") else "linux"
        item = case(platforms=[other], skip_reason="requires the other platform")
        self.assert_failure(self.run_suite([item]), "no cases ran")

    def test_prototype_prompt_allowance_requires_explicit_opt_in(self):
        item = case(mode="prompt", strip_prompt=True)
        item["expect"]["stdout"] = "hello\n"
        self.assert_success(self.run_suite([item], kind="prototype"))
        del item["strip_prompt"]
        self.assert_failure(self.run_suite([item], kind="prototype"), "stdout")

    def test_replacement_suite_cannot_tolerate_prototype_prompt(self):
        item = case(mode="prompt", strip_prompt=True)
        item["expect"]["stdout"] = "hello\n"
        self.assert_failure(self.run_suite([item], kind="replacement"), "strip_prompt")

    def test_case_filter_runs_only_named_case(self):
        items = [case(name="chosen"), case(name="not chosen", mode="hang")]
        result = self.run_suite(items, extra=("--case", "chosen"))
        self.assert_success(result)
        self.assertIn("chosen", result.stdout)
        self.assertNotIn("not chosen", result.stdout)

    def test_unknown_case_filter_fails(self):
        self.assert_failure(self.run_suite([case()], extra=("--case", "missing-case")),
                            "missing-case")

    def test_invalid_cli_limits_fail(self):
        for option, value in (("--timeout", "0"), ("--timeout", "nan"),
                              ("--timeout", "inf"), ("--output-limit", "0"),
                              ("--output-limit", "-1")):
            with self.subTest(option=option, value=value):
                self.assert_failure(self.run_suite([case()], extra=(option, value)), option)

    def test_invalid_fixture_documents_fail(self):
        base = {"version": 1, "name": "invalid test", "kind": "self", "cases": [case()]}
        documents = []
        for key, value in (("version", 2), ("kind", "unknown"), ("cases", [])):
            document = copy.deepcopy(base)
            document[key] = value
            documents.append((key, document))
        document = copy.deepcopy(base)
        document["cases"].append(case())
        documents.append(("duplicate", document))
        for key, value in (("typo", True), ("timeout", -1), ("timeout", 10**1000), ("output_limit", 0),
                           ("platforms", ["linux"]), ("args", "echo")):
            document = copy.deepcopy(base)
            document["cases"][0][key] = value
            documents.append((key, document))
        for description, document in documents:
            with self.subTest(description=description):
                result = self.run_suite(document=document)
                self.assert_failure(result)
                self.assertNotIn("Traceback", result.stdout)

    def test_fixture_paths_cannot_escape_or_replace_internal_directories(self):
        for path in ("../escape", "/absolute", ".home/overwrite", ".tmp/overwrite"):
            for field in ("setup", "files"):
                with self.subTest(path=path, field=field):
                    item = case()
                    if field == "setup":
                        item["setup"] = {path: "contents"}
                    else:
                        item["expect"]["files"] = {path: {"type": "absent"}}
                    self.assert_failure(self.run_suite([item]))

    def test_invalid_json_reports_source_path(self):
        fixture = self.directory / "broken.json"
        fixture.write_text("{ not JSON }")
        self.assert_failure(self.run_suite(fixture=fixture), "broken.json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
