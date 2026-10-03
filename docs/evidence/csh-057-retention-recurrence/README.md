# CSH-057: macOS sanitizer retention recurrence

Review on 2026-09-29 classifies the observed failure as **the aggregate
60-second deadline expiring after substantial completed work**. The specific
reason for the hosted elapsed time remains unconfirmed. This is an investigation
record, not a demonstrated repair or a new acceptance of the failure. CSH-057 /
[#99](https://github.com/melliott18/cshell/issues/99) remains open at `review`.
The [earlier disposition](../csh-057-retention-disposition/README.md) covers only
the earlier observation; its recurrence policy applies here.

## What the failing progress establishes

The complete [failed macOS log](hosted-failure.log.gz) is from
[run 36602681743, job 109523732498](https://github.com/melliott18/cshell/actions/runs/36602681743/job/109523732498),
checkout `c707ecb6f2681a30e4f899709b12c7b4f7bc7d62`.
The runner reports:

```text
timeout after 60s (last output at 58.721s; no output for 1.282s; 524 bytes captured; process group killed)
status: expected 0, got -9
```

All 524 captured stdout bytes are the exact expected prefix. The last line is
`retention capacity=256 round=2 completed=128`. This follows successful launch
and reap assertions for at least **448 capacity-fill children**:
32 + 32 + 256 + 128. It also follows both 32-child rounds' status checks and
the first 256-child round's foreground-preservation and exact numeric waits.
The second fallback round has not reported completion; live-record retention,
formatting and final child cleanup have no completion evidence in this run.

`58.721s` is the harness's monotonic **read time**, not a timestamp recorded by
the fixture. There are no individual arrival times for earlier checkpoints,
per-child durations, timeout-time stacks or recorded SIGALRM mask/disposition.
The 1.282-second final output gap does not demonstrate a five-second operation
stall. It also cannot rule out a delayed read, an earlier stall, a late stall or
additional work between checkpoints. The runner's outer deadline can expire
before a newly armed five-second fill alarm. Absence of SIGALRM is not proof
that its inherited state was correct or every operation took less than five
seconds.

This evidence substantially narrows the old empty-output ambiguity: a large
prefix completed, and the outer runner killed an unfinished case. It does not
prove host load, a deadlock, or a particular slow system call. Cumulative
sanitizer fork/wait cost remains the leading explanation, rather than a proven
hosted root cause. The original historical failure remains unknown-cause.

## Peer run and source review

The [passing peer log](hosted-peer.log.gz),
[run 36602689841, job 109523761967](https://github.com/melliott18/cshell/actions/runs/36602689841/job/109523761967),
checked out synthetic merge `b77a5d5d04233bd16cf745a6f016f7d78cee061e`.
GitHub's commit comparison verifies that both checkouts have the identical tree
`7f26ac69a90fbb493bb3e718ae1d2cbded807c0a`, with no changed files. Both runners
used macOS 15.7.9 / 24G830, image `macos-15-arm64` version `20260907.0337.1` and
`make -j2 test test-pty test-host-profile` for the sanitizer step.

| Hosted case | Failure job | Passing peer |
| --- | ---: | ---: |
| Normal | 0.416128 s, pass | 0.334152 s, pass |
| ASan/UBSan | 60.065563 s, timeout | 51.183455 s, pass |

These are GitHub log intervals from suite header to result, including logging
and runner overhead. The timeout's 58.721-second observation instead comes from
the runner's monotonic clock. Parallel make permits concurrent work but records
neither actual machine load nor its contribution to the failure.

Compared with the prior green `faf2e95`, the failed source has identical
`jobs.c`, retention C/JSON and pipe/PTY capture files. CSH-066 changes shallow
parse/execute/expand work through native-stack checks, `getrlimit`, thread-local
bound caching and iterative execution-plan ownership. Inspection found no new
job-wait, signal-mask or launch-barrier change explaining this failure; it does
not quantify the cost of the changed paths or rule out a runtime defect.
[hosted-analysis.json](hosted-analysis.json) retains source blobs, exact log
lines, extracted output and the peer tree comparison.

## Local measurements

Local probes use current main `60295934db1c971a2b3aac582f88b0f766eccce2`, on
macOS 14.8.7 / 23J520 arm64, Apple Clang 15.0.0 and Python 3.12.2. This differs
from the hosted failed revision and OS. They measure the current work, not the
historical runner. All retain the original exact stdout/status oracle,
619 children, 60-second outer deadline and fixture alarms.

| Probe | Outcome |
| --- | --- |
| Unmodified ASan/UBSan fixture | Pass, 15.472 s |
| Serial fixture with file-backed phase/fork timing | Pass, 20.483 s |
| Four spawned, single-threaded diagnostic workers | All pass, 32.685–32.762 s |

The serial trace records 576 fill operations totaling 10.751 seconds in `run`
and 8.260 seconds in `reap`. The 615 parent `context_job` forks total 10.942
seconds; this overlaps `run` and must not be added to it. The four direct
live/format helper forks are outside that count. The longest instrumented
serial operation is 0.063 seconds; across the concurrent traces it is 0.376
seconds. The concurrent launcher exit is insufficient as an oracle: all four
per-worker `failures` lists were also checked and are empty.

These successful profiles support cumulative fork/reap cost as a plausible
mechanism. They neither reproduce the timeout nor establish hosted load as its
cause. No further passing retries are counted as a fix. The complete temporary
instrumentation is [profile.patch](profile.patch); it was removed from working
source after the probes. Source/binary identities, build logs, raw traces and
the failed initial patch application are retained. No runtime, fixture,
assertion, alarm, deadline or CI scheduling change is proposed by this review.

## Remaining closure gate

The recurrence still requires either a demonstrated corrective change or an
explicit new disposition reviewing this failure and the aggregate budget.
Another green run alone does neither. A concrete next diagnostic is a failure
capture with child-side monotonic start/end times for each fork/run/reap,
recorded alarm mask/disposition, and a bounded stack sample before cleanup;
those observations can distinguish accumulated short operations from a stuck
operation or delayed runner scheduling. Existing cleanup must remain bounded.

Dividing retention, eviction and live/format checks into separate cases is a
possible test-design change, not a diagnosis. It must retain capacities 32/256,
saved/unsaved IDs, exact statuses, foreground preservation, eviction, manager
reuse and descendant cleanup. Separate cases change the aggregate suite budget
and can remove same-manager interactions; that tradeoff must be reviewed
explicitly. This record does not silently make that change or reuse the old
non-blocking disposition.

## Reproduction and artifact verification

From the repository root, regenerate the summaries without running the fixture:

```sh
python3 docs/evidence/csh-057-retention-recurrence/analyze_hosted.py > /tmp/csh057-hosted-analysis.json
cmp /tmp/csh057-hosted-analysis.json docs/evidence/csh-057-retention-recurrence/hosted-analysis.json
python3 docs/evidence/csh-057-retention-recurrence/analyze_profiles.py
```

The hosted analyzer uses the retained compressed logs, local Git objects and a
read-only GitHub comparison API call. The profile analyzer reads only retained
traces/results and asserts all expected phase counts and successful outcomes.
`inventory.json` lists SHA-256 and size for every evidence file except itself.

The local probes used the existing
[`probe_retention.py`](../csh-057-retention-review/probe_retention.py) and
[`diagnose_retention.py`](../csh-057-timeouts/diagnose_retention.py) observers,
with `MallocNanoZone=0`, normal sanitizer build flags recorded in the logs, and
`--workers 4` for the concurrent check. `smoke.capture` passes `MallocNanoZone`
but does not inherit `ASAN_OPTIONS`/`UBSAN_OPTIONS` into the case; this also
applies to the hosted retention invocation despite its step-level variables.
