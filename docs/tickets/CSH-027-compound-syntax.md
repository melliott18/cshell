# CSH-027: Parse compound commands and function definitions

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-009
- Depends on: CSH-005
- Branch: feature/CSH-027-compound-syntax
- Issue: [#28](https://github.com/melliott18/cshell/issues/28)

## Goal

Represent structured shell programs in the AST before implementing their runtime
semantics, enabling parser work alongside execution and expansion development.

## Scope

- Extend grammar and AST nodes for `if`, `for`, `while`, `until`, `case`, and
  function definitions, including nesting and attached redirections.
- Recognize reserved words only in their grammatical contexts; preserve structured
  words and source positions for subsequent expansion and diagnostics.
- Add parser fixtures only; CSH-028 owns control flow and function execution.

## Acceptance criteria

- [x] Valid nested compound programs and function definitions produce expected
  AST shapes, preserving ordered commands, words, and redirections.
- [x] Reserved words used as ordinary arguments remain words in valid contexts.
- [x] Malformed compounds produce location-aware diagnostics; incomplete input
  is distinguished from a terminal syntax error where the input API requires it.
- [x] Parser cleanup releases all partial AST resources after syntax or allocation
  failures, including nested function and here-document structures.

## Validation

Run table-driven AST fixtures for each grammar production, nesting, separators,
redirections, and malformed/incomplete forms under sanitizers. Fixtures must not
claim runtime support for a successfully parsed compound command.

## Implementation notes/evidence

Record grammar choices, AST ownership, and validation here. Coordinate node
contracts with CSH-028 before either implementation begins. Runtime acceptance in
[CSH-009](CSH-009-compounds-and-functions.md) remains a later integration gate.


### Implemented grammar and ownership

`src/parser.c` now parses `if`/`elif`/`else`, `for` with explicit or omitted
word lists, `while`, `until`, `case`, and `name() compound-command` functions.
The grammar follows POSIX.1-2024 [Shell Grammar](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_10),
including `;&`, empty case bodies, optional pattern opening parentheses, and an
omitted final case terminator. Reserved words remain ordinary structured words
in argument, loop-name, for-list, subject, and applicable pattern contexts.
Names retain continuations and physical positions; quoted/invalid function and
loop names receive syntax diagnostics. Arithmetic `for`, `function name`, and
`;;&` extensions are not added.

The [API contract](../parser-and-ast.md#compound-and-function-payloads) and
[CSH-028 handoff](CSH-028-control-flow-and-functions.md#csh-027-syntax-handoff)
define ordered condition/body branches, separate loop lists, `has_in`, case
patterns and terminators, and function bodies. Function trailing redirections
belong to the function node for invocation-time application. All compound
words preserve tokens, fragments, substitutions, and source positions. No
command execution, definition installation, or expansion occurs here.

Append helpers transfer ownership only on success. Destruction remains iterative
and allocation-free across all payloads, nested substitutions, and redirections.
Pending here-documents retain source order through grammar newlines, including
function definitions, case arms, and substitutions containing case patterns.
The existing 128-context parser limit now covers compound bodies as well.
The existing arithmetic/command-substitution ambiguity and alias integration
limits remain unchanged. Special-builtin function-name restrictions are left
for definition-time execution policy; this syntax API requires an unquoted name
and applies grammatical reserved-word recognition.

### Validation evidence (2026-09-23)

Native environment: Darwin 23.6.0 arm64, Apple Clang 15.0.0, GNU Make 3.81,
Python 3.12.2. Docker environment: Linux aarch64, Debian Bookworm, GCC 12.2.0,
GNU Make 4.3, Python 3.11.2, Docker Engine 24.0.6, UID 10001.

- `make -j8 test-parser`: **223/223** parser checks and direct AST checks pass.
  Coverage includes every new production, nested compounds/functions, ordered
  words/redirections, contextual reserved words, source diagnostics, final EOF
  versus terminal errors, read boundaries, case patterns inside substitutions,
  queued here-documents, vector growth, and nesting limits.
- Fault sweeps fail each allocation in turn across the input/lexer/parser/AST/
  quote stack, including valid and partial function/compound/here-document trees.
  They require zero live allocations and sticky repeated failure results.
  Direct AST fixtures cover helper validation, overflow without ownership loss,
  vector growth, and iterative destruction of 12,000 compound wrappers in
  addition to the existing deep binary/group/substitution trees.
- A fresh source snapshot passes all 223 parser checks and direct AST checks
  with `CC=clang`,
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`
  and `LDFLAGS='-fsanitize=address,undefined'`, with no sanitizer diagnostics.
- `make -j8 test test-pty test-harness`: all module and prototype pipe/PTY suites
  pass. The harness passes 60/61; the unchanged
  `test_timeout_handles_candidate_that_does_not_read_large_stdin` fails because
  its helper does not create a process marker within 0.3 seconds. A focused run
  reproduces the identical failure on unchanged `main` at `f902d24` and this
  branch. This baseline timing failure is not counted as a passing suite.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-027` passes every module suite
  and all four prototype pipe cases. The image also passes `make test-pty
  test-harness`: one PTY fixture and all 61 harness checks.
- A clean GCC Linux build in the Docker image passes all 223 parser checks and
  direct AST checks with the same strict ASan/UBSan flags and `-DNDEBUG`, plus
  `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` and
  `UBSAN_OPTIONS=halt_on_error=1`. No sanitizer or leak diagnostics appeared.
- Independent deterministic syntax comparison covered 1,241 cases against
  `/bin/dash -n` and macOS Bash 3.2.57 `--posix -n`. All differences were
  classified as reference-shell extensions (nonportable names, noncompound
  function bodies, extra for separators, or redirected compounds before esac),
  rather than accepted POSIX productions missing from the implementation.
  Issue 8 `;&` is checked directly in structural fixtures instead of assuming
  that older reference shells support it.
- Changed Markdown links resolve and `git diff --check` passes. No Mermaid
  diagrams changed. These results establish parser/API behavior only; CSH-028
  and later runtime integration still own executable compound semantics.

Integrated into `main` through [pull request #53](https://github.com/melliott18/cshell/pull/53)
on 2026-09-23. Implementation commit: `ee04c9c`; integration commit after
CSH-025: `3b11fad`; merge commit: `0a90665`. GitHub closed issue #28 when the
pull request merged. The combined native run passed all 61 harness checks; a
single hosted macOS startup-timing failure passed on its focused rerun, and both
hosted workflows passed Ubuntu/GCC, macOS/Clang, and Docker Linux.
