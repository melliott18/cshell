# CSH-003: Define invocation, input lifecycle, and behavioral testing

- Status: done
- Type: feat
- Kind: milestone
- Parent: None
- Depends on: CSH-001
- Children: CSH-016, CSH-017, CSH-018
- Branch: Assigned when work starts
- Issue: [#4](https://github.com/melliott18/cshell/issues/4)

## Goal

Run reproducible shell commands through command strings, script files, and
standard input, with correct prompting and observable exit statuses.

## Scope

- Introduce input and shell-state interfaces that support strings, files, and
  terminal input without coupling parsing to standard input.
- Implement `-c`, script-file, and stdin invocation, including the POSIX mapping
  of invocation operands to `$0` and positional arguments for CSH-007.
- Define interactive-mode selection and prompt output according to the chosen
  POSIX requirements; preserve inputs needed for multiline parsing.
- Extend the CSH-001 smoke runner into a portable behavioral harness, preserving
  timeouts and per-case temporary folders while adding fixtures and filesystem
  assertions. Use strict output checks for non-interactive candidate fixtures;
  CSH-039 removes the remaining prototype allowances at the default cutover.
- Run the growing suite through native and Docker targets with explicit candidate
  selection before CSH-039 switches `make test` and `make docker-test` defaults.
- Add build and behavioral checks to CI, including the Docker Linux path and
  native checks on the supported platforms.

## Acceptance criteria

- [x] Each input mode runs commands and exits on exhausted input.
- [x] Non-interactive execution emits no prompt or startup banner.
- [x] File-open and usage errors produce diagnostics and failure statuses.
- [x] Child termination and command-not-found statuses are retained in shell state.
- [x] `exit` with and without an operand has defined, tested behavior.
- [x] Tests assert stdout, stderr, status, and relevant filesystem effects.
- [x] The runner reports hangs as failures and cleans up spawned process groups.
- [x] Tests and CI instructions are linked from the contributor documentation.
- [x] Docker and native targets run the same suite, and CI fails on test errors.

## Validation

Execute the same simple command by `-c`, script file, and redirected stdin. Test
empty inputs, a final line without newline, missing files, unknown commands,
nonzero command statuses, and explicit exit statuses. Confirm a deliberately
hanging fixture is stopped by the test runner.

## Implementation notes/evidence

Invocation arguments must be retained even before parameter expansion exists.
Interactive terminal behavior receives full pseudo-terminal coverage in CSH-011.

## Completion gate

- [x] [CSH-016: Input and invocation](CSH-016-input-and-invocation.md) is done.
- [x] [CSH-017: Test harness and CI](CSH-017-test-harness-and-ci.md) is done.
- [x] [CSH-018: Status and CLI integration](CSH-018-status-and-cli-integration.md)
  is done.
- [x] The original acceptance criteria above pass across all three invocation
  modes through the native and Docker entry points, with CI evidence recorded.

CSH-016 and CSH-017 start independently after CSH-001. CSH-016 defines input
contracts without using the legacy scanner. CSH-018 joins the new front end,
CSH-019 executor, and harness in a testable candidate runtime. CSH-039 switches
the default executable after pipeline validation; this milestone can complete
on the candidate, with the tested target recorded explicitly. Legacy repairs
are not prerequisites for either path.

All three child tickets are complete. CSH-018's final candidate suite exercised
267 pipe cases across `-c`, script-file, and redirected-stdin modes plus 9 PTY
cases. Full native, harness, strict ASan/UBSan, Ubuntu/GCC, macOS/Clang, and
Docker Linux checks passed before the final child merged through pull request
#58 on 2026-09-23.
