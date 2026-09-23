# CSH-040: Make repeated macOS harness cleanup reliable

- Status: review
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-017
- Branch: `fix/CSH-040-macos-harness-cleanup`
- Issue: [#48](https://github.com/melliott18/cshell/issues/48)

## Goal

Prevent successful descendant cleanup from intermittently failing the macOS
test harness with `Operation not permitted` during repeated process-group kills.

## Scope

- Investigate `capture()` and `kill_group()` in `tests/smoke.py`, which can send
  SIGKILL when a candidate exits and again during final cleanup.
- Preserve detection of real permission failures and guarantees that live
  descendants cannot escape the supported process-group cleanup contract.
- Coordinate shared cleanup changes with CSH-033's pseudo-terminal harness.

## Acceptance criteria

- [x] A focused regression deterministically exercises repeated cleanup after
  candidate exit, including the macOS zombie-group transition where feasible.
- [x] Cleanup remains safe and idempotent for exited groups while live
  descendants are still terminated and real permission failures are reported.
- [x] Native macOS/Linux and Docker harness self-tests pass with bounded checks.

## Validation

Run `make test-harness` natively and in Docker, including the existing
`test_cleanup_kills_descendant_after_successful_parent_exit` case. Add a
controlled regression rather than relying only on repeated CI retries.

## Implementation notes/evidence

Discovered during CSH-022 validation at `c35b80f`. The
[first macOS PR job](https://github.com/melliott18/cshell/actions/runs/35920676755/job/107383522864)
failed that self-test with `[Errno 1] Operation not permitted`; the identical
branch run and the failed job's retry passed. New state fixtures passed, and
`tests/smoke.py`, `tests/test_harness.py`, and the candidate helper were unchanged.

A plausible cause is the second SIGKILL encountering a process group containing
only zombies. Apple's [XNU killpg1 implementation](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/kern/kern_sig.c)
filters zombie members and can return EPERM when no eligible process remains.
The runner catches `ProcessLookupError` but lets this error fail the case. This
is a diagnosis to validate with a focused regression, not grounds to suppress
all EPERM errors. No harness behavior was changed in CSH-022.

### Implementation

- Confirmed the zombie-group diagnosis with an owned child held unreaped after
  SIGKILL: native macOS `killpg` returns EPERM on that group. The regression then
  repeats cleanup three times before reaping the child, without depending on
  orphan reaping or scheduler timing.
- Pipe and PTY cleanup now share `pty_harness.kill_group()`. It accepts ESRCH and
  accepts Darwin EPERM only when a fresh, bounded session snapshot finds no live
  member in the target group. Linux EPERM, EACCES, live group members, and failed
  or expired snapshots still fail. The pipe contract remains limited to its
  original group; PTY cleanup retains its existing session-wide coverage.
- Pipe final cleanup closes all streams even when group cleanup fails, attempts
  a direct leader kill as a fallback, and bounds leader reaping to the remaining
  one-second cleanup budget. Successful fallback cannot erase the group error.
- Added controlled pipe post-exit/final-cleanup and PTY snapshot/kill transition
  regressions, permission and snapshot failure checks, and a real zombie-group
  test on macOS/Linux. Test teardown uses the same verified group-kill rule.

### Validation (2026-09-23)

- Native macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2:
  `make -j2 && make test && make test-pty` passed 63 input/invocation checks,
  61 lexer checks, both state suites, four prototype pipe cases, and one prototype
  PTY case. The existing generated scanner signedness warning is unchanged.
  `make test-harness` passed all 61 self-tests without skips in 19.52 seconds,
  including the original successful-parent-exit descendant cleanup case.
- Debian Bookworm Linux aarch64, Python 3.11.2, Docker Engine 24.0.6:
  `make docker-build DOCKER_IMAGE=cshell-test:csh-040` and
  `docker run --rm --init cshell-test:csh-040 make test-harness` passed all
  61 self-tests without skips in 7.68 seconds, as UID 10001 without a terminal.
- The controlled pipe regression was also run with `tests/smoke.py` from the
  original `852c433` revision and failed at the second group kill with the
  injected EPERM, as expected; the fixed runner passes the same regression.
- Python byte-compilation of the four changed harness modules and
  `git diff --check` passed. Independent implementation review found no
  actionable issues.
- [PR #50](https://github.com/melliott18/cshell/pull/50) implements this ticket.
  [PR CI run 35931206050](https://github.com/melliott18/cshell/actions/runs/35931206050)
  passed native Ubuntu 24.04/GCC, native macOS 15/Clang, and Docker Linux at
  implementation commit `19cfc44`. The jobs include all harness self-tests,
  module and behavioral fixtures, PTY smoke checks, and native state sanitizer
  checks. The corresponding push CI run also passed all three environments.
  The ticket remains in review until integration into `main`.
