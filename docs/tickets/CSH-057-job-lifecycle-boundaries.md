# CSH-057: Verify remaining job lifecycle boundaries

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-034, CSH-035
- Branch: test/CSH-057-job-lifecycle-boundaries
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
instead of 130). This intermittent failure remains unresolved; issue #99 and
this ticket remain open for follow-up even after the scoped changes merge.
