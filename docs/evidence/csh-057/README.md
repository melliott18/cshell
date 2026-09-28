# CSH-057 job lifecycle validation

Final source/test revision: `adb9e5c103f7183836eb5f8f19ba180b134a004a`;
branch `test/CSH-057-job-lifecycle-boundaries`, based on `a26053c`.
Runtime changes are in `ce76d1c`; `3045124` fixes a test observation race,
and `adb9e5c` fixes only the new fixture's state teardown. Normal full suites
ran at `3045124`; both changed fixture suites are rerun at `adb9e5c` on both hosts.
Later commits contain documentation and evidence only. The final source digest
(Makefile, Dockerfile, src, include, tests, tools; no Python caches) is
`d284b8e7eb5c9c08281af0bff25a1cd590ab8d3e32a04f097c4ef688843f06d8`.
The full-suite `3045124` digest is
`406ceab7f5771ef1e61e037444921625347b1ec8fdad5f6dcac525b09c9f0696`.
The `*-final-fixture-identity.json` records distinguish final fixture validation
from the preceding normal full-suite identities.

The [exact requirement map](../../jobs-signals-evidence.md#csh-057) owns the
normative interpretation, assertions and limitations for EXEC-009, JOB-001–003,
and U-032. Full requirement families remain implemented subsets. This is not a
POSIX conformance declaration. Host-scale CHILD_MAX exhaustion is not claimed:
the fixture interposes 32 and unknown (-1, fallback 256), checks the query and
uses real bounded sequential children. Final native host CHILD_MAX is 10666;
the Docker host query is -1, so its production default is 256.

## Final results

| Environment / command | Result |
| --- | --- |
| Native macOS 14.8.7 arm64, `make test test-pty test-harness` | Exit 0. 3,113 runtime cases; 148 jobs runtime cases; 30 job PTY and 30 runtime PTY cases; retention and notification API suites; existing fault suites; 71 harness self-tests pass. |
| Debian 12 arm64 Docker, `make -j2 test test-pty && make test-harness` | Exit 0. Same public runtime/job/terminal and module assertions; 71 harness self-tests pass. |
| Native ASan/UBSan, `make test test-pty` with flags below | Exit 0 at `3045124`; all 3,113 runtime cases, both 30-case terminal suites and module/fault assertions pass. The final fixture teardown also passes both focused suites at `adb9e5c`. |
| Docker ASan/UBSan, full target prerequisites/PTY checks plus four runtime batches | Module/fault assertions, 148 jobs runtime cases and both 30-case PTY suites pass. Runtime batches exercise all 3,113 cases: 3,109 pass, four time out at 5 seconds. The exact four cases then pass three serial reruns (12/12), unchanged limits. This is not a clean full sanitizer invocation; see the retained failure below. |
| Loaded notification fixture regression, six concurrent runners × 15 rounds | 90/90 pass after its launch-barrier correction; 1,260 individual notify/state scenarios. |

Native compiler is Apple clang 15; Linux compiler is GCC 12.2 / glibc 2.36.
Identities include UTC timestamp, source revision/digest, binary path/realpath
and SHA-256, helper and generated-suite hashes, flags, compiler, OS/system library,
Python, host CHILD_MAX, and relevant environment. Docker image/engine metadata
are in `docker-image.json` and `docker-engine.txt`; the base is the repository's
Debian bookworm-slim image. Linux evidence here is Docker, not a native Linux host.

The stock-host audits retain **12 native** timestamp-test gaps and **9 Linux**
printf/kill gaps, owned by CSH-052/056 and their qualified-host profile. They are
not jobs failures or new allowances. Capability skips remain owned as follows:
CSH-046 unequal UID/GID probes require a root Linux run (both normal runs use
unprivileged users); CSH-053 Shift-JIS/Big5/GBK pathname/locale capabilities are
unavailable on the tested hosts, plus GB18030 raw pathnames on macOS; CSH-042
translated ENOENT diagnostics are unavailable on this macOS installation.
No CSH-057 case skips on either host. No reference shell supplies an oracle.

## Reproduction and bounds

```sh
make test-jobs test-jobs-pty test-harness
make test test-pty test-harness
# The same source snapshot, with the repository Dockerfile:
docker build -t cshell-csh057:final .
docker run --rm --init cshell-csh057:final sh -c \
  'make -j2 test test-pty && make test-harness'
```

Sanitizer flags on both hosts:

```text
CFLAGS=-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer
LDFLAGS=-fsanitize=address,undefined
ASAN_OPTIONS=halt_on_error=1
UBSAN_OPTIONS=halt_on_error=1
MallocNanoZone=0 (native macOS)
```

Native sanitizer work uses an exported copy of the final source in
`/tmp/csh057-sanitizer.shWsbm`, keeping the worktree's normal executable intact.
Linux sanitizer work initially runs `make clean` inside a fresh container before
rebuilding. A snapshot retains that compiled sanitizer build; the corrected
full run mounts the final fixture source read-only and rebuilds it. The source
digest validates the mounted snapshot against the final repository revision.
The final Linux runtime sweep is also split into four independent harnesses by
`run_runtime_batches.py`. It preserves each generated fixture verbatim, checks
unique names and complete coverage, and retains the default per-case timeout
and output limits. `docker-sanitizer-runtime-batches.json` records the original
suite digest, all case names, batch digests, commands and exit statuses; the
four `docker-sanitizer-runtime-*.log.gz` files contain individual results.
This changes test scheduling only, not runtime or fixture semantics. The original
sequential runtime recipe was stopped (container exit 143) after the complete
batch sweep and serial timeout rechecks; its preceding prerequisites and PTY
results are retained in `docker-sanitizer-final.log.gz`. No failure is removed
from the batch totals or relabeled as a pass. `docker-sanitizer-results.json`
records this composition and the interruption explicitly.

The host-utility audit disables Linux LeakSanitizer for its own subprocesses;
that limitation does not apply to the normal smoke module/PTY suites. Their
Linux LeakSanitizer caught the new fixture's state leak described below. The
controlled smoke environment keeps MallocNanoZone but uses sanitizer defaults
rather than inheriting arbitrary ASAN_OPTIONS/UBSAN_OPTIONS from the caller.

The shared runner supplies controlled C locale/PATH, temporary HOME/TMPDIR and
working directories, no supplied TZ, umask 077, output/resource limits and bounded descendant
cleanup. PTYs are controlling sessions, 24×80, canonical input, ISIG, no echo,
exact LF output. Public job PTY cases retain the five-second case limit.
Retention has five-second progress alarms and a 60-second outer limit;
notification has ten-second phase alarms, a five-second foreground-child alarm,
and a 30-second outer limit. All final children are consumed/cancelled, followed
by an ECHILD assertion. The PTY runner independently cleans all session groups.

ESRCH proves a completed background child was reaped; WSTOPPED/WNOWAIT proves
stopping without consuming the job manager's status; nonblocking reads prove
absence of early bytes. A pipe barrier proves process-group/terminal handoff
precedes foreground test-child progress. Compound tests wait for the helper's
CONT-handler message before another stop. Polling delays throttle predicates;
elapsed time never proves correct state. Negative timeout runs are failures,
not accepted alternative results.

## Retained failures and development records

All log filenames below are stored compressed with `.gz`. Earlier failures
remain failures even where later runs pass. Intermediate logs were recorded
during uncommitted development and do not all have per-run binary hashes; the
final identities are the authoritative cross-platform execution records.

| Log / observation | Disposition and owner |
| --- | --- |
| `baseline-retention.log` | Production evicted the oldest saved ID while registering a foreground utility at capacity. Fixed by limiting eviction to asynchronous launches. CSH-057. |
| `baseline-live-retention.log` | Old running/stopped jobs reduced space for newer completed results. Fixed by retaining them in addition to completed-result capacity. CSH-057. |
| `baseline-startup.log` | Controlling session leader looped when another group owned its terminal, bounded timeout and cleanup. Fixed by claiming the leader's terminal before nested-shell TTIN handling. CSH-057. |
| `baseline-notifications.log` | Exact normal/signal notification bytes differed; initial assertions were captured with stderr, so this run does not identify a unique failed assertion. Revised fixture preserves diagnostics separately. Format fixes and later exact cases are retained. CSH-057. |
| `baseline-notification-timing.log` | After format fixes, the foreground observer could not receive an immediate notify completion; bounded failure. Fixed by notifying while the foreground wait polls. CSH-057. |
| `baseline-compound.log` | Trace included the forbidden post-stop command. The initial expected job number also omitted the earlier external echo job. Corrected ID to 2, and fixed executor suspension propagation so pending commands are discarded. CSH-057. |
| `native-full.log`, `notification-loaded.log` | Initial full run failed inside the new notification fixture. Preserved diagnostics and six concurrent runners reproduced three `setpgid` ESRCH failures: its foreground test child exited before group assignment. Added a launch barrier; `notification-loaded-fixed.log` passes 90/90. CSH-057 test defect, not a production barrier defect. |
| `native-loaded-failure.log` | Concurrent full validation hit a five-second macOS ps snapshot timeout in the stock stty PTY check, a two-second ps timeout checking watchdog cleanup, and two ten-second harness subprocess timeouts. No shell transcript/status mismatch was established. The subsequent serial full run passes; the loaded failures remain recorded under the CSH-040/054 transport/load boundary. |
| `docker-sanitizer.log` | LeakSanitizer found state allocations leaked by the new fixture: context destruction clears its borrowed state pointer, so the following state destroy saw NULL. Fixed by saving the owner before context destruction. The already-failed container was stopped after preserving its identity; final sanitizer rerun uses the corrected fixture. CSH-057. |
| `docker-sanitizer-runtime-{0,1,2,3}.log` | Four five-second timeouts: `control: continue outside context (file)`, `control: break invalid 1 2 (file)`, `control: break outside context (stdin)`, and `control: break invalid 999999999999999999999999999 (stdin)`. Each failed batch exits 1; 3,109 other cases pass, with no sanitizer diagnostic. All four exact cases pass three consecutive serial reruns in `docker-sanitizer-timeouts-serial.log`, without changing the five-second budget or source. The cause is not established; concurrent host/load effects are an inference, not proof. Retained under the CSH-040/054 bounded transport/load boundary. Normal full validation and native sanitizer validation pass; no clean full Linux sanitizer invocation is claimed. |
| `docker-retention-race.log` | The executor could already have reaped a fast completed child before the fixture's WNOWAIT observation (ECHILD). The fixture now accepts that observation while still requiring the exact retained numeric wait result. CSH-057. Also records a failed identity invocation because the image does not copy Dockerfile; final identity collection mounts it read-only. |

Other `build-*`, `*-iteration-*`, `notification-*`, `retention-fixed`,
`builtin-child-stop`, `suspension-status`, `native-focused`, and `docker-full`
logs preserve intermediate build/focused/full successes. `native-final`,
`docker-final`, and the sanitizer logs identify final runs; do not substitute an
intermediate success for a later failing revision. `native-loaded-identity.json`
identifies the earlier `ce76d1c` loaded attempt. `artifacts.json` inventories the
retained artifacts with hashes.
