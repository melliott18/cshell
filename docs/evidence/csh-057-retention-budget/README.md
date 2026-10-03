# CSH-057: observed aggregate retention budget exhaustion

The 2026-09-30 review finds direct hosted evidence that the 60-second retention
budget expires during continuing, short fork/run/reap operations. This supports
a correction to the fixture's aggregate budget. It does not establish an
unsolvable shell bug, a job-manager deadlock, or the reason one hosted machine
takes longer than another.

## Original observations

PR [#167](https://github.com/melliott18/cshell/pull/167) added the phase, fork,
alarm-state and bounded stack observers before this review. Its
[failed macOS job](https://github.com/melliott18/cshell/actions/runs/36662308140/job/109719513272)
ran checkout `bc74783bde46cd3b5783be03c778036f7132d460`. The
[passing peer job](https://github.com/melliott18/cshell/actions/runs/36662312181/job/109719525200)
ran synthetic merge `5e8bb85d3f2ba8dd65dc8503e3b37a4ffb4a93e9`.
The retained GitHub comparison verifies the same tree,
`74bb7a54bab992e8c055f6f69a3ae90921594eeb`, with no changed files.
GitHub job metadata identifies the PR head for both jobs; each artifact's
`metadata.json` records its actual `GITHUB_SHA` checkout separately.

Both used the existing 619-child case, exact stdout/status oracle, five-second
fill alarms, 60-second outer limit, and one-second cleanup budgets. Their
metadata records Darwin 24.6.0 arm64; the failed stack report identifies macOS
15.7.9 / 24G830 and the Xcode 16.4 ASan runtime. The controlled environment
forwards `MallocNanoZone=0`; it does not inherit CI's `ASAN_OPTIONS` or
`UBSAN_OPTIONS`. These facts are retained, not changed for this comparison.

| Measured observation | Failed hosted case | Passing peer |
| --- | ---: | ---: |
| Capture duration | 60.057027 s | 35.123378 s |
| Successful parent forks | 578 | 619 |
| Completed capacity-fill children | 573 of 576 | 576 of 576 |
| Completed run intervals | 574 | 609 |
| Run elapsed sum / maximum | 30.509023 / 0.137856 s | 19.828561 / 0.084438 s |
| Completed reap intervals | 574 | 611 |
| Reap elapsed sum / maximum | 28.993772 / 0.152365 s | 14.546919 / 0.064316 s |
| Parent fork elapsed sum / maximum | 30.367362 / 0.137022 s | 19.816514 / 0.083845 s |
| Completed numeric-wait elapsed sum | 0.019158 s | 0.047994 s |

The run and reap intervals are sequential and non-overlapping; the analyzer
checks that relationship. Their failed-run sum is **59.502795 seconds**.
Fork intervals are nested in run, foreground, overflow or helper work and
must not be added to that sum. These are elapsed intervals around operations,
not CPU times or a measurement of kernel execution alone; scheduling and
observer overhead are included.

The failed trace contains 4,698 valid, complete records with no truncation or
diagnostic errors. It records fallback round 2, iteration 253 completing its
reap at 59.855967 seconds after the fixture's first record. Iteration 254 then
successfully forks and returns from execution, entering its reap at 59.904408
seconds after that first record. Relative to `capture-start.json`, those times
are **59.949104** and **59.997545 seconds**. The capture-start observation is
immediately before `smoke.run_case`, including setup; it is not the exact
internal `smoke.capture` deadline origin. No root event gap exceeds 0.153 seconds.
The final operation is unfinished because the outer runner kills the case;
its eventual outcome cannot be recovered from the trace.

The last stdout checkpoint reports only 512 completed fills, at fallback
round 2 / completed 192. The runner's 6.494-second stdout gap therefore does
**not** mean execution stopped: the side channel records 61 more completed
fills and a further launch after that checkpoint. This is the distinction the
earlier progress-only logs could not establish.

All observed SIGALRM records show an unblocked mask, no pending alarm and
default disposition; none of the signal/timer queries fails. Each fill's
start records a positive timer at most five seconds, and the final reap starts
with 4.951594 seconds remaining. The trace therefore establishes normal alarm
state at the observation points and aggregate exhaustion during short
operations. It cannot prove signal state between every observation or predict
the final child's behavior after the outer kill.

## Stack and observer limitations

The failed run's watcher triggers on case age at 57.040311 seconds, while its
oldest observed operation is only 0.024305 seconds old. Its single root sample
finishes in 1.613566 seconds. The report contains 317 of 355 sampled stacks in
`sigsuspend`, 15 in the kernel fork call, and other short registry/observer work.
The trace shows further children completing during and after this sample.
These are samples across progressing waits, not evidence of a single stuck
wait. There is **no child stack sample** in this failed artifact: only the
root attempt is recorded. The record does not say why no child was selected,
and it does not expose the final child's stack at the outer deadline.

The observer records timestamps, queries signals/timers, writes the trace, and
samples the root. That work can perturb scheduling and contributes to elapsed
time. The failed trace's progress and bounded intervals remain observations
of this instrumented run; it is not an uninstrumented throughput benchmark.
The peer finishes before sampling and has no stack attempts. Its 619 parent
forks produce 618 child-entry records: the missing record belongs to the final
held formatting helper, which may be cancelled before entering the observer.
No claim of 619 observed child entries is made. Its exact fixture assertions,
final ECHILD check, and successful bounded cleanup all pass.

Both complete uploaded artifacts also include intentional stalled-child
controls. They correctly fail with SIGALRM for the normal mask and with the
outer deadline for an intentionally blocked alarm. Their diagnostic verdicts
are PASS; the contained fixture failures are intentional and preserved. Those
controls are not the actual retention timeout. There are no diagnostic or
watcher-cleanup failures in either actual retention case.

## Corrective budget decision and remaining scope

A **120-second aggregate budget**, retaining the original five-second alarms,
is supported by this observed exhaustion. It gives the complete 619-child
workload additional aggregate headroom while keeping individual operations,
all exact assertions, capacities 32 and fallback 256, both rounds on each
manager, saved/unsaved IDs, foreground preservation, oldest eviction, live
records, formatting and descendant cleanup intact. This is a test-budget
repair; it is not a shell signal-handling change or a claim that the hosted
fork cost has been reduced. It also avoids splitting the fixture's process
and manager interactions to obtain several independent outer budgets.

The factor of two is an explicit bounded headroom choice, not a derived upper
bound on arbitrary hosted scheduling. Any future outer timeout remains a
failure. A blocked/ignored alarm, long individual operation, sanitizer finding,
status/ownership error or cleanup failure also remains a failure. Changing
the aggregate budget does not turn either retained failed run into a pass.
The tradeoff is that the outer guard now detects excessive total cost, or a
stall whose phase alarm is itself disabled, after at most 120 rather than 60
seconds. The ordinary five-second phase-alarm failure path is unchanged.

The earlier empty-output historical failure and the 2026-09-29 progress-only
recurrence retain their original evidence and limitations. This new trace
demonstrates one specific timeout mechanism; it does **not** reconstruct the
unobserved internal state of those older runs. The precise reason the failed
machine's fork/reap intervals are slower than the identical-tree peer remains
unconfirmed. There is no evidence that the issue is unsolvable and no basis
for closing it as an accepted runtime bug on that premise.

## Fix validation

The change consists of the JSON case budget and diagnostic runner default
moving from 60 to 120 seconds, with case-age sampling moving from 57 to 117
seconds. The runtime and C lifecycle fixture are unchanged. The branch is
`fix/CSH-057-retention-budget`, based on diagnostic PR #167 at `bc74783`.
The [ticket](../../tickets/CSH-057-job-lifecycle-boundaries.md) stays at review:
the separate terminal-fault timeout from that PR remains undispositioned.
This test-budget change does not resolve that potential runtime or harness bug.

| Validation on the repair | Result |
| --- | --- |
| Native macOS normal retention | Exact oracle passed in 0.420 and 0.640 s |
| Native macOS ASan/UBSan retention | Exact oracle passed in 21.530 s |
| Native harness / jobs / PTY | 94 harness tests, 148 jobs cases, 30 public jobs PTY cases, 14 lifecycle PTY cases, notifications, terminal-fault fixture and ownership/watchdog checks passed |
| Native normal and sanitizer stalled-child controls | Default alarm produces SIGALRM around five seconds; explicitly blocked alarm reaches its six-second control deadline; all four root/child samples per build captured and cleanup checks pass |
| Linux/Docker normal | Retention in 0.364 s; same harness/jobs/PTY checks and failure controls passed |
| Linux/Docker ASan/UBSan | Retention in 2.277 s and failure controls passed; stack sampling remains explicitly unavailable on Linux |
| Deliberately slowed sanitizer fixture, old bound | Timeout retained at 60.043 s, with continued short-operation progress |
| Same slowed binary, new bound | All 619 children and the exact production oracle passed in **90.578 s** |

The controlled workload uses [controlled-delay.patch](controlled-delay.patch)
only in a temporary checkout. It inserts a 100 ms delay before each real fork;
619 such calls need at least 61.9 seconds of aggregate delay while each phase
still has the original five-second alarm. This is injected cumulative cost,
not a simulation of a hung child, and it does not claim to reproduce the
unmeasured reason for hosted fork cost. [check_budget.py](check_budget.py)
checks both outcomes, the unchanged oracle, all 619 successful parent forks,
default/unblocked alarm observations, short root-event gaps and progress near
the deadline. The same binary fails under the former bound and passes beyond
60 seconds under the corrected bound. The delay patch is **not** applied to
shipping test or runtime sources. The deliberate failure is retained unchanged.

[Native validation metadata](native-validation.json) and
[native artifacts](native-validation.tar.gz) retain source/binary identities,
commands, normal/sanitizer traces, exact outcomes, controls and the delayed
before/after results. Native compilation used Apple Clang 15, macOS 14.8.7
arm64 and Python 3.12.2. The extra trace-progress assertions were added to the
control checker during its run and then verified against both saved traces;
no additional fixture run is claimed for those assertions.
[Linux metadata](linux-validation.json) and
[Linux artifacts](linux-validation.tar.gz) preserve the independent container
checks. The Linux sanitizer probe used GCC with disclosed `-fno-pie/-no-pie`
flags as a conservative probe choice; no PIE failure was observed, and that
probe is not claimed to use identical hosted flags. Sanitizers stayed enabled.
No new complete `make test` result or fixed-branch hosted CI pass is claimed.

The investigation also ruled out copied-job disposal as a useful runtime fix:
615 instrumented `csh_jobs_after_fork` calls totaled 0.076602 s, maximum
0.000520 s. [That isolated profile](child-disposal-profile.tar.gz) retains its
source, temporary patch and exact-oracle results. The separate earlier local
[baseline](local-baseline.json) passed in 26.301 s while sampled; its sample is
in the native archive. These are observed local costs, not controlled hosted
throughput comparisons, and no speculative runtime optimization is shipped.

To reproduce the controlled budget check, export this revision to a temporary
checkout, apply `controlled-delay.patch` there, and build `jobs_lifecycle` with
the sanitizer flags in `native-validation.json`. From the original checkout:

```sh
MallocNanoZone=0 python3 docs/evidence/csh-057-retention-budget/check_budget.py \
  /absolute/path/to/delayed/build/tests/jobs_lifecycle /tmp/csh057-budget-check
```

## Offline reproduction and provenance

From the repository root:

```sh
python3 docs/evidence/csh-057-retention-budget/analyze.py > /tmp/csh057-budget-analysis.json
cmp /tmp/csh057-budget-analysis.json docs/evidence/csh-057-retention-budget/analysis.json
```

The analyzer uses only the retained archives, job records and comparison
response. It executes no fixture, network request, or archived program, and
does not extract archives onto the filesystem. It verifies archive hashes,
trace validity, phase pairing, non-overlap, alarm states, expected completed
work, outcomes, diagnostic controls and matching source trees.

`hosted-failed.tar.gz` and `hosted-peer.tar.gz` preserve every original file
from their uploaded artifacts, including checks, stack reports and watcher
logs. Their deterministic archive packaging does not alter member contents.
`provenance.json` identifies artifact names, runs, jobs and archive hashes;
`analysis.json` records every member's SHA-256 together with computed timings.
`hosted-*-job.json` and `hosted-comparison.json` preserve the read-only GitHub
API responses used for source and job attribution. Original artifact paths
inside their JSON remain the hosted paths; they are historical data.
