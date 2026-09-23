# CSH-035: Complete traps and shell signal semantics

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-011
- Depends on: CSH-009, CSH-031, CSH-032, CSH-034
- Branch: Assigned when work starts
- Issue: [#36](https://github.com/melliott18/cshell/issues/36)

## Goal

Execute traps and handle signals at the specified points without unsafe signal
handlers or inconsistent child, terminal, and shell-state ownership.

## Scope

- Implement `trap`, pending-trap dispatch, signal inheritance/reset rules,
  interrupted input/waits, and required exit/hangup behavior.
- Preserve trap status/environment semantics across functions, evaluation,
  subshells, command substitutions, builtins, and external commands.
- Audit signal handlers for permitted operations; document selected POSIX option
  groups and implementation choices before closing the signals milestone.

## Acceptance criteria

- [ ] Trap installation, listing, reset, ignored actions, invalid operands, and
  exit actions have specified output, environment, and exit-status behavior.
- [ ] Pending traps execute at required safe points during command execution and
  waits, with tested ordering and status preservation where specified.
- [ ] Children, subshells, and substitutions inherit/reset signals and traps as
  required; interactive interrupts leave the shell and terminal usable.
- [ ] Signal handlers use only permitted operations, and rapid/coalesced signals
  cannot corrupt shell state or cause duplicate child reaping.
- [ ] Exit, hangup, and interrupted input/wait policies are documented and tested
  for the selected profile, including cleanup after error paths.

## Validation

Run script cases and bounded CSH-033 PTY cases covering traps during waits,
subshells, functions, and shell exit. Exercise native and Docker builds, record
capability limits, and inspect cleanup after forced harness timeouts.

## Implementation notes/evidence

Record implementation choices and results here. Review all original
[CSH-011](CSH-011-signals-and-job-control.md) criteria with combined jobs/traps
regressions; completion of an individual family is not enough to close it.
