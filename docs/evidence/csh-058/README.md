# CSH-058 signal edge evidence

The [assertion map](../../jobs-signals-evidence.md#csh-058) identifies every
case family, normative source, policy and limitation. Production changes and
the original matrix are commit `74bcc04e67a6b42503b86d52828a00aae903c50b`, based
on `a26053cd404ef18f8d2013eab5e5eab818aa26f0`. Commit `0dbf8d6` changes only
fixture watchdog/environment handling, CI budgets/settings, and documentation.
The final focused runs exercise those fixture changes; the earlier full runs
exercise identical production code. Neither revision claims POSIX conformance.

## Reproduced defects

`baseline.py` uses the final delivery probe against the pre-ticket production
source, built in a separate copy. `baseline-native.log.gz` and
`baseline-docker.log.gz` reproduce all four failures. Inputs, expected and actual
stdout/stderr/status are retained as JSON lines; no failure is an expected-success
regression oracle. The final matrix asserts their corrected behavior.

| Defect | Before | After |
| --- | --- | --- |
| Interactive TERM ignore followed by child reset | Exec child remains ignored and survives TERM | Child has default disposition and terminates by TERM |
| Ignored entry CHLD in a general substitution | Output arrives with `cannot wait for command: No child processes` | Output and collected child status without a diagnostic |
| Caught INT in a monitored background compound | Child receives the unmonitored implicit ignore | Child receives default INT and terminates by INT |
| Parent TTOU action while reclaiming terminal | Foreground wait fails with EIO and status 1 | Terminal ownership/modes restored, exact output, status 0 |

The CHLD fix prevents kernel auto-reaping while a shell still owns children;
macOS also needs SA_NOCLDWAIT cleared. Exec restores the logical ignore. Forked
ignored trap entries reset to child baselines rather than parent interactive
handlers/policy. Monitored background commands do not request unmonitored
INT/QUIT ignores. Terminal ownership/mode operations block TTOU temporarily,
without replacing user trap handlers.

## Final validation

| Record | Command / result |
| --- | --- |
| `native-final.log.gz` | `make -j4 test test-pty test-harness`: pass, including 3,113 runtime cases, 2,464 new edge cases, 30 runtime PTY + 17 jobs PTY + one fault PTY, legacy signal/entry-ignore/blocked-wait cases, APIs/fault checks, and 71 harness self-tests. |
| `docker-final.log.gz` | In the retained full-run image, `make -j2 test test-pty && make test-harness`: pass; 3,113 runtime cases, 2,495 new edges, same PTY/harness counts. |
| `native-fixture-final.log.gz` | Final fixture revision: `make -j4 test-signal-edges`: pass, 2,464 cases. |
| `docker-fixture-final.log.gz` | Final fixture revision, Docker root: `make -j2 test-signal-edges`: pass, 2,495 cases. |
| `sanitizer-final.log.gz` | Native instrumented source copy: `make -j2 test-traps test-jobs test-jobs-pty test-control`: running; no completed native sanitizer pass claimed yet. |
| `docker-sanitizer-final.log.gz` | Final fixture revision, Docker root, ASan/UBSan: `make -j2 test-signal-edges`: pass, 2,495 cases, no sanitizer diagnostics. |

Native is macOS 14.8.7 (23J520), arm64, Apple Clang 15.0.0, Python 3.12.2.
Docker is Debian bookworm Linux/aarch64, GCC 12.2.0, glibc 2.36, Python 3.11.
Identity JSON records exact versions, UTC collection times, source manifests,
compiler flags, binary/helper hashes and relevant environment. Full-run identities
are distinct from final-fixture identities. The Docker full-run identity rebuilds
helpers in the same immutable image with identical source/flags; its runtime
binary is the image binary used in that run. `docker-images.json` retains image IDs.
These are native macOS and Linux-container results, not bare-metal Linux or a
claim about every host. No new signal case is capability-skipped. Existing
host-utility known gaps and invocation/locale capability skips retain their
existing owners; they are not new signal failures.

## Bounds and interpretation

Each signal case has a five-second outer deadline. The helper's internal
watchdog is four seconds and is cancelled before launching the public runtime.
All cases run in owned sessions; PTYs use the existing bounded session cleanup.
The stop-delivery probe's child has a separate process group with a living
parent in the same session, so default terminal stops cannot be mistaken for
ignores because of orphaned-group suppression. Group-delivery targets only the
fixture's own session/group and independently acknowledges both recipients.
Permission tests interpose jobs.c's syscall on synthetic operands and deliver
the successful follow-up signal only to themselves. They make no claim about
credential enforcement by the host kernel.

Public waits hold a child on a FIFO and write a builtin-only readiness marker.
Linux requires a sigsuspend wchan; macOS requires interruptible sleep after that
marker. No external command or other blocking operation occurs on the parent
path between marker and wait. Exact trap/interrupted/second/third wait results
are required. The two-signal variant confirms STOP, queues both signals and
resumes with CONT. Poll delays are pacing only, never evidence of blocking.

Runtime/API/group cases use `bounded_run` (2 MiB output bound); PTY cases use
65,536 bytes, canonical ISIG/no-echo/LF terminals, and five-second case bounds
with separately bounded cleanup. Public-wait output is file-backed under the
runner's CPU/file/descriptor limits. Environment is PATH=os.defpath, LANG=C,
LC_ALL=C, per-suite temporary HOME/TMPDIR, no TZ override (host default), and umask 077 in
children. The final driver forwards only ASAN_OPTIONS, UBSAN_OPTIONS and
MallocNanoZone in addition to that environment. Signal discovery queries
1..1023, verifies NSIG fits, and asserts every exposed catchable condition;
these hosts expose none beyond CSH_TRAP_LIMIT. Numeric conditions are extensions;
KILL/STOP installation is a robustness contract outside POSIX guarantees.

## Earlier failures retained

`native-full.log.gz`, `docker-full.log.gz`, and `sanitizer-full.log.gz` are initial,
concurrently loaded runs, not passes. Docker also reproduced the caught-TTOU
shell defect before its fix. Native PTY cleanup exceeded its existing five-second
ps snapshot budget. Docker's 0.3-second `test_terminal_eof_does_not_hide_a_running_candidate`
expired before the helper wrote its setup marker. Native sanitizer jobs cleanup
exceeded its two-second ps observation bound; the control `case fallthrough skips
patterns (stdin)` case timed out at five seconds and could not reap its leader
within the separate second. The initial native sanitizer portability phase
subsequently passed all 2,206 cases with five pre-existing capability groups skipped.
These observations do not identify a new shell semantic defect. Final native and
Docker full runs pass their original limits; the focused native sanitizer run
rechecks jobs, control and signal/terminal behavior. No timeout was enlarged to
turn an individual failure into success, and arbitrary-load reliability is not
claimed.

`docker-sanitizer.log.gz` is the initial leak-enabled instrumented attempt. Its
launcher alarm propagated through exec and terminated the shell after four
seconds despite correct completed probe output. A standalone diagnostic took
about two seconds with leak detection and about 0.03 seconds without it. The
fixture correction cancels the launcher alarm and forwards sanitizer options.
The obsolete container run was stopped after this failure, so its unfinished
other targets are not passes. The final Docker run uses explicit
`ASAN_OPTIONS=halt_on_error=1:detect_leaks=0` and
`UBSAN_OPTIONS=halt_on_error=1`. This is ASan/UBSan evidence, with no Linux
LeakSanitizer claim. The native instrumented run uses its platform defaults.

## Reproduction

```sh
make -j4 test test-pty test-harness
make -j4 test-signal-edges

docker build -t cshell-csh058:final .
docker run --rm --init cshell-csh058:final sh -c \
  'make -j2 test test-pty && make test-harness'

# Use a separate source/build copy for instrumentation.
ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
make -j2 test-traps test-jobs test-jobs-pty test-control CC=clang \
  CFLAGS='-Wall -Wextra -Wpedantic -Wshadow -Werror -std=c99 -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```
