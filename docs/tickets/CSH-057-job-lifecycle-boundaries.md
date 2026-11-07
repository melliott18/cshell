# CSH-057: Verify remaining job lifecycle boundaries

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-034, CSH-035
- Branch: fix/CSH-057-terminal-fault-timeout
- Issue: [#99](https://github.com/melliott18/cshell/issues/99)

## Final verification and integration: 2026-10-02

[Final hosted evidence](../evidence/csh-057-final-verification/README.md)
verifies repair head `48af5bc` in the complete PR workflow: Ubuntu, Docker and
macOS normal/sanitizer checks passed. The duplicate push workflow passed Ubuntu
and Docker; its macOS job failed 17 separate CSH-054 exit-operand batches.
Both macOS jobs passed retention, crash-notification isolation, repeated
resumes, terminal faults and the new queued-output cleanup regression. The
push failure remains a failure, owned by reopened [CSH-054 / #90](CSH-054-signal-contract-gaps.md).

Independent review found no actionable blocker. PRs
[#167](https://github.com/melliott18/cshell/pull/167),
[#172](https://github.com/melliott18/cshell/pull/172), and
[#173](https://github.com/melliott18/cshell/pull/173) are integrated into `main`
as `0938eeb`, `d06891e`, and `57e8c40`, respectively. The final integration tree
is byte-for-byte identical to the verified repair head and PR merge tree.
All eight acceptance criteria have their mapped evidence, so this ticket is
complete. These repairs change tests, diagnostics and their aggregate budgets;
production runtime sources remain unchanged by this stack.

This disposition does not prove every historical failure's cause or declare
an unsolvable bug. The unrecorded historical Mach receiver remains a potential
host/fixture issue. A new CSH-057 timeout, status/ownership error, sanitizer
finding or cleanup failure reopens #99; a passing retry does not erase it.
CSH-054, CSH-058 and the broader conformance gates retain their separate owners.

## Integrated repair: public PTY teardown and aggregate timing

The [follow-up diagnosis](../evidence/csh-057-pty-teardown/README.md) reproduces
the remaining cleanup failure with the real sanitizer shell. After killing its
owned groups, the open PTY master can hold the leader in exit while unread
output remains. An empty session snapshot does not prove the child is waitable.
Closing that master releases the exact-child wait immediately. Cleanup now
closes it after group teardown and before the unchanged one-second reap. A
queued-output regression fails under the old cleanup and passes with the fix;
the captured transcript and any original timeout failure remain unchanged.

The same 32-cycle shell/fixture binary, with a controlled 160 ms startup delay
per helper, exceeds five seconds but passes all 419 steps in about 6.3 seconds.
Only that case receives ten seconds of aggregate headroom. All 29 other public
jobs PTY cases retain five seconds. Separately, both subsequent hosted macOS
jobs exhausted their 45-minute job budget while still passing tests. The native
job budget is now 60 minutes, with individual case bounds unchanged apart from
the explicitly scoped repeated-resume correction.

These changes repair demonstrated harness and budget defects; they do not
reconstruct every historical scheduling interval or prove an unsolvable shell
bug. Final verification and integration are recorded above. Prior failures
below remain in the record, including separate CSH-054 exit-operand observations.

## Earlier closure verification: 2026-10-01

The [hosted verification](../evidence/csh-057-terminal-crash-notification/hosted-verification/README.md)
confirms the terminal-fault repair in normal and ASan/UBSan macOS checks.
Mach isolation and retention also passed both builds in both hosted runs.
However, the push run's sanitizer `repeated background resumes preserve prompt
and terminal` case timed out at five seconds while waiting for step 328, then
failed to reap its leader within one second. This separate public PTY recurrence
was owned by CSH-057 / #99, so the condition for closing the whole ticket
was not then met. The passing peer did not erase it. The peer's overall macOS failure
belongs to CSH-054 exit-operand tests. Ubuntu and Docker passed both runs.

[PR #173](https://github.com/melliott18/cshell/pull/173) and its prerequisite
PRs #172/#167 were then unmerged and status remained `review`. The final
verification above supersedes that hold; no issue is declared unsolvable and
no failing result is converted to a pass.

## Integrated repair: terminal crash-notification isolation

The [terminal investigation](../evidence/csh-057-terminal-crash-notification/README.md)
reproduces the terminal-fault timeout with a controlled inherited Mach
`EXC_CRASH` receiver. The original `execute_faults --jobs-terminal` binary
hits its unchanged five-second deadline with empty output and status -9 when
the receiver withholds its reply. Replying releases the exiting child. With
the fixture fix, the same original oracle passes in 0.058 seconds without a
notification to that receiver; the sanitizer build passes in 0.901 seconds.

Only the test child deliberately receiving SIGQUIT clears its inherited
task-level crash-notification port on macOS. Signal dispositions, masks,
SIGQUIT status, production code, terminal assertions and all deadlines remain
unchanged. The new `test-job-crash-notification` regression demonstrates the
held-notification/SIGKILL dependency and verifies isolation with exact SIGQUIT
termination. Removing the isolation call makes that regression fail, with
bounded cleanup. Linux explicitly reports this Mach-specific check unavailable
and continues its existing terminal and job checks.

The original orphan's exact binary and machine-code return addresses narrow
its location to the pending launch-signal loop. Its specific signal and actual
exception receiver were not recorded. The controlled experiment establishes
an actionable fixture vulnerability with the same failure signature; it does
not retrospectively prove the original receiver's identity or an operating
system bug. No evidence proves this issue unsolvable. Its retained uncertainty
is documented as a potential host/fixture issue, with same-ticket ownership if
the failure recurs after isolation.

This change builds on retention-budget [PR #172](https://github.com/melliott18/cshell/pull/172),
which builds on diagnostic [PR #167](https://github.com/melliott18/cshell/pull/167).
CSH-057 then remained at `review` pending integration and resolution of the
public PTY recurrence above; final verification now closes that hold. The
historical terminal failure is not erased or converted into a passing run.
The distinct CSH-058 signal-probe observation below is not fixed by this
child-specific change.

### Retention aggregate-budget repair

The [retention evidence](../evidence/csh-057-retention-budget/README.md)
records 59.503 seconds of completed short run/reap operations before the hosted
60-second outer timeout. PR #172 raises the finite aggregate budget to 120
seconds, preserving all 619 children, exact assertions, manager reuse and
five-second phase alarms. Its controlled slowed binary failed at the old
60-second limit and passed the same assertions in 90.578 seconds under the new
budget. The evidence retains normal/sanitizer macOS and Docker validation and
the limits of inferring older failure causes.

### Separate failures retained from the diagnostic review

The diagnostic PR's native normal validation passed 94 harness checks, 148 jobs
cases and 30 public jobs PTY cases. The subsequent unchanged `execute_faults
--jobs-terminal` case hit its five-second outer deadline with empty output;
cleanup exhausted its snapshot budget and reported fallback EPERM for leader
group 18494. This historical terminal-fault observation motivated the isolation
repair above; its exact original receiver remains unknown under issue #99.
The separate full normal suite stopped in the unchanged CSH-058
`runtime/QUIT/interactive=0/entry-ignore=0/action=0/subshell/reset=False`
probe with status 142 and only `default:` output, owned by
[CSH-058 / #100](CSH-058-signal-edge-evidence.md).

Both attempts left owned children reported as `UE` after SIGKILL: terminal
fixture child 18538 and signal-probe child 99718. Preserved samples locate the
terminal child in `context_job` through `sigprocmask`, and the signal-probe
child in `raise` through `__pthread_kill`. These observations do not establish
a shared cause or a connection to hosted retention timing. The cleanup EPERM
names the terminal leader's group, not child 18538's group; a snapshot-budget
failure does not by itself prove one slow `ps` invocation. No complete normal
suite pass is claimed. Final sanitizer outcomes belong to the linked evidence
record and are not inferred here.

## Historical review disposition

The scoped lifecycle implementation and all demonstrated repairs are integrated:
PR #109 (`ab0c779`), PR #112 (`19cd70e`), PR #121 (`87fdfe8`), and the diagnostic
worker repair in PR #124 (`893b10b`). All eight acceptance criteria below have
their mapped evidence. Review at `66f8900` accepts the historical hosted
retention timeout as **unknown-cause, non-blocking for this scoped completion**.
Its failed result is retained; it is not declared fixed, passed, or proven load.

The [formal disposition](../evidence/csh-057-retention-disposition/README.md)
records the rationale, remaining risk, unchanged CI enforcement, and reopening
criteria. Issue #99 remains the owner of the historical record and any
recurrence. A new retention timeout, unexpected termination, sanitizer finding,
status/ownership error or cleanup failure reopens this ticket; successful retries
do not erase that failure. CSH-050 and CSH-012 retain their independent acceptance
gates, and the requirement families remain implemented subsets.

## Goal

Close the job-specific obligations retained by
[CSH-054](CSH-054-signal-contract-gaps.md), without treating its signal fixes or
selected wait witnesses as full jobs verification. Owns residual
[EXEC-009](../posix-matrix.md#exec-009), [JOB-001](../posix-matrix.md#job-001),
[JOB-002](../posix-matrix.md#job-002), [JOB-003](../posix-matrix.md#job-003), and
[U-032](../posix-utilities.md#u-032).

## Scope and acceptance criteria

- [x] Exercise CHILD_MAX retained statuses and permitted eviction with saved and
  unsaved IDs, bounded sequential children, and explicit capacity assertions.
- [x] Show that successful `fg` consumes a known ID, while interrupted/stopped
  jobs retain the appropriate identity and result.
- [x] Start a controlling-session leader when another group initially owns its
  terminal; assert the standard's required ownership transition without an
  orphaned-group stop loop. Existing nested nonleader tests do not cover this.
- [x] Assert background pipeline and compound group membership. Classify
  suspended compound membership's permitted/unspecified portions separately.
- [x] Stop/resume a compound job and prove completed commands are not replayed.
- [x] Deliver SIGSTOP during a shell builtin, then CONT; verify continued
  execution, process groups, terminal settings, and bounded teardown.
- [x] Assert notification timing during foreground execution with notify on/off,
  all applicable stop-signal variants, `jobs` formats, and completed/signal
  notification bytes. Existing idle notification witnesses are insufficient.
- [x] Update the forward/reverse requirement links and exact assertion map;
  repair any demonstrated defects or name narrower owning tickets.

## Validation

Use the CSH-033/040 bounded PTY transport and CSH-054 cleanup budgets. Run native
macOS, Linux Docker, ASan/UBSan, `make test-jobs test-jobs-pty test-harness`, and
the full suites. Use readiness/terminal predicates, never sleeps as proof of
state. Retain every failing run and every capability skip with an owner.
Full UP/XSI and genuinely unspecified outcomes stay separately classified.

## Implementation and disposition

Implemented on `test/CSH-057-job-lifecycle-boundaries`. Runtime/test commit
`ce76d1c` repairs foreground/capacity eviction, retention alongside old live jobs,
session-leader terminal startup, foreground notify delivery, POSIX-locale job
output, and suspension propagation through foreground compounds. `3045124`
corrects the retention fixture's already-reaped-child observation. `adb9e5c`
corrects the new fixture's borrowed-state teardown, found by LeakSanitizer.

The [exact assertion map](../jobs-signals-evidence.md#csh-057) distinguishes the
controlled CHILD_MAX API fixture (32 and fallback 256) from public PTY witnesses.
It records every acceptance condition, all four stop signals, intact
background-first compounds, and the permitted/unspecified policy for originally
foreground compounds. Full UP/XSI remains unselected and parent requirements
remain implemented subsets. CSH-058 retains the separate signal edge inventory.

## Validation record

[Retained logs, identities, failed-before observations and final results](../evidence/csh-057/README.md)
include the production defects, two diagnosed fixture races and a fixture state leak, loaded macOS
transport failures, final native/Docker suites and ASan/UBSan. The source digest
is shared across platforms; later evidence/documentation commits do not change
runtime/test inputs. No CSH-057 capability skips are converted into passes.

The Linux sanitizer batch sweep retains four five-second control-flow timeouts;
the exact cases pass three serial reruns with unchanged limits. The record does
not claim a clean full Linux sanitizer invocation. Native and Docker normal
full suites, native full sanitizer, and all CSH-057 sanitizer checks pass.

Integration review on 2026-09-28: hosted run 36313722641 passed all jobs, but
duplicate macOS job 108604370895 in run 36313720185 failed the pre-existing
`repeated background resumes preserve prompt and terminal` assertion (status 1
instead of 130). The ticket remained open after the scoped changes merged to
investigate this failure.

### Foreground resume follow-up

`33d32a7` fixes the reproduced continuation race. If Ctrl-C finishes a job
between foreground display and SIGCONT, Darwin can reject the latter with
EPERM. Previously `fg` returned 1 and reported an extra completion notice.
It now collects owned statuses and accepts a failed continuation only for a
fully completed job, returning 130 and consuming its identity. A live stopped
job still rejects EPERM and retains its state.

The [follow-up evidence](../evidence/csh-057-pty-fix/README.md) retains the
hosted failure, a deterministic public PTY reproduction, the failing-before
module regression, and final native/Docker normal and sanitizer checks.
The public test's exact transcript, foreground predicates, 32 cycles and
five-second deadline are unchanged. PR #112 integrated that follow-up as
`19cd70e`; the ticket then remained at review for the distinct timeout
observations below. The earlier general-runtime timeout records are not erased.

During combined integration with CSH-048/050/060 on 2026-09-28, a concurrent
native/Docker run hit the unchanged five-second public PTY deadline at step
157. This was a timeout, not the previously diagnosed status-1/EPERM result.
Hosted duplicate run 36455644289 also timed out in the 60-second retention
fixture; run 36455693791 passed all hosted jobs. Issue #99 stayed open to track
these observations without weakening assertions or claiming that the
continuation fix resolved every scheduling failure. The final disposition above
supersedes that temporary hold; the observations remain in the record.

### Timeout diagnosis follow-up

The [timeout investigation](../evidence/csh-057-timeouts/README.md) supersedes
classification of the retained PTY timeouts as load failures. New traces show
normal progress ending within milliseconds, followed by a whole-case timeout.
They reproduce concurrent parent/child process-group assignment losing terminal
signal delivery, inherited blocked INT/CHLD after a Darwin signal-aware wait,
and a continuation refusal during the gap between group departure and a
reportable child exit. The separate hosted retention timeout remains
unclassified; passing local probes do not establish its historical cause.

The launch barrier now makes the parent the sole process-group writer. Darwin
wait cleanup clears deferred mask restoration before restoring the caller's
mask. After a rejected continuation, only an owned child whose `getpgid`
returns ESRCH may be waited for synchronously; live job errors remain errors.
Regression coverage includes pending launch signals, the exit-status gap,
unchanged live-EPERM rejection, and an explicit mask check in the PTY helper.

Timeout diagnostics retain progress timing and both ends of long output.
The retention fixture flushes exact phase/capacity checkpoints while keeping
its 60-second outer deadline, five-second phase alarms, and all assertions.
Validation and failed attempts are recorded with the follow-up evidence. At that
stage, issue #99 remained open for review and the unclassified hosted retention
observation; its later formal disposition is recorded above.

### Merged repair review and retention timing

PR #121 merged as `87fdfe8`. Review at `faf2e95` found no actionable correctness
regression in the three runtime repairs; the complete hosted integration run
passed Ubuntu, Docker, and macOS normal/sanitizer checks.

The [retention review evidence](../evidence/csh-057-retention-review/README.md)
records hosted sanitizer passes in 40.556, 54.911 and 41.413 seconds against the
unchanged 60-second deadline. Local timing and stack sampling show progressing
fork/child-wait work across the 619-child fixture. Cumulative sanitizer process
cost is the leading hypothesis, but the original buffered failure log cannot
establish its cause and the timeout has not reproduced. A diagnostic-only skip
of redundant completed-record waits did not materially shorten the probe and
was not applied to the runtime.

The separate concurrent diagnostic launcher now uses spawned single-threaded
processes instead of threads around Python `preexec_fn`. Controlled success and
failure cases verify process isolation and retained outcomes; two actual normal
retention probes pass. This diagnostic defect did not affect hosted CI. The
historical retention observation remains owned here without claiming it is
fixed, extending deadlines, or treating another passing rerun as a diagnosis.

### Hosted recurrence during 2026-09-29 integration

Issue #99 is reopened under the recurrence policy. macOS sanitizer job
109523732498 in run 36602681743 hit the unchanged 60-second retention deadline.
Its last progress at 58.721 seconds was capacity 256, round 2, completed 128.
The duplicate run 36602689841 passed; that pass does not explain this failure.
The earlier statement that the timeout had not reproduced describes the prior
review only. No assertion or deadline is relaxed by this integration.

The [recurrence evidence](../evidence/csh-057-retention-recurrence/README.md)
preserves both complete hosted logs, verifies their identical source trees,
extracts the exact 524-byte expected prefix, and records source review and local
fork/reap timing. The observed mechanism is aggregate deadline exhaustion after
substantial completed work; the reason for the variable hosted elapsed time
remains unconfirmed. No new runtime defect or corrective change is established.
