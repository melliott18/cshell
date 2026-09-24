#!/usr/bin/env python3
"""Materialize shared cases for smoke.py; all execution uses its bounded runner.

Absolute helper paths and host errno text are resolved here, so the identical
source fixtures work in native macOS and Linux/Docker builds.
"""
import argparse
import errno
import json
import os
from pathlib import Path
import shlex
import signal


def cases(helper):
    result = []

    def cross(name, script, status=0, stdout="", stderr="", *, setup=None,
              files=None):
        for mode, source in (("string", "-c"), ("file", "script"), ("stdin", "stdin")):
            contents = dict(setup or {})
            args, stdin = [], ""
            if mode == "string":
                args = ["-c", script, "shell-name", "one", "two"]
            elif mode == "file":
                contents["script"] = script
                args = ["script", "one", "two"]
            else:
                stdin = script
            expect = {"stdout": stdout, "stderr": stderr.replace("@SOURCE@", source),
                      "status": status}
            if files:
                expect["files"] = files
            result.append({"name": f"{name} ({mode})", "args": args, "stdin": stdin,
                           "setup": contents, "expect": expect})

    cross("empty input", "")
    cross("blank and comment input", "\n# comment\n\n")
    cross("successful output", f"{helper} both\n", stdout="out\n", stderr="err\n")
    cross("literal quoting", f"{helper} args '' 'two words' '$literal' \\*\n",
          stdout="[]\n[two words]\n[$literal]\n[*]\n")
    cross("nonzero completion", f"{helper} status 37\n", status=37)
    cross("nonzero final unterminated line", f"{helper} status 37", status=37)
    cross("successful final unterminated line", f"{helper} args final", stdout="[final]\n")
    cross("failure followed by blank lines", f"{helper} status 37\n\n# keep status\n", status=37)
    cross("failure followed by success", f"{helper} status 37\n{helper} args once\n",
          stdout="[once]\n")
    missing = "cshell: no-such-cshell-command: command not found\n"
    cross("unknown command", "no-such-cshell-command\n", status=127, stderr=missing)
    cross("unknown command then exit", "no-such-cshell-command\nexit\n", status=127, stderr=missing)
    cross("unknown command parent continues", f"no-such-cshell-command\n{helper} args once\n",
          stdout="[once]\n", stderr=missing)
    cross("found but unexecutable", "./denied\n", status=126,
          setup={"denied": "exit 0\n"},
          stderr=f"cshell: ./denied: cannot execute: {os.strerror(errno.EACCES)}\n")
    for suffix in ("", "exit\n", "\n# keep status\n"):
        cross(f"signal retained {suffix!r}", f"{helper} signal\n{suffix}",
              status=128 + signal.SIGTERM)
    cross("signal parent continues", f"{helper} signal\n{helper} args once\n",
          stdout="[once]\n")
    cross("exit initially", "exit\n", status=0)
    cross("exit preserves last status", f"{helper} status 37\nexit\n{helper} args never\n", status=37)
    cross("exit end options preserves status", f"{helper} status 37\nexit --\n", status=37)
    for operand, status in (("0", 0), ("42", 42), ("255", 255), ("256", 0),
                            ("-1", 255), ("+7", 7), ("-- 19", 19), ("0009", 9)):
        cross(f"exit numeric {operand}", f"exit {operand}\n{helper} args never\n", status=status)
    for operand in ("bad", "''", "' 1'", "'1 '", "+", "-", "1x", "1.5",
                    "999999999999999999999999999999999", "-- bad", "1 2", "bad 2"):
        message = "too many arguments" if operand in ("1 2", "bad 2") else "numeric status required"
        cross(f"exit invalid {operand}", f"exit {operand}\n{helper} args never\n", status=2,
              stderr=f"cshell: exit: {message}\n")
        # -i string/file contexts avoid prompts; real terminal cases below also
        # assert continuation and no-operand exit after the error.
        for mode in ("string", "file"):
            script = f"exit {operand}\n{helper} args continued\nexit 9\n"
            result.append({"name": f"interactive exit invalid {operand} ({mode})",
                           "args": ["-ic", script] if mode == "string" else ["-i", "script"],
                           "setup": {"script": script} if mode == "file" else {}, "stdin": "",
                           "expect": {"stdout": "[continued]\n", "stderr": f"cshell: exit: {message}\n",
                                      "status": 9}})
    cross("pipeline output", f"{helper} args pipeline | {helper} copy\n",
          stdout="[pipeline]\n")
    cross("high volume pipeline",
          f"{helper} generate 8388608 | {helper} copy | {helper} copy | {helper} count\n",
          stdout="8388608\n")
    cross("pipeline failed child is reaped",
          f"no-such-cshell-stage | {helper} count\n{helper} args alive\n",
          stdout="0\n[alive]\n", stderr="cshell: no-such-cshell-stage: command not found\n")
    cross("pipeline expansion rejected before any stage executes",
          f"{helper} args never >effect | {helper} args $HOME\n",
          status=2, stderr="cshell: expansion is not supported by literal execution\n",
          files={"effect": {"type": "absent"}})
    cross("pipeline uses final status", f"{helper} status 7 | {helper} status 0\n")
    cross("pipeline final failure", f"{helper} status 0 | {helper} status 9\n", status=9)
    cross("negated pipeline", f"! {helper} status 0 | {helper} status 9\n")
    cross("pipeline builtin state is isolated",
          f"cd nested | {helper} copy\n{helper} args parent >proof\n",
          setup={"nested/seed": ""},
          files={"proof": {"type": "file", "content": "[parent]\n"}})
    cross("external prefix assignment", f"CSHELL_RUNTIME_VALUE=stage {helper} environment CSHELL_RUNTIME_VALUE\n",
          stdout="CSHELL_RUNTIME_VALUE=stage\n")
    cross("special builtin assignment persists",
          f"CSHELL_RUNTIME_VALUE=stage export CSHELL_RUNTIME_VALUE\n{helper} environment CSHELL_RUNTIME_VALUE\n",
          stdout="CSHELL_RUNTIME_VALUE=stage\n")
    cross("pipeline builtin assignment is isolated",
          f"export CSHELL_RUNTIME_PIPE=value | {helper} copy\n{helper} environment CSHELL_RUNTIME_PIPE\n",
          stdout="CSHELL_RUNTIME_PIPE=<unset>\n")
    cross("special builtin error stops script", f"export 1bad\n{helper} args never\n",
          status=1, stderr="cshell: export: invalid operand\n")
    cross("pipeline special builtin error is isolated",
          f"export 1bad | {helper} copy\n{helper} args alive\n",
          stdout="[alive]\n", stderr="cshell: export: invalid operand\n")
    for mode in ("string", "file"):
        script = f"export 1bad\n{helper} args continued\nexit\n"
        result.append({"name": f"interactive special builtin error ({mode})",
                       "args": ["-ic", script] if mode == "string" else ["-i", "script"],
                       "setup": {"script": script} if mode == "file" else {}, "stdin": "",
                       "expect": {"stdout": "[continued]\n",
                                  "stderr": "cshell: export: invalid operand\n",
                                  "status": 0}})
    absent = {"effect": {"type": "absent"}}
    for syntax in (f"{helper} args a && {helper} args b",
                   f"{helper} args a || {helper} args b", f"{helper} args a; {helper} args b",
                   f"{helper} args a &", f"({helper} args compound)",
                   f"{{ {helper} args compound; }}", "if true; then true; fi", "f() { true; }"):
        cross(f"unsupported construct {syntax}", f"{syntax} >effect\n{helper} args never\n", status=2,
              stderr="cshell: only a foreground simple command or pipeline is supported\n", files=absent)
    for word in ("$HOME", "$((1+2))", "*", "~", "$(>nested)", "`>nested`"):
        message = ("command substitution is not supported by literal execution"
                   if word.startswith("$(>") else "expansion is not supported by literal execution")
        cross(f"unsupported expansion {word}", f"{helper} args >effect {word}\n", status=2,
              stderr=f"cshell: {message}\n", files={**absent, "nested": {"type": "absent"}})
    cross("ordered redirections", f"{helper} both >captured 2>&1\n{helper} args restored\n",
          stdout="[restored]\n", files={"captured": {"type": "file", "content": "out\nerr\n"}})
    cross("parent redirection restoration", f"cd . >captured\n{helper} both\n",
          stdout="out\n", stderr="err\n", files={"captured": {"type": "file", "content": ""}})
    cross("exit after restoring redirection", "exit 23 >captured\n", status=23,
          files={"captured": {"type": "file", "content": ""}})
    cross("parent cd persists", f"cd nested\n{helper} args here >proof\n",
          setup={"nested/seed": ""}, files={"nested/proof": {"type": "file", "content": "[here]\n"}})
    cross("quoted heredoc and following command", f"{helper} copy <<'END'\n$literal\nEND\n{helper} args after\n",
          stdout="$literal\n[after]\n")
    cross("multiline literal", f"{helper} args 'first\nsecond'\n", stdout="[first\nsecond]\n")
    cross("environment imported", f"{helper} environment LC_ALL\n", stdout="LC_ALL=C\n")
    cross("syntax error prevents execution", ")\n", status=2,
          stderr="cshell: @SOURCE@: 1:1: expected command\n")
    cross("incomplete final quote", 'echo "', status=2,
          stderr="cshell: @SOURCE@: 1:6: unterminated double quote\n")
    cross("complete command before rejection", f"{helper} args first\n{helper} args $HOME\n",
          status=2, stdout="[first]\n", stderr="cshell: expansion is not supported by literal execution\n")
    redirection_error = f"cannot apply redirection: {os.strerror(errno.ENOENT)}\n"
    cross("exit redirection failure stops script", f"exit >missing/path\n{helper} args never\n",
          status=1, stderr="cshell: " + redirection_error)
    cross("regular builtin redirection failure continues", f"cd . >missing/path\n{helper} args once\n",
          stdout="[once]\n", stderr="cshell: " + redirection_error)
    cross("external redirection failure continues", f"{helper} args never >missing/path\n{helper} args once\n",
          stdout="[once]\n", stderr=f"cshell: {shlex.split(helper)[0]}: " + redirection_error)
    # A command reading shared stdin must receive the bytes after its own line.
    result.append({"name": "stdin has no command read-ahead", "stdin": f"{helper} copy\npayload\n",
                   "expect": {"stdout": "payload\n", "stderr": "", "status": 0}})
    for mode in ("string", "file"):
        script = f"{helper} copy\n{helper} args after\n"
        result.append({"name": f"command stdin independent of {mode} source", "stdin": "payload\n",
                       "args": ["-c", script] if mode == "string" else ["script"],
                       "setup": {"script": script} if mode == "file" else {},
                       "expect": {"stdout": "payload\n[after]\n", "stderr": "", "status": 0}})
    for name, args, message, status in (
        ("missing command operand", ["-c"], "-c requires a command string", 2),
        ("unsupported option", ["-x"], "-x: unsupported shell option", 2),
        ("conflicting modes", ["-cs"], "-cs: -c and -s cannot be combined", 2),
        ("missing script", ["missing"], f"missing: 1:1: cannot open script: {os.strerror(errno.ENOENT)}", 127),
        ("directory script", ["."], f".: 1:1: script is a directory: {os.strerror(errno.EISDIR)}", 1),
    ):
        result.append({"name": name, "args": args, "stdin": "",
                       "expect": {"stdout": "", "stderr": f"cshell: {message}\n", "status": status}})
    result.append({"name": "explicit stdin mode operands", "args": ["-s", "one", "two"],
                   "stdin": "exit 17", "expect": {"stdout": "", "stderr": "", "status": 17}})
    result.append({"name": "dash leading script", "args": ["--", "-script"], "stdin": "",
                   "setup": {"-script": "exit 17"},
                   "expect": {"stdout": "", "stderr": "", "status": 17}})
    return result


def terminal_cases(helper):
    result = []

    def terminal(name, steps, output, status):
        result.append({"name": name, "transport": "pty", "steps": steps,
                       "expect": {"output": output, "status": status}})

    terminal("terminal exit status", [{"expect": "$ "}, {"foreground": "leader"}, {"send": "exit 23\n"}], "$ ", 23)
    terminal("terminal EOF initially", [{"expect": "$ "}, {"control": "D"}], "$ ", 0)
    for operand, message in (("bad", "numeric status required"), ("1 2", "too many arguments")):
        diagnostic = f"cshell: exit: {message}\n"
        terminal(f"terminal invalid exit {operand}",
                 [{"expect": "$ "}, {"send": f"exit {operand}\n"},
                  {"expect": diagnostic + "$ "}, {"send": "exit\n"}], "$ " + diagnostic + "$ ", 2)
    terminal("terminal failure then EOF", [{"expect": "$ "}, {"send": f"{helper} status 37\n"},
             {"expect": "$ "}, {"control": "D"}], "$ $ ", 37)
    diagnostic = f"cshell: cannot apply redirection: {os.strerror(errno.ENOENT)}\n"
    terminal("terminal exit redirection error continues", [{"expect": "$ "},
             {"send": "exit >missing/path\n"}, {"expect": diagnostic + "$ "}, {"send": "exit\n"}],
             "$ " + diagnostic + "$ ", 1)
    terminal("terminal signal parent continues", [{"expect": "$ "}, {"send": f"{helper} signal\n"},
             {"expect": "$ "}, {"send": "exit\n"}], "$ $ ", 128 + signal.SIGTERM)
    terminal("terminal multiline and blank prompts", [{"expect": "$ "}, {"send": "\n"},
             {"expect": "$ "}, {"send": "# comment\n"}, {"expect": "$ "},
             {"send": f"{helper} args 'first\n"}, {"expect": "> "}, {"send": "second'\n"},
             {"expect": "[first\nsecond]\n$ "}, {"send": "exit\n"}],
             "$ $ $ > [first\nsecond]\n$ ", 0)
    terminal("terminal heredoc prompts", [{"expect": "$ "}, {"send": f"{helper} copy <<'END'\n"},
             {"expect": "> "}, {"send": "body\n"}, {"expect": "> "}, {"send": "END\n"},
             {"expect": "body\n$ "}, {"send": "exit\n"}], "$ > > body\n$ ", 0)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    helper = shlex.quote(str(args.helper.resolve()))
    suite = {"version": 1, "name": "cshell runtime", "kind": "replacement",
             "cases": terminal_cases(helper) if args.output.name == "runtime-pty.json" else cases(helper)}
    args.output.write_text(json.dumps(suite, indent=2) + "\n")


if __name__ == "__main__":
    main()
