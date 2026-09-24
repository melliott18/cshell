# Value expansion API

[CSH-024](tickets/CSH-024-value-expansions.md) adds independent value expansion
in [`expand.h`](../include/cshell/expand.h) and [`expand.c`](../src/expand.c).
It consumes the lexer's owned WORD tokens and shell-state storage. CSH-026
connects this API to the public executable through `src/prepare.c`.
The value API delegates command execution and retains quote metadata.
[CSH-025](tickets/CSH-025-field-and-pathname-expansion.md) adds the separate
`csh_expand_fields()` stage in [`fields.c`](../src/fields.c) and
[`pathname.c`](../src/pathname.c) to produce final fields.

## Inputs, output, and ownership

`csh_expand_word(state, word, options, out, error)` borrows a structured word
and mutable state. A NULL options pointer selects argument expansion without a
command-substitution provider. The caller supplies an empty output destination
and releases success with `csh_expansion_destroy()`. Output strings and arrays
are independently owned: neither the token nor state must remain alive.

| Context | Input and subsequent processing |
| --- | --- |
| `CSH_EXPAND_ARGUMENT` | One lexical command/argument word; preserves positional field boundaries and marks unquoted expansion bytes for later IFS splitting |
| `CSH_EXPAND_ASSIGNMENT` | The value word only, excluding `NAME=`; permits tilde after syntactic unquoted colons and suppresses splitting/globbing |
| `CSH_EXPAND_PATTERN` | One pattern operand; suppresses splitting/globbing while preserving quoted pattern characters |
| `CSH_EXPAND_REDIRECTION` | One scalar file/descriptor operand; no splitting or pathname generation, even interactively |
| `CSH_EXPAND_HEREDOC` | A body-mode token; no root tilde, splitting, or pathname generation |

The parser/assignment owner must provide a structured value word for assignment
context. Relocate fragment byte offsets when constructing a value-only token;
do not pass the whole assignment spelling as a value. Context restrictions
remain in the result for `csh_expand_fields()` to honor.

Each output field owns a sequence of spans. A span records its bytes, length,
quote mode, origin (literal, tilde, parameter, arithmetic, substitution), IFS
eligibility (`split`), and explicit-empty retention (`keep_empty`). Escaped bytes
and tilde replacements carry single-quote protection. Adjacent spans belong to
the same field. A quoted `$@` creates separate fields, with surrounding text
joined to the first/last field; zero positional parameters contribute no fields.
Empty quoted positionals remain explicit empty spans. An unquoted unset value
has an empty, unprotected span for the final stage to discard when appropriate.

For example, with `v='a b'`, `x$v"$v"` is one intermediate field containing:

| Bytes | Origin | Quote | Split |
| --- | --- | --- | --- |
| `x` | literal | none | no |
| `a b` | parameter | none | yes |
| `a b` | parameter | double | no |

Quote spelling is interpreted to obtain value bytes, but its protection remains
in these spans until the final stage completes quote removal. Consumers must not flatten
and re-lex the bytes: expansion results never become new shell syntax.

Failures clear and release all output, return an enum plus source fragment and
position, and restore the shell-state checkpoint taken before evaluation. No
error prints, exits, or sets shell status. `${name:?word}` supplies the expanded
message in the inline diagnostic (up to 255 bytes). The executor decides status
and interactive exit policy. Restoration can invalidate previously borrowed
state views even when the observable state is unchanged. External effects of a
substitution callback cannot be rolled back by this storage checkpoint.

## Parameters and tilde

The API supports variables, numbered positionals (including `${10}`), `$0`, `$#`,
`$?`, `$!`, `$$`, `$-`, `$@`, and `$*`. Default, alternate, assignment, error,
length, and four pattern-removal operators distinguish unset from set-empty.
Unselected operands are not evaluated. Assignment operands are scalarized,
assigned, then substituted with the parameter's quote context; their inner quote
protection does not inhibit later splitting of the assigned value, following
the [Issue 8 assignment-operator rationale](https://pubs.opengroup.org/onlinepubs/9799919799/xrat/V4_xcu_chap02.html#tag_23_02_06_02).
Some older reference shells differ here.
Readonly errors roll back the entire word. Stored `nounset` and `allexport` bits
are honored for relevant expansion reads and assignments.

Unquoted argument `$*` initially retains positional fields like `$@`; quoted
`$*` joins by the first character of IFS (space when unset, no separator when
empty). For assignment/pattern contexts, `$@` and `$*` are joined the same way,
a documented choice for `$@` in contexts where the standard leaves its behavior
unspecified. Modified `@`/`*` forms, including their length, are rejected as
invalid; their results are unspecified by the standard. `$-` uses stable order
`abCefimnuvx` for the stored letter options; `pipefail` has no letter.

A wholly unquoted syntactic tilde-prefix uses shell `HOME` or `getpwnam()` for a
login name. Missing HOME or an unknown login leaves the prefix unchanged. HOME
set to empty yields a protected empty span. A trailing home slash is omitted
when the suffix starts with a slash. Quoted/escaped prefix bytes prevent tilde
expansion. Assignment values also recognize prefixes after literal unquoted
colons; parameter-operator words only recognize a leading prefix. Colons or
tildes produced by expansions never create new tilde sites.

Parameter length and removal candidates follow multibyte character boundaries
in the caller's active C/POSIX or UTF-8 locale. Patterns use `fnmatch()` with no pathname flags,
so slashes and leading dots are ordinary characters. Quoted pattern characters
are escaped for the matcher. Invalid multibyte sequences are processed one byte
at a time, a documented choice where the standard leaves behavior unspecified.
Locale initialization and full locale portability remain ENV-004/CSH-037 work;
the fixtures establish C-locale behavior and selected UTF-8 cases, not all locales.

## Dollar-single-quote decoding

[`quote.h`](../include/cshell/quote.h) and [`quote.c`](../src/quote.c) expose
`csh_quote_decode()` independently for parser here-document delimiter reuse.
It takes the contents of one `$'…'` region, excluding delimiters, and returns a
malloc-owned NUL-terminated byte string with an explicit length. It performs no
parameter, arithmetic, or command expansion. Expansion decodes every such
region before evaluating any value expansions in the word.

[Issue 8 section 2.2.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02_04)
defines the required escapes. The API records choices for unspecified cases:

- A decoded NUL discards that byte and the remainder of its quoted region;
  adjacent fragments continue normally.
- Hexadecimal escapes consume at most two digits; octal escapes consume at most
  three digits and reduce the result modulo 256.
- Unknown escapes, backslash-newline, and a trailing backslash remain literal.
- `\e` and `\cX` use ASCII control encodings; unavailable single-byte controls
  return INVALID after a locale representability check. The API never changes
  the process locale. The documented supported encodings are C/POSIX and ASCII
  compatible locales.

## Arithmetic and parser cooperation

[`arithmetic.h`](../include/cshell/arithmetic.h) exposes an evaluator for an
already-expanded expression and a grammar-only probe. Expansion first expands
its nested parameter/substitution/arithmetic fragments with scalar context.
The evaluator implements signed `long`, decimal/octal/hexadecimal constants,
C integer operators, assignment operators, short-circuit `&&`/`||`, conditional
`?:`, and comma. Variable values must be integer constants with an optional
sign. Unset/empty variables become zero except for nounset; recursive evaluation
of variable strings, `sizeof`, increment/decrement, and integer suffixes are not
supported. Empty expressions produce zero.

Overflow, division by zero, `LONG_MIN / -1`, and invalid shift counts return
errors before undefined C operations occur. Negative left shifts are rejected;
negative right shifts round toward negative infinity. Assignments roll back on
all errors, and the result scalar is unchanged on evaluator failure. Both
arithmetic parsing and word expansion bound recursive nesting at 128 levels and
return explicit errors above that limit.

`csh_arith_probe()` checks expression grammar and assignment targets without
reading state or evaluating operations. Oversized constants and `1/0` remain
syntactically arithmetic. A parser must represent nested shell expansions as
arithmetic operands while probing: it must not execute them to disambiguate.

The [Issue 8 arithmetic-first rule](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_03)
also needs lexer input checkpoint/replay to reinterpret an invalid arithmetic
candidate as command substitution. This was coordinated with concurrent
CSH-005 work: this ticket supplies the probe; the existing lexer still reserves
`$((` for arithmetic and cannot replay a failed candidate. The parser/lexer
checkpoint/replay integration is tracked by [CSH-041](tickets/CSH-041-arithmetic-substitution-replay.md).
`$((echo hi); )` is still diagnosed as incomplete arithmetic; the explicit
`$( (echo hi); )` form uses the existing command-parser handshake. No full
ambiguity-resolution claim is made by these module tests.

## Deferred substitutions and integration

`csh_expand_options.substitute` is a lazy callback receiving state, the borrowed
token, and the command/backquote fragment index. CSH-026 associates that
index with the parser-owned command AST and executes it in a forked environment,
capturing output/status and removing trailing newlines. Selected backquotes are
decoded once and parsed through the ordinary parser. The callback
returns borrowed, already-normalized bytes valid until its next invocation;
expansion copies them immediately and rejects embedded NULs. The callback must
report failures through the expansion result/error contract.

Without a callback, an encountered command/backquote returns `DEFERRED` with
its fragment index and no partial output or state mutation. Unselected operands
never request substitution. This is an explicit integration boundary, not a
command parser or an executor. CSH-026 implements execution order, capture,
substitution status, here-document context, and end-to-end scripts; CSH-025 implements
IFS splitting, filename generation, and final metadata removal described below.

Run `make test-expand` for bounded API, arithmetic, decoder, and allocation-fault
fixtures without the legacy build. See [Testing](testing.md#value-expansion-api-and-sanitizer-checks)
for sanitizer and Docker validation.

## Final fields and pathname generation

`csh_expand_fields(state, expansion, options, out, error)` borrows a successful
intermediate expansion and reads the current shell IFS and `noglob` option.
Release its independent strings/vector with `csh_fields_destroy()`. The
`csh_fields.count` records the argument count; an allocated `values` vector has
an extra NULL terminator. Zero fields may use a NULL vector. Neither state nor
input is changed, and the result survives their destruction. On failure all
partial output is released and cleared. Diagnostics use `CSH_FRAGMENT_ROOT`
because the intermediate fields have no source positions.

Argument context first splits only eligible unquoted expansion spans. Literal
IFS bytes, protected tilde replacements, escaped bytes, and quoted spans stay
intact. Unset IFS means space/tab/newline; empty IFS disables delimiter splitting
but still removes implicit empty values. Whitespace delimiters coalesce;
non-whitespace delimiters can terminate empty fields. Explicit quoted empty
spans remain at their original positions, so a quoted empty after a trailing
separator can retain a final empty argument. Positional field boundaries from
the value stage remain separate.

The implementation follows the
[Issue 8 field-splitting algorithm](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_05).
In particular, `x=' a'; set -- ""$x` produces an empty field followed by `a`:
the explicit empty candidate precedes the separator. Some older reference
shells discard that candidate, so the fixture asserts the specified result
without using those shells as an oracle. IFS characters are decoded in the
caller's locale; only space, tab, and newline count as IFS whitespace. Invalid
multibyte sequences in IFS are treated as individual bytes. Input bytes need not
be valid characters, and a multibyte delimiter cannot cross span/result
boundaries. The supported locale evidence covers C/POSIX and selected UTF-8
cases; process locale initialization remains CSH-037 work.

After splitting, argument fields undergo pathname generation unless
`CSH_OPT_NOGLOB` is set. Each pathname component uses POSIX `fnmatch()` with
leading-dot protection. Unquoted `*`, `?`, and bracket expressions match names;
quoted pattern characters and protected backslashes remain literal. Unquoted
expansion-produced backslashes escape the following pattern character outside
bracket expressions, as specified by section 2.14.1; handling within brackets
follows the host `fnmatch()` choice. They never introduce new shell syntax. A leading dot must be explicitly matched outside brackets; this API chooses
not to let a bracket list such as `[.]` introduce a hidden name. Pattern
components exclude
`.` and `..`, while literal `./` and `../` remain usable. Slashes separate
components, repeated slash spelling is preserved, and a trailing slash requires
a directory. Directory symlinks are followed; dangling symlinks can match the
final component. Matches for each field are sorted with the active locale's
collation (byte order breaks ties). An unmatched pattern remains unchanged.
Matched filenames are never split or expanded again.

Assignment context omits splitting and pathname generation and returns plain
value bytes, including an empty value. Pattern context also omits both stages,
but returns matcher-ready strings: quote-protected pattern characters and
protected backslashes are escaped for `fnmatch()` without `FNM_NOESCAPE`.
A quoted byte within a POSIX bracket subexpression (class, collating element,
or equivalence class) makes that subexpression literal. Reference shells differ
on quoted class names; fixtures assert this protection policy directly.
These escapes encode matching semantics, not shell syntax, and must not be
re-lexed or used as ordinary argument strings. CSH-026 routes parameter-removal
operands through this same final pattern
encoder, including protection for quoted POSIX class names and empty patterns.

The optional `csh_field_options.interrupted` callback is polled during splitting,
traversal, and output copying. It runs in ordinary execution and must not mutate
the borrowed state, input, locale, or working directory. A nonzero result or
filesystem `EINTR` returns `CSH_EXPAND_INTERRUPTED`; all directory streams and
allocations are released. Path traversal is iterative, keeps at most one
stream open, and returns `CSH_EXPAND_LIMIT` beyond 4096 components. Missing,
inaccessible, overlong, and symlink-loop paths are non-matches. Allocation
failures and filesystem `ENOMEM` return `NOMEM`; other filesystem failures
(including descriptor exhaustion) return `IO`.

This finalization stage cannot reverse earlier successful value-expansion side
effects. An executor requiring an atomic whole-word operation should checkpoint
state around both calls. CSH-026 takes a checkpoint around both stages in
command preparation.
The public executable uses these APIs for all command words and expanded
redirection operands.

## Integrated execution and capture

`src/prepare.c` expands command arguments first, applying declaration context to
assignment-shaped operands of resolved `export` and `readonly` commands. It then
expands and applies each redirection in source order, followed by prefix values.
Assignment slices retain fragment identities and rebase byte offsets so nested
substitutions continue to use the parser's ASTs. Later prefix values see earlier
prefix assignments; final persistence/export still depends on command category.
Arguments see the prior environment. Redirections of commands with no command
name expand against a copied state. Redirection and here-document `$@`/`$*` join
with the first IFS character, the same documented scalar-context choice as
assignment operands.

Substitutions fork copied state and cwd, use a fresh execution context, and
capture stdout through a close-on-exec pipe. The parent drains output before
waiting for its exact child PID. This handles output larger than pipe capacity
and leaves unrelated children waitable. Every trailing newline byte is removed;
interior newlines and other non-NUL bytes survive. A capture allocation failure
drains and discards remaining output before reaping. Embedded NUL output is a
diagnosed expansion error. `exit` and expansion errors terminate only the
substitution environment; its status becomes the substitution status.
The last obtained substitution status becomes the final status when no command
name remains. While expanding a command, `$?` retains the prior pipeline status
from the current environment, as specified by Issue 8 section 2.5.2; older host
shells can differ here. A substitution starts with that status in its copied state.

`csh_parser_document()` uses a dedicated lexer body mode, without wrapping body
bytes in synthetic shell quotes. Literal single/double quotes, whitespace,
operators and tilde survive; parameter, arithmetic and command/backquote
expansions remain active. Backslash only protects dollar, backquote, backslash
and newline at body level. Nested commands use the ordinary command lexer and
parser, including their own here-documents. Parsing/expansion of the body is
lazy; a skipped command never interprets its collected body.

Expansion failures use `csh_error_message()` for the owned diagnostic and
`error.reported` to avoid duplicate output when the executor reports under active
redirections. Noninteractive contexts request exit; interactive contexts return
to the next parser boundary. A failing word restores state across value and
field expansion; completed earlier words, substitutions and filesystem effects
are not rolled back. Pipeline stage expansion occurs after connecting that
stage's pipes and inside the stage's isolated environment.

`make test-runtime test-runtime-pty test-substitution` covers these boundaries,
including large captures, status, state, exact output, private descriptor
relocation, initially closed standard descriptors, and injected resource
failures. The [CSH-026 ticket](tickets/CSH-026-substitution-and-heredoc-integration.md)
records validation. These checks do not close the CSH-008 milestone or establish
full POSIX compliance.
