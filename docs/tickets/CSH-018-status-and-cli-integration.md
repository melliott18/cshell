# CSH-018: Integrate invocation modes with command and shell exit statuses

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-003
- Depends on: CSH-016, CSH-017
- Branch: Assigned when work starts
- Issue: [#19](https://github.com/melliott18/cshell/issues/19)

## Goal

Join the input-mode and harness work so every supported invocation has verified
output, failure behavior, and final shell status.

## Scope

- Retain command completion and signal-derived statuses in shell state.
- Define and implement tested `exit` behavior with and without an operand.
- Run shared behavioral cases through `-c`, script files, and redirected stdin.
- Remove prototype prompt allowances for non-interactive harness fixtures.
- Connect the expanded suite to existing native and Docker CI entry points.

## Acceptance criteria

- [ ] Equivalent commands in all three modes have matching stdout, stderr, and
  statuses; successful completion, nonzero completion, and unknown commands are
  covered with specified expectations.
- [ ] Child termination by signal is recorded using the selected POSIX status
  mapping and does not incorrectly terminate a continuing parent shell.
- [ ] `exit` without an operand preserves the applicable last status; numeric,
  invalid, and excess operands have documented, tested outcomes by context.
- [ ] Empty input, EOF after a failed command, and final lines without a newline
  terminate with the defined shell status and no non-interactive prompt/banner.
- [ ] Native and Docker CI run the cross-mode fixtures, including usage and
  file-open errors, without weakening the harness's timeout or cleanup checks.

## Validation

Run `make test` and `make docker-test` with shared command fixtures across every
mode. Use helper executables for exact exit and signal statuses, avoiding syntax
that the prototype does not implement. Test malformed `exit` operands separately
in interactive and non-interactive contexts and record specification decisions.

## Implementation notes/evidence

This is the integration gate for CSH-003, not another independent test runner.
Use the input API from CSH-016 and harness from CSH-017. Preserve a documented
status interface for CSH-022 and later execution work; signal fixtures must assert
the defined mapping instead of assuming every shell returns the same integer.
