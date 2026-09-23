# Value expansion API

[CSH-024](tickets/CSH-024-value-expansions.md) adds independent value expansion
in [`expand.h`](../include/cshell/expand.h) and [`expand.c`](../src/expand.c).
It consumes the lexer's owned WORD tokens and shell-state storage. The default
`cshell` executable still runs the prototype. This API does not execute commands,
split fields on IFS, expand filenames, or discard the final quote metadata.

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

The parser/assignment owner must provide a structured value word for assignment
context. Relocate fragment byte offsets when constructing a value-only token;
do not pass the whole assignment spelling as a value. Context restrictions
remain in the result for CSH-025 to honor.

Each output field owns a sequence of spans. A span records its bytes, length,
quote mode, origin (literal, tilde, parameter, arithmetic, substitution), IFS
eligibility (`split`), and explicit-empty retention (`keep_empty`). Escaped bytes
and tilde replacements carry single-quote protection. Adjacent spans belong to
the same field. A quoted `$@` creates separate fields, with surrounding text
joined to the first/last field; zero positional parameters contribute no fields.
Empty quoted positionals remain explicit empty spans. An unquoted unset value
has an empty, unprotected span for CSH-025 to discard when appropriate.

For example, with `v='a b'`, `x$v"$v"` is one intermediate field containing:

| Bytes | Origin | Quote | Split |
| --- | --- | --- | --- |
| `x` | literal | none | no |
| `a b` | parameter | none | yes |
| `a b` | parameter | double | no |

Quote spelling is interpreted to obtain value bytes, but its protection remains
in these spans until CSH-025 completes quote removal. Consumers must not flatten
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
checkpoint/replay integration remains an explicit CSH-005/CSH-026 follow-up.
`$((echo hi); )` is still diagnosed as incomplete arithmetic; the explicit
`$( (echo hi); )` form uses the existing command-parser handshake. No full
ambiguity-resolution claim is made by these module tests.

## Deferred substitutions and integration

`csh_expand_options.substitute` is a lazy callback receiving state, the borrowed
token, and the command/backquote fragment index. CSH-026 can associate that
index with the parser-owned command AST, execute it in the proper isolated
environment, capture output/status, and remove trailing newlines. The callback
returns borrowed, already-normalized bytes valid until its next invocation;
expansion copies them immediately and rejects embedded NULs. The callback must
report failures through the expansion result/error contract.

Without a callback, an encountered command/backquote returns `DEFERRED` with
its fragment index and no partial output or state mutation. Unselected operands
never request substitution. This is an explicit integration boundary, not a
command parser or an executor. CSH-026 owns real execution order, capture,
substitution status, here-document context, and end-to-end scripts; CSH-025 owns
IFS splitting, filename generation, and final metadata removal.

Run `make test-expand` for bounded API, arithmetic, decoder, and allocation-fault
fixtures without the legacy build. See [Testing](testing.md#value-expansion-api-and-sanitizer-checks)
for sanitizer and Docker validation.
