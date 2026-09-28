# CSH-050 unmet-criteria review

The review starts from integrated `8ffb99e`. It confirms that PR #112's
foreground-resume status correction is present and that CSH-057's separate
PTY/retention timeouts remain unresolved. It also finds and repairs a distinct
partial-delivery defect in the U-026/JOB-003/U-032 implementation.

## Defect and regression

`kill_builtin` used its cumulative return status to decide whether to clear a
job's stopped flags. After an earlier invalid operand, a successful CONT or
KILL left later jobs recorded as stopped. If one stage of an ungrouped pipeline
rejected delivery, successful siblings were also left stopped. Subsequent job
state inspection could therefore disagree with the signal just delivered.

The fix updates each successful group/stage delivery independently, preserves
stopped state for denied delivery, and still returns a nonzero aggregate status.
It changes no signal selection, permission rule, wait status encoding or deadline.
The existing supported job-operand and continue-after-error contracts supply
the expectations; this review does not promote an entire POSIX family.

`tests/kill_job_state.c` creates two real stopped children. A launch pipe and
`waitid(WSTOPPED | WNOWAIT)` establish their state without scheduling sleeps.
Fourteen cases cross grouped/ungrouped delivery and CONT/KILL with an invalid
operand before/after the job, a denied group, or a denied first/last ungrouped
stage. Only the EPERM syscall result is interposed; successful signals are real
and target only owned children. The assertions check immediate stopped flags
before another poll can collect WCONTINUED, exact diagnostics, cumulative status,
final-stage wait status, and ECHILD. Denied children are explicitly killed for
cleanup after their retained state is checked; their cleanup status is accounted
for in the final wait assertion. Four-second helper alarms and the existing
five-second smoke limit remain unchanged.

On both macOS and Linux, the original implementation fails eight cases and
passes six. Failures are the earlier-invalid-operand cases and both ungrouped
partial-permission branches, for CONT and KILL. The controls with an invalid
operand afterward or a wholly refused group pass. The fixed implementation
passes all fourteen. `native-before.log.gz` retains the initial failure output;
`docker-before.log.gz` reconstructs the original jobs.c from `8ffb99e` with the
final fixture and records the source/binary hashes. Native's initial failed
binary was rebuilt before hashing; that run is identified by source/fixture
history and log rather than a retrospectively invented binary identity.

## Validation and source identities

Functional source/test revision is `0834de2`, based on `8ffb99e`. Final Makefile
commit `ad154be` only adds `mkdir -p` before case generation to prevent a clean
parallel build race; `generator-check.log.gz` verifies generating all 14 cases
from an empty build directory. All production C and case definitions are
identical between those revisions.

| Record | Command / result |
| --- | --- |
| `native-after.log.gz` | `make test-kill-job-state`: 14 passed, zero failures/skips. |
| `native-focused.log.gz` | `make test-jobs-signals test-harness`: exit 0, including all 14 new cases, 148 jobs, 207 trap/exit, 2,464 signal-edge and 361 signal-contract cases, lifecycle/API/fault/interrupted-wait checks, 30 jobs PTY + 32 runtime PTY cases, and 74 harness self-tests. |
| `native-full.log.gz` | `make test test-pty test-host-profile`: exit 0. All 3,341 runtime cases and terminal suites pass; the qualified host profile reports 1,162 passed, zero failures/gaps. |
| `native-sanitizer.log.gz` | ASan/UBSan `make test-jobs test-jobs-pty`: exit 0, including all 14 new cases, 148 jobs cases, retention, ownership/fault/watchdog checks, notification API, 30 jobs PTY cases and one fault PTY case. No sanitizer diagnostics. |
| `docker-full.log.gz` | `make test test-pty test-harness test-host-profile`: exit 0, including 14 new cases, 3,341 runtime cases, 2,495 signal edges, both terminal suites and 74 harness self-tests; qualified profile 1,162 passed, zero failures/gaps. |
| `docker-sanitizer.log.gz` | ASan/UBSan `make test-jobs test-jobs-pty`: exit 0, all 14 new cases, 148 jobs cases, retention, API/fault/watchdog checks and 30+1 PTY cases pass without sanitizer diagnostics. |

Normal and sanitizer source manifests on both platforms match:
`de047d369f4fd13208111f4d3c5ec4e317b7cf88eb72775900e1be10fabf4366`.
The identity JSON files retain exact source manifests, revision/dirty state,
binary/helper/generated-suite hashes, UTC timestamps, OS/libc/compiler/Python
versions, flags and relevant environment. Collection reuses CSH-058's identity
collector, with additional helper hashes. Host-profile manifests separately
identify the qualified utilities; their passing results do not qualify stock
utilities.

Native is macOS 14.8.7 (23J520), Darwin 23.6.0 arm64, Apple Clang 15.0.0,
Python 3.12.2. Docker uses Debian 12 arm64, Linux 6.4.16-linuxkit, GCC 12.2.0,
glibc 2.36, Python 3.11.2 and Docker engine 24.0.6. Exact image and engine
metadata is retained. Normal flags are the repository defaults:
`-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`,
`-D_POSIX_C_SOURCE=200809L -Iinclude`, no extra linker flags/libraries.

## Reproduce

```sh
make test-kill-job-state
make test-jobs-signals test-harness
make test test-pty test-host-profile

docker build -t cshell-test:csh-050-acceptance .
docker run --rm --init cshell-test:csh-050-acceptance \
  make test test-pty test-harness test-host-profile

# In a separate clean source/build copy:
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
make test-jobs test-jobs-pty \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The smoke runner uses controlled C locale/PATH, per-case HOME/TMPDIR, no supplied
TZ and umask 077. It retains MallocNanoZone but does not forward arbitrary
ASAN_OPTIONS/UBSAN_OPTIONS; instrumented smoke children use sanitizer defaults.
API runners inherit the documented caller environment. The Docker sanitizer
caller supplies `ASAN_OPTIONS=halt_on_error=1:detect_leaks=0` and
`UBSAN_OPTIONS=halt_on_error=1`; smoke children still use sanitizer defaults.
There is no blanket Linux LeakSanitizer claim. Output/resource bounds,
PTY session/terminal setup and cleanup remain those in the existing CSH-050/057/058
records. No reference-shell outcome supplies the oracle.

## Remaining acceptance work

CSH-050's platform criterion stays unchecked. The earlier foreground-resume
status defect is integrated, but the separate five-second public PTY timeout
and 60-second retention timeout remain owned by CSH-057. Its active investigation
is independent of this partial-delivery correction. Fresh passing observations
here do not diagnose or erase those intermittent failures. No uncommitted
CSH-057 work is included in this revision.

The normal full runs retain their stock-host gaps (12 native timestamp cases,
nine Linux printf/kill cases), distinct from the passing opt-in qualified profile.
CSH-052/056 own that distinction; CSH-061 owns the wider host residuals. The
Linux container is unprivileged, so the two CSH-046 unequal-ID probes skip on
both hosts. CSH-053's unavailable encoding/pathname groups and CSH-042's
unavailable native translated ENOENT diagnostic retain their recorded reasons
and owners. None is a new jobs/signal skip or an inapplicability claim. The
new fourteen cases have no skips.

Native Linux outside Docker and a fresh full sanitizer suite are not run locally
in this follow-up. CI owns native Linux coverage. Parent requirements remain
implemented subsets and CSH-012 stays closed; the ticket is reviewable but cannot
honestly be marked complete while the named timeout evidence remains unresolved.
