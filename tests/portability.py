#!/usr/bin/env python3
"""Bounded CSH-037 runtime probes using the shared shell fixture runner.

The oracles below cover selected Issue 8 language rules; they are not a
conformance verdict for an entire matrix family.  A UTF-8 locale is probed
before its cases are run because locale names differ by platform.
"""

import argparse
import locale
from pathlib import Path
import sys
import tempfile

import smoke
import locale_cases
import multibyte_cases


def utf8_locale():
    original = locale.setlocale(locale.LC_CTYPE)
    for name in ("C.UTF-8", "en_US.UTF-8"):
        try:
            locale.setlocale(locale.LC_CTYPE, name)
        except locale.Error:
            continue
        finally:
            locale.setlocale(locale.LC_CTYPE, original)
        return name
    return None


def case(name, script, *, stdout="", stderr="", status=0, env=None,
         setup=None, modes=("string", "file", "stdin")):
    for mode in modes:
        args, source = [], ""
        contents = dict(setup or {})
        if mode == "string":
            args = ["-c", script]
        elif mode == "file":
            contents["script"] = script
            args = ["script"]
        else:
            source = script
        yield {"name": f"{name} ({mode})", "args": args, "stdin": source,
               "env": env or {}, "setup": contents,
               "expect": {"stdout": stdout, "stderr": stderr, "status": status}}


def cases(selected):
    # A UTF-8 filename is two bytes but one character.  In the C locale,
    # 'caf?' must remain literal because '?' matches only one byte.
    yield from case("C locale multibyte pattern", "printf '%s\\n' caf?\n",
                    stdout="caf?\n", setup={"café": ""})

    if selected is None:
        print("SKIP: 18 UTF-8 locale cases: no C.UTF-8 or en_US.UTF-8 locale "
              "installed (owner CSH-042)",
              flush=True)
    else:
        for pattern in ("caf?", "caf[[:alpha:]]"):
            yield from case(f"UTF-8 pathname {pattern}",
                            f"printf '%s\\n' {pattern}\n", stdout="café\n",
                            env={"LC_ALL": selected}, setup={"café": ""})
        # LC_ALL takes precedence over LC_CTYPE, including after assignment.
        # Pathname matching is not evidence for the separate lexical-startup
        # rule; that interpretation and locale-update coverage remain CSH-042.
        yield from case("LC_ALL overrides LC_CTYPE", "printf '%s\\n' caf?\n",
                        stdout="caf?\n", env={"LC_ALL": "C", "LC_CTYPE": selected},
                        setup={"café": ""})
        yield from case("LC_CTYPE when LC_ALL is empty", "printf '%s\\n' caf?\n",
                        stdout="café\n", env={"LC_ALL": "", "LC_CTYPE": selected},
                        setup={"café": ""})
        yield from case("LC_ALL overrides assigned LC_CTYPE",
                        "LC_CTYPE=C; printf '%s\\n' caf?\n", stdout="café\n",
                        env={"LC_ALL": selected}, setup={"café": ""})
        yield from case("UTF-8 IFS character",
                        "IFS=é; VALUE=aéb; printf '<%s>\\n' $VALUE\n",
                        stdout="<a>\n<b>\n", env={"LC_ALL": selected})

    # Keep the generated cases small but vary nesting and quoting.  These are
    # fixed-seed structural probes, with expectations derived from arithmetic
    # and quote rules rather than a reference shell's output.
    for depth in (1, 2, 4, 8, 16, 32):
        expression = "(" * depth + "7+5" + ")" * depth
        yield from case(f"nested arithmetic depth {depth}",
                        f"printf '%s\\n' \"$(({expression}))\"\n", stdout="12\n")
    for count in (1, 2, 4, 8, 16, 32):
        fragments = "".join("'a'\"b\"" for _ in range(count))
        yield from case(f"adjacent quote fragments {count}",
                        f"printf '%s\\n' {fragments}\n", stdout="ab" * count + "\n")

    # More than the historical input line size, with a terminal sentinel.
    # Avoid a huge -c argument: Linux limits each execve argument separately.
    long_value = "a" * (256 * 1024) + "z"
    yield from case("large input line", f"VALUE={long_value}\n"
                    "case \"$VALUE\" in *z) printf 'complete\\n';; esac\n",
                    stdout="complete\n", modes=("file", "stdin"))


def sparse_file_case(binary):
    # Crossing 2 GiB detects accidental 32-bit file-size gates without
    # allocating 2 GiB of physical storage or reading file contents.
    with tempfile.TemporaryDirectory(prefix="cshell-portability-") as temporary:
        directory = Path(temporary)
        large = directory / "large-file"
        with large.open("wb") as output:
            output.truncate((1 << 31) + 1)
        fixture = {"name": "sparse file pathname expansion", "args": ["-c",
                   "printf '%s\\n' large-*"], "stdin": "", "env": {},
                   "expect": {"stdout": "large-file\n", "stderr": "", "status": 0}}
        status, output, failures = smoke.capture(binary, fixture, directory, 5, 65536)
        if status != 0:
            failures.append(f"status: expected 0, got {status}")
        for stream in ("stdout", "stderr"):
            wanted = fixture["expect"][stream].encode()
            if bytes(output[stream]) != wanted:
                failures.append(f"{stream}: expected {wanted!r}, got {bytes(output[stream])!r}")
        if large.stat().st_size != (1 << 31) + 1:
            failures.append("pathname expansion changed the sparse file size")
        for name in (".home", ".tmp"):
            (directory / name).rmdir()
        # The shell must open the redirection at an offset beyond 2 GiB; the
        # harness normally caps file output at 1 MiB, so raise only this case's
        # file-size bound while retaining its time and captured-output bounds.
        append = {"name": "sparse file append redirection", "args": ["-c",
                  "printf x >>large-file"], "stdin": "", "env": {},
                  "expect": {"stdout": "", "stderr": "", "status": 0}}
        append_status, append_output, append_failures = smoke.capture(
            binary, append, directory, 5, 65536, (1 << 31) + 3)
        if append_status != 0:
            append_failures.append(f"status: expected 0, got {append_status}")
        if any(append_output[stream] for stream in ("stdout", "stderr")):
            append_failures.append("append wrote to stdout or stderr")
        if large.stat().st_size != (1 << 31) + 2:
            append_failures.append("append did not advance file offset past 2 GiB")
        else:
            with large.open("rb") as source:
                source.seek(-1, 2)
                if source.read() != b"x":
                    append_failures.append("append wrote the wrong byte")
        failures.extend(append_failures)
        return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, nargs="?", default=Path("./cshell"))
    args = parser.parse_args()
    binary = args.binary.resolve()
    if not binary.is_file():
        parser.error(f"missing executable: {binary}")
    selected = utf8_locale()
    print(f"UTF-8 locale: {selected or 'unavailable'}", flush=True)
    data = locale_cases.host_data()
    print("Locale probes available: " + ", ".join(data), flush=True)
    skips = []
    fixtures = list(cases(selected)) + list(locale_cases.cases(case, selected, data, skips))
    passed, failed, multibyte_skips = multibyte_cases.run(
        binary, Path("build/tests/character_fixture").resolve())
    for fixture in fixtures:
        failures = smoke.run_case(binary, fixture, 5, 65536)
        if failures:
            failed += 1
            print("FAIL:", fixture["name"])
            for reason in failures:
                print(" ", reason)
        else:
            passed += 1
            print("PASS:", fixture["name"])
    try:
        failures = sparse_file_case(binary)
    except OSError as error:
        failures = [f"sparse file setup: {error}"]
    if failures:
        failed += 1
        print("FAIL: sparse file pathname expansion")
        for reason in failures:
            print(" ", reason)
    else:
        passed += 1
        print("PASS: sparse file pathname expansion")
    for reason in skips:
        print("SKIP:", reason, "(owner CSH-042)")
    print(f"Result: {passed} passed, {failed} failed, "
          f"{(0 if selected else 18) + len(skips) + multibyte_skips} skipped (cases/capability groups)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
