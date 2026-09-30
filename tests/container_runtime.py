#!/usr/bin/env python3
"""Exercise the shipped image through Docker, including its real entrypoint."""

import argparse
import json
import os
import pty
import select
import subprocess
import time
import unittest
import uuid


class RuntimeTests(unittest.TestCase):
    docker = "docker"
    image = "cshell:local"

    def setUp(self):
        self.name = "cshell-runtime-check-" + uuid.uuid4().hex
        self.flags = ["--name", self.name, "--network", "none", "--read-only",
                      "--tmpfs", "/tmp:rw,nosuid,nodev,size=16m,mode=1777",
                      "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                      "--memory", "1g", "--cpus", "2", "--pids-limit", "256"]
        self.addCleanup(self.cleanup_container)

    def cleanup_container(self):
        subprocess.run([self.docker, "rm", "-f", self.name],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=30, check=False)

    def run_shell(self, args=(), stdin=None):
        return subprocess.run([self.docker, "run", *self.flags, "-i", self.image, *args],
                              input=stdin, capture_output=True, text=True, timeout=30)

    def test_nonroot_and_runtime_contents(self):
        result = self.run_shell(["-c", "id -u; id -g; printf '%s\\n' \"$HOME\"; "
                                 "test -x /usr/local/bin/cshell && "
                                 "test ! -e /build && test ! -e /work/src && "
                                 "! command -v cc && ! command -v python3"])
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, "10001\n10001\n/home/cshell\n", ""))

    def test_command_pipeline_and_status(self):
        result = self.run_shell(["-c", "printf 'one\\ntwo\\n' | wc -l; exit 23"])
        self.assertEqual(result.returncode, 23)
        self.assertEqual(result.stdout.strip(), "2")
        self.assertEqual(result.stderr, "")

    def test_stdin_and_here_document(self):
        result = self.run_shell(stdin="cat <<END\nhello\nEND\nexit 7\n")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (7, "hello\n", ""))

    def test_script_arguments(self):
        result = self.run_shell(["-c", "cat > /tmp/check.sh; exec cshell /tmp/check.sh 'two words'"],
                                stdin='printf "%s\\n" "$1"\nexit 9\n')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (9, "two words\n", ""))

    def test_exec_status(self):
        result = self.run_shell(["-c", "exec /bin/sh -c 'exit 17'"])
        self.assertEqual((result.returncode, result.stdout, result.stderr), (17, "", ""))

    def test_eof_exits(self):
        result = self.run_shell(stdin="")
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_sigterm_stops_noninteractive_job_without_sigkill(self):
        child = subprocess.Popen([self.docker, "run", *self.flags, self.image, "-c",
                                  "sleep 300 & printf 'ready\\n'; wait"],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertTrue(select.select([child.stdout], [], [], 20)[0], "no readiness output")
            self.assertEqual(child.stdout.readline(), b"ready\n")
            subprocess.run([self.docker, "stop", "--time", "2", self.name],
                           check=True, capture_output=True, timeout=10)
            stdout, stderr = child.communicate(timeout=10)
            self.assertEqual((child.returncode, stdout, stderr), (143, b"", b""))
            state = subprocess.run([self.docker, "inspect", self.name], check=True,
                                   capture_output=True, text=True, timeout=10)
            state = json.loads(state.stdout)[0]["State"]
            self.assertEqual(state["ExitCode"], 143)
            self.assertFalse(state["OOMKilled"])
        finally:
            self.cleanup_container()
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_sigterm_reaches_children_and_preserves_trapped_status(self):
        script = ("trap 'wait; exit 42' TERM; "
                  "sh -c 'trap \"echo child-stopped; exit 0\" TERM; "
                  "printf \"ready\\n\"; sleep 300' & wait")
        child = subprocess.Popen([self.docker, "run", *self.flags, self.image, "-c", script],
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            self.assertTrue(select.select([child.stdout], [], [], 20)[0], "no child readiness")
            self.assertEqual(child.stdout.readline(), b"ready\n")
            subprocess.run([self.docker, "stop", "--time", "2", self.name],
                           check=True, capture_output=True, timeout=10)
            stdout, _ = child.communicate(timeout=10)
            self.assertEqual(child.returncode, 42)
            self.assertIn(b"child-stopped", stdout)
        finally:
            self.cleanup_container()
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)

    def test_interactive_terminal(self):
        master, slave = pty.openpty()
        child = subprocess.Popen([self.docker, "run", *self.flags, "-it", self.image],
                                 stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        output = bytearray()

        def receive(marker):
            deadline = time.monotonic() + 20
            while marker not in output:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([master], [], [], remaining)[0]:
                    self.fail(f"missing {marker!r}: {bytes(output)!r}")
                output.extend(os.read(master, 65536))

        try:
            receive(b"$ ")
            output.clear()
            os.write(master, b"printf 'terminal-ok\\n'\n")
            receive(b"terminal-ok\r\n$ ")
            os.write(master, b"exit 11\n")
            self.assertEqual(child.wait(timeout=20), 11)
        finally:
            self.cleanup_container()
            if child.poll() is None:
                child.kill()
            child.wait(timeout=10)
            os.close(master)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default="docker")
    parser.add_argument("--image", default="cshell:local")
    args = parser.parse_args()
    RuntimeTests.docker = args.docker
    RuntimeTests.image = args.image
    unittest.main(argv=[__file__], verbosity=2)
