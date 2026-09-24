# Parser and AST APIs

[CSH-005](tickets/CSH-005-parser-and-ast.md) adds
[`cshell/parser.h`](../include/cshell/parser.h) and
[`cshell/ast.h`](../include/cshell/ast.h). These modules build with the replacement
input, lexer, alias, and quote modules, independently of the runtime entry point. They never
execute commands, expand arguments, open redirection targets, or mutate shell
state. Runtime integration remains with CSH-018 and CSH-039.

The grammar follows the supported subset of POSIX.1-2024
[shell grammar](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_10)
and [here-documents](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_04).
Module evidence is recorded separately from runtime conformance.

## Reading complete commands

Create a parser with `csh_parser_create(&parser, input, &error)`. It borrows the
input object, which must be unread and outlive the parser, and owns its lexer.
Construction rejects an input whose position has already advanced. No other reader
may consume that input while parsing. `csh_parser_next()` synchronously acquires
physical lines only as required by the current command. It returns at a complete
command's newline, after collecting any pending here-documents. It does not read
the next command line. Semicolon-separated commands on the same line belong to
one returned list. Compound commands, function definitions, pipeline continuations,
and command substitutions can require further physical lines. Blank and comment-only lines are skipped.

| Result | Output and caller action |
| --- | --- |
| `CSH_PARSE_TREE` | Own the returned tree; evaluate it or destroy it before requesting the next complete command as runtime policy requires. |
| `CSH_PARSE_EOF` | Clean EOF with no tree; the error is clear. |
| `CSH_PARSE_INCOMPLETE` | Final EOF inside unfinished syntax, with no tree and a diagnostic. |
| `CSH_PARSE_ERROR` | Invalid syntax, input/allocation failure, or a nesting-limit diagnostic; no tree escapes. |

Pass an empty output pointer. Successful trees remain valid after later parses
and after parser and input destruction. `csh_parser_destroy()` releases only
parser-owned state; use `csh_ast_destroy()` for each returned tree. All failures
and EOF are sticky: subsequent calls reproduce the terminal result without
further input acquisition or allocation. An incomplete result describes final
EOF, not a resumable request to feed more bytes. An interactive continuation
callback and recovery after syntax errors are future runtime work.

Errors carry a static message, suggested shell status, system error where
applicable, and physical byte position. Syntax and incomplete-input diagnostics
suggest status 2; resource and acquisition failures preserve their failure
status. `csh_parser_source_name()` borrows the input's source name. Offsets are
zero-based; lines and byte columns are one-based. The caller formats diagnostics;
the parser never prints or exits.

## Tree shape and word classification

Every complete command is a `CSH_AST_LIST`. Its entries contain an AND/OR tree
and the following separator (`END`, `SEMI`, `AMPERSAND`, or `NEWLINE`), including
the separator's source span. `AMPERSAND` applies asynchronous execution to that
entire preceding AND/OR expression. `&&` and `||` have equal precedence and
associate left; a pipeline binds more tightly. Pipeline nodes preserve command
order and record leading `!`. An unnegated single command is returned directly
inside its list or AND/OR node without a one-element pipeline wrapper. Subshell and brace nodes each own their body list
and any trailing redirections.

Simple commands keep a source-order word vector. Each entry retains its token
and an `assignment` flag; the first ordinary word starts the command's argument
sequence. A simple node can contain only assignments, only redirections, or
both. Assignment classification checks an unquoted valid name and equals sign;
words following the command word are ordinary arguments. Declaration-utility
expansion contexts remain the expansion/execution owner's responsibility.

Reserved-word recognition uses unquoted logical spelling, removing recognized
backslash-newline continuations. Quoted words retain their ordinary-word role.
Classification depends on grammar position: a reserved spelling can be an
argument or a command name after assignment/redirection prefixes. CSH-027
recognizes compound and function syntax at command starts. Loop variable names,
case subjects, for-list words, and case patterns have their own grammar contexts:
`for if in then fi; do echo "$if"; done` retains all those words. An initial
unparenthesized `esac` ends a case command; `(esac)` and `a|esac)` retain it as a
pattern. A closer immediately after an unredirected compound delimiter can omit
a separator, as in `if (test) then (yes) else (no) fi`. A redirected compound
requires a separator before a reserved-word closer.

### Compound and function payloads

All payloads are owned and preserve lexical words without expansion. CSH-028
owns their later execution and function storage; parsing these nodes does not
install definitions or run control flow.

| Kind / payload | Contract for execution |
| --- | --- |
| `IF` / `data.if_clause` | Ordered `branches` contain condition and body lists for `if` then each `elif`; nullable `else_body` is a list. Conditions and selected bodies remain separate. |
| `FOR` / `data.for_clause` | `name` retains an unquoted shell name; `words` retains ordered structured words; `has_in` distinguishes an explicit empty list from the omitted list that uses positional parameters; `body` is a list. |
| `WHILE`, `UNTIL` / `data.loop` | Separate condition and body lists; the node kind selects the future continuation predicate. |
| `CASE` / `data.case_clause` | One subject `word` and ordered `items`, each with ordered `patterns`, a body list (possibly empty), and a terminator. `CASE_BREAK` means `;;`, `CASE_FALLTHROUGH` means POSIX.1-2024 `;&`, and `CASE_END` means an omitted terminator before `esac`. Explicit terminators retain their source spans; omitted spans are zero. |
| `FUNCTION` / `data.function` | Original unquoted name word and a compound body node. Any supported compound can be a body; an ordinary simple command cannot. Trailing redirections belong to the function node for invocation-time application, not the body or definition-time execution. |

All other compound redirections use the node's common ordered redirection vector.
`if`/loop bodies and conditions must be nonempty. Case commands can have no items,
and case item bodies can be empty. The `elif` and case item vectors grow without
a fixed count limit. Function names must be unquoted shell names and cannot be
reserved words in function-name position. This syntax API does not enforce the
application restriction on special-builtin names; CSH-028 owns definition-time
runtime validation. Extensions such as `function name`, arithmetic `for`, and
`;;&` are not implemented.

Words own their original lexer tokens, including physical spelling, positions,
and fragment provenance. Parsed `$(...)` substitutions own body trees associated
with the matching command fragment index and byte range in that token. The
parser uses the lexer's shared-cursor child handshake, so parentheses in groups
and raw here-document bodies do not prematurely terminate substitutions.
Backquote and arithmetic fragments remain syntax for their expansion owners.
Alias substitution is applied during token reading; no parameter, command, or
filesystem expansion occurs.

## Redirections and here-documents

Each simple, compound, or function node owns an ordered redirection vector.
Entries are separately allocated so pending here-document references remain stable as the
vector grows. The exact operator enum, operand word, source span, and optional
IO_NUMBER token are retained. Only an unquoted digit word immediately adjacent
to a redirection operator is an IO_NUMBER; `2>out`, `2 >out`, and `'2'>out` have
different trees. Descriptor conversion and validity belong to execution.
The optional `{name}` descriptor-allocation extension is not implemented.

Here-document operands preserve their original word alongside a separate
quote-removed delimiter and `delimiter_quoted` flag. Delimiter interpretation
performs no parameter, command, arithmetic, pathname, or tilde expansion.
Quote removal applies to the literal delimiter spelling, including text that
resembles substitutions: `${x:-"EOF"}` becomes `${x:-EOF}`, while surrounding
double quotes protect inner single quotes in `"$(echo 'EOF')"`. The original
word and any parsed substitution tree remain unchanged.
Dollar-single-quoted regions use the shared
[`quote.h`](../include/cshell/quote.h) byte decoder. Its documented choices for
unspecified escape and NUL cases also apply to delimiters.

Pending documents are collected in source order at the next grammar newline,
including newlines that continue a pipeline or AND/OR expression. Body bytes
are consumed through the lexer's raw interface and attached to their original
redirections. Quoted delimiters preserve body backslash-newlines. For unquoted
bodies, delimiter recognition uses logical lines with backslash-newlines removed;
`<<-` strips tabs at the beginning of those logical lines. The stored body retains
physical backslash-newline pairs so CSH-026 can process the original escape
spelling during expansion; tabs selected for stripping are already removed.
Quoted bodies preserve both those pairs and their literal interpretation.
Retained bytes are otherwise unexpanded.
`body_start` records the first physical body position; `body_end` is the
physical start of the delimiter logical line, excluding that delimiter.
A matched empty document owns an empty buffer; a NULL buffer denotes an
uncollected document and cannot occur in a successful returned tree.
Premature EOF reports incomplete input and discards the entire affected tree.
CSH-026 owns eventual body expansion and execution integration.

## Ownership, allocation, and limits

AST pointers have one owner and must form an acyclic tree. Constructors create
empty initialized objects. Append helpers move inputs only on success, clearing
the moved word, redirection pointer, or child pointer. Failure leaves the inputs
with their original owners. `csh_ast_if_add`, `csh_ast_case_add`, and
`csh_ast_word_vector_add` follow the same rule. Direct child and word assignment
into fresh payloads also transfers ownership; zero the previous owner.
`csh_ast_case_item_destroy` releases an unattached, partially built case item.
Counts cover initialized entries; capacities belong to the helpers. A node's `destroy_next` field is reserved for cleanup and must
remain NULL during ordinary use.

Destruction iteratively walks owned children without allocation, including
substitution trees, compound payloads, and long AND/OR chains. Words, pipelines,
lists, conditional branches, case items/patterns, redirections, and here-document
bodies grow dynamically with overflow checks. Recursive compound, function-body,
and substitution parsing has a 128-context guard that reports a diagnostic
instead of exhausting the C stack. This implementation limit remains an open
part of the broader unrestricted-command-size requirement; ordinary sequence
length and word/body size have no fixed parser cap.

[CSH-041](tickets/CSH-041-arithmetic-substitution-replay.md) resolves ambiguous
`$((` input with arithmetic-first checkpoint/replay. On `CSH_LEX_REPLAY`, the
parser destroys speculative substitution ASTs at or after the pending command
fragment index and resumes the normal command handshake. Earlier substitutions
in that word survive. Nested parser syntax failures can unwind to the candidate
owner and retry through `csh_lexer_replay_arithmetic()`; resource failures and
nesting-limit errors remain failures. Lexer snapshots preserve physical feeds,
alias source identities, and ancestor word positions. Here-document queues stay
with their parser frames and are rebuilt with the replayed command tree.

Attach a borrowed alias table with `csh_parser_set_aliases()` to enable
[CSH-030 alias substitution](aliases.md). Leave it NULL to retain ordinary
parsing. Change the table only between `csh_parser_next()` calls; the next
complete command sees the new definitions. Alias checks happen before
consuming later tokens, using grammar position and lexer provenance.
