# CSH-005: Parse commands into an owned syntax tree

- Status: done
- Type: feat
- Kind: implementation
- Parent: None
- Depends on: CSH-004
- Branch: feature/parser-and-ast
- Issue: [#6](https://github.com/melliott18/cshell/issues/6)

## Goal

Represent command structure independently of argument expansion and execution.

## Scope

- Introduce parser and AST modules with explicit construction and destruction.
- Parse simple commands, assignment words, pipelines, `!`, sequential and
  asynchronous lists, `&&`/`||`, subshell groups, and brace groups.
- Preserve redirections in source order, including descriptor operands and
  here-document delimiter quoting.
- Collect multiple here-document bodies in source order using the lexer/input
  interface; defer body expansion to CSH-008.
- Reserve extensible nodes for the compound commands delivered by CSH-009.

## Acceptance criteria

- [x] Precedence and associativity match the POSIX grammar.
- [x] Assignments and redirections can be represented without a command name.
- [x] Multiple redirections retain their source order and exact operator kind.
- [x] Incomplete input is distinguishable from invalid syntax and clean EOF.
- [x] Syntax errors prevent execution of the invalid construct and free its tree.
- [x] AST ownership and parser error behavior are documented; parser fixtures
  build without legacy sources, headers, or command-array adapters.

## Validation

Use structural fixtures for precedence, grouping, assignments, and ordered
redirections. Exercise invalid and incomplete constructs with source diagnostics.
Test quoted and unquoted here-document delimiters, `<<-`, multiple pending
documents, and premature EOF. Integrate behavioral execution tests in CSH-006.

## Implementation notes/evidence

Parsing must not execute substitutions or expand filenames. The parser must
leave room for context-sensitive reserved words and alias processing.


### Implemented contract

`include/cshell/parser.h` and `src/parser.c` provide a synchronous pull parser
that borrows an unread input source and owns its lexer. Each successful call
returns one complete command list at a newline or final EOF, after collecting
pending here-documents. Subsequent command input remains unread. Invalid syntax,
final incomplete input, and clean EOF have distinct sticky results; no failed
construct publishes a partial tree or performs execution.

`include/cshell/ast.h` and `src/ast.c` provide owned simple-command words,
assignment classification, pipelines and negation, left-associative AND/OR
trees, sequential/background lists, groups, and source-ordered redirections.
Words preserve original tokens, quoting fragments, and parsed `$(...)` bodies.
Descriptor numbers retain physical spelling and adjacency without conversion.
Construction/append helpers move ownership only on success; destruction uses an
allocation-free iterative walk, including arbitrarily long AND/OR chains.
Compound/function enum kinds are reserved for CSH-009/CSH-027.

Here-documents retain original delimiter words, separately quote-removed
delimiters and quoting flags, unexpanded bodies, and physical body spans.
Collection follows source order through the lexer's raw shared cursor, including
nested substitutions and continuation newlines. Unquoted delimiter matching
joins backslash-newlines; `<<-` strips leading tabs after logical joining.
Stored bodies preserve physical backslash-newline bytes for later CSH-026
interpretation. Dollar-single-quoted delimiter regions use `quote.h`/`quote.c`,
the shared decoder also used by CSH-024. Quote removal also handles literal
expansion-looking delimiter spelling without performing substitutions.

The [API contract](../parser-and-ast.md) documents ownership, supported grammar,
read boundaries, diagnostic behavior, delimiter processing, and extension points.
`make test-parser` builds without legacy sources, headers, Flex, or command-array
adapters. It joins `make test`, Docker, and native CI; CI also runs parser/AST
fixtures under ASan/UBSan.

### Deliberate limits and remaining integration

The public executable still uses the prototype. Execution fixtures, runtime
integration, and cutover remain with CSH-006, CSH-018, and CSH-039. Alias insertion
remains CSH-030 work; backquote execution and here-document expansion remain
CSH-026 work. The lexer's existing arithmetic-first `$((` ambiguity still needs
CSH-024/CSH-026 coordination with a shared-cursor checkpoint/replay interface;
explicitly separated `$( (command); )` is supported.

Word, sequence, pipeline, redirection, and body storage has no fixed parser cap.
Recursive groups and substitutions currently have a 128-context guard with a
structured error instead of C-stack exhaustion. The broader unrestricted-size
requirement in GRAM-005 remains open for deeper recursive syntax, alongside
later compound syntax and portability validation. Optional `{name}` descriptor
allocation is not enabled; execution owns descriptor conversion and validity.
A command substitution that closes before its pending here-document newline is
rejected as a syntax error, selecting a defined diagnostic for a POSIX-unspecified
case. Final EOF without a delimiter reports incomplete input.


### Validation evidence (2026-09-23)

Native environment: Darwin 23.6.0 arm64, Apple Clang 15.0.0, GNU Make 3.81,
Python 3.12.2. Docker environment: Linux aarch64, Debian Bookworm, GCC 12.2.0,
GNU Make 4.3, Python 3.11.2, Docker Engine 24.0.6; tests run as UID 10001.

- `make -j8`, then `make test test-pty test-harness`: the initial full native
  run passed the parser's initial 88 checks, direct AST checks, 63 input checks,
  61 lexer checks, both state suites, four prototype pipe fixtures, one prototype
  PTY fixture, and all 50 harness self-tests. Handwritten code compiled without
  warnings; the unchanged generated scanner retains its native signedness warning.
- The final native run passed all **114 parser checks**, the direct AST checks,
  input/lexer/state suites, and prototype pipe/PTY fixtures. One of 50 harness
  self-tests failed: `test_timeout_kills_same_group_descendants` did not create
  its process marker before its 0.3-second timeout. The focused test reproduced
  the same failure on unchanged `main` at `852c433`; its sources are unchanged
  by this ticket. This baseline startup-timing failure is preserved here rather
  than counted as a passing final harness run.
- A fresh source-only snapshot containing the parser, AST, lexer, input, quote
  sources, replacement headers, and fixtures passed `make test-parser LEX=false`
  with `CC=clang`,
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`,
  and `LDFLAGS='-fsanitize=address,undefined'`: all 114 parser checks and direct
  AST checks passed without sanitizer diagnostics. No legacy header, scanner,
  executor, or Flex was present in this snapshot.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-005` passed the final 114 parser
  checks, direct AST checks, 63 input checks, 61 lexer checks, both state suites,
  and all four prototype fixtures. The image also passed `make test-pty
  test-harness`: one PTY fixture and all 50 harness self-tests.
- A clean GCC Linux build passed all final 114 parser checks and direct AST
  checks with the same strict ASan/UBSan flags and `-DNDEBUG`,
  `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`, and
  `UBSAN_OPTIONS=halt_on_error=1`. No sanitizer or leak diagnostics appeared.
- Fault fixtures fail every allocation in the input/lexer/parser/AST/quote
  stack in turn, covering large words and bodies, nested substitutions,
  dollar-single decoding, queued documents, and invalid/incomplete cleanup.
  They require zero retained allocations and repeatable sticky errors.
- Permanent stress fixtures cover a 200 KB word, 10,000 words, 1,000 pipeline
  commands, 2,000 list entries, and 10,000 AND/OR commands. Direct AST fixtures
  destroy 20,000 binary nodes and 10,000 mixed group/substitution contexts
  iteratively. Assertions remain enabled with `-DNDEBUG`.
- Independent deterministic syntax comparison (seed 52024) matched
  `/bin/dash -n` on all 600 generated supported programs and 400 mutations.
  `/bin/sh` (Bash 3.2) differed on four mutations containing its `&>` extension;
  those extension observations are not POSIX oracles. Source is parsed only,
  never executed.
- Changed Markdown links resolve; `git diff --check` passes. Existing Mermaid
  diagrams are unchanged. These are API/structural checks, not complete shell
  conformance or replacement execution evidence.

Integrated into `main` through [pull request #52](https://github.com/melliott18/cshell/pull/52)
on 2026-09-23. Implementation commit: `4aee69d`; integration commit after
CSH-024 and CSH-040: `062557f`; merge commit: `7d6ae67`. GitHub closed issue #6
when the pull request merged.

At `062557f`, the combined native suite passed 63 input/invocation checks, 61
lexer checks, 114 parser checks plus direct AST ownership checks, state and
value-expansion suites, four prototype pipe cases, one prototype PTY case, and
all 61 harness self-tests. Both the
[pull-request CI](https://github.com/melliott18/cshell/actions/runs/35933831829)
and [branch CI](https://github.com/melliott18/cshell/actions/runs/35933827839)
passed Ubuntu/GCC, macOS/Clang, and Docker Linux after the integration.
