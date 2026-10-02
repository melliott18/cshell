# CSH-082: Prepare application containers for Pipeline

- Status: review
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-039
- Branch: `fix/CSH-082-container-readiness`
- Issue: [#169](https://github.com/melliott18/cshell/issues/169)

## Goal

Provide application-owned test and runtime images compatible with Pipeline's
manual local build contract, with useful failure evidence and bounded shutdown.

## Scope

- Named Docker test/runtime targets; keep the existing development test image.
- Non-root runtime, installed executable, init/signal handling and host utilities.
- Offline test command with JUnit stage reports and retained logs.
- Container checks and exact Pipeline registration/handoff documentation.
- No new POSIX compliance, release qualification, or deployment claim.

## Acceptance criteria

- [x] Runtime image runs command strings, stdin and scripts as UID/GID 10001.
- [x] Runtime has no compiler/test sources and works with a read-only root plus /tmp.
- [x] Noninteractive TERM and exec status propagate through the container init.
- [x] Test target runs the existing strict suites under Pipeline resource/security settings and emits truthful JUnit reports, including failures.
- [x] Existing Docker development commands remain usable; CI checks runtime packaging.
- [x] Document CLI invocation, report paths, platform registration and known limits.

## Validation

Run report-runner success/failure tests, the test image with network disabled,
1 GiB memory, two CPUs, 256 PIDs, no capabilities and no-new-privileges; inspect
its JUnit reports. Run application container integration tests, native harness
checks and git diff --check. Record exact results before review.

## Implementation notes/evidence

The Dockerfile now has `development`, `test`, `build`, and default `runtime`
stages. Make's existing Docker test targets explicitly select development.
Runtime installs the source-built cshell and Tini, runs as UID/GID 10001, and
forwards group termination. Pipeline's test command emits aggregate JUnit cases
for the unchanged strict Make suites and retains their full logs. New tests
exercise report failure handling and the runtime image through its entrypoint.
GitHub CI adds restricted application-image tests and retained reports.

[Validation evidence](../evidence/csh-082/README.md) records successful restricted
Linux ARM64 full/PTY/harness suites, nine runtime-image checks, 89 native harness
checks, unchanged development PTY behavior, Pipeline report acceptance and
failure rejection, and identical tested/shipped cshell binary hashes.

[Container operations and Pipeline handoff](../containers.md) documents exact
commands and registration fields. Pipeline registration/approved-main execution,
hosted CI, other architectures, sanitizer recurrence, and full host qualification
are not claimed complete by this preparation. Keep this ticket at review until
integration into main.
