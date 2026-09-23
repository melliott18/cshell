# CSH-033: Add a bounded pseudo-terminal test harness

- Status: done
- Type: test
- Kind: implementation
- Parent: CSH-011
- Depends on: CSH-017
- Branch: `test/CSH-033-pty-test-harness`
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

- [x] A test can start a fixture or cshell on a controlling pseudo-terminal,
  send input/control characters, and assert bounded output and exit status.
- [x] Deliberately hanging or failing fixtures time out with useful diagnostics
  and leave no owned child processes or terminal descriptors behind.
- [x] Supported native Linux/macOS and Docker environments run applicable cases;
  unavailable terminal capabilities produce explicit, scoped skip reasons.
- [x] Existing cshell explicit-exit behavior is exercised without claiming signal
  or job-control features that have not been implemented.

## Validation

Run harness self-checks with known helper programs, then the current cshell PTY
smoke case. Exercise forced timeout and teardown failures; record platform,
container terminal setup, elapsed bounds, and any capability-based skips.

## Implementation notes/evidence

Record usage and evidence here and update the testing guide during implementation.
CSH-034/035 own shell behavior assertions; this harness can complete independently
without closing [CSH-011](CSH-011-signals-and-job-control.md).


### Implementation

- Added `transport: "pty"` to the existing versioned fixture format, with ordered
  literal output waits, UTF-8 input, Ctrl-C/Ctrl-Z/Ctrl-D/Ctrl-\ controls,
  foreground-group assertions, and foreground-group signal delivery. PTY cases
  assert an exact combined transcript, status, and optional filesystem effects.
- Candidates get a new session and controlling terminal with canonical input,
  signal processing, fixed 24x80 dimensions, echo off, and output postprocessing
  off. The existing isolated environment and resource limits also apply.
- All interaction shares a wall-clock deadline and bounded transcript. Cleanup
  has a separate one-second budget, kills every live group in the owned session,
  reaps the leader, and closes terminal descriptors on success and failure.
  Linux uses procfs and macOS uses a bounded `ps` snapshot with session queries.
  Deliberate `setsid` escapes remain outside the trusted-fixture contract.
- Terminal helper programs cover ownership, terminal-generated signals, real
  stop/continue and terminal restoration, leaderless foreground groups, resource
  limits, and regrouped descendants. These observations do not establish cshell
  signal or job-control support; CSH-034/035 retain those behavior assertions.
- Added independently selectable `test-pty` and `docker-test-pty` targets, a
  prototype startup/explicit-exit case, native/Docker CI coverage, and fixture
  authoring guidance. Existing pipe-suite selection stays compatible.

### Validation (2026-09-23)

- Native macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2:
  `make clean && make -j2 && make test && make test-pty && make test-harness`
  passed 63 input/invocation checks, four prototype pipe cases, one prototype
  PTY case, and 50 harness self-tests (27 PTY-specific). The self-tests completed
  in 17.79 seconds. No capability or platform cases were skipped in these runs.
  The generated legacy scanner retains its existing signedness warning.
- Debian Bookworm Linux aarch64, GCC 12.2.0, Python 3.11.2, Docker Engine 24.0.6:
  `make docker-test DOCKER_IMAGE=cshell-test:csh-033`,
  `make docker-test-pty DOCKER_IMAGE=cshell-test:csh-033`, and
  `docker run --rm --init cshell-test:csh-033 make test-harness` passed the same
  checks with zero skips; all 50 self-tests completed in 7.19 seconds. Containers
  ran as UID 10001 without `-t`, using their normal `/dev/ptmx` and `/dev/pts`.
- A forced 0.25-second missing-output wait completed in 0.462 seconds including
  cleanup on macOS, with a diagnostic naming step 2 and its missing literal.
  Self-tests assert sub-three-second completion for short hangs, blocked input,
  output floods, and successful leader exit with a surviving background group.
- Failure tests cover stopped foreground and separate background groups,
  ignored HUP/TERM, leaderless foreground groups, premature terminal closure,
  wrong transcripts/statuses, output caps, and one deadline across step waits.
  Recorded processes are verified non-running and descriptor snapshots match
  after success, timeouts, floods, configuration failures, and failed execs.
- Injected process-snapshot failures exercise fallback leader kill/reaping and
  fail the case; injected teardown diagnostics cannot become success. Combined
  controlling-terminal unavailability and teardown failure remains a failure.
  Injected unavailable PTYs produce a scoped skip, leave pipe cases runnable,
  and cause an entirely skipped suite to fail.
- `python3 -m py_compile tests/smoke.py tests/pty_harness.py
  tests/test_pty_harness.py tests/helpers/pty_candidate.py` and
  `git diff --check` passed. Native Ubuntu/GCC, macOS/Clang, and Docker CI now
  invoke the prototype PTY case and both harness test modules.

### Integration

- [PR #47](https://github.com/melliott18/cshell/pull/47) merged into `main` on
  2026-09-23 as `a7c4e8b`.
- [PR CI run 35920735096](https://github.com/melliott18/cshell/actions/runs/35920735096)
  passed native Ubuntu/GCC, native macOS/Clang, and Docker Linux for implementation
  commit `d1eda9a`.
- CSH-033 is complete. CSH-011 remains open for the CSH-034/035 shell behavior work.
