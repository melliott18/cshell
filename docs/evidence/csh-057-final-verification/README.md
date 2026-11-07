# CSH-057 final hosted verification and integration

Verified on 2026-10-02. Repair head
`48af5bc524795f3d12ae0ce7ec0cc8722e9cf38f` passes the complete PR workflow.
The duplicate push workflow has a separate CSH-054 failure; both macOS jobs
pass the repaired CSH-057 checks. No failed observation is discarded.

## Hosted results

| Workflow | Ubuntu | Docker | macOS 15 normal and ASan/UBSan |
| --- | --- | --- | --- |
| [PR run 36914086960](https://github.com/melliott18/cshell/actions/runs/36914086960) | Pass | Pass | Pass; complete job 54 min 02 s |
| [Push run 36914080409](https://github.com/melliott18/cshell/actions/runs/36914080409) | Pass | Pass | Failure; 17 CSH-054 exit-operand timeouts, job 44 min 07 s |

Both macOS logs explicitly pass:

- Normal and sanitizer CHILD_MAX retention and crash-notification isolation.
- Repeated background resumes and terminal-fault restoration in normal,
  qualified-host and sanitizer runs.
- The queued-output cleanup regression and all 95 harness self-tests.
- All 2,464 CSH-058 signal-edge cases in normal and sanitizer runs.

Sanitized retention completes in 79.476 seconds (PR) and 85.254 seconds
(push), within the repaired 120-second aggregate bound. Both trace artifacts
finish with no case, diagnostic or watcher-cleanup failure, no truncation and
no alarm-query failure. Controlled stalled-child records intentionally retain
their expected failures; they are distinguished from the positive fixture.
The hosted sanitizer configuration uses `detect_leaks=0`, so these results do
not claim leak detection. Focused native/Linux evidence is retained in the
[PTY repair](../csh-057-pty-teardown/README.md),
[retention repair](../csh-057-retention-budget/README.md), and
[Mach isolation](../csh-057-terminal-crash-notification/README.md) records.

## Separate failure retained under CSH-054

Push macOS job `110543631273` fails ASan/UBSan exit-operand batches 0–15 in
string/file modes and batches 16–95 in string/file/stdin modes. Each exceeds
the unchanged five-second case limit with a partial output prefix. Lines
21958–22026 of its complete log retain all 17 failures; line 22318 reports
344 passed and 17 failed, followed by `make: *** [test-traps] Error 1` at
line 22327. GitHub records exit code 2, not a job-budget cancellation.
The PR peer passes the full 361-case signal suite in both builds.

The passing peer does not diagnose the failures. Neither a production defect
nor an unsolvable condition is established. [CSH-054 / #90](../../tickets/CSH-054-signal-contract-gaps.md)
is reopened to own diagnosis and disposition, retaining the
[earlier five-batch observation](../csh-057-terminal-crash-notification/hosted-verification/README.md).
Its source and case limits are unchanged by the CSH-057 stack.

## Review and integration

Independent reviews found no actionable blocker. Production `src/` and
`include/` are unchanged. Retention instrumentation is confined to the
lifecycle fixture; Mach isolation is confined to the deliberate SIGQUIT child.
PTY cleanup transfers descriptor ownership once, kills owned groups before
closing the master, and then uses the unchanged one-second child wait.
Exact oracles and five-second phase alarms remain enforced. Only the 32-cycle
public PTY case receives ten seconds; 29 other cases retain five seconds.

The stack was merged in dependency order with merge commits:

| PR | Integration commit |
| --- | --- |
| [#167](https://github.com/melliott18/cshell/pull/167) | `0938eeb326e1c581626085af3baf8b9d270b9cc4` |
| [#172](https://github.com/melliott18/cshell/pull/172) | `d06891e649db0bfbc2e338b2fa204822adad80b1` |
| [#173](https://github.com/melliott18/cshell/pull/173) | `57e8c40420a7be764737032eda8296abe71a0b93` |

The tested head, tested PR merge `72190b7bf1f117bd11e9a063852e58dd62588698`,
and final `main` integration `57e8c40` all have tree
`490c2136fb7fdc6c9cc63f7f795fb2649f4faa3b`. A direct Git tree comparison
finds no file differences. This closure update changes documentation/evidence
only; it does not require repeating the same source checks. Newly triggered
integration workflows are separate observations, not the basis of this record.

[CSH-057 / #99](../../tickets/CSH-057-job-lifecycle-boundaries.md) is complete
with its recurrence policy intact. Original unrecorded Mach receiver identity
and other historical uncertainty remain documented as potential host/fixture
issues, not proven operating-system bugs. CSH-054/058 and broader conformance
gates remain separate.

## Retained artifacts

[audit.json](audit.json) maps exact check lines, timestamps, identities, all six
job conclusions and retention results. [audit.tar.gz](audit.tar.gz) preserves
both complete macOS logs, run/job metadata, failure annotations, both uploaded
retention archives and the tested workflow/exit-operand fixture.
[integration.json](integration.json) records merge/tree identity and review
scope. [inventory.json](inventory.json) hashes the retained files. Original
raw log/patch whitespace in older evidence is intentionally preserved.
