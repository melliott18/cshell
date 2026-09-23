# CSH-003: Define invocation, input lifecycle, and behavioral testing

- Status: backlog
- Type: feat
- Depends on: CSH-002
- Branch: Assigned when work starts

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
  assertions. Remove the legacy prompt allowance for non-interactive cases.
- Run the growing suite through both `make test` and `make docker-test`.
- Add build and behavioral checks to CI, including the Docker Linux path and
  native checks on the supported platforms.

## Acceptance criteria

- [ ] Each input mode runs commands and exits on exhausted input.
- [ ] Non-interactive execution emits no prompt or startup banner.
- [ ] File-open and usage errors produce diagnostics and failure statuses.
- [ ] Child termination and command-not-found statuses are retained in shell state.
- [ ] `exit` with and without an operand has defined, tested behavior.
- [ ] Tests assert stdout, stderr, status, and relevant filesystem effects.
- [ ] The runner reports hangs as failures and cleans up spawned process groups.
- [ ] Tests and CI instructions are linked from the contributor documentation.
- [ ] Docker and native targets run the same suite, and CI fails on test errors.

## Validation

Execute the same simple command by `-c`, script file, and redirected stdin. Test
empty inputs, a final line without newline, missing files, unknown commands,
nonzero command statuses, and explicit exit statuses. Confirm a deliberately
hanging fixture is stopped by the test runner.

## Implementation notes/evidence

Invocation arguments must be retained even before parameter expansion exists.
Interactive terminal behavior receives full pseudo-terminal coverage in CSH-011.
