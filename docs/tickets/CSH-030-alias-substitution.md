# CSH-030: Implement alias storage and token substitution

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-004, CSH-005
- Branch: `feature/CSH-030-alias-substitution`
- Issue: [#31](https://github.com/melliott18/cshell/issues/31)

## Goal

Apply aliases at the specified token-reading stage while preserving parser
context, quoting, and bounded recursive substitution behavior.

## Scope

- Add alias storage, lookup, replacement, removal, and `alias`/`unalias` handlers
  behind interfaces suitable for later command-dispatch integration.
- Integrate substitution with token input, respecting command position, quoting,
  trailing blanks, and input/read timing.
- Track active alias expansion to prevent prohibited recursive re-expansion;
  release injected token/input resources on errors and end of input.

## Acceptance criteria

- [x] Lexer/parser fixtures distinguish eligible command words from quoted words,
  ordinary arguments, and words made eligible by trailing-blank alias values.
- [x] Direct and indirect self-reference terminate with the specified expansion
  behavior; valid chained replacements produce the expected token stream.
- [x] Definitions and removals take effect at the required read/parse boundary,
  with fixtures covering multiple commands and multiline input.
- [x] Alias handlers validate operands, report lookup failures, and preserve
  replacement text with tested output/status and memory ownership.

## Validation

Validation record (2026-09-23, native macOS arm64 / Apple Clang 15 and Docker
Linux; all checks below passed):

- `make -j4 test test-pty`: replacement input, lexer (61 checks), parser
  (114 checks plus AST ownership), alias, state, and expansion suites, prototype
  smoke cases, and controlling-terminal startup/exit.
- `make test-harness`: all 61 harness self-tests, including cleanup and PTY
  failure cases.
- `make docker-test DOCKER_IMAGE=cshell-test:csh030`: the same default module
  and prototype suites built and run using the Linux toolchain.
- Focused ASan/UBSan: `make test-lexer test-parser test-alias CC=clang` with
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`
  and `LDFLAGS='-fsanitize=address,undefined'`, after `make clean`. The same
  focused targets and flags also passed with the Linux image's compiler via
  `docker run --rm --init -e ASAN_OPTIONS=halt_on_error=1 -e UBSAN_OPTIONS=halt_on_error=1 cshell-test:csh030`.
  Both runs use `ASAN_OPTIONS=halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1`.
- `git diff --check`: whitespace validation.

The alias fixtures verify storage ownership and atomic failed mutations;
handler output, quoting, options, operand failures and status; command versus
argument eligibility; quoted/escaped words; trailing blanks; direct/indirect
recursion and 300 distinct aliases; IO_NUMBER adjacency across sources;
replacement grammar; here-documents; nested substitutions; boundary-spanning
words; read timing and table mutation; token ownership and physical diagnostic
locations. Lexer and parser fault fixtures fail each allocation in turn and
check sticky errors and complete cleanup of injected input and returned trees.

## Implementation notes/evidence

- [`alias.h`](../../include/cshell/alias.h) owns a standalone table and
  dispatch-ready `alias`/`unalias` handlers. It has no legacy/runtime dependency.
- The parser borrows an optional table through `csh_parser_set_aliases()`;
  callers may change it between complete-command reads. Existing parsers remain
  alias-free unless a table is attached.
- The lexer inserts copied replacement text at the delimited-token boundary,
  tracks active names, restores original input positions, and retains alias
  and physical-invocation provenance. Enclosing command-substitution spelling
  remains original while child ASTs contain substituted tokens.
- The [alias API document](../aliases.md) records POSIX Issue 8 sources and the
  permitted choices: a synthetic separating space, no substitution of reserved
  spellings, and trailing eligibility for quoted final blanks as well as
  unquoted blanks. Empty aliases remove words; they do not erase resulting
  syntax errors such as adjacent separators.
- Definitions and removals take effect on the next complete-command parse;
  semicolon-separated commands and multiline groups already in a returned tree
  remain unchanged. The parser never executes definitions encountered in input.
- CSH-031 still owns dispatcher integration and executed-script checks;
  CSH-010 must demonstrate that behavior before its builtin milestone closes.
  CSH-009's unsupported compound grammar and deferred backquote execution remain
  outside this ticket. The prototype executable is unchanged.
