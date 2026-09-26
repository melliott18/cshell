# CSH-057: Verify remaining job lifecycle boundaries

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-034, CSH-035
- Branch: Assigned when work starts
- Issue: [#99](https://github.com/melliott18/cshell/issues/99)

## Goal

Close the job-specific obligations retained by
[CSH-054](CSH-054-signal-contract-gaps.md), without treating its signal fixes or
selected wait witnesses as full jobs verification. Owns residual
[EXEC-009](../posix-matrix.md#exec-009), [JOB-001](../posix-matrix.md#job-001),
[JOB-002](../posix-matrix.md#job-002), [JOB-003](../posix-matrix.md#job-003), and
[U-032](../posix-utilities.md#u-032).

## Scope and acceptance criteria

- [ ] Exercise CHILD_MAX retained statuses and permitted eviction with saved and
  unsaved IDs, bounded sequential children, and explicit capacity assertions.
- [ ] Show that successful `fg` consumes a known ID, while interrupted/stopped
  jobs retain the appropriate identity and result.
- [ ] Start a controlling-session leader when another group initially owns its
  terminal; assert the standard's required ownership transition without an
  orphaned-group stop loop. Existing nested nonleader tests do not cover this.
- [ ] Assert background pipeline and compound group membership. Classify
  suspended compound membership's permitted/unspecified portions separately.
- [ ] Stop/resume a compound job and prove completed commands are not replayed.
- [ ] Deliver SIGSTOP during a shell builtin, then CONT; verify continued
  execution, process groups, terminal settings, and bounded teardown.
- [ ] Assert notification timing during foreground execution with notify on/off,
  all applicable stop-signal variants, `jobs` formats, and completed/signal
  notification bytes. Existing idle notification witnesses are insufficient.
- [ ] Update the forward/reverse requirement links and exact assertion map;
  repair any demonstrated defects or name narrower owning tickets.

## Validation

Use the CSH-033/040 bounded PTY transport and CSH-054 cleanup budgets. Run native
macOS, Linux Docker, ASan/UBSan, `make test-jobs test-jobs-pty test-harness`, and
the full suites. Use readiness/terminal predicates, never sleeps as proof of
state. Retain every failing run and every capability skip with an owner.
Full UP/XSI and genuinely unspecified outcomes stay separately classified.
