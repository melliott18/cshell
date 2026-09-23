# CSH-011: Implement signals, traps, and interactive job control

- Status: backlog
- Type: feat
- Kind: milestone
- Parent: None
- Depends on: CSH-006, CSH-009, CSH-010
- Children: CSH-033, CSH-034, CSH-035
- Branch: Assigned when work starts
- Issue: [#12](https://github.com/melliott18/cshell/issues/12)

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

## Completion gate

- [ ] [CSH-033: Pseudo-terminal test harness](CSH-033-pty-test-harness.md) is done.
- [ ] [CSH-034: Job control](CSH-034-job-control.md) is done.
- [ ] [CSH-035: Traps and signal semantics](CSH-035-traps-and-signal-semantics.md) is done.
- [ ] The original acceptance criteria above pass together, with recorded
  cross-feature evidence and all completion prerequisites satisfied.

Child dependencies control when each work item can start. The parent
dependencies are completion prerequisites; they are not inherited start gates.
Completing one child does not establish the milestone or POSIX compliance.

## Implementation notes/evidence

Record applicable POSIX option groups and platform assumptions in the
requirements matrix before claiming the job-control milestone is complete.
