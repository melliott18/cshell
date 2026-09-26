# CSH-051 validation artifacts

The [clause map](../../shell-option-evidence.md) links all 13 requirements to
source, policy, implementation and exact fixture assertions. The source/test
revision is `e1091a5fd818a85ec6a7b2ddc90a54cf1fdd8c9d`; later commits add only
evidence documentation. Native and Docker identities have the same source
fingerprint. The normal runs began before that commit on identical source/test
bytes. Identity collection timestamps are post-run UTC timestamps, not inferred
process-start times.

## Results

| Environment / command | Result |
| --- | --- |
| Native macOS, `make -j4 test test-pty test-harness` | Pass: 2,299 runtime cases (including all 1,101 option cases), 30 runtime PTY cases (8 option cases), 15 job PTY cases, module/fault suites, 64 harness self-tests. Three unrelated capability skips below. |
| Linux/Docker, same command | Runtime, PTY and module/fault suites pass with the same runtime/PTY counts. Two root-only invocation skips. One harness self-test failed its setup deadline; isolated retry below passes. The combined command's status is 2, retained in the record. |
| Linux/Docker, `make test-harness` isolated retry | All 64 pass on the same built image, unchanged deadlines and fixtures. |
| Linux/Docker root, `python3 tests/invocation.py ./cshell` | All 51 pass, covering the two non-root skips. |
| Native ASan/UBSan, `make -j4 test-options test-runtime-pty` | All 1,101 option and 30 runtime PTY cases pass; no sanitizer diagnostics. |
| Linux/Docker ASan/UBSan, `python3 /tmp/sanitizer.py` | All 1,101 option and 30 runtime PTY cases pass; no sanitizer diagnostics. Leak scanning explicitly disabled in the case environment; see below. |

No option or option-PTY case is skipped. The normal suite's root-only SH-004
uid/gid witnesses are owned by CSH-046; the Docker root run supplies them.
Native translated ENOENT diagnostics skip because installed locales have no
translated libc message. Scope is LC_MESSAGES evidence, owned by CSH-042;
Docker's installed locale supplies that branch. Docker is Linux/aarch64, not a
separate bare-metal Linux-host run; no unexecuted host configuration is claimed.

The first native attempt, `native-suite-limit.log.gz`, failed before loading the
runtime suite because pretty-printed JSON with the longer native helper paths
exceeded the runner's 1 MiB cap. CSH-051 changes only serialization to compact
JSON, preserving the cap; the final native runtime file is 767,302 bytes.
Its other suite results are retained but the attempt is not called a pass.

The Docker parallel harness failure is
`test_snapshot_failure_reports_teardown_error_and_reaps_leader`: its helper did
not record process setup within the fixture's 150 ms bound under concurrent
load. `docker.log.gz` retains the failure; `docker-harness-retry.log.gz` retains
the isolated success without timeout changes. This is a scheduling-sensitive
harness observation, not an option-language failure or a waived assertion.
Future recurrence belongs to the CSH-033 harness area; no stronger claim of
load-independent harness reliability is made here.

The initial Docker sanitizer run (`docker-sanitizer.log.gz`) timed out in
`options: terminal monitor default` and `options: O-001 invalid option (stdin)`;
no sanitizer violation was reported. A trivial-shell timing probe measured
1.173 seconds with leak scanning enabled and 0.007 seconds with it disabled.
That incomplete run was deliberately stopped (container status 143), preserving
its log. The same instrumented binary then ran both complete suites through
[sanitizer.py](sanitizer.py), with per-case
`ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and
`UBSAN_OPTIONS=halt_on_error=1`. All unchanged output/status/state assertions and
five-second deadlines pass in `docker-asan-ubsan.log.gz`. Derived
`docker-*-asan-ubsan.json.gz` snapshots record these environment overrides.
This is ASan/UBSan evidence, **not a Linux LeakSanitizer pass**. The original
runner sanitizes its child environment, so setting these variables only on
`make` would not have applied them to the shell under test.

## Identity and assertions

`native-identity.json` and `docker-identity.json` record executable path/realpath,
SHA-256, compiler, flags, OS/libc or system-library version, architecture, Python,
source fingerprint and generated-suite hashes. Sanitizer identities are separate.
`docker-images.json` records immutable build, built-container and base image
identities, rather than relying on mutable tags. `artifacts.json` hashes the
retained artifacts and records command statuses. `identity.py` reproduces the
platform identity collection; pass `EVIDENCE_REVISION` inside Docker, which has
no Git metadata. The source fingerprint is SHA-256 of a sorted JSON map from
relative Makefile/src/include/tests paths to file SHA-256, excluding Python caches.
Documentation and evidence artifacts are outside that fingerprint.

`native-options.json.gz` and `docker-options.json.gz` preserve all 1,101 expanded
exact names, full invocation arguments, input scripts/bytes, setup files, expected
stdout/stderr/status and filesystem state. `*-runtime-pty.json.gz` preserves
terminal input/control sequences, prompt synchronization and exact output/status.
A `PASS` from the shared runner means all those assertions, the five-second
case bound, output/resource limits and cleanup checks succeeded. These options
use predicate-based terminal setup in the runner; ephemeral process IDs and
fresh temporary directory names are not stored as fixed expected values.
Normal full logs contain each named option assertion as part of the runtime
suite; focused sanitizer logs contain them under the option suite.

Read artifacts with `gzip -dc FILE.log.gz` or
`gzip -dc native-options.json.gz | python3 -m json.tool`.

## Reproduction

```sh
make clean
make -j4 test test-pty test-harness
make test-options
python3 docs/evidence/csh-051/identity.py

docker build -t cshell-test:csh-051 .
docker run --rm --init cshell-test:csh-051 make -j4 test test-pty test-harness
docker run --rm --init cshell-test:csh-051 make test-harness
docker run --rm --init --user 0 cshell-test:csh-051 python3 tests/invocation.py ./cshell

make clean
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
make -j4 test-options test-runtime-pty \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

For the passing Docker sanitizer run, build `cshell`, `build/tests/options.json`
and `build/tests/runtime-pty.json` with the same flags after `make clean` in the
container. Bind-mount this directory's `sanitizer.py` and execute it with Python;
it adds the explicit sanitizer variables to each fixture's child environment
and runs both suites sequentially. See the derived suite snapshots for the
complete invocation and environment.
The normal build uses the Makefile defaults recorded in the identities. No C
runtime code changed, so sanitizer evidence is scoped to the newly exercised
option and interactive paths; normal validation includes the full module/fault
and integration suites. Standard/implementation policies, not reference-shell
output, determine expected results.
