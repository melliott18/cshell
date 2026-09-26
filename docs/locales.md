# Locale behavior

CSH-042 tests C/POSIX and installed UTF-8 locales on macOS and Linux. The runtime
uses libc character decoding, `fnmatch`, `strcoll`, and `strerror`. Locale names,
character classes outside the portable character set, collation weights, and
translated system messages come from the host. An installed locale name alone
does not establish support for its encoding throughout the shell.

## Selection and changes

At startup, nonempty `LC_ALL` overrides each category; a nonempty category
variable overrides `LANG`; unset/empty values fall through. The default is C.
`LC_CTYPE` controls character lengths, pattern classes and multibyte IFS;
`LC_COLLATE` controls pattern collation and pathname ordering; `LC_MESSAGES`
controls libc diagnostic text. LC_NUMERIC, LC_MONETARY and LC_TIME are also
initialized consistently, although they are not shell-language test oracles.

After startup, successful assignment, `unset`, and assignment-scope rollback
refresh the categories from **shell variables**, including unexported values.
Export controls child environments, not the current shell's locale. Temporary
builtin assignments restore the prior effective categories. Subshell and command
substitution changes are process-local. Readonly/failed variable mutations do
not change the locale. State construction/cloning alone does not modify libc;
`main` opts the active state into locale management after environment import.
Restoration does not allocate shell storage, but libc may allocate internally.

The lexer recognizes ASCII shell syntax independently of libc locale changes.
For C/POSIX and UTF-8, later LC_CTYPE changes preserve literal text, quoting,
escaped newlines, eval, and subshell parsing. This is bounded evidence for the
startup lexical rule, not proof for every encoding. A reproduced Shift-JIS
character containing byte `0x5c` loses that byte during lexical processing;
[CSH-053](tickets/CSH-053-multibyte-lexical-boundaries.md) owns the fix and the
startup decoding-context tests for encodings containing syntax-valued bytes.
New external shell invocations initialize their own locale from the exported
environment.

If an effective locale name is unavailable or invalid, cshell silently selects
C for **all** categories. The variable values are retained. Correcting/unsetting
the offending variable recomputes the locale. An invalid lower-precedence name
hidden by LC_ALL has no effect. This is a cshell policy: [POSIX internationalization
variables](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html#tag_08_02)
leave an unsupported locale environment unspecified. It is not a portable-shell
output rule. Startup explicitly resets C if libc rejects the combined request.

## Matching, splitting and messages

Parameter length/removal, `case`, and pathname patterns use the active runtime
categories. Removal advances by complete characters. Pathnames are sorted with
`strcoll`, with byte order breaking equal collation weights. The tests derive
locale-qualified order from the installed host data; they do not hard-code a
universal ordering for en_US, fr_FR, or arbitrary ranges/equivalence classes.
Invalid character sequences have only a documented byte-fallback policy, not a
POSIX conformance oracle.

Field splitting and `read` consume complete multibyte IFS characters. Only
space, tab and newline are IFS whitespace. Other characters, including other
Unicode whitespace, are non-whitespace delimiters when present in IFS. `read`
preserves quoted delimiters, consecutive-delimiter empty fields, and the last
variable's remaining fields/separators. CSH-042 fixes the former byte-wise
`read` split, which could split `è` merely because IFS contained `é`.

Cshell has no translated application-message catalogs: its own prefixes and
syntax/builtin messages are English. System-error suffixes use libc's current
LC_MESSAGES catalog, where installed. The French Linux probe checks the actual
host ENOENT translation and LC_ALL/category/LANG precedence; it asserts stderr
and status 1 with empty stdout. Missing catalogs produce a capability skip,
while C-locale diagnostic stream/status checks always run. Native macOS's
candidate locales currently expose no translated ENOENT message. This limitation
does not change diagnostic destinations or exit statuses.

## Evidence boundaries

[`tests/locale_cases.py`](../tests/locale_cases.py), integrated by
[`tests/portability.py`](../tests/portability.py), supplies three-mode fixtures:

| Case family | Evidence and oracle |
| --- | --- |
| Startup precedence | LC_ALL, LC_CTYPE, LANG and empty fallback; LC_COLLATE/LC_MESSAGES host-qualified observations |
| Patterns and values | UTF-8 `?`, bracket alpha classes, quoted patterns, parameter length and all four removal forms; C portable classes |
| IFS/read | Whole characters sharing a leading byte, empty fields, quoted delimiter, trailing delimiter and remainder; `$*` joining |
| Runtime state | CTYPE/LANG/LC_ALL assignments and unset, temporary builtin scope, subshell and substitution isolation |
| Lexical stability | Literal UTF-8 words/quotes and escaped newline after CTYPE changes, eval and nested parsing; other encodings remain CSH-053 |
| Collation | Host-qualified pathname order, initial precedence and runtime assignment/rollback; no portable non-C range-order claim |
| Diagnostics | Host-qualified strerror suffix, precedence, runtime LC_MESSAGES assignment where translated catalogs exist, exact streams/status |
| Invalid locale | Cshell's silent, consistent C fallback and recovery policy (implementation-specific) |

The runner prints available candidate locales and concrete capability skips.
Docker and native Linux CI provision en_US.UTF-8 and fr_FR.UTF-8; the Docker
image explicitly retains French libc catalogs normally excluded by Debian slim.
Run `make test-portability`; full validation is `make test test-pty` plus the
[ASan/UBSan configuration](testing.md). Exact environments and results belong to
[CSH-042](tickets/CSH-042-locale-semantics.md).

These witnesses support [ENV-004](posix-matrix.md#env-004),
[EXP-004](posix-matrix.md#exp-004), [EXP-007](posix-matrix.md#exp-007),
[EXP-008](posix-matrix.md#exp-008), [EXP-010](posix-matrix.md#exp-010),
[EXEC-012](posix-matrix.md#exec-012), and [read](posix-utilities.md#u-027).
They do not promote those broad families to verified; CSH-047/048/049 retain
family-level audits and CSH-053 retains the concrete non-UTF-8 lexical defect.
