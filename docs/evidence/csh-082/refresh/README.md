# CSH-082 integration refresh

Validated on 2026-10-06 in a separate worktree on
`fix/CSH-082-container-readiness-refresh`. The implementation already existed in
[PR #170](https://github.com/melliott18/cshell/pull/170) at `43f26b3`.
Merge `37762a3` combines it with main `e0166e0`; the merge was conflict-free.
No additional shell or container implementation changes were needed.
The accompanying ticket/evidence edits do not change executable inputs.

[validation.json](validation.json) records the tested commit, host, Docker
engine, image identities, container restrictions, and binary hash. The host is
macOS ARM64 and the images are Linux ARM64. The initial runtime build hit a
Docker Hub TLS handshake timeout; retrying the same command succeeded.

## Completed checks

- `make test-harness`: all 98 native checks passed, including report success,
  failure/stale-report replacement, and missing-command failure handling.
  [Native log](native-harness.log.gz).
- `make docker-runtime-test RUNTIME_IMAGE=cshell:csh-082-refresh`: all nine
  runtime checks passed. They cover the real entrypoint, UID/GID 10001,
  read-only root plus writable `/tmp`, installed executable and runtime
  contents, invocation modes, interactive terminal, exit statuses, and
  process-group TERM delivery. [Build and runtime log](runtime-checks.log.gz).
- `make docker-pipeline-build PIPELINE_IMAGE=cshell-pipeline-test:csh-082-refresh`
  built the application-owned test image. [Build log](test-image-build.log.gz).
- The test image's default command passed `make test`, `make test-pty`, and
  all 98 `make test-harness` checks as UID/GID 10001:10001, with network disabled,
  1 GiB memory, two CPUs, 256 PIDs, all capabilities dropped, and
  `no-new-privileges`. The container exited 0. [Command output](pipeline-command.log)
  and [validation metadata](validation.json) retain the command and result.
  The [JUnit report](junit.xml) contains three aggregate cases with zero
  failures/errors/skips; individual case results and existing capability gaps
  remain in [test.log.gz](test.log.gz), [test-pty.log.gz](test-pty.log.gz),
  and [test-harness.log.gz](test-harness.log.gz).
- `make docker-build DOCKER_IMAGE=cshell-development:csh-082-refresh`, followed
  by `docker run --rm --init cshell-development:csh-082-refresh make
  test-runtime-pty`: all 33 cases passed. [Development log](development-check.log.gz).
- `/work/cshell` in the test image and `/usr/local/bin/cshell` in the runtime
  image have identical SHA-256 hashes:
  `01db4d7d05f8d91402df59d7bb90debaf3c03b7fdd88f5066316a0b16574175d`.
- `git diff --check` passed.

## Original hosted CI reconciliation

The original PR's
[hosted run](https://github.com/melliott18/cshell/actions/runs/36783277712)
passed native Linux, Docker, and application-container checks. Its macOS
sanitizer step failed at `test-job-retention` after the old 60-second deadline;
the [retained excerpt](previous-ci-failure.log) identifies that failure.
The current main includes the subsequent
[CSH-057 retention budget repair](../../csh-057-retention-budget/README.md)
and [integration verification](../../csh-057-final-verification/README.md).
This refresh retains those repairs without weakening container assertions.

Fresh hosted CI and sanitizer execution, other architectures, full host-profile
qualification, and Pipeline registration/approved-main execution are not
established by this local record. The ticket remains at review until merged.
