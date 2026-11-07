# CSH-057 retention failure capture

## Result and scope

This change supplies the missing per-child timing, alarm observations, and
bounded macOS stack capture for future retention failures. It does **not**
diagnose or disposition hosted run 36602681743. That recurrence remains owned
by [CSH-057 / #99](../../tickets/CSH-057-job-lifecycle-boundaries.md), alongside
the new local terminal-fault observation below. The original exact retention
stdout/status assertions, 619 children, five-second progress alarms, and
60-second outer deadline are unchanged. No production source is modified.

Base: `ff736b7894b7ae992ca99ecd33d977cd2376a8e1`; branch:
`test/CSH-057-retention-diagnostics`. [Environment](environment.json) identifies
macOS 14.8.7 arm64, Apple Clang 15 and Python 3.12.2.
[Source hashes](source-sha256.json) identify the final runtime, test, Makefile
and workflow inputs, including newly added files. The environment record's
`source_diff` is an earlier tracked-file-only snapshot, not that manifest.

## Capture contract

`make test-job-retention` runs `tests/retention_diagnostics.py`, which calls the
existing `smoke.run_case` with the unchanged JSON oracle and resource limits.
The fixture alone links a fork-interposed executor object. Setting
`CSH_RETENTION_TRACE` enables an append-only, unbuffered JSONL side channel;
ordinary shell objects are unaffected. Without the variable, observation is
inactive. Children close the diagnostic descriptor immediately after their
entry record; it is also close-on-exec.

Each record contains:

| Field | Meaning |
| --- | --- |
| `t` | Absolute `CLOCK_MONOTONIC` microseconds; compare timestamps within the run |
| `p`, `c` | Emitting PID and related child PID/fork return value |
| `e` | Operation boundary: `fork+`, `fork-parent`, `fork-child`, `run+/-`, `reap+/-`, `wait+/-`, and phase/cleanup events |
| `n`, `r`, `i` | Capacity, one-based round and item; zero when not applicable |
| `a` | `[SIGALRM blocked, pending, disposition, remaining ITIMER_REAL microseconds]` |

Disposition is 0/default, 1/ignored or 2/handler; -1 indicates a failed query.
Subtract paired boundaries to distinguish fork cost, execution, child reaping
and retained-status waits. Child-entry and parent-return timestamps are both
kept; file ordering across processes is not a total timestamp order. Parent
and child timestamps use the same explicit clock as the watcher. Alarm queries
are read-only and preserve errno. The observer installs no signal handler,
unblocks no signal and changes no alarm. The last record describes the last
**observed** state, not necessarily the mask or pending state at final timeout.
In particular, a blocked-alarm control's earlier pending=0 does not claim the
alarm stayed nonpending after its timer expired.

A separate, single-threaded Python process reads new records every 20ms. It
requests at most one pair of stack samples when an individual operation reaches
2 seconds, total capture age reaches 57 seconds, or the latest observed timer
approaches the sampling budget. Aggregate rounds do not trigger an operation
stall merely by doing many successful children. On macOS it samples the fixture
and at most one still-owned recorded child concurrently with
`/usr/bin/sample PID 1 1 -mayDie -file OUTPUT`. A sample can perturb timing; the
record is evidence of observed work, not an overhead-free performance benchmark.

Bounds are explicit:

- Trace stops with a truncation record near 768 KiB, below the unchanged 1 MiB
  fixture file limit. Missing, partial, truncated or malformed timing is a
  diagnostic failure, even if the fixture succeeds.
- The sampler pair shares 2.5 seconds. Each sampler's report plus retained
  console output is capped at 1 MiB, with `RLIMIT_FSIZE` also enforced.
- Watcher startup has a 2-second readiness budget before the case starts.
  Its absolute lifetime is case budget plus 5 seconds; parent loss also ends it.
- Watcher self-cleanup has 0.5 seconds, and main independently allows 1 second
  for watcher-session cleanup after the existing case cleanup. Neither resets
  or extends the candidate's deadline. Ownership checks precede group kills,
  including sampler descendants that create a different process group.
- Watcher cleanup status -9 is deliberate self-termination and is separate
  from the candidate's result. Cleanup failures remain failures.

Sampling is best effort: unavailable, vanished target, timeout, truncation,
interruption and tool error are recorded explicitly. Linux currently records
sampler unavailable; timing/alarm and cleanup checks still run. There is no
claim of native Linux stack capture. An early assertion failure may end before
a useful sample is possible; its partial timing and raw outcome remain.

Each unique `build/retention-diagnostics/retention-*` directory contains the
trace, binary hash and run identity, exact selected case/environment,
configuration, trigger, attempts, stack/console files and final result.
`build/retention-diagnostics-checks` holds deliberate failure controls. Native
CI uploads both directories with `if: always()` and 30-day retention. Successful
normal-stage artifacts can be removed by the existing sanitizer clean; a failed
normal stage skips that clean. The ephemeral Docker path has no new uploader.

## Validation and retained failures

[Results summary](results-summary.json) indexes every retained real-case result,
including unsuccessful sample attempts. Durations below include the diagnostic
wrapper; `capture_duration_seconds` separately covers the existing runner.

| Validation | Result |
| --- | --- |
| Normal retention | Three passing invocations, 0.709–0.831 seconds; exact original oracle |
| Final normal failure controls | Default alarm status -14; blocked alarm outer timeout at 6 seconds/status -9; all four root/child samples captured |
| ASan/UBSan retention | Passed in 23.389 seconds; 5,572 events, all 619 parent/child fork pairs, complete trace, default unblocked alarm observations |
| ASan/UBSan failure controls | Expected -14 and outer 6-second/-9 results preserved; default control's two sample attempts timed out; blocked control captured both root and child |
| Full harness | 94 tests passed; after final sampler tuning all 8 new regressions passed again |
| Normal jobs subset | 148 runtime cases plus ownership/fault/watchdog checks passed |
| Normal public jobs PTY | All 30 shell cases and notification case passed; subsequent terminal fault fixture failed (below) |
| Full normal suite | Failed in unchanged CSH-058 SIGQUIT probe (below); not a clean full-suite pass |
| Linux/Docker | Local daemon returned HTTP 500 with default API 1.24 and explicit 1.44; no local Linux result |

The control fixture uses a readiness pipe, then waits for a deliberately paused
child. Native samples show parent `__wait4` and child `pause`/`__sigsuspend`.
The blocked variant changes only its explicit test-launcher's inherited mask;
production observation never does. The control checker requires actual root
and child call graphs across the two macOS cases, while retaining each attempt's
individual outcome. It does not label an unavailable sample captured. Both
normal and sanitizer controls verified teardown of their own processes.

The new harness regressions cover unchanged success/input, timeout status,
progressing rounds, missing sampler, hung sampler and a descendant in another
process group, output bounds, unrelated-process ownership, and missing trace.

Failed development attempts are also retained:

- Initial fake producer used Python `time.monotonic()` while C used
  `CLOCK_MONOTONIC`; their epochs differ on this Darwin system. The progressing
  round regression failed. Both now explicitly use `CLOCK_MONOTONIC`.
- The first real sampling controls used a 1.5-second budget and no `-mayDie`;
  all four attempts ended without reports during symbol processing. Final
  diagnostics use the documented `-mayDie` option and a 2.5-second budget,
  beginning at a 2-second operation age. The original case limits did not change.
- Even with that adjustment, the sanitizer default-alarm control's samples
  exhausted their budget. Those failures are retained; the other control
  demonstrated both real stack roles without enlarging the budget again.

### Separate normal-suite failures

`make test test-pty` stopped in the unchanged CSH-058 signal inheritance suite:
`runtime/QUIT/interactive=0/entry-ignore=0/action=0/subshell/reset=False` returned
142 with `default:` instead of `default:terminated\n`. This is consistent with
its four-second helper alarm, not the Python five-second timeout. Owned child
99718 was sampled in `main -> raise -> pthread_kill -> __pthread_kill`.
[CSH-058 / #100](../../tickets/CSH-058-signal-edge-evidence.md) owns the signal edge
observation; the earlier repaired launcher-alarm case had complete output and
is not the same signature.

`make test-jobs test-jobs-pty` later passed 148 jobs and 30 public PTY cases but
`execute_faults --jobs-terminal` reached the unchanged five-second outer bound
with empty output. Cleanup exhausted its shared snapshot budget and fallback
kill of leader group 18494 returned EPERM. Owned child 18538, in its own group,
was sampled in `context_job -> sigprocmask`. The fixture prints only after all
checks, so the failed subcase is unconfirmed; SIGQUIT is a hypothesis, not a
classification. A snapshot-deadline message does not prove one slow `ps`, and
EPERM for group 18494 does not describe a kill of group 18538.

Both children remained visible as `UE`, PPID 1 after exact-PID SIGKILL requests.
No successful cleanup is claimed. These post-failure samples are weaker than
sampling the live parent before the original deadline. The terminal observation
remains under #99, cross-linked to #100; harness cleanup context is CSH-040/033.
It is not covered by the historical retention disposition. No common cause with
the hosted retention failure, host-load cause, or kernel defect is established.
The modified fork object links only into `jobs_lifecycle`, and production source,
`execute_faults`, `signal_edges_helper`, their JSON oracle and the PTY harness
are unchanged. The broad failures were not retried merely to obtain green logs.

## Reproduce and inspect

```sh
make test-job-retention test-retention-diagnostics test-harness
make clean
MallocNanoZone=0 ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 \
UBSAN_OPTIONS=halt_on_error=1 make -j2 test-job-retention test-retention-diagnostics \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The smoke runner's existing environment policy forwards `MallocNanoZone`; it
does not implicitly forward ASAN_OPTIONS/UBSAN_OPTIONS into candidates. Metadata
records that limitation and the selected case environment. No sanitizer
report was observed in the focused run; this is not a leak-check claim.

[Normal artifacts](normal-artifacts.tar.gz) contain raw cases, traces, stacks,
all development/validation logs, sampler probes, and the two orphan reports.
[Sanitizer artifacts](sanitizer-artifacts.tar.gz) contain the final positive
retention and negative controls. [Build log](sanitizer-build.log) and
[focused log](sanitizer-focused.log) retain commands/results. Extract archives
into separate directories: their original `build/` paths overlap. Absolute
paths in JSON identify original runs; archived content is under the listed
relative member paths. [Artifact hashes](artifacts-sha256.json) provide integrity.

Closure still requires a supported corrective change or a new explicit
recurrence disposition. Diagnostic capability and passing controlled tests do
not supply that disposition.
