# CSH-049 run artifacts

See the [clause map](../../execution-evidence.md) and
[ticket run record](../../tickets/CSH-049-execution-evidence.md#validation-record).

`validation.json` records source and binary identity, generated-suite hashes,
compiler/flags, OS/libc/Python, Docker image/base digest, controlled-environment
context and artifact hashes. Source hashes cover Makefile, src, include and tests,
excluding Python caches; they agree across native, Docker and native ASan copies.
Normal Docker generated-suite/helper hashes were reconstructed from the same
immutable image after the test container exited; the native copies are retained.

The `.log.gz` files retain raw results. Read one with `gzip -dc FILE.log.gz`.
`native-harness.log.gz` is a failed attempt, followed by an unchanged passing
retry. `*-known-gaps.log.gz` are **failing** strict CSH-055 reproductions and
must not be counted as passes. Normal test logs include capability skips with
explicit owners. No diagnostic or prompt normalization is applied.

Reproduce normal validation from the worktree:

```sh
make -j4 test
make test-pty
make test-harness
make docker-build DOCKER_IMAGE=cshell-test:csh-049
docker run --rm --init cshell-test:csh-049 sh -c 'make -j4 test && make test-pty && make test-harness'
docker run --rm --init --user 0 cshell-test:csh-049 python3 tests/invocation.py ./cshell
```

`docker-asan.log.gz` is a failed combined run: all 248 new execution cases
passed, three existing offset cases timed out, and make left later API targets
unrun. Binary and suite identities come from that stopped container.

The focused new cases are `make test-execution-evidence`. Sanitizer flags and
scope are in the ticket. Generated helper paths differ by worktree; source
fixture bytes and the recorded hashes identify the exact assertions.


The `hosted-*.log.gz` files retain completed job logs for the linked hosted
run. Ubuntu and Docker passed full checks. macOS passed normal checks and
failed an existing sanitizer terminal transcript assertion. The additional
push-run macOS log is a distinct attempt; consult its actual failure, not an
assumed common cause. Hosted binary hashes are not available from this workflow.

## Integrated rerun (2026-09-28)

The `integrated/` directory records revision
`b1b6b1583a883e7fbb5616a317c1633bf85052b4` after CSH-055 and the subsequent
signal/job integrations. Its lookup reproducer **passes**; the original
`*-known-gaps.log.gz` files above remain historical failures.

- `native-test`, `native-pty`, `native-harness` and `native-lookup` logs contain
  fresh native normal checks. `docker-normal` contains full normal, execution,
  PTY, harness and strict lookup checks; `docker-build` retains build output.
- `native-identity.json` and `docker-identity.json` use the existing
  [CSH-055 collector](../csh-055/identity.py). Source digests agree; the Docker
  collector read a snapshot of the completed container with the original
  Dockerfile mounted read-only. `docker-images.jsonl` identifies both images.
  Collection happened after tests; timestamps are not run-start timestamps.
- `integrated-hosted-{macos,ubuntu,docker}.log.gz` and accompanying run/job
  metadata retain successful full normal and ASan/UBSan checks from hosted run
  36449808979 on that exact revision. Linux job logs were fetched directly via
  the job-log API because `gh run view --log` returned only the macOS log.
  Hosted binary hashes are unavailable.
- `case-crosscheck.json` records that each of the 319 generated execution case
  names appears as passing three times per hosted environment: normal runtime,
  qualified-PATH runtime and sanitizer runtime. Only the helper's absolute path
  in three case *names* is mapped for comparison; raw logs and byte-exact
  runtime assertions are unchanged. Each host also passes the 51 descriptor/read
  probes in normal and sanitizer stages.
- `artifacts.json` hashes every retained integration artifact except itself.

Reproduce with `make -j4 test test-execution-evidence`, `make test-pty`,
`make test-harness`, and the strict smoke command in the ticket. Docker used
`make docker-build DOCKER_IMAGE=cshell-test:csh-049-integrated`, then a named
container running `make -j2 test test-execution-evidence && make test-pty &&
make test-harness && python3 tests/smoke.py ./cshell --suite
 tests/fixtures/execution-known-gaps.json`. Normal flags and local/hosted
sanitizer distinctions are recorded in the ticket. No new local sanitizer run
was needed for the evidence-only edits; full hosted sanitizers cover the exact
runtime/test revision. Existing capability skips, stock-host gaps and CSH-057's
intermittent terminal failure remain separate from these passing runs.
