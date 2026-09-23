# CSH-017: Build a bounded behavioral harness and continuous integration

- Status: review
- Type: test
- Kind: implementation
- Parent: CSH-003
- Depends on: CSH-001
- Branch: `test/CSH-017-test-harness-and-ci`
- Issue: [#18](https://github.com/melliott18/cshell/issues/18)

## Goal

Make existing and future shell behavior reproducible through one test harness
that runs natively, in Docker, and in continuous integration.

## Scope

- Extend the current Python smoke runner with fixtures and filesystem assertions.
- Preserve per-case temporary directories, timeouts, and process-group cleanup.
- Bound output/resource use and provide actionable per-case failure diagnostics.
- Add supported-platform native jobs and the Docker Linux test path to CI.
- Use current stdin invocation; allow later modes without requiring CSH-016.
- Provide explicit native/Docker selection of a candidate executable or module
  fixture target; keep prototype smoke results distinct from replacement results.

## Acceptance criteria

- [x] Fixtures assert stdout, stderr, exit status, and relevant filesystem effects
  while isolating each case's working directory and environment.
- [x] A deliberately hanging child/process-group fixture is stopped and cleaned
  up; excessive-output fixtures fail without unbounded runner memory growth.
- [x] `make test` and `make docker-test` run the same selected fixture suite and
  return failure when a fixture fails.
- [x] CI builds and tests the supported native platforms and Docker Linux path;
  an intentionally failing fixture demonstrates failure propagation locally.
- [x] Contributor/testing docs explain fixture authoring, limits, platform skips,
  and current prototype allowances without claiming language compliance.

## Validation

Run the real smoke suite natively and in Docker. Exercise harness self-fixtures
for mismatched status/output, filesystem assertions, hangs, spawned descendants,
and output limits; each deliberately failing case must yield a useful failure.
Validate CI configuration and record available CI run results after pushing.
Keep harness self-fixtures separate from passing shell-behavior expectations.

## Implementation notes/evidence

This work is independently actionable against the CSH-001 stdin interface.
The current prototype prompt allowance remains isolated from strict replacement
fixtures introduced by CSH-018; CSH-039 deletes it entirely at cutover. Allow an
explicit candidate executable target so new modules do not require legacy
compatibility. Use adapters or
fixture metadata for future invocation modes, not mandatory unsupported flags.


### Implementation

- Added versioned JSON suites with exact stream/status checks, setup files,
  file/directory/absence assertions, explicit platform skip reasons, and candidate
  arguments. Prototype prompt stripping is opt-in and rejected in strict suites.
- Replaced file-backed capture with bounded streaming of both output channels
  while feeding stdin without blocking. Every case has a fresh environment and
  directory, a wall-clock timeout, inherited resource limits, and process-group
  cleanup after both failure and normal leader exit.
- Added independent harness self-fixtures and 23 CLI integration tests. Native
  and Docker entry points share executable, build target, suite, case, and limit
  selection. CI runs native Ubuntu/GCC, native macOS/Clang, and Docker Linux.

### Local validation (2026-09-23)

- macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2 runner (system Python
  3.9.6 helper): `make clean && make -j2 && make test && make test-harness`
  passed: four prototype cases and 23 harness checks. The generated Flex scanner
  retains its existing signedness warning; no C sources changed.
- Debian Bookworm Linux aarch64, GCC 12.2.0, Python 3.11.2:
  `make docker-test DOCKER_IMAGE=cshell-test:csh-017` and
  `docker run --rm --init cshell-test:csh-017 make test-harness` passed with the
  same four prototype cases and 23 harness checks.
- Native and Docker tests with `TEST_TARGET=`,
  `TEST_BINARY=tests/helpers/candidate.py`, and
  `TEST_SUITE=tests/fixtures/self/passing.json` each passed four self-fixtures.
  Selecting `tests/fixtures/self/failing.json` instead produced seven intentional
  failures and nonzero Make status in both environments. Diagnostics identify
  mismatched stdout/stderr/status, missing/wrong files, timeout, and output limit.
- Harness checks verify cleanup of a hanging parent and descendant, cleanup
  after a successful parent exits, combined output caps, stdin/output backpressure,
  inherited resource limits, filesystem and environment isolation, and rejected
  invalid metadata. All-skipped selections fail rather than report empty success.
- Docker builds selecting `TEST_TARGET=build/main.o` or an empty target did not
  build `cshell`; generated module executables belong under excluded `build/`.
- Actionlint 1.7.12 accepted `.github/workflows/tests.yml`; `git diff --check`
  passed. The documented strict JSON example passed against `/bin/sh`.
- Hosted CI results will be recorded after the branch is pushed. The ticket
  remains `review` until integration; passing these tests is not a claim of
  POSIX shell compliance.
