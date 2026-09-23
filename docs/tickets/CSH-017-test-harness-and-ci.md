# CSH-017: Build a bounded behavioral harness and continuous integration

- Status: ready
- Type: test
- Kind: implementation
- Parent: CSH-003
- Depends on: CSH-001
- Branch: Assigned when work starts
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

## Acceptance criteria

- [ ] Fixtures assert stdout, stderr, exit status, and relevant filesystem effects
  while isolating each case's working directory and environment.
- [ ] A deliberately hanging child/process-group fixture is stopped and cleaned
  up; excessive-output fixtures fail without unbounded runner memory growth.
- [ ] `make test` and `make docker-test` run the same selected fixture suite and
  return failure when a fixture fails.
- [ ] CI builds and tests the supported native platforms and Docker Linux path;
  an intentionally failing fixture demonstrates failure propagation locally.
- [ ] Contributor/testing docs explain fixture authoring, limits, platform skips,
  and current prototype allowances without claiming language compliance.

## Validation

Run the real smoke suite natively and in Docker. Exercise harness self-fixtures
for mismatched status/output, filesystem assertions, hangs, spawned descendants,
and output limits; each deliberately failing case must yield a useful failure.
Validate CI configuration and record available CI run results after pushing.
Keep harness self-fixtures separate from passing shell-behavior expectations.

## Implementation notes/evidence

This work is independently actionable against the CSH-001 stdin interface.
The current prompt allowance remains explicit until CSH-018 installs tests for
all invocation modes and removes it from non-interactive cases. Use adapters or
fixture metadata for future invocation modes, not mandatory unsupported flags.
