# CSH-049 residual execution validation

The [condition map](../../execution-residuals.md) specifies exact cases and
oracles. The [ticket](../../tickets/CSH-049-execution-evidence.md#residual-acceptance-review-2026-09-28)
records source revisions, disposition and platform results. No production
runtime change or test timeout increase is part of this work.

## Source identities

- Initial implementation `6c3e602`: 492 new runtime cases, 811 execution cases
  total, 204 controlled redirection probes. Source digest
  `30dea68a2be29a017675a2c7708bb1260ac25385e50869ad5ea3af1919e2e60a`.
- Final implementation `990e706`: adds 72 empty-target cases (564 new, 883
  execution cases total); the other 811 fixture structures and all compiled
  code are unchanged. Source digest
  `dcc8247cf5015e582e7af79aaf22d091a488e477efd2d7cdec29cf30d53bce86`.

Manifests use [the existing identity collector](../csh-055/identity.py):
Makefile, Dockerfile, src, include and tests excluding Python caches. Native,
Docker and native sanitizer copies agree within each revision. Collection
occurs after tests; timestamps are not asserted to be exact run-start times.
Flags, compiler, libc/OS, Python, binary/helper hashes and generated-suite hashes
are in the identities. Subsequent documentation changes are outside the digest.

## Runs and reproduction

`native-focused.log.gz` passes the initial 811-case focused suite, 51 existing
contracts and 204 new probes. `native-full`, `native-pty`, `native-harness` and
`docker-normal` logs preserve full normal/API/PTY/harness checks at that revision:
3,833 runtime cases, 30 jobs and 32 runtime PTY cases, supporting terminal
fixtures and 74 harness tests. Docker normal also runs the focused target.

`native-empty.log.gz` is the **failed** first attempt at the extra 72 cases
from `a8c35cd`: 12 noclobber setups fail before reaching the tested operand.
`990e706` changes the preceding redirect to explicit `>|early`, without changing
expected outputs, status or timeouts. `native-empty-final` then passes 72/72.
`native-final-runtime` and `docker-final-normal` pass all 3,905 final runtime
cases; final Docker also passes all 883 focused cases and 204 boundary probes.
These failures and fixes are fixture evidence, not a shell defect or a waived
redirection requirement.

Normal commands:

```sh
make -j4 test-execution-evidence
make -j2 test
make test-pty
make test-harness
make test-runtime
make docker-build DOCKER_IMAGE=cshell-test:csh-049-residuals
# Initial full run, retained in a named container for identity collection:
docker run --name csh-049-residuals-normal --init cshell-test:csh-049-residuals \
  sh -c 'make -j2 test test-execution-evidence && make test-pty && make test-harness'
# Final 72 additions plus all existing runtime cases:
make docker-build DOCKER_IMAGE=cshell-test:csh-049-residuals-final
docker run --name csh-049-residuals-final-normal --init cshell-test:csh-049-residuals-final \
  make -j2 test-runtime test-execution-evidence
```

Docker identities come from snapshots of the actual stopped test containers,
with the original Dockerfile and collector mounted read-only. They are not
rebuilds. Initial/final snapshots and generated-suite hashes are distinct.
The native sanitizer sources are a separate `build/asan` archive; its binary
and build roots are identified explicitly.

Sanitizer validation uses these targets and flags:

```sh
ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
make -j2 test-execution-evidence test-execute test-pipeline test-context \
  test-control test-redirection-offset \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Docker omits `MallocNanoZone`. API runners inherit supplied options; smoke
subprocesses have their controlled environment and default sanitizer options.
No blanket leak-check claim is made. The external descriptor observer remains
uninstrumented under the existing Makefile contract. The new open/fstat shim
and public-main test executable are instrumented.

Initial sanitizer runs select 811 execution cases plus 204 boundary and 51
read/descriptor probes and the listed API/control/offset targets. Final
`*-asan-empty` runs select exactly the 72 added cases from regenerated final
883-case suites on the unchanged sanitizer binaries. Source and generated-suite
identities distinguish those complementary runs; the full initial run is not
relabeled a final 883-case invocation.

The structural selection check verifies unique focused case names and equality
with the full runtime selection. It also compares the 811 old cases before and
after the additions, mapping only the absolute helper build-root prefix for
native sanitizer copies. No output assertion or raw log is normalized.

All new cases run without skips. Existing locale, credential and host-utility
limits retain their original labels/owners. They are not promoted to passes.
Compressed logs are verbatim; `artifacts.json` hashes all retained artifacts
except itself. Hosted jobs, if listed in the ticket, supplement local binary
identities and do not publish binary hashes.

## Hosted native Linux

[Ubuntu job 109104973473](https://github.com/melliott18/cshell/actions/runs/36474588179/job/109104973473)
passes all normal, terminal, qualification, harness and full sanitizer stages
at final implementation `990e706`. Its log and metadata are retained separately.
`hosted-case-crosscheck.json` checks that each of the final 883 execution case
names passes three times (normal, qualified PATH, sanitizer), and that both
normal and sanitizer runs pass all 204 controlled probes and 51 existing
contracts. This establishes native Linux evidence independently of Docker.
The workflow's other jobs are not inferred to pass from the Ubuntu result.

[Hosted Docker job 109104973603](https://github.com/melliott18/cshell/actions/runs/36474588179/job/109104973603)
also passes all final normal, terminal, controlled-host, harness and sanitizer
stages. Its log/metadata are retained independently of local arm64 Docker.
The case cross-check records four passes per execution case (normal, qualified
PATH, controlled BusyBox PATH and sanitizer), and two runs each of the 204
controlled probes and 51 contracts. The hosted macOS job is not a prerequisite
for the separately recorded local native macOS results and is not inferred
successful from the two Linux jobs.
