# CSH-057 merged repair review and retention investigation

Reviewed `main` at `faf2e9525dfe2c2c2cba4598a1d63d49552fc1d7`, including
PR #121 merged as `87fdfe8`. No actionable correctness regression was found
in the three runtime repairs. This review changes the diagnostic worker
launcher and documentation only; the shell and production fixtures are unchanged.

## Runtime review

- The parent assigns every process group before releasing the existing launch
  barrier. Children reset dispositions and retain the launch mask until the
  barrier and descriptor setup finish.
- Both signal-aware job/read waits clear Darwin's deferred saved-mask state
  before restoring the actual caller mask. The zero-time `pselect` preserves
  errno; intentionally inherited masks are still restored.
- After a rejected continuation, the blocking wait is restricted to still-owned
  positive child PIDs with `getpgid` returning ESRCH. A live stopped child keeps
  the original error. The fully exited, departure/status-gap, and live-EPERM
  regressions distinguish these paths.

The full hosted integration run on this revision passed Ubuntu, Docker, and
[macOS normal and sanitizer checks](https://github.com/melliott18/cshell/actions/runs/36487917937/job/109149227930).
PR #121's push run also passed macOS; its duplicate PR macOS job was cancelled.
This review does not claim a new local full-suite run.

## Retention timing evidence

The historical [60-second failure](https://github.com/melliott18/cshell/actions/runs/36455644289/job/109041175577)
had empty, fully buffered stdout. Its original log remains in
[`../csh-057-timeouts/hosted-retention-timeout.log.gz`](../csh-057-timeouts/hosted-retention-timeout.log.gz).
The failing phase and last completed child cannot be recovered from that log.

| Hosted macOS run | Normal | ASan/UBSan |
| --- | ---: | ---: |
| Same source as historical failure, passing duplicate | 0.428 s | 40.556 s |
| PR #121 push | 0.664 s | 54.911 s |
| Merged `main` | 0.500 s | 41.413 s |

These are elapsed GitHub log timestamps between suite start and pass, including
runner overhead. [`hosted-results.json`](hosted-results.json) contains source
commits, exact timestamps and job URLs; the complete passing logs are compressed
alongside it. The 54.9-second pass leaves only about five seconds of margin under
the unchanged outer deadline.

The fixture launches 619 children: 576 capacity fills, two overflow children,
four foreground utilities, 33 live-retention fills, and four held helpers. It
resets a five-second alarm before each capacity/live launch. Cumulative work
can therefore exceed 60 seconds without any individual five-second wait.
Code inspection finds no SIGALRM mask/disposition changes on this path, but
the original runner's inherited alarm state was not recorded.

Local macOS 14.8.7 / Apple Clang 15 results, all with exact production output,
status and the unchanged 60-second deadline:

| Probe | Elapsed | Result |
| --- | ---: | --- |
| Unmodified sanitizer binary | 22.591 s | pass |
| Per-child run/reap timing | 28.769 s | pass |
| Additional parent fork timing | 32.846 s | pass |
| Diagnostic skip of completed-record waits | 32.465 s | pass |
| Unmodified binary with a two-second stack sample | 29.462 s | pass |

All 576 measured launch/reap pairs advanced. In the fork-timed run, 615 parent
`fork()` calls consumed 17.015 seconds; the held helpers' four direct forks were
not instrumented. Across the capacity fills, command execution took 16.735
seconds and reaping took 13.630 seconds. Fork time overlaps command execution
and must not be added to it. In that fork-timed run, the largest measured run
and reap intervals were 0.392 and 0.067 seconds respectively. The phase-only
probe's largest reap interval was 0.440 seconds.

The unmodified binary's sample observed 53 of 104 stacks in `sigsuspend` and
48 in the kernel `fork` call. These are observations of a progressing local
run, not stacks from the historical failure.

The registry does perform redundant scans: `csh_jobs_reap(wait=1)` calls
`wait_job` for completed records, and each call scans the registry again.
Skipping those calls did not materially reduce this probe's elapsed time.
That experiment is retained as `skip-complete.patch` and is **not** applied to
production. It is not a demonstrated explanation or repair for the timeout.

**Disposition:** cumulative process creation/child completion cost under
sanitizers is the leading hypothesis. The hosted passes and local measurements
support that hypothesis; they do not prove the historical cause or reproduce
its timeout. No new retention deadlock was demonstrated. The observation stays
unclassified under CSH-057; neither deadlines nor assertions are relaxed.
If it recurs, the merged flushed capacity/round/phase checkpoints and runner
last-output timing distinguish continued progress from an idle interval. Capture
the current child/parent stacks and alarm state before proposing another repair.
Passing reruns alone are not a closure criterion for that historical record.

## Diagnostic runner repair

The previous `diagnose_retention.py` used a `ThreadPoolExecutor` to call
`smoke.capture`, which uses Python `preexec_fn` for child resource limits.
That violates the runner's explicit single-threaded contract and can deadlock
before the case even starts. Hosted CI invokes `smoke.py` directly from a
single-threaded process, so this defect cannot explain the hosted failure.
The old concurrent probes completed successfully, but that did not make their
launch mechanism safe.

The diagnostic now uses a `ProcessPoolExecutor` with the explicit `spawn`
context. Each worker imports and calls the runner in its own single-threaded
process. CLI arguments, per-worker records, exact comparisons and limits are
preserved. As before, diagnostic case failures are recorded in each result's
`failures` array; callers must inspect those records, not just the launcher exit
status.

`check_spawn_runner.py` verifies two distinct single-threaded spawned workers,
two successful cases, and two intentional output mismatches using production
smoke capture. A file rendezvous establishes concurrent participation without
using elapsed delay as proof. `spawn-check-report.json` records the result.
The same check rejects the original launcher before it enters unsafe capture;
`threaded-before.json` records both workers in the same process with three
active threads. This demonstrates the violated contract without inducing a hang.
Two actual normal retention fixtures also passed through the corrected launcher
in 0.484 and 0.486 seconds, with no capability skips.

## Reproduction and provenance

```sh
make -j4 build/tests/jobs_lifecycle
python3 docs/evidence/csh-057-retention-review/check_spawn_runner.py
python3 docs/evidence/csh-057-timeouts/diagnose_retention.py . /tmp/retention-workers --workers 2
MallocNanoZone=0 python3 docs/evidence/csh-057-retention-review/probe_retention.py \
  /absolute/path/to/sanitized/jobs_lifecycle /tmp/retention-result.json
```

For profiling, export the recorded source commit to a temporary directory and
build with the flags in `identity.json`. Apply `phase-profile.patch`, then
optionally `fork-profile.patch` and `skip-complete.patch`, in that order. Supply
`'{"CSH_RETENTION_TRACE":"/absolute/path/to/phases.log"}'` as the probe's third
argument to enable phase records. The production fixture does not use that
variable. Retained JSON records identify each variant and its observed output;
the phase logs and build logs are compressed. Patches are diagnostic artifacts,
not shipping runtime changes. Instrumentation and host variation affect timings,
so these are not a controlled throughput benchmark.

`sampling-attempts.json` records the unsuccessful initial process lookup and
log retrieval attempts. `identity.json` records source/toolchain and retained
binary identities; instrumented intermediate binaries were overwritten and
have no retained binary hash. `inventory.json` hashes the artifacts in this
directory. No sanitizer diagnostic or capability skip occurred in these probes.
