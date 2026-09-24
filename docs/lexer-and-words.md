# Lexer and word APIs

[CSH-004](tickets/CSH-004-lexer-and-words.md) introduces
[`cshell/lexer.h`](../include/cshell/lexer.h) and
[`src/lexer.c`](../src/lexer.c). These replacement interfaces build without the
legacy scanner or its argument-array interface. They preserve syntax for the
parser and expansion modules; they do not read descriptors, evaluate words,
print diagnostics, or execute commands. CSH-018 owns replacement-runtime
integration, and CSH-039 owns the public executable's cutover.

The lexical contract follows POSIX.1-2024
[quoting](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02)
and
[token recognition](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_03).
The [parser](parser-and-ast.md) implements the initial command grammar;
expansion and later compound syntax remain separate work.
[CSH-030](aliases.md) adds alias storage and parser-controlled substitution. Passing
module fixtures does not establish runtime behavior or complete conformance.

## Feeding and reading

Create a root lexer with `csh_lexer_create()`, supplying a source name and an
error object. The lexer copies the name. `csh_lexer_feed()` copies the supplied
bytes into its source buffer. The caller can then reuse its input buffer. Set
`final` when the source has ended; a zero-length final feed is valid. No further
feed is allowed after final input or a sticky failure.

Input acquisition stays with the caller. The normal consumer connects the
[input API](input-and-invocation.md) by feeding one physical line at a time,
calling `csh_lexer_next()` until more input is needed. It must honor the parser's
complete-command boundaries before acquiring another line. Feeding a whole
script is useful for fixtures, but is inappropriate for a runtime whose
commands may read from the same input descriptor.

| `csh_lexer_next()` result | Caller action |
| --- | --- |
| `CSH_LEX_TOKEN` | Accept the owned token; continue grammar processing. |
| `CSH_LEX_MORE` | Supply more input when the parser requests it. The lexer retains partial syntax. |
| `CSH_LEX_COMMAND` | Enter a child lexer so the parser can recognize the nested command substitution. |
| `CSH_LEX_EOF` | Handle clean lexical EOF. The parser still decides whether its grammar is complete. |
| `CSH_LEX_ERROR` | Read the error, release owned outputs, and destroy the root lexer. |

Pass an empty token destination. A successful token result transfers ownership
to the caller; every other result clears the destination. Call
`csh_token_destroy()` before reusing a destination that owns a token.

`CSH_LEX_MORE` can mean either that the next character is unavailable or that a
word remains unfinished. `csh_lexer_context()` distinguishes these cases and
provides the innermost opening context and position when present. For example,
an unfinished quote can direct the runtime's continuation prompt and later EOF
diagnostic. Lexical completeness is separate from grammar completeness: a
finished `&&` token alone cannot determine whether a command is complete.

## Tokens, fragments, and physical spelling

Each `struct csh_token` owns its source name, raw bytes, and fragment array. It
remains valid independently of the lexer, later feeds, later tokens, and nested
lexer destruction. Use `length` to inspect the raw bytes rather than inferring
their length from a C string. An input NUL byte is diagnosed rather than
silently truncating the source; this also applies to raw skipping.

`raw` records physical source spelling, including quote delimiters, escape
characters, substitution delimiters, and escaped newlines. This supports
diagnostics without losing how the user wrote a word. It is not an expanded
argument and is not automatically the spelling used for parser classification.
For example, a backslash-newline between `i` and `f` does not prevent the parser
from recognizing `if` in the appropriate grammar position.

Word fragments form a flat tree in preorder. A fragment's `parent` is the index
of its containing fragment, or `CSH_FRAGMENT_ROOT` for a direct child of the
word. Its half-open `[begin, end)` range indexes the token's raw bytes. Parent
ranges contain their child ranges; concatenating every fragment would
therefore duplicate nested bytes. Delimiter-containing fragments include their
delimiters in the range.

| Fragment kind | Preserved information |
| --- | --- |
| `CSH_FRAGMENT_TEXT` | Text and its quote context. |
| `CSH_FRAGMENT_QUOTED` | A quoted region, including an empty pair of quotes. |
| `CSH_FRAGMENT_ESCAPE` | An escape sequence whose source spelling must survive until interpretation. |
| `CSH_FRAGMENT_CONTINUATION` | A backslash-newline removed when interpreting the logical spelling. |
| `CSH_FRAGMENT_PARAMETER` | Parameter syntax and its nested word structure. |
| `CSH_FRAGMENT_COMMAND` | The complete raw `$(...)` region accepted through the parser handshake. |
| `CSH_FRAGMENT_ARITHMETIC` | Arithmetic-expansion syntax without evaluation. |
| `CSH_FRAGMENT_BACKQUOTE` | Backquoted command syntax without execution. |

The quote enum distinguishes unquoted, single-quoted, double-quoted, and
dollar-single-quoted regions. Adjacent regions stay in one word. Empty quoted
regions remain represented even though they contain no text. Expansion must
keep this information: an explicit empty quoted argument differs from an
unquoted expansion that produces no fields.

Dollar-single-quoted escapes remain source spelling in this module. [CSH-024](value-expansions.md)
decodes them before expansion and owns the resulting byte and locale choices.
The lexer records boundaries and quoting without evaluating escape values.

For logical spelling, omit continuation fragments in the lexical context that
recognized them. Preserve other quote and escape spelling until the relevant
parser or expansion operation interprets it. In particular, quoted reserved
words must remain distinguishable from unquoted reserved words. Source text
inside a command fragment is opaque to the surrounding word's fragment tree;
the nested parser owns its tokens and syntax.

Source positions use the input API convention: zero-based byte offsets and
one-based physical lines and byte columns, with exclusive end positions.
Continuations can therefore span multiple physical lines even when they join
one logical token. Positions are not display columns or Unicode character
indices.

The lexer emits word tokens without deciding whether they are assignments,
reserved words, names, or descriptor numbers. CSH-005 applies those contextual
classifications. It must retain both quoting facts and adjacency to the next
redirection operator; `2>file`, `2 >file`, and `'2'>file` are distinct inputs.
Braces and `!` are words for parser classification, not standalone lexer
operators. The operator enum includes Issue 8's `;&`.

## Command-substitution handshake

The closing parenthesis of a command substitution is a grammar decision.
Counting parentheses cannot distinguish a `case` pattern terminator, and
ordinary token scanning must not inspect here-document bodies as commands.
The lexer consequently suspends at `$(...` and exposes that dependency instead
of guessing a command boundary.

1. On `CSH_LEX_COMMAND`, call `csh_lexer_command_begin(parent, &child, error)`.
   The child shares the parent's source cursor, positioned immediately after
   the opening `$(`.
2. Parse the child token stream. Only the deepest active frame may consume
   tokens. Nested command substitutions repeat this protocol.
3. When the grammar accepts its matching `CSH_TOKEN_RPAREN`, call
   `csh_lexer_command_end(parent, child, &closing, error)` before requesting
   another child token.
4. On success, the child is destroyed and the parent's pending command fragment
   covers the full raw substitution. Resume `csh_lexer_next(parent, ...)` to
   finish the surrounding word.

`command_end()` checks the closing token against the last child token. It does
not validate the command grammar: the parser must identify the correct closing
parenthesis. The closing token remains caller-owned and must still be
destroyed. The parent owns the child frame's lifetime; do not separately
destroy a child after completing the handshake. On failure, destroy the root,
which releases outstanding descendants and unpublished state.

All frames share fed bytes and one cursor. Feeding either active frame makes
input available to the entire chain. A parent word retains the raw bytes it
needs while its child consumes tokens or here-document content. No second
descriptor reader, copied-script parser, or heuristic parenthesis scanner is
required. The source may release earlier bytes when no active word needs them.

Backquote fragments retain their raw source for later command parsing and
escape interpretation. Arithmetic fragments retain syntax for the expansion
owner. These fragment types do not imply that a command AST or arithmetic
evaluator exists in CSH-004.

The current lexer treats a `$((` opener as arithmetic syntax. It tracks nested
contexts and its closing `))`, but cannot decide whether the contents form a
valid arithmetic expression. The
[Issue 8 ambiguity rule](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_03)
also requires trying command-substitution parsing once the input cannot be
parsed as arithmetic. CSH-024 supplies `csh_arith_probe()` for grammar-only classification;
[its contract](value-expansions.md#arithmetic-and-parser-cooperation) records the
coordinated CSH-005/CSH-026 requirement for lexer checkpoint/replay and fallback. Until then, an ambiguous input such as
`$((echo hi); )` is diagnosed as incomplete arithmetic; the explicitly
separated `$( (echo hi); )` uses the command-parser handshake. This limitation
does not affect the lexer preserving ordinary arithmetic expansion syntax.

## Here-document collection

The [CSH-005 parser](parser-and-ast.md) implements the ordered queue of pending
here-documents, their delimiter interpretation, and their attachment to
redirections. The raw-input handoff
supports collection without running ordinary token recognition on body text.

After the parser reaches the newline that starts pending bodies, it uses
`csh_lexer_pending()` to inspect the remaining source bytes and their physical
position. That function returns a borrowed view, a length, and the source's
final-input flag. The view expires after feed, next, raw-skip, command-frame
operations, or lexer destruction.

The parser copies the body bytes it retains, recognizes its delimiters, and
calls `csh_lexer_skip_raw()` to consume those bytes. It can feed further physical
lines as needed. Raw skipping is allowed only at a token boundary in the active
frame. After collection, ordinary tokenization resumes from the same updated
source position.

Always feed collected bytes through the shared source, including delimiters,
even when their body text is immediately skipped. Reading and discarding them
outside the lexer would invalidate source positions and omit bytes from an
enclosing command fragment. The parser is responsible for distinguishing
quoted delimiters, `<<-` tab handling, and the order of multiple pending bodies.
CSH-026 owns eventual body expansion and execution integration.

## Alias substitution handoff

[CSH-030](aliases.md) implements the handoff. After a delimited word, the parser
checks command position, quoting, alias lookup, and IO_NUMBER classification
before reading another token. `csh_lexer_follows_redirection()` inspects the
immediate logical delimiter without consuming input. Use
`csh_lexer_alias_active()` to suppress recursive names, then
`csh_lexer_alias_push()` to copy replacement text into the source at the current
cursor. Ordinary `feed()` continues to append physical input.

Replacement bytes undergo ordinary token recognition, including operators,
quotes, nested command frames, and raw here-document collection. A synthetic
space separates each replacement from remaining input. A value ending in space
or tab makes the next token's `alias_eligible` flag true, including the permitted
quoted-blank case. Operators and newlines consume the flag as well as words.
Active alias names survive nested substitution and are released when their
replacement input ends, or on failure/destruction.

Tokens produced from replacements own `alias_name`, `source_name` (prefixed
`alias:`), and `invocation_source`. `invocation` records the outermost physical
call site. Alias-local positions do not advance the original input position;
ordinary input positions resume after injected text. A token crossing a source
boundary retains its starting source identity and extends its coordinates over
the captured spelling. Token and fragment ranges therefore stay monotonic even
when quoting or command substitution crosses a replacement boundary. Lexer
errors in replacement text report the physical invocation position;
`csh_lexer_diagnostic_position()` provides the same mapping for parser contexts.

Pending enclosing words capture their original bytes independently. In
`$(short)`, the parent retains that spelling while the child AST sees the alias
replacement. `csh_lexer_command_fragment()` supplies the stable pending fragment
index; use the published fragment's byte ranges instead of subtracting absolute
positions across different sources.

The parser borrows an optional alias table and respects complete-command
boundaries. The [alias contract](aliases.md) records timing, ownership, and
choices allowed by Issue 8. None of these APIs execute alias definitions or
other commands.

## Ownership and failure handling

The root lexer owns its copied source name, fed bytes, internal stacks, and
child frames. A published token belongs exclusively to its caller. Fragment
offsets reference the published token's own raw storage, never the mutable
source buffer. Context-description strings returned by `csh_lexer_context()`
and names returned by the enum-name helpers are static.

Successful constructors and feeds report zero; failure reports -1 through the
provided error object. A constructor clears its output on failure. Lexical
errors are sticky and release unpublished token storage. The caller formats
the diagnostic and decides the runtime status; the lexer never prints or exits.
Published tokens still need their ordinary cleanup after a later lexer error.

Storage grows with retained source, token text, fragments, and nesting rather
than imposing a fixed argument or line limit. Allocation and representational
limits are reported as failures. See the
[CSH-004 validation record](tickets/CSH-004-lexer-and-words.md#validation) for
long-token, repeated-scan, nested-input, and allocation-failure coverage and
the limits of the current evidence.
