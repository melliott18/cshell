# POSIX requirements and evidence matrix

This is the CSH-036 planning baseline for POSIX.1-2024 (Issue 8), based on
`main` at `233a4ca`. It is not a conformance claim. Work in other branches does
not become evidence here until its implementation, fixtures, and results are
linked. [POSIX tracking](posix.md) describes the project target.

The inventory is split into:

- This document: shell language, `sh` invocation, execution, jobs and signals.
- [Utilities and options](posix-utilities.md): special and intrinsic utilities,
  host dependencies, shell options, and conditional option-group decisions.
- [Evidence conventions and differential example](posix-evidence.md): states,
  fixture provenance, exact smoke coverage, and reference-shell records.
- [Requirements by owning ticket](posix-owners.md): reverse lookup across both
  requirement tables. Each row below links back to its implementation owner.

## Reading and maintaining the inventory

Each stable requirement ID identifies a reviewable behavior family, not every
sentence in its source section. Split a row into finer cases as its ticket is
implemented; retain the original ID as a parent or redirect. Every child must
retain the source, applicability, owner, fixture target and evidence. Never
promote a family to verified because one example passes.

`required` means included in the target. `conditional` means that the source's
stated condition or selected profile controls applicability. `unspecified`,
`undefined`, and `implementation-defined` have different meanings; use the
[evidence rules](posix-evidence.md), not a reference shell, to choose assertions.
The Scope column calls out known variations without claiming an exhaustive list
of every unspecified input in the standard. Review the full linked section
before writing tests. A pending profile choice is an open gap, not a passing
or inapplicable result.

Fixture names below are **planned logical IDs**, not links to existing files or
a new harness format. CSH-017/033 own the behavioral/PTY adapters; implementation
tickets add actual fixture paths and case IDs when available. All runtime
families remain open: prototype observations and the bounded CSH-016, CSH-004,
CSH-005, and CSH-022 API evidence below do not establish complete replacement-runtime
behavior. `implemented` requires a linked implementation; `verified` additionally
requires passing,
revision-qualified results for the scoped cases. `inapplicable` requires a
resolved source-based scope decision and remains distinct from skipped tests.

Sources link to the selected Issue 8 edition. Section numbers below deliberately
use Issue 8 numbering (jobs 2.11, signals 2.12, environment 2.13, patterns 2.14).
Where one row names adjacent sections, the link starts at the first relevant
section and the fixture must cite the particular clause it exercises.

<a id="csh-016-api-evidence"></a>

### CSH-016 API evidence

The [input and invocation contract](input-and-invocation.md) is implemented in
[`src/input.c`](../src/input.c) and
[`src/invocation.c`](../src/invocation.c), with assertions in
[`tests/input.py`](../tests/input.py),
[`tests/input_fixture.c`](../tests/input_fixture.c), and
[`tests/input_faults.c`](../tests/input_faults.c). The
[CSH-016 validation record](tickets/CSH-016-input-and-invocation.md#validation-evidence-2026-09-23)
records 63 passing API checks on macOS arm64 and Docker Linux aarch64, including
ASan/UBSan runs. These fixtures inspect source bytes, owned invocation fields,
error/status data, and prompt selection; they execute no shell commands. They
do not supply the revision-qualified end-to-end evidence needed to mark the
families below `verified`. CSH-018 owns replacement-runtime integration and
CSH-039 owns the public executable cutover. Each affected row keeps its broader
runtime or untested subcases open.

<a id="csh-004-api-evidence"></a>

### CSH-004 API evidence

The [lexer contract](lexer-and-words.md), [`src/lexer.c`](../src/lexer.c), and
[`tests/lexer.py`](../tests/lexer.py) implement and test lexical token kinds,
physical spans, quote/escape provenance, incremental nesting, and parser handoffs.
The [validation record](tickets/CSH-004-lexer-and-words.md#validation-evidence-2026-09-23)
details native, sanitizer, and Linux checks. CSH-005 supplies the supported
command-substitution grammar and here-document queue/delimiter processing;
aliases remain with CSH-030. Dollar-single-quote escapes remain raw until CSH-024 decodes them
before expansion. Locale-sensitive multibyte lexical interpretation remains
open in ENV-004/CSH-037. These module checks do not establish runtime conformance.

<a id="csh-005-api-evidence"></a>

### CSH-005 API evidence

The [parser and AST contract](parser-and-ast.md) is implemented in
[`src/parser.c`](../src/parser.c) and [`src/ast.c`](../src/ast.c).
[`tests/parser.py`](../tests/parser.py) checks structural precedence, contextual
words, grouping, source-order redirections, nested substitutions, here-documents,
and source diagnostics. Independent C fixtures cover input boundaries, owned
tree lifetimes, AST transfers, and allocation failures. See the
[ticket validation record](tickets/CSH-005-parser-and-ast.md) for commands and
platform evidence. These checks do not execute commands. CSH-027 compound
syntax, CSH-030 aliases, arithmetic-first ambiguity fallback, recursive nesting
beyond the documented guard, and replacement-runtime evidence remain open.

<a id="csh-022-api-evidence"></a>

### CSH-022 API evidence

The [shell-state contract](shell-state.md) is implemented in
[`src/state.c`](../src/state.c), with independent C assertions in
[`tests/state_fixture.c`](../tests/state_fixture.c) and
[`tests/state_faults.c`](../tests/state_faults.c). `make test-state` checks valid
name import, unset/empty values, export/readonly attributes, owned environment
snapshots, invocation parameter copies, special-parameter metadata, option
storage, clone isolation, and full-state checkpoints. The
[CSH-022 validation record](tickets/CSH-022-shell-state-storage.md#validation-evidence-2026-09-23)
records platform and sanitizer results. These are storage API checks, not shell
execution or expansion evidence. Assignment categories, variable builtins,
startup initialization, and runtime option behavior remain open in their owning
tickets; the broader families below remain `missing`.

<a id="csh-024-api-evidence"></a>

### CSH-024 API evidence

The [value-expansion contract](value-expansions.md) is implemented in
[`src/expand.c`](../src/expand.c), [`src/arithmetic.c`](../src/arithmetic.c), and
[`src/quote.c`](../src/quote.c). `make test-expand` checks intermediate field and
span provenance, null/unset operators, positional parameters, tilde, patterns,
checked arithmetic, decoding, deferred callback inputs, and allocation failures.
See the [validation record](tickets/CSH-024-value-expansions.md#validation-evidence-2026-09-23)
for native/Docker and ASan/UBSan coverage. These APIs are implemented and tested
independently of command execution. CSH-025 splitting/globbing, CSH-026 script
integration, and parser/lexer arithmetic fallback replay remain open; no row
below claims complete runtime verification based on these module tests.


## Invocation and input

| ID | Requirement | Source | Scope / variations | Owning tickets | Planned fixture ID | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="sh-001"></a>SH-001 | Read commands from stdin, a script, or `-c`; keep command input distinct from utility stdin. | [sh OPTIONS, STDIN](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_04) | required | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-018](tickets/CSH-018-status-and-cli-integration.md) | `invocation/modes` | missing; [API evidence](#csh-016-api-evidence): string/file/fd sources, copied invocation mappings, and no read-ahead beyond a newline; cross-mode execution and utility-stdin integration remain open. Stdin-only prototype observation: [SMOKE-EXTERNAL](posix-evidence.md#smoke-external) |
| <a id="sh-002"></a>SH-002 | Map `command_name`, script name, arguments, `$0`, and implicit `-s`; honor the standalone `-` operand. | [sh OPERANDS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_05) | required; undefined operand combinations excluded | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-022](tickets/CSH-022-shell-state-storage.md) | `invocation/operands` | missing; [API evidence](#csh-016-api-evidence): `invocation: ... with copied operands` checks `-c`, script, implicit/explicit `-s`, `--`, and lone `-` mappings; [state API evidence](#csh-022-api-evidence) also checks independent storage of these mappings; language-level parameter expansion remains open |
| <a id="sh-003"></a>SH-003 | Read non-executable scripts; resolve slash and slashless script operands. | [sh OPERANDS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_05) | required; optional PATH search is choice D-001 | [CSH-016](tickets/CSH-016-input-and-invocation.md) | `invocation/script-search` | missing; [API evidence](#csh-016-api-evidence): opens generated non-executable scripts by absolute path and slashless cwd operand; missing/unreadable/directory errors checked. No PATH search is the documented API policy; PATH-only negative fixture and runtime behavior remain open |
| <a id="sh-004"></a>SH-004 | Detect interactive mode using `-i` or stdin plus terminal stdin/stderr; handle invocation errors. | [sh OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_04) | required; conditional terminal/identity tests | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-018](tickets/CSH-018-status-and-cli-integration.md), [CSH-033](tickets/CSH-033-pty-test-harness.md) | `pty/interactive-detection` | missing; [API evidence](#csh-016-api-evidence): all stdin/stderr terminal combinations, `-s` operands, forced `-i` modes, and usage/open error data; unequal-identity cases and runtime diagnostic/status handling remain open |
| <a id="sh-005"></a>SH-005 | Empty strings, blank/comment-only files exit zero; EOF preserves applicable last-command status. | [sh INPUT FILES / EXIT STATUS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_07) | required | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-018](tickets/CSH-018-status-and-cli-integration.md) | `invocation/empty-eof-status` | missing; [API evidence](#csh-016-api-evidence): empty sources, empty `-c`, final unterminated lines, and repeated EOF; blank/comment execution and zero/last-command exit status remain open. Explicit exit smoke does not test EOF |
| <a id="sh-006"></a>SH-006 | Preserve bytes for commands reading stdin; allow all input types with a character-only, NUL-free parsed prefix; remove shell-imposed line limits. | [sh STDIN / INPUT FILES](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_06) | required; asynchronous interactive shared reads unspecified | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-031](tickets/CSH-031-evaluation-builtins.md) | `input/read-ahead-long-lines` | missing; [API evidence](#csh-016-api-evidence): file NUL/high-byte preservation, file/fd 200 KB lines, dynamic buffer growth, and shared-fd bytes after a newline; parsed-prefix and utility-consumption behavior remain open |
| <a id="sh-007"></a>SH-007 | Enable blocking reads when input is a nonblocking FIFO or terminal, including after completion. | [sh STDIN](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_06) | required when FIFO/terminal starts nonblocking | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-033](tickets/CSH-033-pty-test-harness.md) | `input/nonblocking-fifo-tty` | missing; [API evidence](#csh-016-api-evidence): `fd-contract` checks shared-pipe blocking normalization; implementation also handles terminals and does not restore nonblocking flags. Nonblocking-terminal and post-completion assertions remain open |
| <a id="sh-008"></a>SH-008 | Avoid non-interactive prompt output; send diagnostics to stderr and apply shell exit/error rules. | [sh STDERR / EXIT STATUS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_11) | required | [CSH-018](tickets/CSH-018-status-and-cli-integration.md) | `invocation/streams-errors` | missing; smoke deliberately strips prompts |
| <a id="sh-009"></a>SH-009 | Do not fail pathname expansion because of file size; document redirection offset maximum. | [sh DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_03) | required; implementation-defined maximum, D-002 | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md), [CSH-037](tickets/CSH-037-portability-audit.md) | `portability/large-files` | missing |

## Lexing and grammar

| ID | Requirement | Source | Scope / variations | Owning tickets | Planned fixture ID | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="lex-001"></a>LEX-001 | Recognize words, longest operators, comments, newlines, and nested substitutions without early expansion. | [2.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_03) | required | [CSH-004](tickets/CSH-004-lexer-and-words.md) | `lexer/tokens-nesting` | [API evidence](#csh-004-api-evidence); runtime and remaining grammar/expansion cases open |
| <a id="lex-002"></a>LEX-002 | Apply backslash escaping and remove escaped newlines before token boundaries. | [2.2.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02_01) | required | [CSH-004](tickets/CSH-004-lexer-and-words.md) | `lexer/escape-continuation` | [API evidence](#csh-004-api-evidence); runtime and remaining grammar/expansion cases open |
| <a id="lex-003"></a>LEX-003 | Preserve literal single-quoted text, empty words, and adjacent quoted/unquoted fragments. | [2.2.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02_02) | required | [CSH-004](tickets/CSH-004-lexer-and-words.md) | `lexer/single-quotes` | [API evidence](#csh-004-api-evidence); runtime and remaining grammar/expansion cases open |
| <a id="lex-004"></a>LEX-004 | Preserve double-quote context for dollar/backquote/backslash and parameter/substitution nesting. | [2.2.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02_03) | required; undefined/unspecified nested edge cases kept out of exact oracles | [CSH-004](tickets/CSH-004-lexer-and-words.md), [CSH-024](tickets/CSH-024-value-expansions.md), [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md) | `lexer/double-quotes` | [API evidence](#csh-004-api-evidence); runtime and remaining grammar/expansion cases open |
| <a id="lex-005"></a>LEX-005 | Decode Issue 8 dollar-single-quote escapes and retain resulting quoting. | [2.2.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02_04) | required; unspecified escape cases and implementation-defined locale encoding, D-003 | [CSH-004](tickets/CSH-004-lexer-and-words.md), [CSH-024](tickets/CSH-024-value-expansions.md) | `lexer/dollar-single-quotes` | [API evidence](#csh-024-api-evidence); runtime and full requirement-family verification open |
| <a id="lex-006"></a>LEX-006 | Substitute eligible aliases recursively with recursion prevention and correct token/parse timing. | [2.3.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_03_01) | required; alias/reserved-word and parse timing choices, D-004 | [CSH-030](tickets/CSH-030-alias-substitution.md), [CSH-004](tickets/CSH-004-lexer-and-words.md), [CSH-005](tickets/CSH-005-parser-and-ast.md) | `lexer/alias-boundaries` | missing |
| <a id="gram-001"></a>GRAM-001 | Recognize reserved words only in their grammatical positions; preserve names and assignment words. | [2.4; 2.10.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_04) | required; extra reserved words have specified/unspecified cases | [CSH-005](tickets/CSH-005-parser-and-ast.md), [CSH-027](tickets/CSH-027-compound-syntax.md) | `parser/reserved-assignments` | [API evidence](#csh-005-api-evidence); supported command positions and assignment classification; later compound syntax/runtime open |
| <a id="gram-002"></a>GRAM-002 | Parse pipelines, lists, groups, redirections and complete commands with specified precedence. | [2.10.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_10_02) | required; optional IO_LOCATION tracked D-002 | [CSH-005](tickets/CSH-005-parser-and-ast.md) | `parser/precedence-complete-command` | [API evidence](#csh-005-api-evidence); structural subset implemented, runtime evidence open |
| <a id="gram-003"></a>GRAM-003 | Collect multiple here-documents in order; preserve delimiter quoting, `<<-`, and incomplete-input state. | [2.3; 2.7.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_04) | required; source-specified unspecified nested cases excluded | [CSH-005](tickets/CSH-005-parser-and-ast.md), [CSH-004](tickets/CSH-004-lexer-and-words.md) | `parser/heredoc-queue` | [API evidence](#csh-005-api-evidence); collection and delimiter interpretation implemented, expansion/runtime open |
| <a id="gram-004"></a>GRAM-004 | Parse every compound command and function definition, including Issue 8 case fall-through `;&`. | [2.9.4; 2.9.5](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04) | required | [CSH-027](tickets/CSH-027-compound-syntax.md) | `parser/compounds-functions` | missing |
| <a id="gram-005"></a>GRAM-005 | Distinguish syntax errors from incomplete input; execute only valid complete commands, without arbitrary command-size limits. | [2.8.1; 2.9; 2.10](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01) | required | [CSH-005](tickets/CSH-005-parser-and-ast.md), [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-018](tickets/CSH-018-status-and-cli-integration.md) | `parser/errors-incomplete-large` | [Input API evidence](#csh-016-api-evidence) and [parser API evidence](#csh-005-api-evidence); invalid/incomplete/EOF and growing sequences implemented; recursive nesting guard and runtime execution remain open |

## Variables and expansion

| ID | Requirement | Source | Scope / variations | Owning tickets | Planned fixture ID | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="env-001"></a>ENV-001 | Import valid environment names with export attributes; preserve unset/empty, readonly and export state. | [2.5.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03) | required | [CSH-022](tickets/CSH-022-shell-state-storage.md), [CSH-029](tickets/CSH-029-state-builtins.md) | `state/import-attributes` | missing; [state API evidence](#csh-022-api-evidence) covers storage/import/attributes and independent exported snapshots; variable builtin and runtime integration remain open |
| <a id="env-002"></a>ENV-002 | Maintain positional parameters and `@`, `*`, `#`, `?`, `-`, `$`, `!`, `0`, including quoting and subshell behavior. | [2.5.1–2.5.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_01) | required; context-specific unspecified `@` cases labeled in fixtures | [CSH-022](tickets/CSH-022-shell-state-storage.md), [CSH-024](tickets/CSH-024-value-expansions.md) | `state/positional-special` | [API evidence](#csh-024-api-evidence); runtime and full requirement-family verification open |
| <a id="env-003"></a>ENV-003 | Initialize IFS, PPID and PWD correctly; consume HOME, PATH and locale variables with specified precedence. | [2.5.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03) | required; PWD exceptional cases unspecified | [CSH-022](tickets/CSH-022-shell-state-storage.md), [CSH-029](tickets/CSH-029-state-builtins.md) | `state/shell-variables` | missing; raw storage import does not implement IFS/PPID/PWD startup rules or variable consumption; CSH-029 and runtime consumers remain open |
| <a id="env-004"></a>ENV-004 | Respect initial LC_CTYPE lexical interpretation, locale-sensitive patterns and diagnostic locale. | [2.5.3; sh ENVIRONMENT VARIABLES](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_08) | required; locale availability is a test precondition | [CSH-004](tickets/CSH-004-lexer-and-words.md), [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md), [CSH-037](tickets/CSH-037-portability-audit.md) | `portability/locale` | missing |
| <a id="env-005"></a>ENV-005 | Track ENV startup, LINENO, PS1/PS2/PS4, history/editor/mail variables and NLSPATH requirements. | [2.5.3; sh ENVIRONMENT VARIABLES](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03) | conditional UP/XSI; profile resolution in [utility map](posix-utilities.md) | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-022](tickets/CSH-022-shell-state-storage.md), [CSH-031](tickets/CSH-031-evaluation-builtins.md), [CSH-032](tickets/CSH-032-shell-options.md), [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) | `pty/profile-variables` | missing; [API evidence](#csh-016-api-evidence): physical byte/line positions and caller-provided PS1/PS2 selection for interactive stdin; LINENO semantics, prompt expansion/output, startup variables, and profile remain open, not inapplicable |
| <a id="exp-001"></a>EXP-001 | Apply ordered, context-sensitive expansions; preserve field provenance, quoted empties and multi-field exceptions. | [2.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06) | required; optional expansion extensions excluded, D-008 | [CSH-024](tickets/CSH-024-value-expansions.md), [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md), [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md) | `expansion/order-context` | [API evidence](#csh-024-api-evidence); runtime and full requirement-family verification open |
| <a id="exp-002"></a>EXP-002 | Expand tilde prefixes for home/login names and assignments, treating the result as quoted. | [2.6.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_01) | required; unset HOME/unknown login cases unspecified | [CSH-024](tickets/CSH-024-value-expansions.md) | `expansion/tilde` | [API evidence](#csh-024-api-evidence); runtime and full requirement-family verification open |
| <a id="exp-003"></a>EXP-003 | Implement parameter default, assign-default, error, alternate and null-versus-unset operators; expand operator words only when needed. | [2.6.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_02) | required | [CSH-024](tickets/CSH-024-value-expansions.md) | `expansion/parameter-default-null` | [API evidence](#csh-024-api-evidence); runtime and full requirement-family verification open |
| <a id="exp-004"></a>EXP-004 | Implement parameter length, shortest/longest prefix/suffix pattern removal and nested/quoted operands. | [2.6.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_02) | required; source-specified special-parameter cases unspecified | [CSH-024](tickets/CSH-024-value-expansions.md), [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md) | `expansion/parameter-patterns` | [API evidence](#csh-024-api-evidence); runtime and full requirement-family verification open |
| <a id="exp-005"></a>EXP-005 | Execute both command-substitution forms in the required environment; strip trailing newlines and preserve statuses. | [2.6.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_03) | required; NUL output, redirection-only substitution and parse timing have unspecified cases, D-004 | [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md) | `expansion/command-substitution` | missing |
| <a id="exp-006"></a>EXP-006 | Evaluate arithmetic expressions, variables, required operators and diagnostics using supported integer semantics. | [2.6.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_04) | required; optional arithmetic extensions documented separately, D-005 | [CSH-024](tickets/CSH-024-value-expansions.md) | `expansion/arithmetic` | [API evidence](#csh-024-api-evidence); runtime and full requirement-family verification open |
| <a id="exp-007"></a>EXP-007 | Split only eligible expansion results with unset/empty IFS, separators, whitespace and empty-field rules. | [2.6.5](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_05) | required; additional IFS whitespace implementation-defined, D-003 | [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md) | `expansion/ifs-fields` | missing |
| <a id="exp-008"></a>EXP-008 | Expand matching pathnames, ordering and unmatched patterns; respect quoted patterns and noglob. | [2.6.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_06) | required | [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md), [CSH-032](tickets/CSH-032-shell-options.md) | `expansion/glob` | missing |
| <a id="exp-009"></a>EXP-009 | Remove syntactic quotes last while retaining quoted expansion results and literal quote characters. | [2.6.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_07) | required | [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md) | `expansion/quote-removal` | missing |
| <a id="exp-010"></a>EXP-010 | Match single/multiple-character patterns, bracket expressions/classes, quoting, slashes and leading periods. | [2.14.1–2.14.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_14) | required; locale-sensitive results use locale-qualified expectations | [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md), [CSH-028](tickets/CSH-028-control-flow-and-functions.md) | `expansion/pattern-notation` | missing |
| <a id="exp-011"></a>EXP-011 | Use assignment context for declaration-utility operands; defer context until applicable command-name processing. | [2.9.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_01) | required; expanded declaration-utility recognition unspecified, D-006 | [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md), [CSH-029](tickets/CSH-029-state-builtins.md), [CSH-031](tickets/CSH-031-evaluation-builtins.md) | `expansion/declaration-utility` | missing |

## Redirections

| ID | Requirement | Source | Scope / variations | Owning tickets | Planned fixture ID | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="red-001"></a>RED-001 | Apply redirections left to right, expand targets in context, use default descriptor numbers and restore parent descriptors. | [2.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07) | required; supported descriptor maximum implementation-defined, D-002 | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md) | `redirection/order-restore` | missing |
| <a id="red-002"></a>RED-002 | Open `<`, `>` and `>\|` with specified creation/truncation and noclobber handling. | [2.7.1–2.7.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_01) | required | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-032](tickets/CSH-032-shell-options.md) | `redirection/input-output-noclobber` | missing |
| <a id="red-003"></a>RED-003 | Append using `>>`, creating missing files without truncating existing data. | [2.7.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_03) | required | [CSH-019](tickets/CSH-019-simple-command-redirections.md) | `redirection/append` | missing |
| <a id="red-004"></a>RED-004 | Deliver here-documents with quoted/unquoted delimiters, tab stripping, expansion and evaluation timing. | [2.7.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_04) | required; backing object type unspecified, never require seeking | [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md), [CSH-019](tickets/CSH-019-simple-command-redirections.md) | `redirection/heredoc-expansion` | missing |
| <a id="red-005"></a>RED-005 | Duplicate/close input and output descriptors using `<&` and `>&`, including invalid-descriptor failures. | [2.7.5–2.7.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_05) | required; non-digit/non-minus operand cases unspecified | [CSH-019](tickets/CSH-019-simple-command-redirections.md) | `redirection/duplicate-close` | missing |
| <a id="red-006"></a>RED-006 | Open read/write redirections with `<>`, creation and offset behavior. | [2.7.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_07) | required | [CSH-019](tickets/CSH-019-simple-command-redirections.md) | `redirection/read-write` | missing |

## Execution and errors

| ID | Requirement | Source | Scope / variations | Owning tickets | Planned fixture ID | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="exec-001"></a>EXEC-001 | Process simple-command expansion, redirection and assignment in the specified order and permitted alternatives. | [2.9.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_01) | required; allowed order alternatives for special/no-name commands | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-023](tickets/CSH-023-assignment-environments.md), [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md) | `execution/simple-order` | missing |
| <a id="exec-002"></a>EXEC-002 | Apply prefix assignment lifetime by no-name/external/special/function category; enforce readonly errors. | [2.9.1.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_02) | required; visibility/export/function persistence choices D-006 | [CSH-023](tickets/CSH-023-assignment-environments.md), [CSH-028](tickets/CSH-028-control-flow-and-functions.md), [CSH-029](tickets/CSH-029-state-builtins.md) | `execution/assignment-categories` | missing |
| <a id="exec-003"></a>EXEC-003 | Handle assignment/redirection-only commands and last-substitution status without corrupting parent state. | [2.9.1.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_03) | required; redirection/substitution subshell sharing unspecified | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-023](tickets/CSH-023-assignment-environments.md), [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md) | `execution/no-command-name` | missing |
| <a id="exec-004"></a>EXEC-004 | Search commands with correct special-builtin/function/intrinsic/PATH precedence; execute pathname commands and format fallback. | [2.9.1.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_04) | required; search/cache choices qualified by source | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-031](tickets/CSH-031-evaluation-builtins.md) | `execution/search-fallback` | missing; absolute-path literal case observed in [SMOKE-EXTERNAL](posix-evidence.md#smoke-external) |
| <a id="exec-005"></a>EXEC-005 | Pass argv, environment and open descriptors to external commands; apply rules for initially closed standard descriptors. | [2.9.1.5–2.9.1.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_05) | required; permitted descriptor reopening cannot be mistaken for a failure | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-023](tickets/CSH-023-assignment-environments.md) | `execution/argv-env-fds` | missing |
| <a id="exec-006"></a>EXEC-006 | Connect concurrent pipeline stages before command redirections and wait for required completion. | [2.9.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_02) | required; waiting for all stages permitted | [CSH-020](tickets/CSH-020-pipeline-lifecycle.md) | `execution/pipeline-volume-order` | missing |
| <a id="exec-007"></a>EXEC-007 | Compute pipeline status and `!` negation, including Issue 8 pipefail selection. | [2.9.2 Exit Status](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_02_01) | required | [CSH-020](tickets/CSH-020-pipeline-lifecycle.md), [CSH-032](tickets/CSH-032-shell-options.md) | `execution/pipeline-status` | missing |
| <a id="exec-008"></a>EXEC-008 | Execute sequential, AND and OR lists with short-circuiting, precedence and final status. | [2.9.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_03) | required | [CSH-021](tickets/CSH-021-lists-and-execution-contexts.md) | `execution/lists-short-circuit` | missing; newline sequence observation only: [SMOKE-SEQUENCE](posix-evidence.md#smoke-sequence) |
| <a id="exec-009"></a>EXEC-009 | Launch asynchronous lists without waiting; track IDs/status, stdin redirection and required interactive messages. | [2.9.3.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_03_02) | required; job-control/interactive conditions | [CSH-021](tickets/CSH-021-lists-and-execution-contexts.md), [CSH-034](tickets/CSH-034-job-control.md) | `execution/asynchronous-lists` | missing |
| <a id="exec-010"></a>EXEC-010 | Execute brace groups in the current environment and parenthesized groups in subshell environments. | [2.9.4.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04_01) | required | [CSH-021](tickets/CSH-021-lists-and-execution-contexts.md) | `execution/group-environments` | missing |
| <a id="exec-011"></a>EXEC-011 | Execute for loops, including positional-parameter defaults, expansion timing and zero-iteration status. | [2.9.4.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04_03) | required | [CSH-028](tickets/CSH-028-control-flow-and-functions.md) | `execution/for` | missing |
| <a id="exec-012"></a>EXEC-012 | Execute case matching, pattern expansion, no-match status, `;;` termination and `;&` fall-through. | [2.9.4.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04_05) | required; expansion order among patterns for one clause unspecified; stop at first match | [CSH-028](tickets/CSH-028-control-flow-and-functions.md), [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md) | `execution/case-fallthrough` | missing |
| <a id="exec-013"></a>EXEC-013 | Execute if/elif/else, while and until with condition-controlled evaluation and specified statuses. | [2.9.4.4–2.9.4.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04_07) | required | [CSH-028](tickets/CSH-028-control-flow-and-functions.md) | `execution/conditionals-loops` | missing |
| <a id="exec-014"></a>EXEC-014 | Define/invoke functions with call-time redirections, argument restoration, status, scope and separate function/variable namespaces. | [2.9.5](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_05) | required; optional extra characters in function names, D-006 | [CSH-028](tickets/CSH-028-control-flow-and-functions.md) | `execution/functions` | missing |
| <a id="exec-015"></a>EXEC-015 | Apply interactive/non-interactive consequences for syntax, expansion, assignment, utility, redirection and read errors. | [2.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01) | required; unrecoverable read errors must not execute buffered commands except EXIT trap; dot exceptions included | [CSH-018](tickets/CSH-018-status-and-cli-integration.md), [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-031](tickets/CSH-031-evaluation-builtins.md), [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) | `execution/error-consequences` | missing |
| <a id="exec-016"></a>EXEC-016 | Retain zero/nonzero statuses; report 126/127 execution failures and documented signal-derived values above 128. | [2.8.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_02) | required; signal mapping implementation-defined, D-007 | [CSH-018](tickets/CSH-018-status-and-cli-integration.md), [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) | `execution/status-mapping` | missing; startup/explicit exit zero observed in [SMOKE-EXIT](posix-evidence.md#smoke-exit) |
| <a id="env-006"></a>ENV-006 | Preserve or isolate cwd, descriptors, umask, limits, traps, variables, functions, aliases, options and known child IDs by context. | [2.13](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_13) | required; pipeline current-environment extension permitted, D-007 | [CSH-021](tickets/CSH-021-lists-and-execution-contexts.md), [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md), [CSH-028](tickets/CSH-028-control-flow-and-functions.md), [CSH-030](tickets/CSH-030-alias-substitution.md) | `execution/context-isolation` | missing |

## Jobs and signals

| ID | Requirement | Source | Scope / variations | Owning tickets | Planned fixture ID | Current evidence |
| --- | --- | --- | --- | --- | --- | --- |
| <a id="job-001"></a>JOB-001 | Initialize process/foreground groups according to controlling-terminal and foreground/background startup state. | [2.11](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_11) | conditional on terminal/job-control conditions; monitor selection is UP-related, see utility profile | [CSH-034](tickets/CSH-034-job-control.md), [CSH-033](tickets/CSH-033-pty-test-harness.md) | `pty/job-control-startup` | missing |
| <a id="job-002"></a>JOB-002 | Group foreground/background pipelines and lists; hand off and regain the terminal, retaining stopped jobs and terminal settings. | [2.11](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_11) | required under specified conditions; suspended compound membership partly unspecified | [CSH-034](tickets/CSH-034-job-control.md), [CSH-020](tickets/CSH-020-pipeline-lifecycle.md), [CSH-033](tickets/CSH-033-pty-test-harness.md) | `pty/stop-resume-terminal` | missing |
| <a id="job-003"></a>JOB-003 | Track job numbers/known PIDs and issue stopped/completed notifications at monitor/notify-dependent times. | [2.11](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_11) | required under specified conditions; utilities/options also in [utility map](posix-utilities.md) | [CSH-034](tickets/CSH-034-job-control.md), [CSH-033](tickets/CSH-033-pty-test-harness.md) | `pty/job-notifications` | missing |
| <a id="sig-001"></a>SIG-001 | Apply interactive shell signal dispositions and asynchronous-list SIGINT/SIGQUIT inheritance. | [2.12; sh ASYNCHRONOUS EVENTS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_09) | required; unmonitored terminal-stop disposition choices, D-007 | [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md), [CSH-034](tickets/CSH-034-job-control.md) | `signals/dispositions-inheritance` | missing |
| <a id="sig-002"></a>SIG-002 | Defer trapped signals during foreground commands; interrupt wait with status above 128 before dispatching the trap. | [2.12](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_12) | required; order of multiple pending traps unspecified | [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) | `signals/trap-wait-timing` | missing |
| <a id="sig-003"></a>SIG-003 | Reset/retain signal and trap state as required across subshells, functions, substitutions, exec and exit. | [2.13; trap](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_13) | required; utility-specific details in [utility map](posix-utilities.md) | [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md), [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md), [CSH-031](tickets/CSH-031-evaluation-builtins.md) | `signals/trap-environments` | missing |

## Open implementation choices

These are decision records to resolve within existing owners, not new tickets or
permission gates. Profile choices also appear in the [utility map](posix-utilities.md).
Record the chosen behavior, rationale, implementation and fixtures here before
the owning ticket closes; CSH-037 audits any still-open item. Permitted choices
must not silently become normative requirements for other shells.

| ID | Open choice and affected requirements | Owner and resolution path | Evidence |
| --- | --- | --- | --- |
| D-001 | SH-003: optional PATH search for a slashless script missing from cwd; SH-004: handling `-i` when real/effective identity differs. | [CSH-016](tickets/CSH-016-input-and-invocation.md) documents policy and targeted invocation fixtures. | API choice: [direct path opening without PATH search](input-and-invocation.md#invocation-contract). `-i` unconditionally selects interactivity in [the parser](../src/invocation.c); unequal-identity and PATH-only negative fixtures remain missing, as does runtime evidence |
| D-002 | SH-009, RED-001, GRAM-002: offset and descriptor maxima (at least descriptors 0–9); whether optional `{varname}` IO_LOCATION is supported, with its implementation-defined behavior if selected. | [CSH-019](tickets/CSH-019-simple-command-redirections.md) records limits/choice with [CSH-005](tickets/CSH-005-parser-and-ast.md); CSH-037 checks platforms. | missing; open |
| D-003 | LEX-005, EXP-007: dollar-single-quote byte encodings where locale encoding is implementation-defined; additional IFS whitespace classification. | [CSH-024](tickets/CSH-024-value-expansions.md) and [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md) document choices and locale cases. | [decoder choices](value-expansions.md#dollar-single-quote-decoding) documented; IFS/locale breadth open |
| D-004 | LEX-006, EXP-005: alias parse timing and command-substitution parsing alternatives permitted by the source. | [CSH-030](tickets/CSH-030-alias-substitution.md) and [CSH-026](tickets/CSH-026-substitution-and-heredoc-integration.md) record supported timing; oracle allows source-permitted alternatives. | missing; open |
| D-005 | EXP-006: optional arithmetic extensions, numeric representation and platform limits. | [CSH-024](tickets/CSH-024-value-expansions.md) records required integer support and separates extension tests; CSH-037 checks portability. | [signed-long model and limits](value-expansions.md#arithmetic-and-parser-cooperation) documented and API-tested; runtime/portability breadth open |
| D-006 | EXP-011, EXEC-002/014: assignment visibility/export/persistence where unspecified; expanded declaration names; optional extra characters in function names. | [CSH-023](tickets/CSH-023-assignment-environments.md), [CSH-028](tickets/CSH-028-control-flow-and-functions.md) and [CSH-031](tickets/CSH-031-evaluation-builtins.md) choose consistent semantics and classify fixtures. | missing; open |
| D-007 | EXEC-016, ENV-006, SIG-001: signal-to-status mapping, permitted current-shell pipeline stages, unmonitored terminal-stop signal actions. | [CSH-018](tickets/CSH-018-status-and-cli-integration.md), [CSH-020](tickets/CSH-020-pipeline-lifecycle.md), [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) document choices and native/PTY checks. | missing; open |
| D-008 | EXP-001 and LEX-001: optional expansion extensions and non-POSIX operators; input starting with `#!` is unspecified by §2.1. | [CSH-004](tickets/CSH-004-lexer-and-words.md) and [CSH-025](tickets/CSH-025-field-and-pathname-expansion.md) label extensions explicitly; [CSH-016](tickets/CSH-016-input-and-invocation.md) documents shebang policy. | Input acquisition [preserves bytes without interpreting syntax](input-and-invocation.md#reading-and-positions), including no special `#!` handling in [the reader](../src/input.c). Explicit shebang fixture and lexer/runtime interpretation remain open; expansion/operator choices remain missing |

Legacy `|&` and `>>&` behavior is not evidence for Issue 8. Issue 8 additions such
as dollar-single-quotes, `;&`, and `pipefail` are standard requirements, even if
an older reference shell rejects them. Allocation failure, process ownership and
sanitizer checks supplement this matrix through their module tickets; they do
not establish language conformance.

## Inventory review and remaining depth

This baseline covers the Chapter 2 families from shell processing/quoting through
special builtins, the `sh` page, and the shell-associated Chapter 1 utility
requirements. It is intentionally a family inventory: detailed operand/error
combinations, locale matrices, and individual UP editing commands still need
fixture-level decomposition by the listed owner. The option-group inventory
retains unselected or unresolved branches explicitly. The shell does not claim
to implement the full collection of host utilities in the POSIX system profile.

For each implementation PR, inspect the linked source sections for missed
subcases, add rows if required, update [reverse ownership](posix-owners.md), and
record actual evidence and unresolved cases in the ticket. CSH-029 checks utility
allocation; CSH-035 checks interactive/profile decisions; CSH-037 re-audits the
full inventory against the supported platforms before any conformance claim.
The [CSH-036 validation record](tickets/CSH-036-conformance-matrix.md) records
source/link checking and the independent family review for this baseline.
