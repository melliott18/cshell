#!/usr/bin/env python3
"""Bounded final-field API checks and selected standard-defined sh comparisons."""

import argparse
from dataclasses import dataclass
import math
import os
from pathlib import Path
import shlex
import tempfile

from smoke import capture


OUTPUT_LIMIT = 256 * 1024
FILES = (
    "alpha.txt", "beta.txt", "space name.txt", ".hidden.txt",
    "a*.txt", "a?.txt", "a[1].txt", "a*X.txt", "a\\X.txt",
    "back\\slash.txt", "no[x", "z2", "zA", "z10",
)


@dataclass
class Case:
    name: str
    source: str
    expected: list
    x: str = ""
    y: str = ""
    ifs: object = None
    parameters: tuple = ()
    context: str = "argument"
    noglob: bool = False
    differential: bool = True


def cases():
    yield Case("unset IFS trims and folds whitespace", "$x", ["one", "two", "three"], x=" \tone\n two\tthree \n")
    yield Case("explicit default IFS", "$x", ["one", "two"], x=" \none\t two ", ifs=" \t\n")
    yield Case("empty IFS keeps whitespace", "$x", [" a\tb\n "], x=" a\tb\n ", ifs="")
    yield Case("whitespace-only IFS subset", "$x", ["a\tb", "c\nd"], x="  a\tb c\nd ", ifs=" ")
    yield Case("tab-only IFS retains spaces", "$x", [" a ", " b "], x="\t a \t\t b \t", ifs="\t")
    yield Case("nonwhitespace delimiter empties", "$x", ["", "a", "", "b"], x=",a,,b,", ifs=",")
    yield Case("single nonwhitespace delimiter", "$x", [""], x=",", ifs=",")
    yield Case("two nonwhitespace delimiters", "$x", ["", ""], x=",,", ifs=",")
    yield Case("mixed IFS trims around separators", "$x", ["", "a", "", "b"], x=" , a , , b , ", ifs=" ,")
    yield Case("multiple nonwhitespace delimiters", "$x", ["a", "", "b", ""], x="a,:b::", ifs=",:")
    yield Case("non-IFS whitespace is data", "$x", ["a b", " c "], x="a b, c ", ifs=",")
    yield Case("literal delimiter never splits", "a,b", ["a,b"], ifs=",")
    yield Case("literal punctuation between expansions", "$x,$y", ["a", ",b"], x="a,", y="b", ifs=",")
    yield Case("adjacent expansion whitespace", "$x$y", ["a", "b"], x="a ", y=" b")
    yield Case("adjacent expansion punctuation", "$x$y", ["a", "", "b"], x="a,", y=",b", ifs=",")
    yield Case("literal prefix and suffix", "pre${x}post", ["prea", "bpost"], x="a b")
    yield Case("literal prefix before leading delimiter", "pre${x}", ["pre", "a"], x=" a")
    yield Case("literal suffix after trailing delimiter", "${x}post", ["a", "post"], x="a ")
    yield Case("unset parameter disappears", "$absent", [])
    yield Case("empty parameter disappears", "$x", [])
    yield Case("empty IFS still removes implicit null", "$x", [], ifs="")
    yield Case("whitespace parameter disappears", "$x", [], x=" \t\n ")
    yield Case("single quoted empty", "''", [""])
    yield Case("double quoted empty", '""', [""])
    yield Case("quoted empty parameter", '"$x"', [""])
    yield Case("quoted absent parameter", '"$absent"', [""])
    yield Case("trailing quoted empty has position", '$x""', ["a", ""], x="a ")
    # Issue 8 counts explicit quoted emptiness as a nonempty candidate; some
    # older /bin/sh implementations drop it before an IFS whitespace boundary.
    yield Case("leading quoted empty has position", '""$x', ["", "a"], x=" a", differential=False)
    yield Case("quoted empty after nonwhite separator", '$x""', ["", ""], x=",", ifs=",")
    yield Case("quoted empty before nonwhite separator", '""$x', [""], x=",", ifs=",")
    yield Case("empty between two split expansions", '$x""$y', ["a", "", "b"], x="a ", y=" b", differential=False)
    yield Case("quoted whitespace remains", '"$x"', [" a\tb "], x=" a\tb ")
    yield Case("escaped whitespace remains", "a\\ b", ["a b"])
    yield Case("quoted at preserves boundaries", '"$@"', ["a b", "", "*"], parameters=("a b", "", "*"))
    yield Case("quoted at prefix and suffix", 'pre"$@"post', ["prea b", "", "*post"], parameters=("a b", "", "*"))
    yield Case("quoted at without parameters", '"$@"', [])
    yield Case("quoted at absent between literals", 'pre"$@"post', ["prepost"])
    yield Case("unquoted at splits each parameter", "$@", ["a", "b", "c", "d"], parameters=("a b", "", "c d"))
    yield Case("quoted star joins with first IFS", '"$*"', ["a,b,,c"], ifs=", ", parameters=("a,b", "", "c"))
    yield Case("quoted star with empty IFS", '"$*"', ["a bc"], ifs="", parameters=("a b", "", "c"))
    yield Case("quoted star without parameters", '"$*"', [""])
    yield Case("arithmetic eligible for splitting", "$((121))", ["", "2"], ifs="1")
    yield Case("tilde result protected", "~/name", ["home space/*/name"], differential=False)
    yield Case("parameter default splitting", "${absent:-a,b}", ["a", "b"], ifs=",")
    yield Case("quoted parameter default", '"${absent:-a,b}"', ["a,b"], ifs=",")

    text_matches = sorted("files/" + name for name in FILES if name.endswith(".txt") and not name.startswith("."))
    yield Case("star matches sorted names and whitespace", "files/*.txt", text_matches)
    yield Case("question mark", "files/z?", ["files/z2", "files/zA"])
    yield Case("bracket range", "files/z[0-9]", ["files/z2"])
    yield Case("bracket character class", "files/z[[:digit:]]", ["files/z2"])
    yield Case("negated bracket", "files/z[!0-9]", ["files/zA"])
    yield Case("quoted bracket member", "files/z['2']", ["files/z2"])
    yield Case("unquoted character class remains active", "patterns/[[:alpha:]]", ["patterns/a", "patterns/b", "patterns/z"])
    # Reference shells differ on quoted class names, and some (including
    # dash) omit collating/equivalence syntax. Assert our protected-pattern
    # interpretation and the C-locale matching results directly here.
    yield Case("quoted character class name is literal", "patterns/[[:'alpha':]]", ["patterns/:]", "patterns/a]"], differential=False)
    yield Case("quoted class opening marker is literal", "patterns/[[':'alpha:]]", ["patterns/:]", "patterns/a]"])
    yield Case("quoted class closing marker is literal", "patterns/[[:alpha':']]", ["patterns/:]", "patterns/a]"])
    yield Case("unquoted collating element remains active", "patterns/[[.a.]]", ["patterns/a"], differential=False)
    yield Case("quoted collating marker is literal", "patterns/[['.'a.]]", ["patterns/a]"])
    yield Case("unquoted equivalence class remains active", "patterns/[[=a=]]", ["patterns/a"], differential=False)
    yield Case("quoted equivalence marker is literal", "patterns/[['='a=]]", ["patterns/=]", "patterns/a]"])
    yield Case("unmatched bracket literal", "files/no[", ["files/no["])
    yield Case("no matching pathname preserved", "files/missing-*.txt", ["files/missing-*.txt"])
    yield Case("quoted star remains literal", "'files/*.txt'", ["files/*.txt"])
    yield Case("escaped star remains literal", "files/a\\*.txt", ["files/a*.txt"])
    yield Case("quoted question with active star", "files/a'?'*.txt", ["files/a?.txt"])
    yield Case("quoted bracket text", "files/'a[1]'*.txt", ["files/a[1].txt"])
    yield Case("unmatched mixed quote pattern restores bytes", "files/q'*'?", ["files/q*?"])
    yield Case("expansion backslash escapes pattern metacharacter", "$x", ["files/back\\*.txt"], x="files/back\\*.txt")
    yield Case("quoted literal backslash with active pattern", r"'files/back\'*.txt", ["files/back\\slash.txt"])
    yield Case("expanded escaped star with active question", "$x", ["files/a*.txt"], x=r"files/a\*?txt")
    # Keep the quoted star protected across the span boundary. Older sh
    # implementations differ here; the backslash filename is a deliberate decoy.
    yield Case("pending expansion escape before quoted star", "$x'*'?.txt", ["files/a*X.txt"], x="files/a\\", differential=False)
    yield Case("escaped slash remains a pathname separator", "$x", ["files/z2", "files/zA"], x=r"files\/z?")
    yield Case("unmatched bracket leaves expansion backslash raw", "$x", [r"files/no[\x"], x=r"files/no[\x")
    yield Case("quoted variable suppresses pattern", '"$x"', ["files/*.txt"], x="files/*.txt")
    yield Case("expanded pattern remains active", "$x", ["files/z2", "files/zA"], x="files/z?")
    yield Case("splitting before pathname expansion", "$x", ["files/z2", "files/zA", "files/missing*"], x="files/z? files/missing*")
    yield Case("set f suppresses only globbing", "$x", ["files/z?", "files/*.txt"], x="files/z? files/*.txt", noglob=True)
    yield Case("set f removes quote syntax", "files/a'?'*.txt", ["files/a?*.txt"], noglob=True)
    yield Case("dotfiles require literal initial dot", "files/.[h]*", ["files/.hidden.txt"])
    yield Case("bracket dot cannot introduce dotfile", "files/[.]hidden*", ["files/[.]hidden*"], differential=False)
    yield Case("quoted initial dot enables hidden match", "files/'.'h*", ["files/.hidden.txt"])
    yield Case("multiple wildcard directory components", "tree/*/sub/*.c", ["tree/one/sub/a.c", "tree/two/sub/b.c"])
    yield Case("literal missing directory retains pattern", "absent/path/*.c", ["absent/path/*.c"])
    yield Case("nondirectory prefix retains pattern", "files/z2/*.c", ["files/z2/*.c"])
    yield Case("hidden directory not entered implicitly", "tree/*/.h", ["tree/one/.h", "tree/two/.h"])
    yield Case("trailing slash filters files", "tree/*/", ["tree/one/", "tree/two/"])
    yield Case("matching final literal must exist", "tree/*/missing", ["tree/*/missing"])
    yield Case("matching final literal remains sorted", "tree/*/sub/a.c", ["tree/one/sub/a.c"])
    # The API retains slash runs; reference shells can normalize later ones.
    yield Case("slash runs retained", "tree//*/sub//*.c", ["tree//one/sub//a.c", "tree//two/sub//b.c"], differential=False)
    yield Case("dot relative prefix retained", "./files/z?", ["./files/z2", "./files/zA"])
    yield Case("absolute path matching", "@ROOT@/files/z?", ["@ROOT@/files/z2", "@ROOT@/files/zA"])
    yield Case("directory symlink traversal", "links/*/sub/*.c", ["links/dir/sub/a.c"])
    yield Case("directory symlink with trailing slash", "links/*/", ["links/dir/"])
    yield Case("dangling symlink is pathname match", "links/dead*", ["links/dead"])
    yield Case("dangling symlink cannot take trailing slash", "links/dead*/", ["links/dead*/"])

    for context in ("assignment", "pattern"):
        yield Case(f"{context} suppresses splitting and globbing", "$x", ["files/*.txt a b"], x="files/*.txt a b", context=context, differential=False)
        yield Case(f"{context} preserves empty scalar", "$x", [""], context=context, differential=False)
    yield Case("assignment removes protection syntax", "'files/*[?]'", ["files/*[?]"], context="assignment", differential=False)
    yield Case("pattern retains quoted wildcard protection", "'files/*[?]'", [r"files/\*\[\?\]"], context="pattern", differential=False)
    yield Case("pattern protects bracket punctuation", "'!-^'", [r"\!\-\^"], context="pattern", differential=False)
    yield Case("pattern protects quoted class name", "[[:'alpha':]]", [r"[\[:alpha:]]"], context="pattern", differential=False)
    yield Case("pattern preserves active syntax", "files/z[!0-9]*", ["files/z[!0-9]*"], context="pattern", differential=False)
    yield Case("pattern preserves active expansion backslash", "$x", [r"back\*"], x="back\\*", context="pattern", differential=False)
    yield Case("pattern protects quoted expansion backslash", '"$x"', [r"back\\\*"], x="back\\*", context="pattern", differential=False)
    yield Case("pattern keeps pending escape before quoted star", "$x'*'", [r"\*"], x="\\", context="pattern", differential=False)
    yield Case("assignment preserves expansion backslash", "$x", ["back\\*"], x="back\\*", context="assignment", differential=False)


def populate(directory):
    (directory / "files").mkdir()
    for filename in FILES:
        (directory / "files" / filename).write_bytes(b"")
    (directory / "patterns").mkdir()
    for filename in ("a", "b", "z", "a]", ":]", ".]", "=]"):
        (directory / "patterns" / filename).write_bytes(b"")
    for name, filename in (("one", "a.c"), ("two", "b.c"), (".hidden", "secret.c")):
        subdirectory = directory / "tree" / name / "sub"
        subdirectory.mkdir(parents=True)
        (subdirectory / filename).write_bytes(b"")
        (subdirectory.parent / ".h").write_bytes(b"")
    (directory / "tree" / "plain-file").write_bytes(b"")
    (directory / "links").mkdir()
    (directory / "links" / "dir").symlink_to("../tree/one", target_is_directory=True)
    (directory / "links" / "dead").symlink_to("../missing")


def run(binary, arguments, directory, timeout):
    status, output, failures = capture(binary, {"args": arguments, "stdin": ""},
        directory, timeout, OUTPUT_LIMIT)
    assert not failures, "; ".join(failures)
    assert status == 0, f"status {status}; stderr={bytes(output['stderr'])[:1000]!r}"
    assert not output["stderr"], f"unexpected stderr: {bytes(output['stderr'])[:1000]!r}"
    return bytes(output["stdout"])


def decode_fields(output):
    header, separator, payload = output.partition(b"\n")
    assert separator and header.isdigit(), f"invalid field count: {output[:1000]!r}"
    values = payload.split(b"\0")
    assert values.pop() == b"", f"missing NUL field terminator: {output[:1000]!r}"
    assert len(values) == int(header), f"field count disagrees with bytes: {output[:1000]!r}"
    return values


def check_case(binary, case, timeout):
    with tempfile.TemporaryDirectory(prefix="cshell-fields-") as temporary:
        directory = Path(temporary)
        populate(directory)
        source = case.source.replace("@ROOT@", temporary)
        expected = [item.replace("@ROOT@", temporary).encode() for item in case.expected]
        arguments = ["expand", case.context, str(int(case.noglob)),
            "unset" if case.ifs is None else "set", case.ifs or "",
            case.x, case.y, source, *case.parameters]
        actual = decode_fields(run(binary, arguments, directory, timeout))
        assert actual == expected, f"expected {expected!r}, got {actual!r}"
        if case.differential:
            # The source expressions are fixed test inputs. All external values
            # are shell-quoted, and the inspector only prints its argv.
            script = f"x={shlex.quote(case.x)}; y={shlex.quote(case.y)}; "
            script += "unset IFS; " if case.ifs is None else f"IFS={shlex.quote(case.ifs)}; "
            script += "set -- " + " ".join(map(shlex.quote, case.parameters)) + "; "
            if case.noglob:
                script += "set -f; "
            script += f"exec {shlex.quote(str(binary))} inspect {source}"
            # capture creates its reserved isolation directories on each run.
            (directory / ".home").rmdir()
            (directory / ".tmp").rmdir()
            reference = decode_fields(run(Path("/bin/sh"), ["-c", script], directory, timeout))
            assert actual == reference, f"reference sh produced {reference!r}, got {actual!r}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", type=Path, default=Path("build/tests/fields_fixture"))
    parser.add_argument("--fault-binary", type=Path)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    binary = args.binary.resolve()
    for candidate in (binary, args.fault_binary):
        if candidate is not None and (not candidate.is_file() or not os.access(candidate, os.X_OK)):
            parser.error(f"not an executable file: {candidate}")
    checks = [(case.name, lambda case=case: check_case(binary, case, args.timeout)) for case in cases()]

    def standalone(candidate, arguments, expected):
        with tempfile.TemporaryDirectory(prefix="cshell-fields-api-") as temporary:
            output = run(candidate, arguments, Path(temporary), args.timeout)
            accepted = expected if isinstance(expected, tuple) else (expected,)
            assert output in accepted, f"unexpected output: {output[:1000]!r}"
            if output.startswith(b"SKIP:"):
                print(output.decode().rstrip())

    checks.append(("invalid API and idempotent cleanup", lambda: standalone(binary, ["invalid"],
        b"PASS: final-field invalid API and cleanup\n")))
    checks.append(("multibyte IFS expansion boundaries", lambda: standalone(binary, ["multibyte"], (
        b"PASS: multibyte IFS respects expansion boundaries\n",
        b"SKIP: multibyte IFS needs an installed UTF-8 locale\n"))))
    if args.fault_binary is not None:
        checks.append(("allocation, I/O, interruption and ownership failures", lambda: standalone(
            args.fault_binary.resolve(), [],
            b"PASS: field/pathname allocation, I/O, interruption, and ownership cleanup\n")))
    failed = 0
    for name, check in checks:
        try:
            check()
        except (AssertionError, OSError, ValueError) as error:
            failed += 1
            print(f"FAIL: {name}: {error}")
        else:
            print(f"PASS: {name}")
    print(f"{len(checks) - failed}/{len(checks)} final-field checks passed")
    return int(failed != 0)


if __name__ == "__main__":
    raise SystemExit(main())
