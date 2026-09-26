# CSH-050: Close jobs, signal and trap evidence gaps

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: Assigned when work starts
- Issue: [#82](https://github.com/melliott18/cshell/issues/82)

## Goal

Separate base and conditional portions, map exact runtime/PTY/API cases to each obligation, resolve or retain concrete CSH-044/045 defects, and reproduce foreground/background startup, terminal restoration, notifications, trap timing/inheritance and wait/status cases. Record capability skips with reasons and owners and never count intermittent failure as a pass.

## Explicit current limitation

The retained job/signal/trap witnesses do not form complete requirement-family evidence, and intermittent failures are tracked in CSH-044/045. Base signal/asynchronous-list/wait semantics remain applicable even while the UP utility profile is unselected; implemented job-control extensions need their supported behavior and terminal capability conditions recorded separately.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [EXEC-009](../posix-matrix.md#exec-009) | Launch asynchronous lists without waiting; track IDs/status, stdin redirection and required interactive messages. |
| [JOB-001](../posix-matrix.md#job-001) | Initialize process/foreground groups according to controlling-terminal and foreground/background startup state. |
| [JOB-002](../posix-matrix.md#job-002) | Group foreground/background pipelines and lists; hand off and regain the terminal, retaining stopped jobs and terminal settings. |
| [JOB-003](../posix-matrix.md#job-003) | Track job numbers/known PIDs and issue stopped/completed notifications at monitor/notify-dependent times. |
| [SIG-001](../posix-matrix.md#sig-001) | Apply interactive shell signal dispositions and asynchronous-list SIGINT/SIGQUIT inheritance. |
| [SIG-002](../posix-matrix.md#sig-002) | Defer trapped signals during foreground commands; interrupt wait with status above 128 before dispatching the trap. |
| [SIG-003](../posix-matrix.md#sig-003) | Reset/retain signal and trap state as required across subshells, functions, substitutions, exec and exit. |
| [U-008](../posix-utilities.md#u-008) | `exit`: current environment termination, 0–255 statuses, applicable signal-derived statuses, omitted operand, EXIT trap behavior. |
| [U-015](../posix-utilities.md#u-015) | `trap`: set/reset/ignore/list, Issue 8 `-p` and reinput, EXIT, saved status, signal inheritance/subshell listing; XSI numeric signals under O-021. Invalid conditions warn and return non-zero without becoming special-builtin errors. Exclude undefined SIGKILL/SIGSTOP installations from pass/fail oracles. |
| [U-026](../posix-utilities.md#u-026) | `kill`: `-s`, `-l`, default TERM, PID/process-group/job operands, signal-name/status mapping and diagnostics. Supply/record external host kill as well; alternate forms under O-021. |
| [U-032](../posix-utilities.md#u-032) | `wait`: all/selected known children, last-operand status, unknown PID 127, status retention and consumed IDs; interrupts/traps and enabled job-control operands. |

Relevant documented choices: D-007, JOB-001/JOB-002/JOB-003 applicability, U-015/U-026 conditional XSI portions. Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/jobs_cases.py](../../tests/jobs_cases.py)
- [tests/jobs_fixture.c](../../tests/jobs_fixture.c)
- [tests/trap_cases.py](../../tests/trap_cases.py)
- [tests/traps.py](../../tests/traps.py)
- [tests/runtime_cases.py](../../tests/runtime_cases.py)

These are starting points for inspection, not claims that the complete rows
already pass. Reuse exact case names and assertions where they are sufficient;
add or split fixtures only for a concrete coverage gap.

## Acceptance criteria

- [ ] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [ ] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [ ] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [ ] Matrix rows and reverse ownership links reflect only the verified scope;
  broad rows are split where necessary and the CSH-012 compliance gate remains
  closed while any applicable requirements are unmet.

## Validation

Run the applicable focused suites above and the integration paths documented in
[Testing](../testing.md), including `make test test-pty test-harness`, Docker
and ASan/UBSan checks where the changed paths require them. Record exact case
names and results following the [evidence rules](../posix-evidence.md).
Reference-shell comparisons are separate observations, never normative oracles.

## Implementation notes/evidence

Allocated by the CSH-037 follow-up audit at baseline `58ca5c3`. The explicit
limitation and complete row list above replace reliance on already-completed
implementation tickets as owners of remaining verification work.
