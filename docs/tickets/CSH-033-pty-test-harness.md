# CSH-033: Add a bounded pseudo-terminal test harness

- Status: backlog
- Type: test
- Kind: implementation
- Parent: CSH-011
- Depends on: CSH-017
- Branch: Assigned when work starts
- Issue: [#34](https://github.com/melliott18/cshell/issues/34)

## Goal

Provide reproducible terminal-driven tests before full signals and job control
exist, so their implementation has a trustworthy observation and cleanup path.

## Scope

- Extend the behavioral harness with pseudo-terminal creation, controlled input,
  captured output, bounded waits, and deterministic process cleanup.
- Supply helper programs for terminal ownership, stop/continue, and signal
  observations; keep fixture capabilities separate from cshell support claims.
- Add current startup/explicit-exit checks and expose future Ctrl-C/Ctrl-Z and
  foreground/background test APIs for CSH-034/035.

## Acceptance criteria

- [ ] A test can start a fixture or cshell on a controlling pseudo-terminal,
  send input/control characters, and assert bounded output and exit status.
- [ ] Deliberately hanging or failing fixtures time out with useful diagnostics
  and leave no owned child processes or terminal descriptors behind.
- [ ] Supported native Linux/macOS and Docker environments run applicable cases;
  unavailable terminal capabilities produce explicit, scoped skip reasons.
- [ ] Existing cshell explicit-exit behavior is exercised without claiming signal
  or job-control features that have not been implemented.

## Validation

Run harness self-checks with known helper programs, then the current cshell PTY
smoke case. Exercise forced timeout and teardown failures; record platform,
container terminal setup, elapsed bounds, and any capability-based skips.

## Implementation notes/evidence

Record usage and evidence here and update the testing guide during implementation.
CSH-034/035 own shell behavior assertions; this harness can complete independently
without closing [CSH-011](CSH-011-signals-and-job-control.md).
