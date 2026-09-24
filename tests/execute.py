#!/usr/bin/env python3
"""Replacement executor fixtures; each subprocess has a hard timeout and cwd."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile

from smoke import child_limits


OUTPUT_LIMIT = 2 * 1024 * 1024


def bounded_run(arguments, *, cwd, env, timeout):
    """Bound output and kill the whole fixture group, including forked commands."""
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(arguments, cwd=cwd, env=env,
                                   stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=errors, start_new_session=True,
                                   preexec_fn=lambda: child_limits(timeout, OUTPUT_LIMIT))
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise AssertionError(f"fixture exceeded {timeout}s") from None
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=1)
        output.seek(0)
        errors.seek(0)
        stdout = output.read(OUTPUT_LIMIT + 1)
        stderr = errors.read(OUTPUT_LIMIT + 1)
        assert len(stdout) + len(stderr) <= OUTPUT_LIMIT, "fixture output limit exceeded"
        return subprocess.CompletedProcess(arguments, process.returncode, stdout, stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("binary")
    parser.add_argument("--helper", required=True)
    parser.add_argument("--fault-binary", required=True)
    parser.add_argument("--assignment-binary", required=True)
    args = parser.parse_args()
    binary = str(Path(args.binary).resolve())
    helper_path = str(Path(args.helper).resolve())
    helper = shlex.quote(helper_path)
    fault_binary = str(Path(args.fault_binary).resolve())
    checked = 0
    with tempfile.TemporaryDirectory(prefix="cshell-execute-") as temporary:
        cwd = Path(temporary).resolve()
        env = dict(os.environ, PATH="/bin:/usr/bin", HOME=temporary)
        env.pop("PRIVATE", None)
        env.pop("VISIBLE", None)

        def run(script, expected=0, stdout=b"", stderr=b"", *, flags=()):
            nonlocal checked
            result = bounded_run([binary, *flags, script], cwd=cwd, env=env, timeout=10)
            assert result.returncode == expected, (script[:160], result)
            assert result.stdout == stdout, (script[:160], result.stdout, stdout)
            if stderr is None:
                assert result.stderr, (script[:160], "expected diagnostic")
            else:
                assert result.stderr == stderr, (script[:160], result.stderr, stderr)
            checked += 1
            return result

        def file(name, data, mode=0o644):
            path = cwd / name
            path.write_bytes(data)
            path.chmod(mode)
            return path

        def contents(name, expected):
            assert (cwd / name).read_bytes() == expected, name

        run(f"{helper} args one '' 'two three' \"$literal\"\n", expected=2, stderr=None)
        run(f"{helper} args one '' 'two three' '\u0024literal' '*' '~' a\\ b\n",
            stdout=b"[one]\n[]\n[two three]\n[$literal]\n[*]\n[~]\n[a b]\n")
        run(f"{helper} args $'a\\nb'\n", stdout=b"[a\nb]\n")
        run(f"{helper} args pre'quoted'\"double\"post \\* \\~ a\\\nb\n",
            stdout=b"[prequoteddoublepost]\n[*]\n[~]\n[ab]\n")
        run(f"{helper} status 19\n", expected=19)
        run(f"{helper} signal\n", expected=143)
        run("no-such-cshell-command\n", expected=127, stderr=None)
        run("./missing-command\n", expected=127, stderr=None)
        file("denied", b"exit 0\n")
        run("./denied\n", expected=126, stderr=None)
        (cwd / "directory-command").mkdir()
        run("./directory-command\n", expected=126, stderr=None)
        file("text-script", b"printf 'fallback:%s:%s\\n' \"$0\" \"$1\"\nexit 17\n", 0o755)
        run("./text-script payload\n", expected=17, stdout=b"fallback:./text-script:payload\n")
        file("missing-interpreter", b"#!/missing/cshell-interpreter\n", 0o755)
        run("./missing-interpreter\n", expected=126, stderr=None)
        file("-t", b"printf 'dash:%s\\n' \"$1\"\n", 0o755)
        run("-t payload\n", stdout=b"dash:payload\n", flags=("--state-path", ""))
        (cwd / "-scripts").mkdir()
        file("-scripts/probe", b"printf 'dash-directory:%s\\n' \"$1\"\n", 0o755)
        run("probe payload\n", stdout=b"dash-directory:payload\n", flags=("--state-path", "-scripts"))
        run("-scripts/probe direct\n", stdout=b"dash-directory:direct\n")
        (cwd / "path-one").mkdir()
        (cwd / "path-two").mkdir()
        file("path-one/probe", b"exit 55\n")
        shutil.copy2(helper_path, cwd / "path-two/probe")
        run("probe args found\n", stdout=b"[found]\n", flags=("--state-path", "path-one:path-two"))
        run("probe args blocked\n", expected=126, stderr=None, flags=("--state-path", "path-one"))
        run("probe args missing\n", expected=127, stderr=None, flags=("--state-path", "absent"))
        shutil.copy2(helper_path, cwd / "local-probe")
        run("local-probe args here\n", stdout=b"[here]\n", flags=("--state-path", ":absent"))
        run("probe environment PATH PRIVATE VISIBLE\n",
            stdout=b"PATH=<unset>\nPRIVATE=<unset>\nVISIBLE=from-state\n",
            flags=("--state-path", "path-two"))
        run(f"PRIVATE=local VISIBLE=overwritten\n{helper} environment PRIVATE VISIBLE\n"
            f"PRIVATE='' VISIBLE=first VISIBLE='last=one' {helper} environment PRIVATE VISIBLE\n"
            f"{helper} environment PRIVATE VISIBLE\n",
            stdout=b"PRIVATE=<unset>\nVISIBLE=overwritten\nPRIVATE=\nVISIBLE=last=one\nPRIVATE=<unset>\nVISIBLE=overwritten\n",
            flags=("--state-path", "path-two"))
        run(f"PATH=path-two probe environment PATH\n{helper} environment PATH\n",
            stdout=b"PATH=path-two\nPATH=<unset>\n", flags=("--state-path", "absent"))
        run(f"PRIVATE=temporary ./missing-command\n{helper} environment PRIVATE\n",
            stdout=b"PRIVATE=<unset>\n", stderr=None)
        run(f"PRIVATE=temporary {helper} args never <missing-assignment-input\n"
            f"{helper} environment PRIVATE\n", stdout=b"PRIVATE=<unset>\n", stderr=None)
        run(f"{helper} both 2>&1 >order-one\n", stdout=b"err\n")
        contents("order-one", b"out\n")
        run(f"{helper} both >order-two 2>&1\n")
        contents("order-two", b"out\nerr\n")
        run(f"{helper} both >overwrite-first >overwrite-second 2>&1\n")
        contents("overwrite-first", b"")
        contents("overwrite-second", b"out\nerr\n")
        file("input", b"from-input\n")
        run(f"{helper} copy <input >copied\n")
        contents("copied", b"from-input\n")
        run(f"{helper} args added >>copied\n")
        contents("copied", b"from-input\n[added]\n")
        run(f"{helper} args replaced >|copied\n")
        contents("copied", b"[replaced]\n")
        run(f"{helper} fd-write 3 3<>read-write\n")
        contents("read-write", b"fd\n")
        run(f"{helper} copy 3 3<>read-write\n", stdout=b"fd\n")
        run(f"{helper} copy 3 3<input\n", stdout=b"from-input\n")
        run(f"{helper} copy 3 3<&0 <input\n", stdout=b"")
        run(f"{helper} copy 3 <input 3<&0\n", stdout=b"from-input\n")
        run(f"{helper} fd-write 3 3\\\n>continued-fd\n")
        contents("continued-fd", b"fd\n")
        run(f"{helper} closed 9 9>&-\n")
        run(f"{helper} closed 0 <&-\n")
        run(f"{helper} closed 1 >&-\n")
        run(f"{helper} copy <<'EOF'\n$literal `text` \\keep\nEOF\n",
            stdout=b"$literal `text` \\keep\n")
        run(f"{helper} copy <<EOF\nplain text\nEOF\n", stdout=b"plain text\n")
        run(f"{helper} copy <<ONE <<TWO\nfirst\nONE\nsecond\nTWO\n", stdout=b"second\n")
        run(f"{helper} copy <<-EOF\n\tstripped\n\tEOF\n", stdout=b"stripped\n")
        large = "x" * (96 * 1024) + "\n"
        run(f"{helper} copy <<'EOF'\n{large}EOF\n", stdout=large.encode())
        (cwd / "nested").mkdir()
        run(f"HOME=nested cd\n{helper} environment HOME\n{helper} pwd\n",
            stdout=("HOME=" + temporary + "\n" + str(cwd / "nested") + "\n").encode())
        run(f"cd nested\n{helper} pwd\n", stdout=(str(cwd / "nested") + "\n").encode())
        run(f"cd\n{helper} pwd\n", stdout=(str(cwd) + "\n").encode())
        run(">empty-command-output\n")
        contents("empty-command-output", b"")
        run(f"cd . >builtin-output\n{helper} args restored\n", stdout=b"[restored]\n")
        contents("builtin-output", b"")
        run(f"cd missing 2>builtin-error\n{helper} both\n", stdout=b"out\n", stderr=b"err\n")
        assert (cwd / "builtin-error").read_bytes()
        run(f"exit 23 >exit-output\n{helper} args never\n", expected=23)
        contents("exit-output", b"")
        run(f"{helper} status 7\nexit\n{helper} args never\n", expected=7)
        # The exec-failure child must _exit, rather than resume this input loop.
        run(f"./missing-command\n{helper} args once\n", stdout=b"[once]\n", stderr=None)
        for syntax in (
            f"{helper} args $HOME", f"{helper} args $((1+2))",
            f"{helper} args $(touch substitution-effect)",
            f"{helper} args `touch backtick-effect`", f"{helper} args *",
            f"{helper} args ~", f"NAME=$HOME {helper} args assignment",
            f"{helper} args a | {helper} copy", f"{helper} args a && {helper} args b",
            f"{helper} args a || {helper} args b", f"{helper} args a; {helper} args b",
            f"{helper} args a &", f"({helper} args compound)",
            f"{{ {helper} args compound; }}",
        ):
            run(f">unsupported-effect {syntax}\n", expected=2, stderr=None)
            assert not (cwd / "unsupported-effect").exists(), syntax
        for name in ("substitution-effect", "backtick-effect"):
            assert not (cwd / name).exists()
        for operand in ("1>&bad", "999999999999999999999999999>target", "3<&999999999999999999999999"):
            run(f"{helper} args >unsupported-effect {operand}\n", expected=2, stderr=None)
            assert not (cwd / "unsupported-effect").exists(), operand
        for body in ("$HOME", "`touch heredoc-effect`", "back\\slash"):
            run(f"{helper} copy >unsupported-effect <<EOF\n{body}\nEOF\n", expected=2, stderr=None)
            assert not (cwd / "unsupported-effect").exists()
        assert not (cwd / "heredoc-effect").exists()
        run(f"{helper} args >unsupported-effect >$HOME\n", expected=2, stderr=None)
        assert not (cwd / "unsupported-effect").exists()
        result = bounded_run([binary, "--api"], cwd=cwd, env=env, timeout=10)
        assert result.returncode == 0, result
        assert result.stdout == b"execution API checks passed\n", result
        assert b"cd" in result.stderr, result
        result = bounded_run([str(Path(args.assignment_binary).resolve())], cwd=cwd, env=env, timeout=15)
        assert result.returncode == 0, result
        assert result.stdout == b"assignment dispatch checks passed\n", result
        assert result.stderr == b"", result
        result = bounded_run([fault_binary], cwd=cwd, env=env, timeout=15)
        assert result.returncode == 0, result
        assert result.stdout == b"execution fault checks passed\n", result
        assert result.stderr == b"", result
    print(f"execution fixtures passed ({checked} behavior cases, API and fault checks)")


if __name__ == "__main__":
    main()
