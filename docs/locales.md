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
builtin assignments restore the prior effective categories. Assignment-only
redirection clones reselect the parent locale after expansion, on both success
and failure. Subshell and command
substitution changes are process-local. Readonly/failed variable mutations do
not change the locale. State construction/cloning alone does not modify libc;
`main` opts the active state into locale management after environment import.
Restoration does not allocate shell storage, but libc may allocate internally.

The runtime saves an immutable libc locale object immediately after startup
locale selection. Lexer lookahead and word fragments decode whole characters
using that context; eval, dot files, aliases, backquotes, here-documents and
command substitutions use the same saved context, including after fork.
Later LC_CTYPE, LANG or LC_ALL assignments cannot reinterpret source bytes.
A newly invoked external shell takes its own snapshot from its environment.
Startup snapshot allocation failure is fatal before source execution.

CSH-053 preserves syntax-valued constituent bytes in ASCII-compatible,
stateless encodings. Native macOS witnesses cover Shift-JIS, Big5, GBK and
GB18030; Linux provisions GB18030. A split lexer feed waits for the complete
character, while positions and fragment offsets remain byte based. Invalid or
final incomplete sequences use a one-byte fallback (project policy, not a
portable oracle). Stateful encodings are not established by these witnesses.
Dollar-single-quote source decoding and delimiter/backquote quote removal use
the saved lexical context; the representability check for generated control
escapes still uses current LC_CTYPE. Expansion, IFS, pattern construction and
`read` continue using current categories. `read` protects complete escaped
characters and never interprets a constituent backslash as an escape.

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
| Lexical stability | UTF-8 and CSH-053 raw-byte words, quotes, aliases, here-documents, eval/dot and nested parsing after locale changes; external shells select a fresh context |
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
family-level audits. [CSH-053](tickets/CSH-053-multibyte-lexical-boundaries.md)
records the bounded non-UTF-8 witnesses and their remaining encoding limits.

### Raw-byte lexical witnesses (CSH-053)

[`tests/multibyte_cases.py`](../tests/multibyte_cases.py) compares exact output
bytes, empty stderr and status in command-string, script-file and stdin modes.
It covers constituent bytes `5c`, `60`, `7c`, `5b`, `5d`, `7b` and `7d` in
locale-qualified characters, without transcoding scripts or expected output.
The [character API fixture](../tests/character_fixture.c) first verifies libc
can decode every selected character, then checks startup/current decoding and
all feed splits of bare, quoted, escaped and dollar-adjacent words.

Unavailable candidate locales produce encoding-specific skips. macOS rejects
these non-UTF-8 filenames, so pathname cases explicitly skip on that filesystem;
Linux exercises both literal multibyte path components and quoted patterns
followed by wildcards. The startup-C invalid-byte examples assert the documented
fallback policy; valid-character witnesses are the specification-derived
preservation assertions. Run `make test-portability` (included in `make test`).
These tests add ENV-004, LEX-002/004 and EXP-010 evidence without declaring any
whole requirement family verified.
