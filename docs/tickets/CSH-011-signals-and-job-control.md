# CSH-011: Implement signals, traps, and interactive job control

- Status: backlog
- Type: feat
- Depends on: CSH-006, CSH-009, CSH-010
- Branch: Assigned when work starts

## Goal

Give interactive and non-interactive shells the required signal behavior and
explicit ownership of jobs and the controlling terminal.

## Scope

- Add signal and job modules with safe signal notification and normal-flow
  handling of state changes.
- Implement `trap`, signal inheritance/reset rules, interrupted waits, and
  pending-trap execution at specified points.
- Implement process groups, foreground terminal handoff, stopped/continued jobs,
  and job-related builtins required by the selected profile.
- Add pseudo-terminal tests for interactive prompting, interrupts, and job state.

## Acceptance criteria

- [ ] Foreground interrupts affect the job and leave an interactive shell usable.
- [ ] The shell regains terminal control after foreground completion or stop.
- [ ] Background and stopped jobs have stable records and are eventually reaped.
- [ ] Trap actions run with the required status and environment semantics.
- [ ] Signal handlers use only operations permitted in signal context.
- [ ] Exit, hangup, and interrupted input/wait behavior follow the selected POSIX
  requirements and any permitted policy is documented.
- [ ] Job control is gated by terminal/platform capability without breaking
  non-interactive operation.

## Validation

Use a pseudo-terminal harness with bounded waits for Ctrl-C, Ctrl-Z, foreground
and background jobs, continuation, and terminal restoration. Run script tests
for traps during waits, child termination, subshells, and shell exit. Verify
cleanup after a harness timeout.

## Implementation notes/evidence

Record applicable POSIX option groups and platform assumptions in the
requirements matrix before claiming the job-control milestone is complete.
