# CSH-046: Close invocation, lexical, grammar and alias evidence gaps

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: Assigned when work starts
- Issue: [#78](https://github.com/melliott18/cshell/issues/78)

## Goal

Inventory source clauses and map the existing module/runtime case names before adding missing public-runtime cases. Record required versus unspecified invocation and alias behavior, syntax boundaries, nonblocking-input invariants and chosen extensions. Cross-link every assertion, implementation and native/Docker run; do not classify module-only assertions as runtime coverage.

## Explicit current limitation

Module and runtime witnesses exist, but the complete invocation/input, token/grammar and alias requirement families are not traced to reviewed clause-level runtime assertions and revision-qualified platform results. The record lacks PATH-only negative invocation, unequal-identity interactive invocation, nonblocking terminal/post-completion descriptors, and documented nesting/shebang/operator policy witnesses.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [SH-001](../posix-matrix.md#sh-001) | Read commands from stdin, a script, or `-c`; keep command input distinct from utility stdin. |
| [SH-002](../posix-matrix.md#sh-002) | Map `command_name`, script name, arguments, `$0`, and implicit `-s`; honor the standalone `-` operand. |
| [SH-003](../posix-matrix.md#sh-003) | Read non-executable scripts; resolve slash and slashless script operands. |
| [SH-004](../posix-matrix.md#sh-004) | Detect interactive mode using `-i` or stdin plus terminal stdin/stderr; handle invocation errors. |
| [SH-005](../posix-matrix.md#sh-005) | Empty strings, blank/comment-only files exit zero; EOF preserves applicable last-command status. |
| [SH-006](../posix-matrix.md#sh-006) | Preserve bytes for commands reading stdin; allow all input types with a character-only, NUL-free parsed prefix; remove shell-imposed line limits. |
| [SH-007](../posix-matrix.md#sh-007) | Enable blocking reads when input is a nonblocking FIFO or terminal, including after completion. |
| [SH-008](../posix-matrix.md#sh-008) | Avoid non-interactive prompt output; send diagnostics to stderr and apply shell exit/error rules. |
| [LEX-001](../posix-matrix.md#lex-001) | Recognize words, longest operators, comments, newlines, and nested substitutions without early expansion. |
| [LEX-002](../posix-matrix.md#lex-002) | Apply backslash escaping and remove escaped newlines before token boundaries. |
| [LEX-003](../posix-matrix.md#lex-003) | Preserve literal single-quoted text, empty words, and adjacent quoted/unquoted fragments. |
| [LEX-004](../posix-matrix.md#lex-004) | Preserve double-quote context for dollar/backquote/backslash and parameter/substitution nesting. |
| [LEX-005](../posix-matrix.md#lex-005) | Decode Issue 8 dollar-single-quote escapes and retain resulting quoting. |
| [LEX-006](../posix-matrix.md#lex-006) | Substitute eligible aliases recursively with recursion prevention and correct token/parse timing. |
| [GRAM-001](../posix-matrix.md#gram-001) | Recognize reserved words only in their grammatical positions; preserve names and assignment words. |
| [GRAM-002](../posix-matrix.md#gram-002) | Parse pipelines, lists, groups, redirections and complete commands with specified precedence. |
| [GRAM-003](../posix-matrix.md#gram-003) | Collect multiple here-documents in order; preserve delimiter quoting, `<<-`, and incomplete-input state. |
| [GRAM-004](../posix-matrix.md#gram-004) | Parse every compound command and function definition, including Issue 8 case fall-through `;&`. |
| [GRAM-005](../posix-matrix.md#gram-005) | Distinguish syntax errors from incomplete input; execute only valid complete commands, without arbitrary command-size limits. |
| [U-017](../posix-utilities.md#u-017) | `alias`: create/redefine/query/list with reusable quoting; affect current shell/subshells; token substitution and read timing. |
| [U-031](../posix-utilities.md#u-031) | `unalias`: named removal and `-a`, nonexistent names/error status, current environment and future token-read effects. |

Relevant documented choices: D-001, D-002 (IO_LOCATION syntax only), D-003 (dollar-single-quote encoding only), D-004 (aliases), D-008. Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/input.py](../../tests/input.py)
- [tests/lexer.py](../../tests/lexer.py)
- [tests/parser.py](../../tests/parser.py)
- [tests/alias_parser.c](../../tests/alias_parser.c)
- [tests/runtime_cases.py](../../tests/runtime_cases.py)
- [tests/evaluation_cases.py](../../tests/evaluation_cases.py)

These are starting points for inspection, not claims that the complete rows
already pass. Reuse exact case names and assertions where they are sufficient;
add or split fixtures only for a concrete coverage gap.

## Acceptance criteria

- [ ] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [ ] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [ ] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [ ] Matrix rows and reverse ownership links reflect only the verified scope;
  broad rows are split where necessary and the CSH-012 compliance gate remains
  closed while any applicable requirements are unmet.

## Validation

Run the applicable focused suites above and the integration paths documented in
[Testing](../testing.md), including `make test test-pty test-harness`, Docker
and ASan/UBSan checks where the changed paths require them. Record exact case
names and results following the [evidence rules](../posix-evidence.md).
Reference-shell comparisons are separate observations, never normative oracles.

## Implementation notes/evidence

Allocated by the CSH-037 follow-up audit at baseline `58ca5c3`. The explicit
limitation and complete row list above replace reliance on already-completed
implementation tickets as owners of remaining verification work.
