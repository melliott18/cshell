#!/usr/bin/env python3
"""Bounded structural tests for replacement parser/AST APIs; never execute source."""

import argparse
import json
import math
import os
from pathlib import Path
import tempfile

from lexer import Fixture, positions


def name(value):
    return value.lower().replace("csh_ast_", "").replace("csh_token_", "").replace("csh_fragment_", "").replace("csh_quote_", "").replace("-", "_")


class ParserFixture(Fixture):
    def parse(self, data, outcome="eof"):
        output = self.run("parse", data=data)
        try:
            result = json.loads(output)
        except ValueError:
            raise AssertionError(f"invalid JSON: {output[:1000]!r}") from None
        assert result["result"] == outcome, result
        assert result["repeats"] == 3, result
        if outcome == "eof":
            assert result["error"] is None, result
        else:
            error = result["error"]
            assert error["message"] and error["status"] == 2 and error["errno"] == 0, result
            assert error["position"] in positions(data), result
        validate(result["trees"], data)
        return result


def validate(trees, data):
    at = positions(data)
    nodes = list(trees)
    while nodes:
        node = nodes.pop()
        if node is None:
            continue
        kind = name(node["kind"])
        words = []
        if kind == "simple":
            words += [item["word"] for item in node["words"]]
        elif kind == "pipeline":
            nodes.extend(node["commands"])
        elif kind in ("and", "or"):
            nodes += [node["left"], node["right"]]
        elif kind == "list":
            nodes += [item["command"] for item in node["items"]]
        elif kind in ("brace", "subshell"):
            nodes.append(node["body"])
        else:
            assert False, f"unsupported published node {kind}"
        for redir in node["redirections"]:
            words.append(redir["operand"])
            if redir["io_number"] is not None:
                validate_token(redir["io_number"], data, at)
            if redir["delimiter"] is not None:
                assert redir["body"] is not None, "published pending heredoc"
                for field in ("body_start", "body_end"):
                    assert redir[field] in at, redir
        for word in words:
            token = word["token"]
            validate_token(token, data, at)
            for sub in word["substitutions"]:
                fragment = token["fragments"][sub["fragment"]]
                assert name(fragment["kind"]) == "command", sub
                assert (sub["begin"], sub["end"]) == (fragment["begin"], fragment["end"]), sub
                nodes.append(sub["body"])


def validate_token(token, data, at):
    start, end = token["start"][0], token["end"][0]
    assert 0 <= start < end <= len(data), token
    assert token["start"] == at[start] and token["end"] == at[end], token
    assert token["source"] == "fixture-source", token
    assert token["raw"].encode("latin1") == data[start:end], token
    for index, fragment in enumerate(token["fragments"]):
        begin, finish = fragment["begin"], fragment["end"]
        assert 0 <= begin <= finish <= end - start, fragment
        assert fragment["start"] == at[start + begin] and fragment["finish"] == at[start + finish], fragment
        if fragment["parent"] is not None:
            assert 0 <= fragment["parent"] < index, fragment


def command(tree):
    assert name(tree["kind"]) == "list" and len(tree["items"]) == 1, tree
    return tree["items"][0]["command"]


def one(fixture, data):
    result = fixture.parse(data)
    assert len(result["trees"]) == 1, result
    return command(result["trees"][0])


def raw_words(node):
    assert name(node["kind"]) == "simple", node
    return [(item["word"]["token"]["raw"], item["assignment"]) for item in node["words"]]


def shape(node):
    kind = name(node["kind"])
    if kind == "simple":
        return tuple(item[0] for item in raw_words(node))
    if kind in ("and", "or"):
        return (kind, shape(node["left"]), shape(node["right"]))
    if kind == "pipeline":
        return ("pipeline", node["negated"], tuple(shape(child) for child in node["commands"]))
    if kind == "list":
        return ("list", tuple((shape(item["command"]), item["separator"]) for item in node["items"]))
    return (kind, shape(node["body"]))


def expect(condition, message):
    assert condition, message


def cases(fixture):
    for label, data in (("empty input", b""), ("blank input", b" \t\n\n"),
                        ("comments only", b"#one\n # two"), ("continuation only", b"\\\n\n")):
        yield label, lambda data=data: expect(fixture.parse(data)["trees"] == [], "expected clean EOF")

    def basic():
        result = fixture.parse(b"one\ntwo; three &\nfour")
        assert [shape(tree) for tree in result["trees"]] == [
            ("list", ((("one",), "newline"),)),
            ("list", ((("two",), "semi"), (("three",), "ampersand"))),
            ("list", ((("four",), "end"),)),
        ], result
    yield "complete commands and separator kinds", basic

    def precedence():
        result = fixture.parse(b"a || b && c | d; e & ! f\n")
        assert shape(result["trees"][0]) == ("list", (
            (("and", ("or", ("a",), ("b",)), ("pipeline", False, (("c",), ("d",)))), "semi"),
            (("e",), "ampersand"), (("pipeline", True, (("f",),)), "newline"))), result
    yield "pipeline AND/OR and list precedence", precedence
    yield "AND/OR associate left equally", lambda: expect(
        shape(one(fixture, b"a && b || c && d")) ==
        ("and", ("or", ("and", ("a",), ("b",)), ("c",)), ("d",)), "incorrect associativity")
    yield "negation applies to whole pipeline", lambda: expect(
        shape(one(fixture, b"! a | b && c")) ==
        ("and", ("pipeline", True, (("a",), ("b",))), ("c",)), "incorrect negation")
    yield "newlines continue pipeline and AND/OR", lambda: expect(
        shape(one(fixture, b"a |\n b &&\n c ||\n d\n")) ==
        ("or", ("and", ("pipeline", False, (("a",), ("b",))), ("c",)), ("d",)), "lost continuation")

    def groups():
        node = one(fixture, b"(a; b &) 3>out | { c && d; } <in\n")
        assert name(node["kind"]) == "pipeline", node
        left, right = node["commands"]
        assert name(left["kind"]) == "subshell" and name(right["kind"]) == "brace", node
        assert shape(left["body"]) == ("list", ((("a",), "semi"), (("b",), "ampersand"))), left
        assert shape(right["body"]) == ("list", ((("and", ("c",), ("d",)), "semi"),)), right
        assert left["redirections"][0]["io_number"]["raw"] == "3", left
        assert right["redirections"][0]["operand"]["token"]["raw"] == "in", right
    yield "subshell and brace groups with trailing redirections", groups
    yield "brace close after self-delimited compound", lambda: expect(
        name(one(fixture, b"{ (echo x) }\n")["kind"]) == "brace", "brace compound close")

    assignments = (
        (b"A=1 B='two'", [("A=1", True), ("B='two'", True)]),
        (b">out A=1 2>&1 B=x echo C=3", [("A=1", True), ("B=x", True), ("echo", False), ("C=3", False)]),
        (b"A\\\nB=x", [("A\\\nB=x", True)]),
        (b"A\\=x", [("A\\=x", False)]),
        (b"'A'=x", [("'A'=x", False)]),
        (b"1A=x B=y", [("1A=x", False), ("B=y", False)]),
        (b"A=1 if", [("A=1", True), ("if", False)]),
        (b">out if", [("if", False)]),
    )
    for data, expected in assignments:
        yield f"assignment classification {data!r}", lambda data=data, expected=expected: expect(
            raw_words(one(fixture, data)) == expected, "assignment/command-word classification")
    yield "redirections without command name", lambda: expect(
        raw_words(one(fixture, b">one 2>&1 <input")) == [], "standalone redirections")

    def redirections():
        node = one(fixture, b"echo <a >b >>c <&0 >&2 <>d >|e 12>f\n")
        redirs = node["redirections"]
        assert [name(redir["operator"]) for redir in redirs] == [
            "less", "great", "dgreat", "less_and", "great_and", "less_great", "clobber", "great"], redirs
        assert [redir["operand"]["token"]["raw"] for redir in redirs] == list("abc02def"), redirs
        assert [redir["io_number"]["raw"] if redir["io_number"] else None for redir in redirs] == [None] * 7 + ["12"], redirs
    yield "ordered redirections preserve every operator", redirections
    for data, words, descriptor in (
        (b"echo 2>x", ["echo"], "2"),
        (b"echo 2 >x", ["echo", "2"], None),
        (b"echo '2'>x", ["echo", "'2'"], None),
        (b'echo "2">x', ["echo", '"2"'], None),
        (b"echo \\2>x", ["echo", "\\2"], None),
        (b"echo 2\\\n>x", ["echo"], "2\\\n"),
        (b"echo 2x>x", ["echo", "2x"], None),
        (b"echo 999999999999999999999>x", ["echo"], "999999999999999999999"),
    ):
        def descriptor_check(data=data, words=words, descriptor=descriptor):
            node = one(fixture, data)
            assert [word for word, _ in raw_words(node)] == words, node
            token = node["redirections"][0]["io_number"]
            assert (token["raw"] if token else None) == descriptor, node
        yield f"descriptor adjacency {data!r}", descriptor_check

    for data, expected in (
        (b"echo } ! if {", ["echo", "}", "!", "if", "{"]),
        (b"'if' \\! \"{\"", ["'if'", "\\!", '"{"']),
        (b"echo >if <}", ["echo"]),
    ):
        yield f"reserved-word context {data!r}", lambda data=data, expected=expected: expect(
            [word for word, _ in raw_words(one(fixture, data))] == expected, "reserved word lost literal context")

    def heredocs():
        node = one(fixture, b"cat <<A <<-'B' <<C\\ D\n$x $(not grammar\nA\n\t$y\\\n\tB\nlast\nC D\n")
        redirs = node["redirections"]
        assert [(name(r["operator"]), r["delimiter"], r["quoted"], r["body"]) for r in redirs] == [
            ("dless", "A", False, "$x $(not grammar\n"),
            ("dless_dash", "B", True, "$y\\\n"),
            ("dless", "C D", True, "last\n"),
        ], redirs
    yield "multiple heredocs retain source order and quoting", heredocs
    for data, delimiter, body, quoted in (
        (b"cat <<''\nbody\n\n", "", "body\n", True),
        (b'cat <<"END"\n$x\nEND\n', "END", "$x\n", True),
        (b"cat <<E'ND'\ntext\nEND\n", "END", "text\n", True),
        (b"cat <<END\nEND", "END", "", False),
        (b"cat <<-END\n\t\ttext\n \tstay\n\tEND\n", "END", "text\n \tstay\n", False),
        (b"cat <<E\\\nND\nbody\nEND\n", "END", "body\n", False),
        (b"cat <<END\nE\\\nND\n", "END", "", False),
        (b"cat <<'END'\nE\\\nND\nEND\n", "END", "E\\\nND\n", True),
        (b"cat <<$'E\\x4eD'\nbody\nEND\n", "END", "body\n", True),
        (b"cat <<$'E\\tD'\nbody\nE\tD\n", "E\tD", "body\n", True),
        (b"cat <<$'END\\0ignored'X\nbody\nENDX\n", "ENDX", "body\n", True),
        (b"cat <<-END\n\tfoo\\\n\tbar\nEND\n", "END", "foo\\\n\tbar\n", False),
        (b"cat <<-END\n\t\\\n\tfoo\nEND\n", "END", "\\\nfoo\n", False),
        (b"cat <<-'END'\n\tfoo\\\n\tbar\nEND\n", "END", "foo\\\nbar\n", True),
        (b"cat <<-END\n\tE\\\n\tND\nEND\n", "END", "E\\\n\tND\n", False),
        (b"cat <<${EOF}\nbody\n${EOF}\n", "${EOF}", "body\n", False),
        (b"cat <<${E\\\nOF}\nbody\n${EOF}\n", "${EOF}", "body\n", False),
        (b"cat <<$(echo)\nbody\n$(echo)\n", "$(echo)", "body\n", False),
        (b"cat <<$X\nbody\n$X\n", "$X", "body\n", False),
        (b'cat <<${x:-"EOF"}\nbody\n${x:-EOF}\n', "${x:-EOF}", "body\n", True),
        (b'cat <<$(echo "EOF")\nbody\n$(echo EOF)\n', "$(echo EOF)", "body\n", True),
        (b"cat <<$(ec\\\nho)\nbody\n$(echo)\n", "$(echo)", "body\n", False),
        (b'cat <<"${x}"\nbody\n${x}\n', "${x}", "body\n", True),
        (b'cat <<\'$(echo "EOF")\'\nbody\n$(echo "EOF")\n', '$(echo "EOF")', "body\n", True),
        (b'cat <<"$(echo \'EOF\')"\nbody\n$(echo \'EOF\')\n', "$(echo 'EOF')", "body\n", True),
        (b'cat <<"${x:-\'EOF\'}"\nbody\n${x:-\'EOF\'}\n', "${x:-'EOF'}", "body\n", True),
        (b"cat <<${x:-'EOF'}\nbody\n${x:-EOF}\n", "${x:-EOF}", "body\n", True),
    ):
        def heredoc(data=data, delimiter=delimiter, body=body, quoted=quoted):
            redir = one(fixture, data)["redirections"][0]
            assert (redir["delimiter"], redir["body"], redir["quoted"]) == (delimiter, body, quoted), redir
        yield f"heredoc delimiter/body {data!r}", heredoc

    def substitution():
        data = b"echo prefix$(a && (b; c))suffix ${x:-$(d)} $((1+$(e)))\n"
        node = one(fixture, data)
        words = node["words"]
        assert len(words) == 4, node
        assert all(len(item["word"]["substitutions"]) == 1 for item in words[1:]), words
        sub = words[1]["word"]["substitutions"][0]
        inner = command(sub["body"])
        assert name(inner["kind"]) == "and" and name(inner["right"]["kind"]) == "subshell", inner
    yield "nested substitutions preserve ASTs and fragment identity", substitution
    yield "empty command substitution", lambda: one(fixture, b"echo $()\n")

    def nested_heredoc():
        data = b"cat <<OUT $(cat <<IN\ninside ) $(unparsed\nIN\n)\noutside\nOUT\n"
        node = one(fixture, data)
        outer = node["redirections"][0]
        inner = command(node["words"][1]["word"]["substitutions"][0]["body"])["redirections"][0]
        assert outer["body"] == "outside\n" and inner["body"] == "inside ) $(unparsed\n", node
        assert inner["body_start"][0] < outer["body_start"][0], node
    yield "nested substitution heredoc queue resumes outer queue", nested_heredoc
    for data in (b"cat <<A |\nbody\nA\nnext\n", b"cat <<A &&\nbody\nA\nnext\n"):
        yield f"heredoc before continuation {data!r}", lambda data=data: expect(
            one(fixture, data)["left"]["redirections"][0]["body"] == "body\n"
            if b"&&" in data else
            one(fixture, data)["commands"][0]["redirections"][0]["body"] == "body\n", "continuation heredoc")

    invalid = (
        (b";", 0), (b"&", 0), (b"| echo", 0), (b"echo && || next", 8),
        (b"echo >;", 6), (b"echo | ;", 7), (b")", 0),
        (b"()", 1), (b"{ ; }", 2), (b"(echo) trailing", 7),
        (b"echo ;; next", 5), (b"if true", 0), (b"i\\\nf true", 0),
        (b"echo\x00bad", 4), (b"echo\n  ;", 7),
        (b"echo $(cat <<EOF) tail\nEOF\n", 16),
    )
    for data, offset in invalid:
        def error(data=data, offset=offset):
            result = fixture.parse(data, "error")
            assert result["error"]["position"] == positions(data)[offset], result
            assert len(result["trees"]) == (1 if data.startswith(b"echo\n") else 0), result
        yield f"invalid syntax diagnostic {data!r}", error
    for data in (b"echo |", b"echo &&", b"echo ||\n", b"!", b"(", b"(echo", b"{ echo;",
                 b"{ echo }", b"echo >", b"echo 'unterminated", b"echo ${x", b"echo $(other",
                 b'echo "unterminated', b"echo $'unterminated", b"echo $((1+2)",
                 b"echo `unterminated", b"echo trailing\\", b"cat <<$'E\\nD'\nE\nD\n",
                 b"cat <<A\nbody\n", b"cat <<A", b"cat <<A <<B\none\nA\n"):
        yield f"incomplete construct {data!r}", lambda data=data: expect(
            fixture.parse(data, "incomplete")["trees"] == [], "incomplete tree was published")

    yield "complete commands never read following input", lambda: expect(
        fixture.run("contracts") == b"ok\n", "boundary and ownership contracts")
    yield "parser rejects already-consumed input", lambda: expect(
        fixture.run("consumed") == b"ok\n", "consumed source contract")
    yield "input read failure preserves sticky diagnostic", lambda: expect(
        fixture.run("read-failure") == b"ok\n", "read failure contract")
    yield "200KB command word", lambda: expect(
        raw_words(one(fixture, b"x" * 200000)) == [("x" * 200000, False)], "long token")
    yield "10000 command words", lambda: expect(
        len(raw_words(one(fixture, b"x " * 10000))) == 10000, "word vector growth")
    yield "1000 pipeline members", lambda: expect(
        len(one(fixture, b" | ".join([b"x"] * 1000))["commands"]) == 1000, "pipeline vector growth")
    yield "2000 sequential commands", lambda: expect(
        len(fixture.parse(b";".join([b"x"] * 2000))["trees"][0]["items"]) == 2000, "list vector growth")
    yield "10000 AND/OR commands and iterative destruction", lambda: expect(
        fixture.run("chain", data=b"x" + b" && x || x" * 4999 + b" && x\n") == b"10000\n",
        "binary chain growth or associativity")
    yield "48 nested subshell groups", lambda: one(fixture, b"(" * 48 + b"x" + b")" * 48)
    yield "nesting limit gives structured error", lambda: fixture.parse(b"(" * 200 + b"x" + b")" * 200, "error")

    def no_execution():
        one(fixture, b"echo $(touch parser-executed) `touch parser-executed` > parser-created\n")
        assert not (Path(fixture.directory) / "parser-executed").exists(), "substitution executed"
        assert not (Path(fixture.directory) / "parser-created").exists(), "redirection executed"
    yield "parse never executes substitutions or redirections", no_execution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", nargs="?", default="build/tests/parser_fixture", type=Path)
    parser.add_argument("--fault-binary", type=Path)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    binary = args.binary.resolve()
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"not an executable file: {binary}")
    failed = 0
    with tempfile.TemporaryDirectory(prefix="cshell-parser-") as temporary:
        fixture = ParserFixture(binary, temporary, args.timeout)
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
        print(f"{len(checks) - failed}/{len(checks)} parser checks passed")
    return int(failed != 0)


if __name__ == "__main__":
    raise SystemExit(main())
