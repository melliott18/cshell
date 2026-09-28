# CSH-057: Verify remaining job lifecycle boundaries

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-034, CSH-035
- Branch: fix/CSH-057-retention-timeout
- Issue: [#99](https://github.com/melliott18/cshell/issues/99)

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
`19cd70e`; the ticket remains at review for the distinct timeout observations
below. The earlier general-runtime timeout records are not erased.

During combined integration with CSH-048/050/060 on 2026-09-28, a concurrent
native/Docker run hit the unchanged five-second public PTY deadline at step
157. This was a timeout, not the previously diagnosed status-1/EPERM result.
Hosted duplicate run 36455644289 also timed out in the 60-second retention
fixture; run 36455693791 passed all hosted jobs. Keep issue #99 open to track
these timeout observations without weakening assertions or claiming that the
continuation fix resolves every scheduling failure.

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
Validation and failed attempts are recorded with the follow-up evidence. Keep
issue #99 open for review and the unclassified hosted retention observation.

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
retention probes pass. This diagnostic defect did not affect hosted CI. Keep
the historical retention observation under this ticket without claiming it is
fixed, extending deadlines, or treating another passing rerun as a diagnosis.
