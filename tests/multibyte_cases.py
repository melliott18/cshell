"""CSH-053 raw-byte witnesses for ENV-004, LEX-002/004 and EXP-010.

Exact byte/stream/status assertions follow character preservation and quoting
rules, not reference-shell output. Locale capability is checked with libc in
character_fixture before any encoding's cases are counted as evidence.
"""
import errno
import os
from pathlib import Path
import subprocess
import tempfile

ENCODINGS = (
    ("Shift-JIS", ("ja_JP.SJIS", "ja_JP.sjis"), b"\x83"),
    ("Big5", ("zh_TW.Big5", "zh_TW.big5"), b"\xa4"),
    ("GBK", ("zh_CN.GBK", "zh_CN.gbk"), b"\x81"),
    ("GB18030", ("zh_CN.GB18030", "zh_CN.gb18030"), b"\x81"),
)


def witnesses(c, locale):
    emit = b"printf '%s\\n' "
    yield "dollar followed by character", emit + b"$" + c + b"\n", b"$" + c + b"\n", {}
    yield "unquoted newline", emit + c + b"\n", c + b"\n", {}
    quoted_source = emit + b"'" + c + b"' \"" + c + b'" $\'' + c + b"' \\" + c + b"\n"
    yield "quotes and escaped character", quoted_source, (c + b"\n") * 4, {}
    yield "parameter operand and adjacent syntax", b"v=" + c + b"; " + emit + b'"${missing:-' + c + b'}" "${v}"; true|' + emit + c + b"\n", (c + b"\n") * 3, {}
    yield "backquote and command substitution", emit + b'"`printf %s ' + c + b'`" "$(printf %s ' + c + b')"\n', (c + b"\n") * 2, {}
    yield "arithmetic fallback", emit + b'"$((printf %s ' + c + b'))"\n', c + b"\n", {}
    yield "alias replacement", b"alias value='printf %s " + c + b"'\nvalue\n", c, {}
    yield "here-document body", b"cat <<EOF\n" + c + b"\nEOF\n", c + b"\n", {}
    for quote in (b"", b"'", b'"', b"$'"):
        close = quote[-1:] if quote else b""
        yield "here-document delimiter " + repr(quote), b"cat <<" + quote + c + close + b"\nx\n" + c + b"\n", b"x\n", {}
    source = emit + c + b"\n"
    for variable in (b"LC_CTYPE", b"LANG", b"LC_ALL"):
        prefix = variable + b"=C\n"
        yield "fixed startup quotes " + variable.decode(), prefix + quoted_source, (c + b"\n") * 4, {}
        yield "fixed startup " + variable.decode(), prefix + source + b"( " + source + b")\neval '" + b'printf "%s\\n" ' + c + b"'\n. ./source\nv=$( . ./source ); " + emit + b'"$v"\n', (c + b"\n") * 5, {b"source": source}
    if c[-1:] == b"\\":
        yield "new external shell startup", b"LC_ALL=C\nexport LC_ALL\n\"$CSH_TEST_BINARY\" ./source\n", c[:-1] + b"\n" if c[-1:] == b"\\" else c + b"\n", {b"source": source}
        yield "startup C stays C after assignment", b"LC_ALL=" + locale.encode() + b"\neval 'printf \"%s\\n\" " + c + b"\n'\n", c[:-1] + b"\n" if c[-1:] == b"\\" else c + b"\n", {"startup": "C"}
    yield "new external multibyte startup", b"LC_ALL=" + locale.encode() + b"\nexport LC_ALL\n\"$CSH_TEST_BINARY\" ./source\n", c + b"\n", {b"source": source, "startup": "C"}
    yield "read and read raw", b"read v < data; " + emit + b'"$v"\nread -r v < data; ' + emit + b'"$v"\n', (c + b"\n") * 2, {b"data": c + b"\n"}
    yield "read escaped IFS character", b"IFS='" + c + b"'; read a b < data; printf '<%s><%s>\\n' \"$a\" \"$b\"\n", b"<" + c + b"><z>\n", {b"data": b"\\" + c + c + b"z\n"}
    yield "runtime read context", b"LC_ALL=C\nread v < data; " + emit + b'"$v"\n', c[:-1] + b"\n" if c[-1:] == b"\\" else c + b"\n", {b"data": c + b"\n"}
    yield "literal pattern and removal", b"v='" + c + b"'; case $v in \"$v\") printf 'match\\n';; esac\n" + emit + b'"${v#"$v"}" "${v%"$v"}"\n', b"match\n\n\n", {}
    # Raw filenames work on Linux; macOS rejects names not valid UTF-8.
    yield "pathname components", emit + b"'" + c + b"'/*\n", c + b"/x\n", {c + b"/x": b"", "pathname": True}
    yield "pathname literal plus wildcard", emit + b"'" + c + b"'*\n", c + b"x\n", {c + b"x": b"", "pathname": True}
    yield "IFS syntax-valued constituent", b"IFS='\\'; v='" + c + b"'; " + emit + b"$v\n", c + b"\n", {}


def run(binary, helper):
    passed = failed = 0
    skips = []
    for label, names, lead in ENCODINGS:
        selected = None
        for name in names:
            probe = subprocess.run([str(helper), name, lead.hex()], capture_output=True, timeout=10)
            if probe.returncode == 77:
                continue
            if probe.returncode:
                print(f"FAIL: {label} character API: {probe.stderr!r}")
                failed += 1
                break
            selected = name
            passed += 1
            print(f"PASS: {label} character API, split feeds and startup context ({name})")
            break
        if not selected:
            skips.append(f"{label}: no usable candidate locale/decoder")
            continue
        for tail in b"\\`|[]{}":
            c = lead + bytes([tail])
            for title, script, expected, setup in witnesses(c, selected):
                for mode in ("string", "file", "stdin"):
                    with tempfile.TemporaryDirectory(prefix="cshell-multibyte-") as tmp:
                        root = os.fsencode(tmp)
                        try:
                            for name, content in setup.items():
                                if not isinstance(name, bytes):
                                    continue
                                path = root + b"/" + name
                                os.makedirs(os.path.dirname(path), exist_ok=True)
                                with open(path, "wb") as f:
                                    f.write(content)
                        except OSError as error:
                            if not setup.get("pathname") or error.errno not in (errno.EILSEQ, errno.EINVAL):
                                raise
                            reason = f"{label}: raw pathname unavailable on filesystem ({error.strerror})"
                            if reason not in skips:
                                skips.append(reason)
                            continue
                        env = {"PATH": "/usr/bin:/bin", "HOME": tmp, "LANG": selected,
                               "LC_ALL": "", "CSH_TEST_BINARY": str(binary)}
                        if setup.get("startup"):
                            env["LANG"] = setup["startup"]
                        args = [os.fsencode(binary)]
                        if mode == "string":
                            args += [b"-c", script]
                        elif mode == "file":
                            with open(root + b"/script", "wb") as f:
                                f.write(script)
                            args += [b"script"]
                        result = subprocess.run(args, input=script if mode == "stdin" else b"",
                                                cwd=tmp, env=env, capture_output=True, timeout=5)
                        if (result.returncode, result.stdout, result.stderr) != (0, expected, b""):
                            failed += 1
                            print(f"FAIL: {label} {c.hex()} {title} ({mode}): "
                                  f"status={result.returncode} stdout={result.stdout!r} "
                                  f"stderr={result.stderr!r}, expected={expected!r}")
                        else:
                            passed += 1
        print(f"Checked {label} raw-byte runtime witnesses in -c, file and stdin modes")
    for reason in skips:
        print("SKIP: CSH-053 " + reason)
    print(f"CSH-053: {passed} passed, {failed} failed, {len(skips)} capability skips")
    return passed, failed, len(skips)


if __name__ == "__main__":
    import sys
    binary = Path(sys.argv[1] if len(sys.argv) > 1 else "./cshell").resolve()
    _, failures, _ = run(binary, binary.parent / "build/tests/character_fixture")
    sys.exit(bool(failures))
