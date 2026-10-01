# CSH-057: Verify remaining job lifecycle boundaries

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-034, CSH-035
- Branch: fix/CSH-057-retention-budget
- Issue: [#99](https://github.com/melliott18/cshell/issues/99)

## Current review: retention aggregate-budget repair

The [new hosted failure capture and budget repair](../evidence/csh-057-retention-budget/README.md)
diagnoses the instrumented macOS sanitizer timeout in run 36662308140:
completed run and reap intervals consumed 59.503 seconds, no interval took
more than 0.153 seconds, and 573 of 576 capacity fills completed before the
60-second outer deadline. All recorded SIGALRM states were default
and unblocked. The next child was launched and entered its wait just before
the runner killed the fixture. This demonstrates aggregate-budget exhaustion
during observed progress; the final child's unobserved outcome remains unknown.
It does not identify the reason for host-to-host cost variation or recover the
missing telemetry from the original empty-output failure.

The fix raises the finite retention outer budget to **120 seconds** and moves
case-age stack sampling to 117 seconds. Both the JSON case and diagnostic
runner enforce that bound. All 619 children, exact output/status assertions,
two-round manager reuse, five-second phase alarms, two-second operation-stall
sampling, and bounded cleanup remain. No runtime code, sanitizer setting,
retry policy or expected-failure allowance changes. The linked evidence
retains the actual failed run and explains the explicit budget tradeoff.

This branch builds on the diagnostic observer in [PR #167](https://github.com/melliott18/cshell/pull/167).
The [original diagnostic review](../evidence/csh-057-retention-diagnostics/README.md)
remains a historical record, including its separate failures. This ticket is
at `review` pending integration and disposition of the terminal-fault
observation below. The retention failure is not proved unsolvable, and no
unresolved shell defect is relabeled as fixed by increasing its test budget.

Validation on this repair passed native macOS and Linux/Docker retention,
ASan/UBSan retention, 94 harness checks per platform, jobs/PTY checks and the
five-second stalled-child controls. A temporary 100 ms per-fork delay makes
the same sanitized binary fail at the former 60-second bound, then pass all
619 children and exact assertions in 90.578 seconds under the new bound.
The delay is diagnostic-only; the linked evidence retains both outcomes and
platform/flag limitations. No new full-suite or fixed-branch hosted pass is
claimed.

### Separate failures retained from the diagnostic review

The diagnostic PR's native normal validation passed 94 harness checks, 148 jobs
cases and 30 public jobs PTY cases. The subsequent unchanged `execute_faults
--jobs-terminal` case hit its five-second outer deadline with empty output;
cleanup exhausted its snapshot budget and reported fallback EPERM for leader
group 18494. This new terminal-fault observation remains undispositioned under
issue #99. The separate full normal suite stopped in the unchanged CSH-058
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
