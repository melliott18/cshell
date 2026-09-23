# CSH-040: Make repeated macOS harness cleanup reliable

- Status: ready
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-017
- Branch: Assigned when work starts
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

- [ ] A focused regression deterministically exercises repeated cleanup after
  candidate exit, including the macOS zombie-group transition where feasible.
- [ ] Cleanup remains safe and idempotent for exited groups while live
  descendants are still terminated and real permission failures are reported.
- [ ] Native macOS/Linux and Docker harness self-tests pass with bounded checks.

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
