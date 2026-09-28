# CSH-057 historical retention timeout: formal disposition

Decision: accept the historical failure as an **unknown-cause observation that
does not block CSH-057's scoped completion**. The investigation of the available
record is complete. This is a review decision about scope and residual risk,
not a root-cause finding or a conversion of a failed run into a pass.

Reviewed source: `66f8900420525f54b2b53d7342b336f0d7656a5f`, 2026-09-28.
The user explicitly requested investigation or formal disposition after the
runtime and diagnostic-worker repairs were merged. CSH-057 / GitHub issue
[#99](https://github.com/melliott18/cshell/issues/99) retains ownership of the
record and any recurrence. No successor ticket or scheduled monitor is needed
to preserve that ownership; the existing retention CI test remains enforced.

## Observation and limits

[Hosted macOS sanitizer job 109041175577](https://github.com/melliott18/cshell/actions/runs/36455644289/job/109041175577)
at `787983461ca56efea431cae59b9bf8b9d181bf37` reached the retention fixture's
60-second outer deadline. The runner killed it with status `-9`; stdout was
empty and the old fixture's output was fully buffered. The log cannot establish
whether its first output statement was reached. There is no retained
last-child progress, stack sample or alarm-state observation from that failure.
Its cause cannot be recovered from the available log.

The [original failing log](../csh-057-timeouts/hosted-retention-timeout.log.gz),
[timeout investigation](../csh-057-timeouts/README.md), and
[merged-repair review](../csh-057-retention-review/README.md) remain unchanged in
their factual outcomes. The latter's temporary requirement to keep the ticket
open is superseded by this decision.

Cumulative sanitizer process cost is a supported hypothesis: the 619-child
fixture passed hosted sanitizer runs in 40.556, 54.911 and 41.413 seconds, and
local measurements showed progressing fork/child-wait work. The historical
timeout did not reproduce, and those passing observations do not establish its
cause. No evidence proves either a runtime stall or a harmless scheduling
delay in the failed run. CSH-045's separately reproduced aggregate-alarm defect
is not a diagnosis of this failure.

## Why scoped completion is accepted

- CSH-057's eight concrete lifecycle criteria are implemented and checked in the
  [ticket](../../tickets/CSH-057-job-lifecycle-boundaries.md#scope-and-acceptance-criteria).
  The [exact assertion map](../../jobs-signals-evidence.md#csh-057) identifies
  CHILD_MAX/fallback retention, saved/unsaved IDs, eviction with live records,
  foreground consumption, terminal startup, group membership, non-replay,
  builtin stop/resume, notification timing and output assertions.
- The original implementation and demonstrated repairs are integrated as
  `ab0c779` (PR #109), `19cd70e` (PR #112), `87fdfe8` (PR #121), and `893b10b`
  (PR #124). The PTY races have failing-before/passing-after evidence; the
  independent diagnostic-worker repair does not claim to fix hosted retention.
- [Full hosted run 36487917937](https://github.com/melliott18/cshell/actions/runs/36487917937)
  passed native Ubuntu, macOS, Docker and their sanitizer stages at `faf2e95`.
  Comparing that revision with the reviewed `66f8900` shows no changes to
  `src/`, `include/`, the retention fixture/JSON, pipe/PTY runners, Makefile,
  or CI workflow. Later host-profile tests and the Dockerfile did change; the
  whole CI workload/image is not claimed identical. The diagnostic script is
  outside the retention case's production inputs. PR #124's controlled
  worker-isolation check and its deliberately failing cases are retained
  separately.
- Repeated investigation found no further actionable runtime repair. The
  missing historical telemetry cannot be restored by more successful reruns.
  Completion therefore rests on the implemented acceptance criteria, integrated
  fixes, retained validation and this explicit risk decision together.

There is residual risk: an undiscovered intermittent runtime or harness defect
could have caused the old failure. This decision accepts that uncertainty for
CSH-057's bounded deliverable. It does not assert universal reliability, complete
JOB/EXEC/wait-family verification or POSIX compliance. It does not close CSH-050
or CSH-012 or satisfy their separate platform/conformance gates.

## Enforcement and reopening

The retention fixture stays in `make test-jobs`, `make test` and hosted normal
and ASan/UBSan CI. Its exact outputs/statuses, all 619 children, five-second
phase alarms, 60-second outer deadline, and bounded descendant cleanup remain
unchanged. There is no skip, expected-failure allowance, retry-to-green policy,
timeout extension or sanitizer suppression introduced by this disposition.

Reopen **CSH-057 / #99** on any newly observed retention timeout, unexpected
signal termination, sanitizer finding, retained-status/eviction error, or
child-ownership/cleanup failure. A new failure is not covered by this historical
acceptance, even if it resembles the old symptom or a retry passes.

For that recurrence:

1. Preserve the failing source revision, platform/toolchain/sanitizer settings,
   job URL, complete output and runner result before rerunning.
2. Use the merged flushed capacity/round/completion and live/formatting markers
   plus the runner's last-output timing to locate progress. Collect parent/child
   stacks, process/session identities and alarm mask/disposition when available;
   diagnostic collection must not postpone the existing cleanup deadline.
3. Distinguish a stalled operation from continued cumulative progress using the
   new evidence. Reproduce and repair a demonstrated defect with a regression,
   or make a fresh, explicitly reviewed disposition of that new observation.
   Do not reuse this decision or a passing retry as proof of its cause.

This is a recurrence procedure, not deferred mandatory work for the old record.
No indefinite repetition or proof that an intermittent failure can never recur
is required to complete the scoped ticket.

## Review validation

This change is documentation only. The review checked all eight ticket criteria,
merge identities, retained evidence inventories and the unchanged relevant
source paths. Independent review agreed that same-ticket ownership and explicit
reopening conditions are preferable to an empty successor investigation.
[`review.json`](review.json) records the source comparison and CI snapshots.
The new macOS runs were still in progress at the snapshot; they are not reported
as passes. The earlier complete green run is identified by its own revision.
No new runtime or sanitizer execution is claimed for this documentation change.
