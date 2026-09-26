#!/usr/bin/env python3
"""Generate strict shell job-control cases for the CSH-033 PTY transport."""
import argparse
import json
from pathlib import Path
import shlex
import signal


def cases(helper, shell):
    result = []

    def terminal(name, steps, output, status=0):
        result.append(dict(name=name, transport="pty", steps=steps,
                           expect=dict(output=output, status=status)))

    for monitor in ("+m", "-m"):
        terminal(f"interactive ignored signals with monitor {monitor}", [
            {"expect": "$ "}, {"send": f"set {monitor}\n"}, {"expect": "$ "},
            {"control": "Z"}, {"control": "\\"}, {"signal": "TERM"},
            {"send": "kill -s TSTP $$; kill -s QUIT $$; kill -s TTIN $$; kill -s TTOU $$; echo alive\n"},
            {"expect": "alive\n$ "}, {"foreground": "leader"},
            {"send": "set -m\n"}, {"expect": "$ "},
            {"send": f"{helper} check\n"}, {"expect": "terminal-ok\n$ "},
            {"send": "exit\n"}], "$ $ alive\n$ $ terminal-ok\n$ ")

    # CSH-050 / JOB-001, JOB-002: exact nested-startup handshakes.
    for mode in ("foreground", "background"):
        handshake = ("startup-stopped\n" if mode == "background" else "") + "startup-foreground\n$ "
        terminal(f"nested {mode} startup and restoration", [
            {"expect": "$ "}, {"send": f"{helper} startup {mode} {shell}\n"},
            {"expect": handshake}, {"foreground": "leader"},
            {"send": "echo $?\n"}, {"expect": "0\n$ "},
            {"send": f"{helper} check\n"}, {"expect": "terminal-ok\n$ "},
            {"send": "exit\n"}], "$ " + handshake + "0\n$ terminal-ok\n$ ")
    terminal("foreground Ctrl-C and restored terminal", [
        {"expect": "$ "}, {"send": f"{helper} hold\n"}, {"expect": "ready\n"},
        {"foreground": "other"}, {"control": "C"}, {"expect": "$ "},
        {"foreground": "leader"}, {"send": "exit\n"}], "$ ready\n$ ", 128 + signal.SIGINT)
    terminal("pipeline shares foreground group and Ctrl-C", [
        {"expect": "$ "}, {"send": f"{helper} producer | {helper} pipeline\n"},
        {"expect": "pipeline-ready\n"}, {"foreground": "other"}, {"control": "C"},
        {"expect": "$ "}, {"foreground": "leader"}, {"send": f"{helper} check\n"},
        {"expect": "terminal-ok\n$ "}, {"send": "exit\n"}], "$ pipeline-ready\n$ terminal-ok\n$ ")
    label = f"{helper} hold"
    terminal("Ctrl-Z jobs bg fg Ctrl-C", [
        {"expect": "$ "}, {"send": label + "\n"}, {"expect": "ready\n"},
        {"control": "Z"}, {"expect": f"[1]+ Stopped {label}\n$ "},
        {"foreground": "leader"}, {"send": "jobs\n"},
        {"expect": f"[1]+ Stopped {label}\n$ "}, {"send": "bg\n"},
        {"expect": f"[1]+ Running {label}\n$ "}, {"send": "fg\n"},
        {"expect": label + "\n"}, {"foreground": "other"}, {"control": "C"},
        {"expect": "$ "}, {"foreground": "leader"}, {"send": "exit\n"}],
        f"$ ready\n[1]+ Stopped {label}\n$ [1]+ Stopped {label}\n$ [1]+ Running {label}\n$ {label}\n$ ", 128 + signal.SIGINT)
    # Repeat real resume notifications without sleeps or relaxed transcripts.
    # Finish each job with Ctrl-C: another immediate Ctrl-Z after fg's display
    # could precede its SIGCONT and would create a race in the fixture itself.
    steps = [{"expect": "$ "}]
    output = "$ "
    for cycle in range(32):
        stopped = f"[{cycle + 1}]+ Stopped {label}\n$ "
        resumed = f"[{cycle + 1}]+ Running {label}\n$ "
        steps.extend([
            {"send": label + "\n"}, {"expect": "ready\n"},
            {"control": "Z"}, {"expect": stopped},
            {"foreground": "leader"}, {"send": "bg\n"}, {"expect": resumed},
            {"foreground": "leader"}, {"send": "fg\n"}, {"expect": label + "\n"},
            {"foreground": "other"}, {"control": "C"}, {"expect": "$ "}])
        output += "ready\n" + stopped + resumed + label + "\n$ "
    steps.extend([{"foreground": "leader"}, {"send": "exit\n"}])
    terminal("repeated background resumes preserve prompt and terminal", steps,
             output, 128 + signal.SIGINT)
    label = f"{helper} producer | {helper} pipeline"
    terminal("pipeline stop resume group and wait", [
        {"expect": "$ "}, {"send": label + "\n"}, {"expect": "pipeline-ready\n"},
        {"control": "Z"}, {"expect": f"[1]+ Stopped {label}\n$ "},
        {"foreground": "leader"}, {"send": "fg %1\n"}, {"expect": label + "\n"},
        {"foreground": "other"}, {"control": "C"}, {"expect": "$ "},
        {"foreground": "leader"}, {"send": "exit\n"}],
        f"$ pipeline-ready\n[1]+ Stopped {label}\n$ {label}\n$ ", 128 + signal.SIGINT)
    label = f"{helper} modes"
    terminal("stopped job modes saved and shell modes restored", [
        {"expect": "$ "}, {"send": label + "\n"},
        {"expect": f"modes-ready\n[1]+ Stopped {label}\n$ "},
        {"foreground": "leader"}, {"send": f"{helper} check\n"},
        {"expect": "terminal-ok\n$ "}, {"send": "fg %1\n"},
        {"expect": f"{label}\nmodes-resumed\n$ "}, {"send": f"{helper} check\n"},
        {"expect": "terminal-ok\n$ "}, {"send": "exit\n"}],
        f"$ modes-ready\n[1]+ Stopped {label}\n$ terminal-ok\n$ {label}\nmodes-resumed\n$ terminal-ok\n$ ")
    terminal("monitor transitions and unavailable jobs", [
        {"expect": "$ "}, {"send": "set +m\n"}, {"expect": "$ "},
        {"send": "fg\n"}, {"expect": "cshell: fg: job control unavailable\n$ "},
        {"send": "set -o monitor\n"}, {"expect": "$ "},
        {"send": f"{helper} check\n"}, {"expect": "terminal-ok\n$ "},
        {"foreground": "leader"}, {"send": "exit\n"}],
        "$ $ cshell: fg: job control unavailable\n$ $ terminal-ok\n$ ")
    # All job descriptors are reserved before outer/inner redirections.
    terminal("terminal descriptor survives redirection operands", [
        {"expect": "$ "}, {"send": f"{{ {helper} check; }} 10>&- 11>&- 12>&- 13>&-\n"},
        {"expect": "terminal-ok\n$ "}, {"foreground": "leader"},
        {"send": f"{helper} check\n"}, {"expect": "terminal-ok\n$ "}, {"send": "exit\n"}],
        "$ terminal-ok\n$ terminal-ok\n$ ")
    label = f"{helper} reader"
    terminal("background terminal reader stops and fg can read", [
        {"expect": "$ "},
        {"send": f"{{ {label} >reader-output & wait %1; }} 2>/dev/null\n"},
        {"expect": f"[1]+ Stopped {label}\n$ "}, {"foreground": "leader"},
        {"send": "fg %1\n"}, {"expect": label + "\n"}, {"foreground": "other"},
        {"send": "x\n"}, {"expect": "$ "}, {"foreground": "leader"},
        {"send": "exit\n"}], f"$ [1]+ Stopped {label}\n$ {label}\n$ ")
    result[-1]['expect']['files'] = {'reader-output': {'type': 'file', 'content': 'reader-ready\nreader-done\n'}}
    label = f"{helper} hold"
    terminal("stopped jobs survive monitor toggles", [
        {"expect": "$ "}, {"send": label + "\n"}, {"expect": "ready\n"},
        {"control": "Z"}, {"expect": f"[1]+ Stopped {label}\n$ "},
        {"send": "set +m; fg %1\n"}, {"expect": "cshell: fg: job control unavailable\n$ "},
        {"send": "set -m; fg %1\n"}, {"expect": label + "\n"},
        {"foreground": "other"}, {"control": "C"}, {"expect": "$ "},
        {"send": "exit\n"}],
        f"$ ready\n[1]+ Stopped {label}\n$ cshell: fg: job control unavailable\n$ {label}\n$ ", 128 + signal.SIGINT)
    terminal("current previous and ambiguous job operands", [
        {"expect": "$ "}, {"send": label + "\n"}, {"expect": "ready\n"},
        {"control": "Z"}, {"expect": f"[1]+ Stopped {label}\n$ "},
        {"send": label + "\n"}, {"expect": "ready\n"},
        {"control": "Z"}, {"expect": f"[2]+ Stopped {label}\n$ "},
        {"send": f"fg %{helper}\n"},
        {"expect": f"cshell: fg: no such job: %{helper}\n$ "},
        {"send": "fg %-\n"}, {"expect": label + "\n"},
        {"control": "C"}, {"expect": "$ "},
        {"send": "kill -KILL %+; wait %2; exit 0\n"}],
        f"$ ready\n[1]+ Stopped {label}\n$ ready\n[2]+ Stopped {label}\n$ cshell: fg: no such job: %{helper}\n$ {label}\n$ ")
    terminal("background completion and wait status", [
        {"expect": "$ "}, {"send": "{ exit 17 & wait %1; } 2>/dev/null\n"},
        {"expect": "$ "}, {"foreground": "leader"}, {"send": "exit\n"}], "$ $ ", 17)
    terminal("unmonitored job stays unmonitored after enabling monitor", [
        {"expect": "$ "},
        {"send": "set +m; { /bin/sleep 60 & } 2>/dev/null; set -m; fg %1\n"},
        {"expect": "cshell: fg: job was started without job control: %1\n$ "},
        {"foreground": "leader"}, {"send": "kill -KILL %1; wait; exit 0\n"}],
        "$ cshell: fg: job was started without job control: %1\n$ ")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--helper", required=True)
    parser.add_argument("--shell", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    helper = shlex.quote(str(Path(args.helper).resolve()))
    Path(args.output).write_text(json.dumps({"version": 1, "name": "shell job control", "kind": "replacement", "cases": cases(helper, shlex.quote(str(Path(args.shell).resolve())))}, indent=2) + "\n")


if __name__ == "__main__":
    main()
