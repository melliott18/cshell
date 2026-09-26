# CSH-052 validation artifacts

The [clause map](../../host-utility-evidence.md) links every scoped requirement
to normative sources, selected policies, implementation and exact assertions.
The final source/test revision is `86db26b` (full revision in each identity).
No C runtime code changed from baseline `09ac115`. Later commits add evidence
and documentation only. Native and Docker final identities carry the same
source fingerprint over Makefile, Dockerfile, src, include and tests, excluding
Python caches. Dockerfile is mounted read-only for identity collection because
the image does not copy its build recipe into `/work`.

## Results

| Environment / command | Outcome |
| --- | --- |
| Native macOS, `make -j4 test test-pty test-harness` | Existing runtime: 3,045 pass; runtime PTY: 30 pass; job PTY: 15 pass; module/fault checks pass. One concurrent harness timeout makes the overall command status 2; isolated retry passes all 65 then-existing self-tests. |
| Linux/Docker, `make -j4 test test-pty` | Existing runtime: 3,045 pass; runtime PTY: 30 pass; job PTY: 15 pass; module/fault checks pass; command status 0. |
| Native final, `make -j4 test-host-utilities test-harness` | 784 host assertions pass, 12 known host gaps, no unexpected failures; 69 harness self-tests pass. |
| Linux/Docker final, `make test-host-utilities test-harness` | 781 host assertions pass, 12 known host gaps, no unexpected failures; 69 harness self-tests pass. |
| Native final ASan/UBSan, focused host runner | Same 784 pass / 12 gaps, no sanitizer diagnostics. |
| Linux/Docker final ASan/UBSan, `make -j4 test-host-utilities` with sanitizer flags | Same 781 pass / 12 gaps, no sanitizer diagnostics. Linux leak scanning explicitly disabled. |
| Linux/Docker root, `python3 tests/invocation.py ./cshell` | All 51 pass, including the two unequal-identity tests skipped as non-root. |
| Linux/Docker, host runner with `--strict-gaps` | Status 1, with all known unmet requirements retained; this is the expected failure of the conformance-oriented mode, not a complete utility pass. |

Native host gaps are the two missing-file timestamp comparisons in both `test`
and `[` across three input modes (12). Docker host gaps are missing `ed`,
printf numbered conversions, printf %b precision and kill status mapping,
each across three modes (12). Missing ed means three executable-lookup cases
cannot be generated on Docker, explaining the three fewer passing assertions.
The missing exec cases are explicitly recorded as GAP; they are not silently
counted as verified lookups. No new host case is capability-skipped. `stty`
runs once on a controlling PTY, in both normal and instrumented runs.

The earlier full integration runs exercised the new target while its fixtures
were still being refined. They establish the **unchanged existing suites**
from baseline `09ac115`; their preliminary host results are superseded by the
complete final focused records at `86db26b`. The final refinements affect only
host-case assertions, diagnostic rejection, terminal restoration and four new
harness self-tests. Existing runtime/module/PTY fixture sources are unchanged.

The initial native harness failure was
`test_cleanup_kills_descendant_after_successful_parent_exit`: its candidate
exceeded the existing one-second deadline under concurrent compilation/testing.
`native-integration.log.gz` retains the failure; `native-harness-retry.log.gz`
retains the isolated pass without timeout changes. The final native and Docker
runs also pass this test among all 69 self-tests. Recurrence belongs to the
CSH-017/033 harness area; no load-independent reliability claim is made.

The existing normal suites skip SH-004 unequal uid/gid cases without Linux root
(CSH-046); the Docker root record covers both. Native installed locales lack a
translated libc ENOENT diagnostic (CSH-042), so that existing capability branch
is skipped there and covered on Docker. The new host suite selects C locale;
it does not claim non-C host behavior. Linux here is Docker/aarch64, not a
separate bare-metal Linux validation or an unexecuted CI run.

## Identity, assertions and reproduction

`*-results.json.gz` preserves every final case name, script, invocation,
expectation, actual bytes (hex), status, file state and verdict. Setup is defined
by `tests/host_utilities.py:setup` at the recorded revision. Each report records
host lookup/real paths, binary hashes and Linux package versions; native tools
without a version option are identified by executable hash and macOS build.
`*-identity.json` records source and binary hashes, compiler, flags, OS/libc,
architecture and helper identities. `docker-images.json` records immutable
built-image identities; the build log records the pinned resolved base digest.
`artifacts.json` hashes the retained files and records command statuses.
Identity timestamps are collection times after a run, not inferred start times.

```sh
make -j4 test test-pty
make test-host-utilities test-harness
python3 docs/evidence/csh-052/identity.py
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper --strict-gaps

docker build -t cshell-test:csh-052 .
docker run --rm --init cshell-test:csh-052 make -j4 test test-pty
docker run --rm --init cshell-test:csh-052 make test-host-utilities test-harness
docker run --rm --init --user 0 cshell-test:csh-052 python3 tests/invocation.py ./cshell

make clean
MallocNanoZone=0 make -j4 test-host-utilities \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Run the same clean/build command in the Docker container for Linux ASan/UBSan.
The Make target sets `--sanitizer` when its LDFLAGS contain `-fsanitize`;
the runner sets halt-on-error variables in each actual child environment,
adding `detect_leaks=0` on Linux. The final native runner reused the instrumented
binary built in the initial sanitizer run because no C files changed; its
binary identity is retained. The helper is intentionally unsanitized to observe
resource/descriptor state without sanitizer startup effects. Every case also
rejects sanitizer text even when a generic host diagnostic would otherwise be
allowed. There is no Linux LeakSanitizer claim.

Read retained logs using `gzip -dc FILE.log.gz`. Standard-derived expectations
are separate from exact known-failure signatures; fixing a host turns a GAP
into PASS without changing the expected result. Remaining obligations and
image limitations are assigned to [CSH-056](../../tickets/CSH-056-host-contract-gaps.md).
