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
        elif kind == "if":
            assert node["branches"], node
            for branch in node["branches"]:
                nodes += [branch["condition"], branch["body"]]
            nodes.append(node["else_body"])
        elif kind == "for":
            words += [node["name"], *node["words"]]
            assert node["has_in"] or not node["words"], node
            nodes.append(node["body"])
        elif kind in ("while", "until"):
            nodes += [node["condition"], node["body"]]
        elif kind == "case":
            words.append(node["word"])
            for item in node["items"]:
                assert item["patterns"], item
                words += item["patterns"]
                assert name(item["body"]["kind"]) == "list", item
                nodes.append(item["body"])
                assert item["terminator"] in ("end", "break", "fallthrough"), item
                if item["terminator"] != "end":
                    for field in ("terminator_start", "terminator_end"):
                        assert item[field] in at, item
                    start, end = item["terminator_start"][0], item["terminator_end"][0]
                    assert data[start:end] == {"break": b";;", "fallthrough": b";&"}[item["terminator"]], item
        elif kind == "function":
            words.append(node["name"])
            assert name(node["body"]["kind"]) in ("brace", "subshell", "if", "for", "while", "until", "case"), node
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
    if kind == "if":
        return (kind, tuple((shape(branch["condition"]), shape(branch["body"])) for branch in node["branches"]),
                shape(node["else_body"]) if node["else_body"] is not None else None)
    if kind == "for":
        return (kind, node["name"]["token"]["raw"], node["has_in"],
                tuple(word["token"]["raw"] for word in node["words"]), shape(node["body"]))
    if kind in ("while", "until"):
        return (kind, shape(node["condition"]), shape(node["body"]))
    if kind == "case":
        return (kind, node["word"]["token"]["raw"], tuple(
            (tuple(word["token"]["raw"] for word in item["patterns"]), shape(item["body"]), item["terminator"])
            for item in node["items"]))
    if kind == "function":
        return (kind, node["name"]["token"]["raw"], shape(node["body"]))
    return (kind, shape(node["body"]))


def expect(condition, message):
    assert condition, message


def compound_cases(fixture):
    def conditional():
        data = b"if a && b; then one; two & elif c\nthen three\nelif d; then four; else five; six; fi\n"
        node = one(fixture, data)
        assert name(node["kind"]) == "if", node
        assert len(node["branches"]) == 3, node
        assert shape(node["branches"][0]["condition"]) == ("list", ((("and", ("a",), ("b",)), "semi"),)), node
        assert shape(node["branches"][0]["body"]) == ("list", ((("one",), "semi"), (("two",), "ampersand"))), node
        assert [raw_words(command(branch["condition"])) for branch in node["branches"][1:]] == [[("c", False)], [("d", False)]], node
        assert shape(node["else_body"]) == ("list", ((("five",), "semi"), (("six",), "semi"))), node
        assert node["start"] == positions(data)[0] and node["end"] == positions(data)[len(data) - 1], node
    yield "if elif else preserve conditions and ordered bodies", conditional

    for data in (b"if true; then yes; fi", b"if\ntrue\nthen\nyes\nfi\n", b"i\\\nf true; then yes; f\\\ni"):
        def if_without_else(data=data):
            node = one(fixture, data)
            assert name(node["kind"]) == "if" and len(node["branches"]) == 1 and node["else_body"] is None, node
            assert raw_words(command(node["branches"][0]["body"])) == [("yes", False)], node
        yield f"if without else {data!r}", if_without_else

    for data, has_in, words in (
        (b"for item; do echo item; done", False, []),
        (b"for item\ndo echo item\ndone", False, []),
        (b"for item in; do echo item; done", True, []),
        (b"for item in\ndo echo item\ndone", True, []),
        (b"for item in a 'b c' \"$x\"; do echo item; done", True, ["a", "'b c'", '"$x"']),
        (b"for item\nin a b\ndo echo item\ndone", True, ["a", "b"]),
        (b"for item in if then else elif fi do done in case esac for while until; do echo item; done", True,
         ["if", "then", "else", "elif", "fi", "do", "done", "in", "case", "esac", "for", "while", "until"]),
    ):
        def for_loop(data=data, has_in=has_in, words=words):
            node = one(fixture, data)
            assert name(node["kind"]) == "for" and node["name"]["token"]["raw"] == "item", node
            assert node["has_in"] is has_in, node
            assert [word["token"]["raw"] for word in node["words"]] == words, node
            assert raw_words(command(node["body"])) == [("echo", False), ("item", False)], node
        yield f"for loop iteration words {data!r}", for_loop

    for keyword in (b"while", b"until"):
        def condition_loop(keyword=keyword):
            node = one(fixture, keyword + b" first; second && third\ndo fourth | fifth; sixth & done")
            assert name(node["kind"]) == keyword.decode(), node
            assert shape(node["condition"]) == ("list", ((("first",), "semi"), (("and", ("second",), ("third",)), "newline"))), node
            assert shape(node["body"]) == ("list", ((("pipeline", False, (("fourth",), ("fifth",))), "semi"), (("sixth",), "ampersand"))), node
        yield f"{keyword.decode()} preserves condition and body lists", condition_loop

    def case_items():
        data = b"case \"$value\" in\n(a|'b c') first; second ;;\nthen|do) third ;&\n*) fourth;\nesac\n"
        node = one(fixture, data)
        assert name(node["kind"]) == "case" and node["word"]["token"]["raw"] == '"$value"', node
        assert [tuple(word["token"]["raw"] for word in item["patterns"]) for item in node["items"]] == [("a", "'b c'"), ("then", "do"), ("*",)], node
        assert [item["terminator"] for item in node["items"]] == ["break", "fallthrough", "end"], node
        assert [raw_words(item["body"]["items"][0]["command"])[0][0] for item in node["items"]] == ["first", "third", "fourth"], node
        assert len(node["items"][0]["body"]["items"]) == 2, node
    yield "case patterns ordered arms and POSIX terminators", case_items

    for data, count in ((b"case x in esac", 0), (b"case x\nin\nesac", 0),
                        (b"case x in a) ;; b) ;& c) esac", 3),
                        (b"case x in (esac) ;; (in|if|then|do) ;; esac", 2),
                        (b"case x in a|esac) ;; esac", 1)):
        def empty_case(data=data, count=count):
            node = one(fixture, data)
            assert name(node["kind"]) == "case" and len(node["items"]) == count, node
            assert all(item["body"]["items"] == [] for item in node["items"]), node
        yield f"case empty bodies and reserved patterns {data!r}", empty_case

    for data, expected in ((b"for in in a; do echo in; done", "in"),
                           (b"for if; do echo if; done", "if"),
                           (b"for x do echo x; done", "x")):
        yield f"for variable context and optional separator {data!r}", lambda data=data, expected=expected: expect(
            one(fixture, data)["name"]["token"]["raw"] == expected, "for variable or optional separator")

    function_bodies = (
        (b"{ echo x; }", "brace"), (b"(echo x)", "subshell"),
        (b"if true; then echo x; fi", "if"), (b"for x in a; do echo x; done", "for"),
        (b"while true; do echo x; done", "while"), (b"until true; do echo x; done", "until"),
        (b"case x in x) echo x ;; esac", "case"),
    )
    for body, kind in function_bodies:
        def function(body=body, kind=kind):
            data = b"my_function ()\n" + body + b" 3>out <in\n"
            node = one(fixture, data)
            assert name(node["kind"]) == "function" and node["name"]["token"]["raw"] == "my_function", node
            assert name(node["body"]["kind"]) == kind and node["body"]["redirections"] == [], node
            assert [redir["operand"]["token"]["raw"] for redir in node["redirections"]] == ["out", "in"], node
            assert node["redirections"][0]["io_number"]["raw"] == "3", node
            assert node["end"] == positions(data)[len(data) - 1], node
        yield f"function definition with {kind} body and attached redirections", function

    yield "special builtin name remains syntactically valid function name", lambda: expect(
        one(fixture, b"export() { echo x; }")["name"]["token"]["raw"] == "export", "syntax applied runtime function restriction")

    for data in (b"if (a) then (b) else (c) fi", b"{ f() { echo x; } }",
                 b"if a | (b) then c; fi", b"while a && (b) do c; done",
                 b"case x in x) (echo x) esac"):
        yield f"compound closing word after self-delimited command {data!r}", lambda data=data: one(fixture, data)

    for data, expected in (
        (b"echo if then elif else fi for in do done while until case esac", "echo if then elif else fi for in do done while until case esac".split()),
        (b"'if' then;", ["'if'", "then"]),
        (b"\\while do done", ["\\while", "do", "done"]),
        (b'"case" in esac', ['"case"', "in", "esac"]),
        (b"function name", ["function", "name"]),
    ):
        yield f"compound reserved words retain ordinary contexts {data!r}", lambda data=data, expected=expected: expect(
            [word for word, _ in raw_words(one(fixture, data))] == expected, "ordinary reserved word changed grammar")

    def nested_compounds():
        data = b"outer() { for x in one two; do if ready; then while more; do case x in one) (echo x) ;; *) until done_yet; do echo x; done ;; esac; done; else fallback() { echo no; }; fi; done; }\n"
        outer = one(fixture, data)
        loop = command(outer["body"]["body"])
        conditional = command(loop["body"])
        while_loop = command(conditional["branches"][0]["body"])
        case = command(while_loop["body"])
        until_loop = command(case["items"][1]["body"])
        fallback = command(conditional["else_body"])
        assert [name(node["kind"]) for node in (outer, loop, conditional, while_loop, case, until_loop, fallback)] == [
            "function", "for", "if", "while", "case", "until", "function"], outer
        assert name(command(case["items"][0]["body"])["kind"]) == "subshell", case
    yield "nested functions and every compound production", nested_compounds

    for source, kind in function_bodies[2:]:
        def compound_redirects(source=source, kind=kind):
            node = one(fixture, source + b" <first 2>second >>third")
            assert name(node["kind"]) == kind, node
            assert [redir["operand"]["token"]["raw"] for redir in node["redirections"]] == ["first", "second", "third"], node
        yield f"{kind} attached redirections remain ordered", compound_redirects

    def substitutions():
        data = b"for x in $(if a; then b; fi) $(case x in x) echo yes ;; esac); do case $(echo x) in $(echo pattern)) echo $(until ready; do wait; done) ;; esac; done"
        node = one(fixture, data)
        assert [name(command(word["substitutions"][0]["body"])["kind"]) for word in node["words"]] == ["if", "case"], node
        case = command(node["body"])
        assert raw_words(command(case["word"]["substitutions"][0]["body"])) == [("echo", False), ("x", False)], case
        pattern = case["items"][0]["patterns"][0]
        assert raw_words(command(pattern["substitutions"][0]["body"])) == [("echo", False), ("pattern", False)], pattern
        echo = command(case["items"][0]["body"])
        assert name(command(echo["words"][1]["word"]["substitutions"][0]["body"])["kind"]) == "until", echo
    yield "structured substitutions in loop words case subjects patterns and bodies", substitutions
    for data in (b"echo $(case x in (x) echo yes ;; esac)",
                 b"echo $(case x in x) case y in y) echo nested ;; esac ;; esac)",
                 b"echo $(f() (case x in x) echo yes ;; esac); f)"):
        yield f"case and function parentheses inside command substitution {data!r}", lambda data=data: one(fixture, data)

    def compound_heredocs():
        data = b"f() { if cat <<IF\ncondition\nIF\nthen for x in a; do cat <<BODY\nloop\nBODY\ndone; fi; } <<FUNCTION\nfunction\nFUNCTION\n"
        node = one(fixture, data)
        conditional = command(node["body"]["body"])
        condition = command(conditional["branches"][0]["condition"])
        loop = command(conditional["branches"][0]["body"])
        body = command(loop["body"])
        assert [part["redirections"][0]["body"] for part in (condition, body, node)] == ["condition\n", "loop\n", "function\n"], node
    yield "heredoc queues across nested compounds and function redirections", compound_heredocs

    def complete_boundaries():
        result = fixture.parse(b"if a\nthen b\nfi\nfor x in a b\ndo echo x\ndone\nf()\n{ echo x; }\nlast\n")
        assert [name(command(tree)["kind"]) for tree in result["trees"]] == ["if", "for", "function", "simple"], result
    yield "multiline compounds publish only complete top-level commands", complete_boundaries

    invalid = (
        (b"if ; then a; fi", b";"), (b"if a; then ; fi", b"; fi"),
        (b"if a; then b; else fi", b"fi"), (b"if a; then b; elif ; fi", b"; fi"),
        (b"if a; do b; fi", b"do"), (b"while a; then b; done", b"then"),
        (b"while ; do b; done", b";"), (b"until a; do ; done", b"; done"),
        (b"for 1x in a; do b; done", b"1x"), (b"for 'x' in a; do b; done", b"'x'"),
        (b"for x in a; then b; done", b"then"), (b"for x; do ; done", b"; done"),
        (b"case x nope a) b ;; esac", b"nope"), (b"case x in |a) b ;; esac", b"|"),
        (b"case x in a|) b ;; esac", b")"), (b"case x in a) b ;;& esac", b"&"),
        (b"f(arg) { a; }", b"arg"), (b"f() echo x", b"echo"),
        (b"'f'() { a; }", b"'f'"), (b"1f() { a; }", b"1f"),
        (b"if (a) >x then b; fi", b"then"), (b"{ (a) >x }", b"}"),
        (b"case x in a) (b) >x esac", b"esac"),
    )
    for data, bad in invalid:
        def invalid_compound(data=data, bad=bad):
            result = fixture.parse(data, "error")
            assert result["trees"] == [], result
            assert result["error"]["position"] == positions(data)[data.index(bad)], result
        yield f"terminal compound diagnostic {data!r}", invalid_compound

    incomplete = (
        b"if", b"if true", b"i\\\nf true", b"if true;", b"if true; then", b"if true; then x;",
        b"if true; then x; elif", b"if true; then x; elif y; then", b"if true; then x; else",
        b"for", b"for x", b"for x in", b"for x in a;", b"for x; do", b"for x; do y;",
        b"while", b"while true;", b"while true; do", b"while true; do x;",
        b"until", b"until true; do x;", b"case", b"case x", b"case x in", b"case x in a|",
        b"case x in a)", b"case x in a) x ;;", b"case x in a) x ;&", b"f(", b"f()", b"f()\n{ x;",
        b"f() { if x; then cat <<EOF\nbody\n", b"if x; then y; fi >",
    )
    for data in incomplete:
        yield f"incomplete compound {data!r}", lambda data=data: expect(
            fixture.parse(data, "incomplete")["trees"] == [], "incomplete compound tree was published")

    def growth():
        branches = one(fixture, b"if x; then y; " + b"elif x; then y; " * 80 + b"fi")
        assert len(branches["branches"]) == 81, branches
        loop = one(fixture, b"for x in " + b"word " * 600 + b"; do x; done")
        assert len(loop["words"]) == 600, loop
        case = one(fixture, b"case x in " + b"a|b|c|d|e|f|g|h|i|j) echo x ;; " * 100 + b"esac")
        assert len(case["items"]) == 100 and all(len(item["patterns"]) == 10 for item in case["items"]), case
    yield "compound branch word arm and pattern vector growth", growth
    yield "32 nested conditional bodies", lambda: one(fixture, b"if x; then " * 32 + b"y; " + b"fi; " * 32)
    yield "compound nesting limit is a structured error", lambda: fixture.parse(b"if x; then " * 200 + b"y; " + b"fi; " * 200, "error")


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

    yield from compound_cases(fixture)

    invalid = (
        (b";", 0), (b"&", 0), (b"| echo", 0), (b"echo && || next", 8),
        (b"echo >;", 6), (b"echo | ;", 7), (b")", 0),
        (b"()", 1), (b"{ ; }", 2), (b"(echo) trailing", 7),
        (b"echo ;; next", 5),
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
