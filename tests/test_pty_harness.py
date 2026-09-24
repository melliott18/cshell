#!/usr/bin/env python3
"""Terminal runner self-tests, independent of cshell's job-control support."""

import copy
from contextlib import redirect_stdout
import errno
import io
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
import smoke


TESTS = Path(__file__).resolve().parent
RUNNER = TESTS / "smoke.py"
CANDIDATE = TESTS / "helpers" / "pty_candidate.py"


def case(mode="exit", *, output="finished\n", status=0, steps=None, args=(), **changes):
    value = {
        "name": "terminal self test",
        "transport": "pty",
        "args": [str(CANDIDATE), mode, *map(str, args)],
        "steps": [] if steps is None else steps,
        "expect": {"output": output, "status": status},
    }
    value.update(changes)
    return value


@unittest.skipUnless(sys.platform == "darwin" or sys.platform.startswith("linux"),
                     "PTY harness supports native macOS and Linux")
class PtyHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            master, slave = pty_harness.open_terminal()
        except pty_harness.PtyUnavailable as error:
            raise unittest.SkipTest(str(error)) from error
        os.close(master)
        os.close(slave)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cshell-pty-test-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def run_suite(self, cases, *, extra=(), env=None):
        fixture = self.directory / "suite.json"
        fixture.write_text(json.dumps({"version": 1, "name": "PTY runner test",
                                       "kind": "self", "cases": cases}))
        return subprocess.run(
            [sys.executable, str(RUNNER), sys.executable, "--suite", str(fixture), *extra],
            cwd=self.directory, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=10, check=False)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout)

    def assert_failure(self, result, *details):
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("Traceback", result.stdout)
        for detail in details:
            self.assertIn(detail.lower(), result.stdout.lower(), result.stdout)

    def process_marker(self):
        marker = self.directory / "processes.json"
        self.addCleanup(self.kill_recorded_processes, marker)
        return marker

    def kill_recorded_processes(self, marker):
        if marker.exists():
            for pid in json.loads(marker.read_text()).values():
                if pid is not None:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def assert_recorded_processes_stopped(self, marker):
        self.assertTrue(marker.exists(), "candidate did not reach process setup")
        for pid in json.loads(marker.read_text()).values():
            if pid is None:
                continue
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if sys.platform.startswith("linux"):
                    try:
                        raw = Path(f"/proc/{pid}/stat").read_text()
                        state = raw.rsplit(")", 1)[1].strip().split()[0]
                    except FileNotFoundError:
                        state = ""
                else:
                    result = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "stat="], stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, text=True, check=False, timeout=2)
                    state = result.stdout.strip()
                # An orphan zombie in a minimal container cannot retain the PTY
                # or run code, even if its init has not reaped it yet.
                if not state or state.startswith("Z"):
                    break
                time.sleep(0.02)
            else:
                self.fail(f"candidate process {pid} is still running ({state})")

    def test_candidate_owns_a_controlling_terminal_with_fixed_attributes(self):
        expected = {
            "canonical": True, "controlling": True, "echo": False,
            "foreground": True, "output_postprocessed": False,
            "session_leader": True, "signals": True, "size": [24, 80],
            "stdio_ttys": True,
        }
        self.assert_success(self.run_suite([
            case("terminal", output=json.dumps(expected, sort_keys=True) + "\n")]))

    def test_prompt_input_merged_output_status_and_files(self):
        item = case("exchange", args=(7,), status=7, setup={"seed.txt": "seed:"},
                    steps=[{"expect": "ready> "}, {"foreground": "leader"},
                           {"send": "hello λ\n"}, {"expect": "stdout:hello λ\n"},
                           {"expect": "stderr:hello λ\n"}],
                    output="ready> stdout:hello λ\nstderr:hello λ\n")
        item["expect"]["files"] = {"result.txt": {"type": "file", "content": "seed:hello λ\n"}}
        self.assert_success(self.run_suite([item]))

    def test_terminal_control_characters_deliver_interrupt_quit_and_eof(self):
        item = case("signals", output="signals ready\ninterrupt\nquit\neof\n", steps=[
            {"expect": "signals ready\n"}, {"control": "C"},
            {"expect": "interrupt\n"}, {"control": "\\"},
            {"expect": "quit\n"}, {"control": "D"}, {"expect": "eof\n"}])
        self.assert_success(self.run_suite([item]))

    def test_foreground_child_stops_continues_and_returns_terminal(self):
        marker = self.process_marker()
        item = case("job-control", args=(marker,),
                    output="child ready\nchild stopped\ncontinued\nleader restored\n",
                    steps=[{"expect": "child ready\n"}, {"foreground": "other"},
                           {"control": "Z"}, {"expect": "child stopped\n"},
                           {"foreground": "other"}, {"signal": "CONT"},
                           {"expect": "continued\n"}, {"send": "exit\n"},
                           {"expect": "leader restored\n"}, {"foreground": "leader"},
                           {"send": "exit\n"}])
        self.assert_success(self.run_suite([item]))
        self.assert_recorded_processes_stopped(marker)

    def test_signal_action_targets_terminal_foreground_group(self):
        item = case("signals", output="signals ready\ninterrupt\neof\n", steps=[
            {"expect": "signals ready\n"}, {"signal": "INT"},
            {"expect": "interrupt\n"}, {"control": "D"}, {"expect": "eof\n"}])
        self.assert_success(self.run_suite([item]))

    def test_signal_reaches_foreground_group_after_its_leader_is_reaped(self):
        marker = self.process_marker()
        item = case("leaderless-group", args=(marker,),
                    output="group ready\nmember terminated\n", steps=[
                        {"expect": "group ready\n"}, {"foreground": "other"},
                        {"signal": "TERM"}, {"expect": "member terminated\n"}])
        self.assert_success(self.run_suite([item]))
        self.assert_recorded_processes_stopped(marker)

    def test_environment_and_resource_limits_match_pipe_transport(self):
        expected = {"allocator_setting": True, "locale": True,
                    "override": True, "host_isolated": True,
                    "home_isolated": True, "temporary_isolated": True}
        environment = case("environment", name="environment", env={"CSHELL_FIXTURE_VALUE": "fixture value"},
                           output=json.dumps(expected, sort_keys=True) + "\n")
        limits = case("limits", name="limits", output=json.dumps(
            {"core": True, "cpu": True, "file": True, "descriptors": True}, sort_keys=True) + "\n")
        self.assert_success(self.run_suite([environment, limits],
                            env=dict(os.environ, CSHELL_HOST_SECRET="must not leak",
                                     MallocNanoZone="0")))

    def test_hang_timeout_is_bounded_and_cleans_leader(self):
        marker = self.process_marker()
        item = case("hang", args=(marker,), output="hanging\n", timeout=5,
                    steps=[{"expect": "hanging\n"}, {"expect": "never emitted"}])
        started = time.monotonic()
        result = self.run_suite([item], extra=("--timeout", "0.3"))
        self.assert_failure(result, "terminal self test", "time", "never emitted")
        self.assertLess(time.monotonic() - started, 3, result.stdout)
        self.assert_recorded_processes_stopped(marker)

    def test_large_send_to_nonreading_candidate_does_not_escape_timeout(self):
        marker = self.process_marker()
        item = case("hang", args=(marker,), output="hanging\n", timeout=0.3,
                    steps=[{"expect": "hanging\n"}, {"send": "x" * 200000}])
        started = time.monotonic()
        result = self.run_suite([item])
        self.assert_failure(result, "time")
        self.assertLess(time.monotonic() - started, 3, result.stdout)
        self.assert_recorded_processes_stopped(marker)

    def test_steps_share_one_deadline(self):
        item = case("paced", output="tick\n" * 8, timeout=0.35,
                    steps=[{"expect": "tick\n"}] * 8)
        self.assert_failure(self.run_suite([item]), "time")

    def test_terminal_eof_does_not_hide_a_running_candidate(self):
        marker = self.process_marker()
        item = case("close-terminal", args=(marker,), output="closing\n", timeout=0.3,
                    steps=[{"expect": "closing\n"}])
        self.assert_failure(self.run_suite([item]), "time")
        self.assert_recorded_processes_stopped(marker)

    def test_timeout_cleans_background_group_ignoring_hup_and_term(self):
        marker = self.process_marker()
        item = case("fork-hang", args=(marker,), output="background ready\n", timeout=0.3,
                    steps=[{"expect": "background ready\n"}])
        self.assert_failure(self.run_suite([item]), "time")
        self.assert_recorded_processes_stopped(marker)

    def test_timeout_cleans_stopped_foreground_job_and_waiting_leader(self):
        marker = self.process_marker()
        item = case("job-control", args=(marker,), timeout=0.4,
                    output="child ready\nchild stopped\n", steps=[
                        {"expect": "child ready\n"}, {"control": "Z"},
                        {"expect": "child stopped\n"}])
        self.assert_failure(self.run_suite([item]), "time")
        self.assert_recorded_processes_stopped(marker)

    def test_successful_leader_exit_cleans_background_group(self):
        marker = self.process_marker()
        item = case("fork-exit", args=(marker,), output="background ready\n", timeout=1,
                    steps=[{"expect": "background ready\n"}, {"send": "exit\n"}])
        started = time.monotonic()
        result = self.run_suite([item])
        self.assert_success(result)
        self.assertLess(time.monotonic() - started, 3, result.stdout)
        self.assert_recorded_processes_stopped(marker)

    def test_output_flood_is_bounded_and_cleans_processes(self):
        marker = self.process_marker()
        item = case("flood", args=(marker,), output="", output_limit=1000000)
        started = time.monotonic()
        result = self.run_suite([item], extra=("--output-limit", "4096"))
        self.assert_failure(result, "output", "limit")
        self.assertLess(time.monotonic() - started, 3, result.stdout)
        self.assertLess(len(result.stdout), 20000, "diagnostics must truncate output")
        self.assert_recorded_processes_stopped(marker)

    def test_expected_output_and_status_mismatches_are_actionable(self):
        for item, detail in ((case(output="wrong output"), "output"),
                             (case(status=7), "status")):
            with self.subTest(detail=detail):
                self.assert_failure(self.run_suite([item]), "terminal self test", detail)

    def test_foreground_mismatch_is_reported_and_cleans_leader(self):
        marker = self.process_marker()
        item = case("hang", args=(marker,), output="hanging\n", steps=[
            {"expect": "hanging\n"}, {"foreground": "other"}])
        self.assert_failure(self.run_suite([item]), "foreground")
        self.assert_recorded_processes_stopped(marker)

    def test_expect_cursor_does_not_reuse_an_earlier_match(self):
        item = case(steps=[{"expect": "finished"}, {"expect": "finished"}])
        self.assert_failure(self.run_suite([item]), "finished")

    def test_exit_before_remaining_steps_is_not_a_false_success(self):
        item = case(steps=[{"expect": "never emitted"}, {"send": "unused\n"}])
        started = time.monotonic()
        result = self.run_suite([item])
        self.assert_failure(result, "never emitted")
        self.assertLess(time.monotonic() - started, 3, result.stdout)

    def test_temporary_directory_removed_after_success_and_failure(self):
        for status in (0, 7):
            with self.subTest(status=status):
                marker = self.directory / f"cwd-{status}"
                result = self.run_suite([case("record-cwd", args=(marker, status), output="")])
                if status == 0:
                    self.assert_success(result)
                else:
                    self.assert_failure(result, "status")
                self.assertFalse(Path(marker.read_text()).exists())

    @staticmethod
    def open_descriptors():
        # listdir's own descriptor is closed before fstat. /dev/fd is available
        # on both supported native platforms and the Linux Docker image.
        descriptors = set()
        for name in os.listdir("/dev/fd"):
            try:
                os.fstat(int(name))
                descriptors.add(int(name))
            except OSError:
                pass
        return descriptors

    def test_terminal_descriptors_closed_after_success_and_failures(self):
        initial = self.open_descriptors()
        items = [case(), case(output="wrong"),
                 case("hang", output="hanging\n", timeout=0.15),
                 case("flood", output="", output_limit=1024),
                 case(steps=[{"expect": "absent"}])]
        for item in items:
            with self.subTest(mode=item["args"][1], expectation=item["expect"]):
                smoke.run_case(Path(sys.executable), item, 2, 65536)
                self.assertEqual(self.open_descriptors(), initial)

    def test_terminal_descriptors_closed_after_launch_and_configuration_errors(self):
        initial = self.open_descriptors()
        for contents, expected_errno in (("invalid executable format\n", errno.ENOEXEC),
                                          ("#!/nonexistent/cshell-test-interpreter\n", errno.ENOENT)):
            with self.subTest(contents=contents):
                executable = self.directory / "broken-candidate"
                executable.write_text(contents)
                executable.chmod(0o700)
                with self.assertRaises(OSError) as raised:
                    smoke.run_case(executable, case(), 1, 65536)
                self.assertEqual(raised.exception.errno, expected_errno)
                self.assertEqual(self.open_descriptors(), initial)
        with mock.patch.object(pty_harness.termios, "tcsetattr",
                               side_effect=pty_harness.termios.error(errno.EIO, "injected terminal failure")):
            with self.assertRaisesRegex(OSError, "injected terminal failure"):
                smoke.run_case(Path(sys.executable), case(), 1, 65536)
        self.assertEqual(self.open_descriptors(), initial)

    def test_teardown_failure_cannot_be_reported_as_success(self):
        cleanup = pty_harness.cleanup_session

        def fail_after_cleanup(*args, **kwargs):
            return cleanup(*args, **kwargs) + ["injected teardown failure"]

        initial = self.open_descriptors()
        with mock.patch.object(pty_harness, "cleanup_session", side_effect=fail_after_cleanup):
            failures = smoke.run_case(Path(sys.executable), case(), 1, 65536)
        self.assertIn("injected teardown failure", failures)
        self.assertEqual(self.open_descriptors(), initial)

    def test_snapshot_failure_reports_teardown_error_and_reaps_leader(self):
        marker = self.process_marker()
        item = case("hang", args=(marker,), output="hanging\n", timeout=0.15)
        initial = self.open_descriptors()
        with mock.patch.object(pty_harness, "session_members",
                               side_effect=OSError("injected snapshot failure")):
            failures = smoke.run_case(Path(sys.executable), item, 1, 65536)
        self.assertTrue(any("cleanup" in failure and "injected snapshot failure" in failure
                            for failure in failures), failures)
        self.assert_recorded_processes_stopped(marker)
        self.assertEqual(self.open_descriptors(), initial)

    def test_controlling_terminal_unavailable_cannot_hide_teardown_failure(self):
        ioctl = pty_harness.fcntl.ioctl

        def unavailable_controlling_terminal(descriptor, operation, *args):
            if operation == pty_harness.termios.TIOCSCTTY:
                raise OSError(errno.EPERM, "injected controlling terminal unavailable")
            return ioctl(descriptor, operation, *args)

        initial = self.open_descriptors()
        with mock.patch.object(pty_harness.fcntl, "ioctl", side_effect=unavailable_controlling_terminal), \
                mock.patch.object(pty_harness, "session_members",
                                  side_effect=OSError("injected snapshot failure")):
            # A capability-only failure raises PtyUnavailable. A simultaneous
            # cleanup failure must instead remain an ordinary failed case.
            failures = smoke.run_case(Path(sys.executable), case(), 1, 65536)
        self.assertTrue(any("cleanup" in failure and "injected snapshot failure" in failure
                            for failure in failures), failures)
        self.assertEqual(self.open_descriptors(), initial)

    def test_unavailable_terminal_is_a_scoped_skip(self):
        pipe = {"name": "pipe still runs", "stdin": "",
                "args": [str(CANDIDATE), "exit"],
                "expect": {"stdout": "finished\n", "stderr": "", "status": 0}}
        for cases, status in (([case(), pipe], 0), ([case()], 1)):
            with self.subTest(cases=len(cases)):
                fixture = self.directory / "capability.json"
                fixture.write_text(json.dumps({"version": 1, "name": "capability test",
                                               "kind": "self", "cases": cases}))
                output = io.StringIO()
                with mock.patch.object(pty_harness, "open_terminal", side_effect=
                                       pty_harness.PtyUnavailable("injected terminal unavailable")), \
                        mock.patch.object(sys, "argv", [str(RUNNER), sys.executable,
                                                        "--suite", str(fixture)]), \
                        redirect_stdout(output):
                    self.assertEqual(smoke.main(), status)
                self.assertIn("SKIP: terminal self test: injected terminal unavailable", output.getvalue())
                if status == 0:
                    self.assertIn("PASS: pipe still runs", output.getvalue())
                else:
                    self.assertIn("no cases ran", output.getvalue())

    def test_invalid_pty_schema_has_scoped_errors(self):
        malformed = [
            {"transport": "unknown"}, {"stdin": ""}, {"steps": "send exit"},
            {"steps": [{}]}, {"steps": [{"unknown": "x"}]},
            {"steps": [{"send": "x", "expect": "x"}]},
            {"steps": [{"send": 3}]}, {"steps": [{"expect": 3}]},
            {"steps": [{"control": "X"}]}, {"steps": [{"signal": "UNKNOWN"}]},
            {"steps": [{"foreground": "unknown"}]},
            {"expect": {"stdout": "", "stderr": "", "status": 0}},
            {"expect": {"output": 3, "status": 0}},
        ]
        for changes in malformed:
            with self.subTest(changes=changes):
                item = case(**changes)
                self.assert_failure(self.run_suite([item]))
        missing_steps = copy.deepcopy(case())
        del missing_steps["steps"]
        self.assert_failure(self.run_suite([missing_steps]), "steps")


if __name__ == "__main__":
    unittest.main(verbosity=2)
