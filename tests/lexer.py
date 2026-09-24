#!/usr/bin/env python3
"""Bounded replacement lexer API tests; no shell text is ever executed."""

import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile


OUTPUT_LIMIT = 32 * 1024 * 1024


class Fixture:
    def __init__(self, binary, directory, timeout):
        self.binary = binary
        self.directory = directory
        self.timeout = timeout

    def run(self, *arguments, data=b""):
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            process = subprocess.Popen(
                [str(self.binary), *arguments], stdin=subprocess.PIPE,
                stdout=stdout, stderr=stderr, cwd=self.directory,
                start_new_session=True, env=dict(os.environ, LC_ALL="C"),
            )
            try:
                process.communicate(data, timeout=self.timeout)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                raise AssertionError(f"subprocess exceeded {self.timeout}s") from None
            stdout.seek(0)
            stderr.seek(0)
            output = stdout.read(OUTPUT_LIMIT + 1)
            errors = stderr.read(OUTPUT_LIMIT + 1)
            assert len(output) <= OUTPUT_LIMIT, "stdout exceeded output limit"
            assert len(errors) <= OUTPUT_LIMIT, "stderr exceeded output limit"
            assert process.returncode == 0, (
                f"fixture status {process.returncode}, stderr={errors[:2000]!r}"
            )
            assert not errors, f"unexpected diagnostic: {errors[:2000]!r}"
            return output

    def scan(self, data, mode="full"):
        output = self.run("scan", mode, data=data)
        try:
            result = json.loads(output)
        except ValueError:
            raise AssertionError(f"invalid JSON: {output[:1000]!r}") from None
        validate_tokens(result["tokens"], data)
        return result


def name(value):
    return value.lower().replace("csh_token_", "").replace("csh_fragment_", "").replace("csh_quote_", "").replace("-", "_")


def positions(data):
    result = [[0, 1, 1]]
    line, column = 1, 1
    for offset, byte in enumerate(data, 1):
        if byte == 10:
            line, column = line + 1, 1
        else:
            column += 1
        result.append([offset, line, column])
    return result


def validate_tokens(tokens, data):
    at = positions(data)
    previous_end = 0
    for token in tokens:
        start, end = token["start"][0], token["end"][0]
        assert previous_end <= start < end <= len(data), token
        assert token["start"] == at[start] and token["end"] == at[end], token
        assert token["source"] == "fixture-source", token
        assert token["raw"].encode("latin1") == data[start:end], token
        previous_end = end
        fragments = token["fragments"]
        if name(token["kind"]) == "word":
            assert fragments, "word must carry quote/fragment evidence"
        for index, fragment in enumerate(fragments):
            begin, finish = fragment["begin"], fragment["end"]
            assert 0 <= begin <= finish <= end - start, fragment
            assert fragment["start"] == at[start + begin], fragment
            assert fragment["finish"] == at[start + finish], fragment
            parent_index = fragment["parent"]
            if parent_index is not None:
                assert 0 <= parent_index < index, "fragment parent must precede child"
                parent = fragments[parent_index]
                assert parent["begin"] <= begin <= finish <= parent["end"], fragment


def simplified(result):
    return [(name(token["kind"]), token["raw"]) for token in result["tokens"]]


def check_scan(fixture, data, expected, commands=0, fragments=None, modes=("full", "line", "byte")):
    baseline = None
    for mode in modes:
        result = fixture.scan(data, mode)
        assert result["error"] is None, result
        assert result["eof_repeats"] == 3, result
        assert result["commands"] == commands, result
        actual = simplified(result)
        assert actual == expected, f"{mode}: expected {expected!r}, got {actual!r}"
        if baseline is not None:
            assert result == baseline, f"{mode} token metadata differs from full feed"
        baseline = result
        if fragments is not None:
            fragments(result["tokens"])


def check_fragments(required):
    """Require semantic spans, while allowing harmless text coalescing choices."""
    def check(tokens):
        found = set()
        for token in tokens:
            for fragment in token["fragments"]:
                found.add((name(fragment["kind"]), name(fragment["quote"]),
                    token["raw"][fragment["begin"]:fragment["end"]]))
        for expected in required:
            assert expected in found, f"missing fragment {expected!r}: {found!r}"
    return check


def check_nested(tokens):
    word = tokens[0]
    fragments = word["fragments"]
    parameter = [i for i, fragment in enumerate(fragments)
        if name(fragment["kind"]) == "parameter"]
    assert len(parameter) == 3, fragments
    assert fragments[parameter[1]]["parent"] == parameter[0], fragments
    assert fragments[parameter[2]]["parent"] == parameter[1], fragments


def without_fragments(forbidden):
    def check(tokens):
        for token in tokens:
            for fragment in token["fragments"]:
                item = (name(fragment["kind"]), name(fragment["quote"]),
                    token["raw"][fragment["begin"]:fragment["end"]])
                assert item not in forbidden, f"unexpected fragment {item!r}"
    return check


def cases(fixture):
    simple = (
        ("empty", b"", []),
        ("blanks", b" \t \t", []),
        ("words and final word", b"one\t two  three", [("word", "one"), ("word", "two"), ("word", "three")]),
        ("physical newlines", b"\nfirst\n\nlast", [("newline", "\n"), ("word", "first"), ("newline", "\n"), ("newline", "\n"), ("word", "last")]),
        ("ordinary shell syntax stays words", b"if A=x { } ~ % : 2 2x", [("word", value) for value in ("if", "A=x", "{", "}", "~", "%", ":", "2", "2x")]),
        ("comments at boundaries", b"# head\nword#inside x #tail\nend", [("newline", "\n"), ("word", "word#inside"), ("word", "x"), ("newline", "\n"), ("word", "end")]),
        ("comments after operators", b"x;# comment\ny", [("word", "x"), ("semi", ";"), ("newline", "\n"), ("word", "y")]),
        ("comments retain literal newline", b"# comment\\\nnext", [("newline", "\n"), ("word", "next")]),
        ("quoted and escaped hashes", b"'#x' \"#y\" \\#z", [("word", "'#x'"), ("word", '"#y"'), ("word", "\\#z")]),
        ("continuation alone is no word", b"\\\n \n", [("newline", "\n")]),
        ("joined continued word", b"ab\\\ncd", [("word", "ab\\\ncd")]),
        ("continued comment boundary", b"\\\n# comment\n''#literal", [("newline", "\n"), ("word", "''#literal")]),
        ("carriage return is ordinary text", b"a\rb", [("word", "a\rb")]),
        ("high bytes preserved", b"x\xffy", [("word", "x\xffy")]),
    )
    for label, data, expected in simple:
        yield label, lambda data=data, expected=expected: check_scan(fixture, data, expected)

    operators = (
        ("&&", "and_if"), ("||", "or_if"), (";;", "dsemi"), (";&", "semi_and"),
        ("<<", "dless"), (">>", "dgreat"), ("<&", "less_and"), (">&", "great_and"),
        ("<>", "less_great"), ("<<-", "dless_dash"), (">|", "clobber"),
        ("|", "pipe"), ("&", "ampersand"), (";", "semi"), ("(", "lparen"),
        (")", "rparen"), ("<", "less"), (">", "great"),
    )
    data = " ".join(raw for raw, _ in operators).encode()
    expected = [(kind, raw) for raw, kind in operators]
    yield "all POSIX operators and longest matches", lambda data=data, expected=expected: check_scan(fixture, data, expected)
    yield "adjacent operators", lambda: check_scan(fixture, b"&&&|||;;;;&<<<<-",
        [("and_if", "&&"), ("ampersand", "&"), ("or_if", "||"), ("pipe", "|"),
         ("dsemi", ";;"), ("dsemi", ";;"), ("ampersand", "&"),
         ("dless", "<<"), ("dless_dash", "<<-")])
    yield "longest match across physical continuations", lambda: check_scan(fixture,
        b"&\\\n& <\\\n<\\\n- >\\\n|", [("and_if", "&\\\n&"),
        ("dless_dash", "<\\\n<\\\n-"), ("clobber", ">\\\n|")])
    yield "all empty quoted words stay present", lambda: check_scan(fixture,
        b"'' \"\" $''", [("word", "''"), ("word", '""'), ("word", "$''")])
    quotes = b"a''\"\"$''b 'single\\text' \"double $x\" $'dollar\\ntext'"
    yield "all quote modes and empty adjacent quotes", lambda: check_scan(fixture, quotes,
        [("word", "a''\"\"$''b"), ("word", "'single\\text'"), ("word", '"double $x"'),
         ("word", "$'dollar\\ntext'")], fragments=check_fragments({
             ("quoted", "single", "''"), ("quoted", "double", '""'),
             ("quoted", "dollar_single", "$''"),
             ("quoted", "single", "'single\\text'"),
             ("quoted", "dollar_single", "$'dollar\\ntext'"),
         }))
    yield "quote delimiters and literal operators", lambda: check_scan(fixture,
        b"'a | ; \" x' \"b ' && y\" $'a\\'b'", [("word", "'a | ; \" x'"),
        ("word", '"b \' && y"'), ("word", "$'a\\'b'")])
    yield "escape context distinction", lambda: check_scan(fixture,
        b"a\\ b \"a\\q\\$\\`\\\"\\\\b\" 'a\\b'", [("word", "a\\ b"),
        ("word", '"a\\q\\$\\`\\"\\\\b"'), ("word", "'a\\b'")], fragments=check_fragments({
            ("escape", "none", "\\ "), ("escape", "double", "\\$"),
            ("escape", "double", "\\`"), ("escape", "double", '\\"'),
            ("escape", "double", "\\\\"),
        }))
    yield "multiline quoted word retains newlines", lambda: check_scan(fixture,
        b"'first\nsecond' \"third\\\nfourth\"", [("word", "'first\nsecond'"),
        ("word", '"third\\\nfourth"')], fragments=check_fragments({
            ("continuation", "double", "\\\n"),
        }))
    yield "nested parameter expansion tree", lambda: check_scan(fixture,
        b"${a:-${b:-${c}}}", [("word", "${a:-${b:-${c}}}")], fragments=check_nested)
    yield "parameter quotes shield braces", lambda: check_scan(fixture,
        b"${x:-\"}\"}${y:-'}'}", [("word", '${x:-"}"}${y:-\'}\'}')])
    yield "quoted parameter pattern resets quote context", lambda: check_scan(fixture,
        b'"${x#\'}\'}"', [("word", '"${x#\'}\'}"')], fragments=check_fragments({
            ("parameter", "double", "${x#'}'}"), ("quoted", "single", "'}'"),
        }))
    yield "quoted parameter default retains quote context", lambda: check_scan(fixture,
        b'"${x:-\'}\'}"', [("word", '"${x:-\'}\'}"')], fragments=check_fragments({
            ("parameter", "double", "${x:-'}"),
        }))
    yield "quoted parameter escaped brace stays inside expansion", lambda: check_scan(fixture,
        b'"${x:-\\}}"', [("word", '"${x:-\\}}"')], fragments=check_fragments({
            ("parameter", "double", "${x:-\\}}"), ("escape", "double", "\\}"),
        }))
    # POSIX leaves pattern-removal VALUES for # unspecified; this asserts only
    # the chosen lexical quote boundaries, without expanding that parameter.
    yield "hash parameter pattern lexical context", lambda: check_scan(fixture,
        b'"${#%\'}\'}"', [("word", '"${#%\'}\'}"')], fragments=check_fragments({
            ("parameter", "double", "${#%'}'}"), ("quoted", "single", "'}'"),
        }))
    yield "simple names and special parameters retain spelling", lambda: check_scan(fixture,
        b"$name $1 $10 $@ $* $# $? $- $$ $! $ \\$name", [("word", value) for value in
        ("$name", "$1", "$10", "$@", "$*", "$#", "$?", "$-", "$$", "$!", "$", "\\$name")],
        fragments=check_fragments({("parameter", "none", "$name"),
            ("parameter", "none", "$1"), ("parameter", "none", "$@"),
            ("escape", "none", "\\$")}))
    yield "dollar-single syntax inside double quote stays literal", lambda: check_scan(fixture,
        b'"$\'x\'"', [("word", '"$\'x\'"')],
        fragments=without_fragments({("quoted", "dollar_single", "$'x'")}))
    yield "continuations in expansion delimiters", lambda: check_scan(fixture,
        b"$\\\n{x} $\\\n(\\\n(1+2)\\\n) $\\\n(echo x)", [("word", "$\\\n{x}"),
        ("word", "$\\\n(\\\n(1+2)\\\n)"), ("word", "$\\\n(echo x)")], commands=1)
    yield "arithmetic nesting and substitution", lambda: check_scan(fixture,
        b"$((1 + (2 * 3) + ${n:-4}))", [("word", "$((1 + (2 * 3) + ${n:-4}))")],
        fragments=check_fragments({("arithmetic", "none", "$((1 + (2 * 3) + ${n:-4}))")}))
    for data, commands, kind in (
        (b"$((echo hi); )", 1, "command"),
        (b"$((echo hi))", 1, "command"),
        (b"$((echo $(echo hi)); )", 3, "command"),
        (b"$((echo $((1+2))); )", 1, "command"),
        (b"$((1/0))", 0, "arithmetic"),
        (b"$((n=2, n+1))", 0, "arithmetic"),
        (b"$((1${n:-2} + ${v}suffix))", 0, "arithmetic"),
    ):
        yield f"arithmetic-first replay {data!r}", lambda data=data, commands=commands, kind=kind: check_scan(
            fixture, data, [("word", data.decode())], commands=commands,
            fragments=check_fragments({(kind, "none", data.decode())}))
    yield "replay across quoted physical continuation", lambda: check_scan(fixture,
        b'"pre$\\\n(\\\n(echo\\\n hi); )post"',
        [("word", '"pre$\\\n(\\\n(echo\\\n hi); )post"')], commands=1,
        fragments=without_fragments({("arithmetic", "double", "$((echo hi); )")}))
    yield "command and generic subshell parentheses", lambda: check_scan(fixture,
        b"pre$(echo (one) $(echo two))post", [("word", "pre$(echo (one) $(echo two))post")], commands=2,
        fragments=check_fragments({("command", "none", "$(echo (one) $(echo two))")}))
    yield "command substitution in double quote", lambda: check_scan(fixture,
        b'"a$(printf \'%s\' \')\')b"', [("word", '"a$(printf \'%s\' \')\')b"')], commands=1,
        fragments=check_fragments({("command", "double", "$(printf '%s' ')')")}))
    yield "command within parameter and arithmetic", lambda: check_scan(fixture,
        b"${a:-$(echo x)}$((1 + $(echo 2)))", [("word", "${a:-$(echo x)}$((1 + $(echo 2)))")], commands=2)
    yield "comment parenthesis cannot end substitution", lambda: check_scan(fixture,
        b"$(# comment )\necho x)", [("word", "$(# comment )\necho x)")], commands=1)
    yield "backquote preservation and escaped delimiter", lambda: check_scan(fixture,
        b"pre`echo \\`x\\``post", [("word", "pre`echo \\`x\\``post")],
        fragments=check_fragments({("backquote", "none", "`echo \\`x\\``")}))
    yield "unquoted backquote ordinary escapes remain text", lambda: check_scan(fixture,
        b"`echo \\q`", [("word", "`echo \\q`")],
        fragments=check_fragments({("text", "none", "echo \\q")}))
    yield "quoted backquote escaped quote metadata", lambda: check_scan(fixture,
        b'"`echo \\"`"', [("word", '"`echo \\"`"')],
        fragments=check_fragments({("escape", "double", '\\"')}))
    yield "unquoted backquote continuation is retained for later parsing", lambda: check_scan(fixture,
        b"`echo a\\\nb`", [("word", "`echo a\\\nb`")],
        fragments=check_fragments({("text", "none", "echo a\\\nb")}))
    yield "quoted backquote continuation has distinct metadata", lambda: check_scan(fixture,
        b'"`echo a\\\nb`"', [("word", '"`echo a\\\nb`"')],
        fragments=check_fragments({("continuation", "double", "\\\n")}))

    errors = (
        (b"'unterminated", 0), (b'"unterminated', 0), (b"$'unterminated", 0),
        (b"${x:-value", 0), (b"$((1 + 2)", 0), (b"`echo x", 0),
        (b"$((1 + ${unfinished", 7), (b"$((1 + $(unfinished", 7),
        (b"$(echo x", 0), (b"abc\\", 3), (b"ok\n  'bad", 5),
        (b"'outer ${literal", 0), (b"before\x00after", 6),
    )
    for data, opening in errors:
        def check_error(data=data, opening=opening):
            baseline = None
            for mode in ("full", "line", "byte"):
                result = fixture.scan(data, mode)
                error = result["error"]
                assert error and error["message"] and error["status"] == 2, result
                assert error["errno"] == 0, result
                assert error["position"] == positions(data)[opening], result
                if baseline is not None:
                    assert result == baseline, f"{mode} error differs from full feed"
                baseline = result
        yield f"incomplete or invalid source {data!r}", check_error

    yield "ownership, MORE contexts, grammar-selected case and heredoc", lambda: expect(
        fixture.run("contracts") == b"ok\n", "contract fixture output")

    def large_word():
        data = b"x" * 200000
        check_scan(fixture, data, [("word", data.decode())])
    yield "200KB token", large_word

    def many_words():
        check_scan(fixture, b"x " * 10000, [("word", "x")] * 10000, modes=("full", "line"))
    yield "10000 tokens without fixed token limit", many_words

    def deep_parameters():
        data = b"${x:-" * 600 + b"value" + b"}" * 600
        check_scan(fixture, data, [("word", data.decode())], modes=("full", "byte"))
    yield "600 nested parameter frames", deep_parameters

    def deep_commands():
        data = b"$(echo " * 200 + b"value" + b")" * 200
        check_scan(fixture, data, [("word", data.decode())], commands=200, modes=("full", "byte"))
    yield "200 parser-assisted command frames", deep_commands

    def continued_opener():
        data = b"$" + b"\\\n" * 10000 + b"{x}"
        check_scan(fixture, data, [("word", data.decode())], modes=("full", "line"))
    yield "10000 physical continuations within expansion opener", continued_opener

    def no_execution():
        data = b"$(touch lexer-executed) `touch lexer-executed` ${HOME} $((2+3))"
        check_scan(fixture, data, [("word", value) for value in
            ("$(touch lexer-executed)", "`touch lexer-executed`", "${HOME}", "$((2+3))")], commands=1)
        assert not (Path(fixture.directory) / "lexer-executed").exists(), "lexer executed source text"
    yield "substitutions preserve spelling without execution", no_execution

    def repeated():
        data = b"word '${literal}' $(echo x)\n"
        first = fixture.scan(data)
        for _ in range(10):
            assert fixture.scan(data) == first, "fresh scan retained old state"
    yield "repeated isolated scans", repeated


def expect(condition, message):
    assert condition, message


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="build/tests/lexer_fixture", type=Path)
    parser.add_argument("--fault-binary", type=Path)
    parser.add_argument("--timeout", type=float, default=10.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    binary = args.binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"not an executable file: {binary}")
    failed = 0
    with tempfile.TemporaryDirectory(prefix="cshell-lexer-") as temporary:
        fixture = Fixture(binary, temporary, args.timeout)
        checks = list(cases(fixture))
        if args.fault_binary is not None:
            faults = Fixture(args.fault_binary.resolve(), temporary, args.timeout)
            checks.append(("allocation failure sweep and cleanup", lambda: faults.run()))
        for label, check in checks:
            try:
                check()
            except (AssertionError, KeyError, IndexError, OSError) as error:
                failed += 1
                print(f"FAIL: {label}: {str(error)[:3000]}")
            else:
                print(f"PASS: {label}")
        print(f"{len(checks) - failed}/{len(checks)} lexer checks passed")
    return int(failed != 0)


if __name__ == "__main__":
    raise SystemExit(main())
