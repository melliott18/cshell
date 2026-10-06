# CSH-082 container preparation validation

The [2026-10-06 integration refresh](refresh/README.md) retains validation
against current main and reconciles the original hosted CI result. The results
below remain the original 2026-09-30 snapshot.

Validated on 2026-09-30 with a macOS ARM64 host and Linux ARM64 Docker engine.
[validation.json](validation.json) records engine/image identities, exact test
container restrictions, binary hash, and the Pipeline parser revision used.
The application base was `ff736b7`; these results cover the CSH-082 working
changes. No shell C source was changed. No AMD64, hosted CI, sanitizer, registry,
or actual approved-main Pipeline checkout run is claimed by this local record.

## Completed checks

- `make docker-pipeline-build`, then the application image's default command
  as UID/GID 10001:10001 with `--network none --memory 1g --cpus 2
  --pids-limit 256 --cap-drop ALL --security-opt no-new-privileges`: exit 0.
- Full `make test`: passed, including 3,950 public runtime cases. The stock host
  suite preserves nine known printf/kill gap instances; identity and locale
  capability skips remain visible in [test.log.gz](test.log.gz).
- `make test-pty`: passed, including 30 job PTY and 33 runtime PTY cases plus
  notification/fault checks. [Terminal log](test-pty.log.gz).
- `make test-harness`: 89 checks passed in the container, including the three
  new report success, failure/stale-report, and unavailable-command checks.
  [Container harness log](test-harness.log.gz).
- `make test-harness` on macOS: 89 passed. [Native log](native-harness.log.gz).
- `make docker-runtime`, then `python3 tests/container_runtime.py --image
  cshell:local`: nine checks passed with read-only root, writable /tmp, no
  network/capabilities, and the same resource limits. Covers real entrypoint,
  non-root identity, runtime contents, command strings, stdin/here-documents,
  script arguments, EOF, exec status, terminal interaction, normal TERM status
  143, and process-group TERM reaching a trapped child with final status 42.
  [Runtime log](runtime-checks.log.gz).
- `make docker-build DOCKER_IMAGE=cshell-082-development:local`, then `docker run
  --rm --init cshell-082-development:local make test-runtime-pty`: 33 passed,
  preserving the existing development-image path. [Log](development-check.log.gz).
- Pipeline's actual `tools.pipeline.runner.check_junit` accepts the retained
  [junit.xml](junit.xml): three aggregate suite cases, zero failures/errors/skips.
  Individual assertions and capability skips are recorded in the full logs.
- A deliberate suite exit 23 produces runner exit 1 and a failed JUnit testcase;
  Pipeline rejects that report. [Rejection evidence](report-rejection.json).
- The test-image `/work/cshell` and runtime `/usr/local/bin/cshell` have identical
  SHA-256 hashes. The runtime image is 99,108,853 bytes locally.
- `git diff --check` passes.

Reports are application-provided regression evidence, not release attestation.
The current Pipeline registration example and CLI invocation are in the
[container guide](../../containers.md). Platform registration and testing a
merged approved-main SHA remain the Pipeline-side onboarding step. CSH-057's
macOS sanitizer recurrence and the host qualification tickets remain separate.
