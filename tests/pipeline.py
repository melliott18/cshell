#!/usr/bin/env python3
"""Bounded pipeline behavior against replacement AST execution, never legacy."""
import argparse
import os
from pathlib import Path
import shlex
import tempfile

from execute import bounded_run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--helper", required=True)
    parser.add_argument("--api-binary", required=True)
    parser.add_argument("--fault-binary", required=True)
    args = parser.parse_args()
    binary, helper_path, api, faults = (
        str(Path(p).resolve()) for p in
        (args.binary, args.helper, args.api_binary, args.fault_binary))
    helper = shlex.quote(helper_path)
    checked = 0
    with tempfile.TemporaryDirectory(prefix="cshell-pipeline-") as temporary:
        cwd = Path(temporary).resolve()
        env = dict(os.environ, PATH="/bin:/usr/bin", HOME=str(cwd))

        def run(script, status=0, output=b"", diagnostic=False):
            nonlocal checked
            result = bounded_run([binary, script], cwd=cwd, env=env, timeout=10)
            assert result.returncode == status, (script[:200], result)
            assert result.stdout == output, (script[:200], result)
            assert bool(result.stderr) == diagnostic, (script[:200], result)
            checked += 1

        run(f"{helper} args payload | {helper} copy | {helper} copy\n",
            output=b"[payload]\n")
        run(" | ".join([f"{helper} args long"] + [f"{helper} copy"] * 47) + "\n",
            output=b"[long]\n")
        run(f"{helper} generate 8388608 | {helper} copy | {helper} copy | {helper} count\n",
            output=b"8388608\n")
        run(f"{helper} generate 8388608 | {helper} copy | {helper} one\n")
        for earlier, final in ((0, 0), (7, 0), (0, 9), (7, 9)):
            for negated in (False, True):
                prefix = "! " if negated else ""
                expected = int(final == 0) if negated else final
                run(f"{prefix}{helper} status {earlier} | {helper} copy | {helper} status {final}\n",
                    status=expected)
        run(f"{helper} signal | {helper} copy\n")
        run(f"{helper} status 0 | {helper} signal\n", status=143)
        run(f"! {helper} status 0 | {helper} signal\n")
        run(f"no-such-cshell-stage | {helper} count\n", output=b"0\n", diagnostic=True)
        run(f"{helper} status 0 | no-such-cshell-stage\n", status=127, diagnostic=True)
        run(f"no-such-cshell-stage | {helper} copy\n{helper} args once\n",
            output=b"[once]\n", diagnostic=True)
        (cwd / "denied").write_text("exit 0\n")
        run(f"{helper} status 0 | ./denied\n", status=126, diagnostic=True)
        (cwd / "fallback").write_text("printf 'fallback\\n'\n")
        (cwd / "fallback").chmod(0o755)
        run(f"./fallback | {helper} copy\n", output=b"fallback\n")
        run(f"{helper} both 2>&1 >stage-output | {helper} copy\n", output=b"err\n")
        assert (cwd / "stage-output").read_bytes() == b"out\n"
        run(f"{helper} both >stage-output 2>&1 | {helper} count\n", output=b"0\n")
        assert (cwd / "stage-output").read_bytes() == b"out\nerr\n"
        (cwd / "input").write_bytes(b"override\n")
        run(f"{helper} status 0 | {helper} copy <input | {helper} copy\n", output=b"override\n")
        run(f"{helper} status 0 | {helper} copy <<'EOF' | {helper} copy\nbody\nEOF\n",
            output=b"body\n")
        run(f"{helper} generate 8388608 | {helper} copy <missing | {helper} count\n",
            output=b"0\n", diagnostic=True)
        run(f"{helper} generate 8388608 | {helper} copy <missing\n", status=1, diagnostic=True)
        run(f"{helper} status 0 | {helper} copy 0<&-\n", status=81)
        run(f"{helper} closed 1 1>&- | {helper} count\n", output=b"0\n")
        run(f"{helper} private-fds | {helper} private-fds | {helper} private-fds\n")
        # Sanitizer runtimes may reserve low descriptors before main. Exercise
        # closed-source failures in a range outside their runtime bookkeeping.
        for descriptor in range(40, 47):
            run(f"{helper} status 0 | {helper} status 0 1>&{descriptor}\n",
                status=1, diagnostic=True)
        (cwd / "nested").mkdir()
        for script in (f"cd nested | {helper} copy", f"{helper} status 0 | cd nested"):
            run(f"{script}\n{helper} pwd\n", output=(str(cwd) + "\n").encode())
        run(f"exit 23 | {helper} copy\n{helper} args alive\n", output=b"[alive]\n")
        run(f"{helper} status 0 | exit 23\n", status=23)
        run(f"{helper} status 0 | exit 23\n{helper} args alive\n", output=b"[alive]\n")
        run(f"{helper} status 7\ncd . | exit\n", status=7)
        run(f"! cd nested\n{helper} pwd\n", output=(str(cwd / "nested") + "\n").encode())
        run("! exit 7\n", status=7)
        run(f"! {helper} status 0\n", status=1)
        run(f"! {helper} status 5\n")
        run(f">empty | {helper} count\n", output=b"0\n")
        assert (cwd / "empty").read_bytes() == b""
        for unsupported in (f"{helper} args $HOME", "cd . && cd .", "(cd .)",
                            "{ cd .; }", "NAME=value cd .", "cd . >$HOME"):
            run(f"{helper} args effect >forbidden | {unsupported}\n", status=2, diagnostic=True)
            assert not (cwd / "forbidden").exists()
        run(f"{helper} args effect >forbidden | cd . &\n", status=2, diagnostic=True)
        assert not (cwd / "forbidden").exists()
        for candidate, flags, expected in (
            (api, [helper_path], b"pipeline API checks passed\n"),
            (faults, ["--pipeline"], b"pipeline fault checks passed\n"),
        ):
            result = bounded_run([candidate, *flags], cwd=cwd, env=env, timeout=25)
            assert result.returncode == 0 and result.stdout == expected, result
            assert result.stderr == b"", result
    print(f"pipeline fixtures passed ({checked} behavior cases, API and fault checks)")


if __name__ == "__main__":
    main()
