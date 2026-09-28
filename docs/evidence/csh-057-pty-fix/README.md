# CSH-057 foreground resume race

Follow-up to [CSH-057](../../tickets/CSH-057-job-lifecycle-boundaries.md), based on
`b1b6b15`. Runtime and regression revision: `33d32a7`. Branch:
`fix/CSH-057-pty-resume`. Later evidence/documentation commits do not alter
runtime/test inputs. The final source digest is
`1a4b1aec9cc11fbbdf22048ab7ecc99e590343f6258cfa9ea33d50ca571f104d`,
shared by normal native and both sanitizer identities. The original [CSH-057 record](../csh-057/README.md) remains
historical evidence, including its separate Linux runtime timeout observations.

## Failure and cause

[Hosted macOS job 108604370895](https://github.com/melliott18/cshell/actions/runs/36313720185/job/108604370895)
failed the 32-cycle `repeated background resumes preserve prompt and terminal`
case: expected status 130 and 7,280 output bytes, received status 1 and 7,526
bytes. The hosted logger retained only the output prefix, so that log alone
cannot identify the extra text or the failing syscall. Its full job log is
retained as `hosted-macos-failure.log.gz`.

Unmodified current-main normal and sanitizer builds each passed 100 local
repetitions. Diagnostic sanitizer builds using current jobs.c and the original
CSH-057 jobs.c each also passed 100. These timing-dependent successes did not
resolve the failure.

The deterministic diagnostic holds the parent between `fg`'s command display
and SIGCONT. The ordinary PTY runner sends Ctrl-C, and `waitid(WEXITED|WNOWAIT)`
confirms the owned child's exit without consuming it. The real Darwin
`kill(-pgid, SIGCONT)` then returns **EPERM**, not the ESRCH previously accepted
by `continue_job`. Every forced cycle produced `cannot foreground job`, an
extra termination notification, and the final status 1. The original failure's
signature is reproduced with a real terminal signal and real kernel error;
no errno is fabricated in this diagnostic. `diagnostic-window.patch.gz` and
`exit-before-continue.log.gz` retain the instrumentation and complete output.

`continue_job` now polls owned child statuses after a rejected continuation.
It accepts the rejection only when the entire job has completed. Foreground
completion then returns the recorded status and consumes the known ID. If a
job is still live or stopped, the original error is preserved. No blanket
EPERM exception or timing delay is introduced.

## Regression and bounds

The existing `terminal_job_faults` in `tests/execute_faults.c`, reached through
`make test-jobs-pty` and `make test-pty`, now checks four scenarios:

- Real kernel SIGCONT result after a synchronized SIGINT exit.
- Forced EPERM and ESRCH after that same confirmed exit, covering both error
  paths on both platforms.
- Forced EPERM for a confirmed stopped, live child; rejection and stopped
  ownership must remain intact until explicit cancellation.

Success requires status 130, no suspension flag, consumed numeric identity
(subsequent wait 127), shell terminal ownership and unchanged terminal flags.
Every scenario checks descriptor/allocation balance and ECHILD after teardown.
The readiness pipe and WNOWAIT observations establish state; elapsed time is
never the synchronization oracle. Existing five-second PTY and ten-second
module alarm limits are unchanged. The original public fixture's bytes,
foreground predicates, 32 cycles and five-second deadline are unchanged.

The new module regression failed before the production fix (`fault-before`)
and passes after it. The same forced scheduling window in the public sanitizer
PTY case passes all 32 cycles after the fix (`fixed-window.patch.gz`,
`exit-before-continue-fixed`). The diagnostic patches are evidence only; the
shipping runtime has no scheduling interposition.

## Validation

Native host: macOS 14.8.7 arm64, Apple clang 15. Linux: Debian 12 arm64 Docker,
GCC 12.2 and glibc 2.36. `identity.py` captures source digests, binaries, helpers,
generated suites, flags and system versions; JSON identities and the artifact
inventory retain their hashes. Linux results are container checks, not a
native Linux host claim. No CSH-057 capability skips are accepted.

| Check | Result |
| --- | --- |
| Native `make -j4 test-jobs test-pty test-harness` | Pass: 148 jobs runtime cases, 30 job PTY cases, 30 runtime PTY cases, lifecycle/API/fault suites, 73 harness self-tests. The final stopped-child refinement also passes `make -j4 test-jobs test-pty`. |
| Native ASan/UBSan `make -j4 test-jobs test-pty` | Pass with the final regression. |
| Docker `make -j2 test-jobs test-pty test-harness` | Pass with the final regression and the same case counts. |
| Docker ASan/UBSan `make -j2 test-jobs test-pty` | Pass with the final regression; no sanitizer diagnostics. |
| Exact public 32-cycle repetitions | 100/100 serial native normal and 100/100 serial native ASan/UBSan cases pass: 6,400 resume cycles total, unchanged bytes and limits. |

Sanitizer flags:

```text
CFLAGS=-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer
LDFLAGS=-fsanitize=address,undefined
MallocNanoZone=0 (macOS)
ASAN_OPTIONS=halt_on_error=1, UBSAN_OPTIONS=halt_on_error=1 (Docker caller)
```

The smoke harness uses its controlled environment and sanitizer defaults;
it preserves MallocNanoZone but does not inherit arbitrary sanitizer options.
LeakSanitizer is not disabled in the Linux smoke fixtures.

Reproduce after building the appropriate normal or sanitizer executable:

```sh
make test-jobs test-pty test-harness
python3 docs/evidence/csh-057-pty-fix/repeat_pty.py
```

## Retained failed attempts

Logs and diagnostic patches are compressed with `.gz` without changing their contents.

| Record | Disposition |
| --- | --- |
| `fault-before` | Deterministic regression fails the status-130 assertion before the runtime fix. |
| `exit-before-continue` | Diagnostic forces the real Darwin EPERM race in all 32 public cycles; status 1 and extra notifications. |
| `final-fault`, `native-sanitizer-fixed` | An intermediate regression revision did not retry its readiness-pipe read after the child's stop generated SIGCHLD. Fixed that fixture's EINTR handling; final native and Linux checks retain the original limits. |
| `native-repeat-final` | During concurrent native sanitizer and Docker work, round 76 exceeded the whole-case five-second budget at cycle 29. All 8,595 captured bytes exactly match the expected prefix; no foregrounding diagnostic occurred. It remains a failed loaded run under the CSH-040 transport/load boundary, separate from the diagnosed EPERM defect. Later serial repetitions do not erase it. |

The follow-up validates the changed jobs path and existing terminal/harness
suites. It does not claim a new full general-runtime conformance sweep or
erase earlier unrelated timeout records.
