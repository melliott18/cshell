# CSH-018: Integrate invocation modes with command and shell exit statuses

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-003
- Depends on: CSH-016, CSH-017, CSH-019
- Branch: feature/CSH-018-status-cli-integration
- Issue: [#19](https://github.com/melliott18/cshell/issues/19)

## Goal

Join the input-mode and harness work so every supported invocation has verified
output, failure behavior, and final shell status.

## Scope

- Connect input, lexer/parser, and the CSH-019 executor through an internal
  candidate runtime/test driver that links no legacy code. CSH-039 owns the
  default `cshell` cutover and deletion after pipeline integration.
- Retain command completion and signal-derived statuses in CSH-022 shell state.
- Define and implement tested `exit` behavior with and without an operand.
- Run shared behavioral cases through `-c`, script files, and redirected stdin.
- Use strict non-interactive output checks for all candidate-runtime fixtures;
  remove the old prototype allowances entirely at the CSH-039 cutover.
- Connect the expanded suite to existing native and Docker CI entry points.

## Acceptance criteria

- [x] The candidate runs only the replacement modules; unsupported constructs
  produce a diagnostic before that construct executes, with no legacy fallback.
- [x] Equivalent commands in all three modes have matching stdout, stderr, and
  statuses; successful completion, nonzero completion, and unknown commands are
  covered with specified expectations.
- [x] Child termination by signal is recorded using the selected POSIX status
  mapping and does not incorrectly terminate a continuing parent shell.
- [x] `exit` without an operand preserves the applicable last status; numeric,
  invalid, and excess operands have documented, tested outcomes by context.
- [x] Empty input, EOF after a failed command, and final lines without a newline
  terminate with the defined shell status and no non-interactive prompt/banner.
- [x] Native and Docker CI run the cross-mode fixtures, including usage and
  file-open errors, without weakening the harness's timeout or cleanup checks.

## Validation

Run shared fixtures across every mode using the candidate runtime in both native
and Docker test targets, and record the precise build/test commands. Keep any
prototype smoke results separate. Use helper executables for exact exit and
signal statuses, avoiding features outside the declared bootstrap subset. Test malformed `exit` operands separately
in interactive and non-interactive contexts and record specification decisions.

## Implementation notes/evidence

This is the integration gate for CSH-003, not another independent test runner.
Use the input API from CSH-016, harness from CSH-017, and executor from CSH-019.
Use the status interface supplied by CSH-022; signal fixtures must assert
the defined mapping instead of assuming every shell returns the same integer.

### Implementation

`src/candidate.c` builds as `build/cshell-candidate`, links only replacement
modules, copies invocation/environment into state, and processes complete
commands with the CSH-019 literal adapter. It prints module diagnostics once,
honors exit requests after descriptor restoration, and returns the state's last
status at EOF. Unsupported complete constructs are rejected before execution;
there is no legacy AST fallback. The default executable cutover remains CSH-039.

`exit [--] [status]` preserves the previous status if omitted and accepts signed
decimal `long` values reduced to eight bits. Empty, whitespace-containing,
nonnumeric, or overflowing values produce status 2. Excess operands are checked
first and also produce 2. Both errors exit a non-interactive candidate and allow
an interactive candidate to continue. Special-builtin redirection errors follow
the same context distinction with status 1. Signal completion uses
`128 + signal_number` (SIGTERM = 143 on tested platforms).

The parser's optional borrowed read hook allows the runtime to print fixed
primary and continuation prompts before physical reads, including blank/comment
lines, multiline quotes, and here-documents. Parser error recovery, prompt
expansion, startup files, and shell signal/job handling remain deferred.
See [Candidate runtime](../candidate-runtime.md) for the full subset and
POSIX.1-2024 specification decisions.

### Validation evidence (2026-09-23)

- Native macOS arm64 / Apple Clang 15: `make -j4 test test-pty test-harness`
  passed **241 candidate pipe cases**, **9 candidate PTY cases**, all existing
  replacement module suites, **61 harness self-tests**, and separately reported
  prototype smoke fixtures (4 pipe / 1 PTY). The generated legacy scanner still
  has its existing signedness warning; replacement sources built cleanly.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-018` passed the same 241
  candidate pipe cases and existing replacement/prototype pipe suites with
  Debian Linux/GCC. `docker run --rm --init cshell-test:csh-018 make test-pty
  test-harness` passed all 9 candidate PTY cases, 1 prototype PTY case, and all
  61 harness self-tests.
- A separate source snapshot with `src/legacy/`, `src/main.c`, and
  `include/cshell/legacy.h` absent passed `make -j4 test-runtime test-runtime-pty
  test-parser test-alias test-execute LEX=false CC=clang` with
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1
  -fsanitize=address,undefined -fno-omit-frame-pointer'` and
  `LDFLAGS='-fsanitize=address,undefined'`. Both sanitizers used
  `halt_on_error=1`. All 250 candidate cases, 223 parser cases, alias suites,
  and 69 execution cases plus API/fault checks passed without sanitizer errors.
- `tests/runtime_cases.py` expands shared cross-mode expectations into strict
  replacement suites for the existing smoke runner. Coverage includes numeric,
  signal and missing-command statuses; continued parent execution; malformed
  exit operands by context; file/usage errors; parser and adapter errors;
  redirection ordering/restoration; and command input without read-ahead.
  Harness timeout, output limit, and cleanup implementations are unchanged.
- `make test` and `make test-pty` include the candidate pipe and terminal suites
  respectively, so existing native and Docker CI paths run them. Native
  ASan/UBSan CI also explicitly runs both candidate suites. Hosted CI results
  remain to be recorded after the branch is pushed.

The ticket remains in review until integration into `main`.
