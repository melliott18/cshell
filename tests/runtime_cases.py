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
from substitution_cases import add_cases
from control_flow_cases import add_control_cases
from evaluation_cases import add_evaluation_cases
from option_cases import add_option_cases, invocation_cases
from trap_cases import add_trap_cases
from syntax_cases import add_syntax_cases
from execution_cases import add_execution_cases, add_execution_errors


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

    add_syntax_cases(cross, helper)
    add_execution_cases(cross, helper)
    add_execution_errors(cross, result)
    add_option_cases(cross, helper)
    result.extend(invocation_cases())
    add_cases(cross, helper)
    add_evaluation_cases(cross, helper)
    add_trap_cases(cross, helper)
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
    cross("pipeline expands arguments in stage",
          f'{helper} args "$(printf pipeline)" | {helper} copy\n',
          stdout="[pipeline]\n")
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
    for name, script, stdout, stderr, status in (
        ("eval syntax recovery", "eval 'if'\necho after\n", "after\n", "cshell: unterminated command group\n", 0),
        ("dot missing recovery", ". ./missing\necho after\n", "after\n", "cshell: cannot find readable dot file\n", 0),
        ("exec failure recovery", "exec no-such-cshell-command\necho after\n", "after\n", "cshell: no-such-cshell-command: command not found\n", 0),
        ("dot positional error restoration", "set -- old; . ./sourced new; echo \"$1:$?\"\n", "old:2\n", "cshell: return: numeric status required\n", 0),
    ):
        result.append({"name": "evaluation: interactive " + name,
                       "args": ["-ic", script], "stdin": "", "setup": {"sourced": "return bad\n"},
                       "expect": {"stdout": stdout, "stderr": stderr, "status": status}})
    add_control_cases(cross, helper)
    cross("AND OR equal precedence", f"{helper} status 0 || {helper} args skipped && {helper} args yes\n",
          stdout="[yes]\n")
    cross("list final status", f"{helper} status 0; {helper} status 19\n", status=19)
    cross("brace state persists", f"{{ export CSH_GROUP=brace; }}; {helper} environment CSH_GROUP\n",
          stdout="CSH_GROUP=brace\n")
    cross("subshell state isolated", f"(export CSH_GROUP=child); {helper} environment CSH_GROUP\n",
          stdout="CSH_GROUP=<unset>\n")
    cross("subshell exit isolated", f"(exit 7); {helper} args alive\n", stdout="[alive]\n")
    cross("brace exit stops list", f"{{ exit 7; }}; {helper} args never\n", status=7)
    cross("compound pipeline", f"{{ {helper} args grouped; }} | ({helper} copy)\n",
          stdout="[grouped]\n")
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
    cross("complete command before rejection", f"{helper} args first\n{helper} args ${{missing:?stop}}\n",
          status=2, stdout="[first]\n", stderr="cshell: stop\n")
    redirection_error = f"cannot apply redirection: {os.strerror(errno.ENOENT)}\n"
    cross("exit redirection failure stops script", f"exit >missing/path\n{helper} args never\n",
          status=1, stderr="cshell: " + redirection_error)
    cross("regular builtin redirection failure continues", f"cd . >missing/path\n{helper} args once\n",
          stdout="[once]\n", stderr="cshell: " + redirection_error)
    cross("external redirection failure continues", f"{helper} args never >missing/path\n{helper} args once\n",
          stdout="[once]\n", stderr="cshell: " + redirection_error)
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
        ("unsupported option", ["-z"], "-z: unsupported shell option", 2),
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

    terminal("options: terminal ignoreeof", [
        {"expect": "$ "}, {"send": "set -o ignoreeof\n"}, {"expect": "$ "},
        {"control": "D"}, {"expect": "cshell: use exit to leave the shell\n$ "},
        {"send": "echo alive\n"}, {"expect": "alive\n$ "}, {"send": "exit 7\n"}],
        "$ $ cshell: use exit to leave the shell\n$ alive\n$ ", 7)
    terminal("options: terminal ignoreeof disable", [
        {"expect": "$ "}, {"send": "set +o ignoreeof\n"}, {"expect": "$ "}, {"control": "D"}], "$ $ ", 0)
    result[-1]["args"] = ["-o", "ignoreeof"]
    terminal("options: terminal invocation job defaults", [
        {"expect": "$ "}, {"send": 'echo "$-"\n'}, {"expect": "bi\n$ "},
        {"send": "set -m; echo \"$-\"\n"}, {"expect": "bmi\n$ "}, {"send": "exit\n"}],
        "$ bi\n$ bmi\n$ ", 0)
    result[-1]["args"] = ["+m", "-b"]
    terminal("options: terminal nounset recovery", [
        {"expect": "$ "}, {"send": 'set -u; echo "$csh_missing"\n'},
        {"expect": "cshell: csh_missing\n$ "}, {"send": "echo alive\n"},
        {"expect": "alive\n$ "}, {"send": "exit\n"}], "$ cshell: csh_missing\n$ alive\n$ ", 0)
    terminal("options: terminal noexec honored", [
        {"expect": "$ "}, {"send": "set -n\n"}, {"expect": "$ "},
        {"send": "echo never; set +n; exit 8\n"}, {"expect": "$ "}, {"control": "D"}], "$ $ $ ", 0)

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
    diagnostic = "cshell: required\n"
    terminal("terminal expansion error recovers", [
        {"expect": "$ "}, {"send": f'{helper} args "${{missing:?required}}" >effect\n'},
        {"expect": diagnostic + "$ "}, {"send": f'{helper} args "$?" "$(printf okay)"\n'},
        {"expect": "[2]\n[okay]\n$ "}, {"send": "exit\n"}],
        "$ " + diagnostic + "$ [2]\n[okay]\n$ ", 0)
    diagnostic = f"cshell: cannot apply redirection: {os.strerror(errno.EBADF)}\n"
    terminal("terminal function preserves private descriptors", [
        {"expect": "$ "}, {"send": "f() { :; } 10>/dev/null\n"},
        {"expect": "$ "}, {"send": "{ f; : <&11; }\n"},
        {"expect": diagnostic + "$ "}, {"send": "exit 0\n"}],
        "$ $ " + diagnostic + "$ ", 0)
    terminal("terminal control operand error recovers", [
        {"expect": "$ "}, {"send": "break 0\n"},
        {"expect": "cshell: break: positive loop count required\n$ "},
        {"send": "exit\n"}], "$ cshell: break: positive loop count required\n$ ", 2)
    terminal("terminal eval syntax error recovers", [
        {"expect": "$ "}, {"send": "eval 'if'\n"},
        {"expect": "cshell: unterminated command group\n$ "},
        {"send": "echo alive\n"}, {"expect": "alive\n$ "}, {"send": "exit\n"}],
        "$ cshell: unterminated command group\n$ alive\n$ ", 0)
    terminal("terminal read continuation prompt", [
        {"expect": "$ "}, {"send": "read value\n"}, {"send": "one\\\n"},
        {"expect": "> "}, {"send": "two\n"}, {"expect": "$ "},
        {"send": "echo \"$value\"\n"}, {"expect": "onetwo\n$ "}, {"send": "exit\n"}],
        "$ > $ onetwo\n$ ", 0)
    terminal("terminal command foreground interrupt", [
        {"expect": "$ "}, { "send": "command /bin/sh -c 'echo ready; exec sleep 20'\n"}, {"expect": "ready\n"},
        {"control": "C"}, {"expect": "$ "}, {"send": "echo \"$?\"\n"},
        {"expect": "130\n$ "}, {"send": "exit\n"}], "$ ready\n$ 130\n$ ", 0)
    terminal("traps: idle Ctrl-C resets prompt", [
        {"expect": "$ "}, {"control": "C"}, {"expect": "$ "},
        {"send": "echo \"$?\"\n"}, {"expect": "130\n$ "},
        {"send": "exit\n"}], "$ $ 130\n$ ", 0)
    terminal("traps: trapped idle Ctrl-C", [
        {"expect": "$ "}, {"send": "trap 'echo interrupted' INT\n"},
        {"expect": "$ "}, {"control": "C"},
        {"expect": "interrupted\n$ "}, {"send": "echo alive\n"},
        {"expect": "alive\n$ "}, {"send": "exit\n"}],
        "$ $ interrupted\n$ alive\n$ ", 0)
    terminal("traps: Ctrl-C discards continuation", [
        {"expect": "$ "}, {"send": "echo 'partial\n"}, {"expect": "> "},
        {"control": "C"}, {"expect": "$ "},
        {"send": "echo alive\n"}, {"expect": "alive\n$ "},
        {"send": "exit\n"}], "$ > $ alive\n$ ", 0)
    terminal("traps: interactive hangup exits", [
        {"expect": "$ "}, {"send": "trap 'echo exit-action' EXIT\n"},
        {"expect": "$ "}, {"send": "kill -HUP $$\n"}],
        "$ $ exit-action\n", 128 + signal.SIGHUP)
    terminal("traps: caught signal preserves partial input", [
        {"expect": "$ "}, {"send": "trap 'echo signal' USR1\n"},
        {"expect": "$ "}, {"send": "echo half"}, {"signal": "USR1"},
        {"expect": "signal\n"}, {"send": "line\n"},
        {"expect": "halfline\n$ "}, {"send": "exit\n"}],
        "$ $ signal\nhalfline\n$ ", 0)
    terminal("traps: idle action can exit", [
        {"expect": "$ "}, {"send": "trap 'exit 23' USR1\n"},
        {"expect": "$ "}, {"signal": "USR1"}], "$ $ ", 23)
    terminal("traps: hangup signals background job", [
        {"expect": "$ "}, {"send": "trap 'wait %1' EXIT\n"}, {"expect": "$ "},
        {"send": "{ /bin/sh -c 'trap \"echo hup >marker; exit 0\" HUP; : >ready; while :; do sleep 0.05; done' & } 2>/dev/null\n"},
        {"expect": "$ "},
        {"send": "/bin/sh -c 'while [ ! -e ready ]; do sleep 0.01; done'; kill -HUP $$\n"}],
        "$ $ $ ", 128 + signal.SIGHUP)
    result[-1]["expect"]["files"] = {"marker": {"type": "file", "content": "hup\n"}}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    helper = shlex.quote(str(args.helper.resolve()))
    suite = {"version": 1, "name": "cshell runtime", "kind": "replacement",
             "cases": terminal_cases(helper) if args.output.name == "runtime-pty.json" else cases(helper)}
    if args.output.name == "control-flow.json":
        suite["name"] = "cshell control flow"
        suite["cases"] = [case for case in suite["cases"] if case["name"].startswith("control: ")]
    if args.output.name == "evaluation.json":
        suite["name"] = "cshell evaluation builtins"
        suite["cases"] = [case for case in suite["cases"] if case["name"].startswith("evaluation: ")]
    if args.output.name == "options.json":
        suite["name"] = "cshell options"
        suite["cases"] = [case for case in suite["cases"] if case["name"].startswith("options: ")]
    if args.output.name == "syntax.json":
        suite["name"] = "cshell invocation and syntax evidence"
        suite["cases"] = [case for case in suite["cases"] if case["name"].startswith("syntax: ")]
    if args.output.name == "execution.json":
        suite["name"] = "cshell execution evidence"
        suite["cases"] = [case for case in suite["cases"] if case["name"].startswith("execution: ")]
    args.output.write_text(json.dumps(suite, indent=2) + "\n")


if __name__ == "__main__":
    main()
