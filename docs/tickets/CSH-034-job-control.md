# CSH-034: Implement process groups and terminal job control

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-011
- Depends on: CSH-006, CSH-033
- Branch: Assigned when work starts
- Issue: [#35](https://github.com/melliott18/cshell/issues/35)

## Goal

Track interactive jobs and transfer the controlling terminal safely between the
shell and foreground process groups while preserving non-interactive execution.

## Scope

- Coordinate with the executor owner on process creation, group assignment,
  status collection, and single ownership of every child and descriptor.
- Implement foreground terminal handoff/restoration, background jobs, stopped and
  continued state, and required job-related builtins/options for the profile.
- Own `jobs`, `fg`, `bg`, `wait`, and applicable `kill` integration; provide safe
  signal notification plumbing, with full trap semantics deferred to CSH-035.

## Acceptance criteria

- [ ] Foreground pipelines share the required process group and receive terminal
  signals; the shell regains control after completion or stop and stays usable.
- [ ] Background, stopped, and resumed jobs have stable records, tested status
  reporting, and eventual reaping without double waits or lost children.
- [ ] Job builtins and monitor-mode transitions validate operands and produce
  specified status/results, including missing jobs and interrupted waits.
- [ ] Terminal capability checks disable unavailable job control cleanly while
  leaving scripts, redirected input, and non-interactive pipelines functional.
- [ ] Timeout/error paths restore terminal state and release owned resources.

## Validation

Use CSH-033 for Ctrl-C, Ctrl-Z, background completion, foreground/background
continuation, and terminal restoration. Run native and Docker script regressions
and stress rapid child exits; record platform/profile applicability and skips.

## Implementation notes/evidence

Record executor coordination and evidence here. CSH-035 completes signal/trap
interactions, exit/hangup policy, and the integrated CSH-011 acceptance review.
