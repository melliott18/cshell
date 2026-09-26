"""CSH-042 locale witnesses. Host-derived oracles are labeled, never universal.

The caller supplies the shared three-input-mode fixture constructor. Locale
selection does not inherit the developer's environment. Catalog/order probes
restore Python's locale before returning, and report unavailable capabilities.
"""

from functools import cmp_to_key
import errno
import locale
import os


NAMES = ("C.UTF-8", "en_US.UTF-8", "fr_FR.UTF-8", "de_DE.UTF-8", "sv_SE.UTF-8")
FILES = ("A1", "B2", "a3", "z4", "ä5", "é6")


def host_data():
    original = locale.setlocale(locale.LC_ALL)
    result = {}
    try:
        for name in ("C",) + NAMES:
            try:
                locale.setlocale(locale.LC_ALL, name)
            except locale.Error:
                continue
            # Issue 8 requires a byte-order tie break for equal collation keys.
            def compare(a, b):
                return locale.strcoll(a, b) or ((a.encode() > b.encode()) -
                                               (a.encode() < b.encode()))
            result[name] = ("\n".join(sorted(FILES, key=cmp_to_key(compare))) + "\n",
                            os.strerror(errno.ENOENT))
    finally:
        locale.setlocale(locale.LC_ALL, original)
    return result


def cases(case, selected, data, skips):
    # These are cshell policy assertions, not portable invalid-locale oracles.
    invalid = "cshell_nonexistent_locale_042"
    for variable in ("LC_ALL", "LC_CTYPE", "LC_COLLATE", "LC_MESSAGES", "LANG"):
        env = {"LC_ALL": "", "LANG": "C", variable: invalid}
        yield from case(f"locale invalid {variable}: silent C fallback",
                        "printf '%s\\n' [a-z]\n", env=env,
                        setup={"a": "", "Z": ""}, stdout="a\n")
    yield from case("locale invalid lower precedence is ignored",
                    "printf 'ok\\n'\n", env={"LC_ALL": "C", "LANG": invalid,
                    "LC_CTYPE": invalid, "LC_COLLATE": invalid,
                    "LC_MESSAGES": invalid}, stdout="ok\n")
    yield from case("locale C bracket classes and removal",
                    "v=ABCabc; printf '%s|%s\\n' \"${v#[[:upper:]]}\" \"${v%[[:lower:]]}\"\n"
                    "case a in [[:alpha:]]) printf 'alpha\\n';; esac\n",
                    stdout="BCabc|ABCab\nalpha\n")

    if selected:
        env = {"LC_ALL": "", "LANG": selected}
        for label, overrides, expected in (
            ("LANG fallback", {}, "café\n"),
            ("empty LC_CTYPE fallback", {"LC_CTYPE": ""}, "café\n"),
            ("LC_CTYPE overrides LANG", {"LC_CTYPE": "C"}, "caf?\n"),
            ("LC_ALL overrides categories", {"LC_ALL": selected, "LC_CTYPE": "C",
                                            "LC_COLLATE": "C"}, "café\n"),
        ):
            yield from case("locale " + label, "printf '%s\\n' caf?\n",
                            env={**env, **overrides}, setup={"café": ""}, stdout=expected)
        yield from case("locale invalid category resets all categories to C (policy)",
                        "v=é; printf '%s\\n' \"${#v}\"\n",
                        env={**env, "LC_MESSAGES": invalid}, stdout="2\n")
        yield from case("locale invalid runtime category recovers after unset (policy)",
                        f"v=é; LC_COLLATE={invalid}; printf '%s\\n' \"${{#v}}\"\n"
                        "unset LC_COLLATE; printf '%s\\n' \"${#v}\"\n",
                        env=env, stdout="2\n1\n")
        yield from case("locale UTF-8 parameter removal character boundaries",
                        "v=éaé; printf '%s|%s|%s|%s|%s\\n' \"${#v}\" \"${v#?}\" "
                        "\"${v%?}\" \"${v##*a}\" \"${v%%a*}\"\n",
                        env=env, stdout="3|aé|éa|é|é\n")
        yield from case("locale UTF-8 case classes and quoted patterns",
                        "case é in [[:alpha:]]) printf 'alpha\\n';; esac\n"
                        "case é in '?') printf 'bad\\n';; ?) printf 'one\\n';; esac\n"
                        "v=éa; printf '%s\\n' \"${v#[[:alpha:]]}\"\n",
                        env=env, stdout="alpha\none\na\n")
        yield from case("locale UTF-8 IFS whole characters and empty fields",
                        "IFS=é; v=èéaééb; printf '<%s>\\n' $v\n"
                        "set -- a b; printf '<%s>\\n' \"$*\"\n",
                        env=env, stdout="<è>\n<a>\n<>\n<b>\n<aéb>\n")
        for label, line, variables, expected in (
            ("whole characters", "èéaééb\n", "a b c d", "<è>\n<a>\n<>\n<b>\n"),
            ("last variable remainder", "aébécé\n", "a b", "<a>\n<bécé>\n"),
            ("single trailing delimiter", "aé\n", "a", "<a>\n"),
            ("escaped delimiter", "a\\ébéc\n", "a b", "<aéb>\n<c>\n"),
        ):
            values = " ".join('"$' + v + '"' for v in variables.split())
            yield from case("locale UTF-8 read IFS " + label,
                            f"IFS=é; read {variables} < data; printf '<%s>\\n' {values}\n",
                            env=env, setup={"data": line}, stdout=expected)
        # Use a UTF-8 value only while CTYPE is UTF-8: invalid C-locale byte
        # sequences are not a specification-derived pattern oracle.
        yield from case("locale runtime CTYPE assignment and unset",
                        f"LC_CTYPE={selected}; v=é; printf '%s\\n' \"${{#v}}\"\n"
                        "LC_CTYPE=C; v=abc; printf '%s\\n' \"${#v}\"\n"
                        "unset LC_CTYPE; v=é; printf '%s\\n' \"${#v}\"\n",
                        env={**env, "LC_CTYPE": "C"}, stdout="1\n3\n1\n")
        yield from case("locale runtime LANG and LC_ALL precedence",
                        f"LANG={selected}; v=é; printf '%s\\n' \"${{#v}}\"\n"
                        "LC_ALL=C; LANG=C; LC_ALL=; "
                        f"LANG={selected}; printf '%s\\n' \"${{#v}}\"\n",
                        env={"LC_ALL": "", "LANG": "C"}, stdout="1\n1\n")
        yield from case("locale temporary builtin assignment restores categories",
                        "LC_ALL=C read v < data; v=é; printf '%s\\n' \"${#v}\"\n",
                        env={"LC_ALL": selected}, setup={"data": "text\n"}, stdout="1\n")
        yield from case("locale subshell and substitution changes stay local",
                        f"LC_CTYPE=C; (LC_CTYPE={selected}; v=é; printf '%s\\n' \"${{#v}}\")\n"
                        f"v=$(LC_CTYPE={selected}; v=é; printf '%s' \"${{#v}}\"); "
                        "printf '%s|%s\\n' \"$v\" \"$LC_CTYPE\"\n",
                        env=env, stdout="1\n1|C\n")
        # Literal UTF-8 words/quotes, escaped newline and nested parsing stay
        # unchanged after assignments, including eval and subshell input.
        yield from case("locale lexical UTF-8 syntax stable after CTYPE change",
                        "LC_CTYPE=C\nprintf '<%s>\\n' 'é' \"é\" é\\\nclair\n"
                        "(eval \"printf '<%s>\\\\n' 'é'\")\n"
                        "v=$(printf '%s' 'é'); printf '<%s>\\n' \"$v\"\n",
                        env=env, stdout="<é>\n<é>\n<éclair>\n<é>\n<é>\n")
    else:
        skips.append("UTF-8 expansion/read/assignment/lexical group: neither C.UTF-8 nor en_US.UTF-8 installed")

    # Host-locale-qualified order; no universal en_US/de_DE ordering assumed.
    collate = next((n for n, (order, _) in data.items()
                    if n != "C" and order != data["C"][0]), None)
    if collate:
        order = data[collate][0]
        setup = {"names/" + name: "" for name in FILES}
        script = "cd names; printf '%s\\n' *\n"
        for label, env, expected in (
            ("LANG", {"LC_ALL": "", "LANG": collate}, order),
            ("category", {"LC_ALL": "", "LANG": collate, "LC_COLLATE": "C"}, data["C"][0]),
            ("LC_ALL", {"LC_ALL": collate, "LC_COLLATE": "C"}, order),
        ):
            yield from case(f"locale host-qualified collation {collate} {label}",
                            script, setup=setup, env=env, stdout=expected)
        yield from case("locale runtime collation and temporary scope restoration",
                        f"cd names; LC_COLLATE={collate}; printf '%s\\n' *\n"
                        "LC_COLLATE=C read v < ../data; printf '%s\\n' *\n"
                        "unset LC_COLLATE; printf '%s\\n' *\n",
                        setup={**setup, "data": "ok\n"},
                        env={"LC_ALL": "", "LANG": "C", "LC_CTYPE": collate},
                        stdout=order + order + data["C"][0])
    else:
        skips.append("distinct non-C collation: none of the installed candidate locales changes the probe order")

    c_message = data["C"][1]
    message_locale = next((n for n, (_, message) in data.items()
                           if message != c_message), None)
    # English fallback is still tested when libc has no translated catalog.
    for n in ("C",) + ((message_locale,) if message_locale else ()):
        for label, env, message in (
            ("LANG", {"LC_ALL": "", "LANG": n}, data[n][1]),
            ("category", {"LC_ALL": "", "LANG": n, "LC_MESSAGES": "C"}, c_message),
            ("LC_ALL", {"LC_ALL": n, "LC_MESSAGES": "C"}, data[n][1]),
        ):
            yield from case(f"locale host-qualified diagnostic {n} {label}",
                            ": < missing\n", env=env, status=1,
                            stderr=f"cshell: cannot apply redirection: {message}\n")
    if message_locale:
        yield from case("locale runtime diagnostic language",
                        f"LC_MESSAGES={message_locale}; : < missing\n", status=1,
                        env={"LC_ALL": "", "LANG": "C", "LC_CTYPE": message_locale},
                        stderr=f"cshell: cannot apply redirection: {data[message_locale][1]}\n")
    else:
        skips.append("translated libc ENOENT diagnostic: installed candidate locales have no translation; cshell has no message catalogs")
