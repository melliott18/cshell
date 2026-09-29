# CSH-050 application of the later retention disposition

Reviewed main `07ee1cb26ffcec0470977d03789ce0ebb156603a` on 2026-09-29 UTC
(2026-09-28 Pacific). This documentation review supersedes the acceptance hold
in [the earlier CSH-050 review](../csh-050-review/README.md), while preserving
that snapshot and every failed result.

## Independent acceptance decision

CSH-050 accepts the [later CSH-057 retention disposition](../csh-057-retention-disposition/README.md)
as sufficient treatment of the **old** retention observation for its own
bounded evidence scope. The cause stays unknown and the run stays failed.
This acceptance rests on the mapped lifecycle assertions, integrated repairs,
identified passing platform evidence, completed investigation of the available
record, unchanged CI enforcement and explicit same-ticket recurrence ownership.
It does not follow merely from CSH-057's `done` status or another green retry.
CSH-050 does not require recovery of telemetry that the historical run never
captured, or proof that the failure cannot recur.

The residual possibility of an undiscovered defect is accepted for that old
observation only. CSH-057 / #99 still owns a new retention failure under its
reopening rules. No result is converted to a pass, no criterion is weakened,
and no deadline or assertion changes.

**CSH-050 nevertheless remains at review:** a newly observed failure in its
own partial-delivery fixture leaves its platform criterion unmet. That failure
is outside the historical retention disposition.

| CSH-050 criterion | Current assessment |
| --- | --- |
| Clause/condition map | Met for the declared 11 families; the map preserves normative sources, policies, exact assertions and narrower limitations. |
| Remaining applicable cases pass on native macOS and Linux/Docker; skips have reasons/owners | Unmet because `kill state: ungrouped/CONT/after` failed on hosted macOS. The old retention observation is no longer the reason for this unchecked box. Current-main macOS CI is also incomplete at the snapshot. |
| Source/suite, binary, compiler/platform and exact assertions recorded | Met within the retained evidence scope. Local identities remain authoritative; hosted source/job metadata supplements them without claiming hosted binary hashes. The new failed result and full failed-step log are retained. |
| Scoped forward/reverse ownership; CSH-012 gate closed | Met: all 11 pairs agree. Host residuals now have CSH-064 as qualification owner following scoped CSH-063 completion. No parent family is promoted and CSH-012 remains independent. |

## New CSH-050 failure

[Run 36497619126](https://github.com/melliott18/cshell/actions/runs/36497619126)
at `a561d638000970d5efa842985f8364790c27bbf3` failed its native macOS normal
`make test` stage. `kill state: ungrouped/CONT/after` expected status 0 and
`partial delivery: state and final wait status passed\n`; it instead returned
`-14` (SIGALRM) with empty stdout. The 14-case suite reported 13 passes and one
failure. The fixture has a four-second alarm; the runner's five-second bound
was not the reported failure. The buffered final-only output cannot identify
which fixture operation was active. There is no demonstrated root cause yet.

The same job passed `CSH-057 bounded CHILD_MAX retention and eviction` immediately
before the partial-delivery suite. Its later terminal, profile, harness and
sanitizer stages were skipped after the normal-stage failure. Ubuntu and Docker
jobs passed. This is neither a successful full three-platform run nor evidence
that the old retention timeout recurred.

The [complete failed-step log](partial-kill-failure.log.gz) and
[run metadata](run-36497619126.json) preserve the evidence. Comparison with
reviewed main finds no changes in `src/`, `include/`, Makefile, the partial-kill
fixture/generator, retention fixture/JSON, smoke/PTY runners or CI workflow.
Host qualification inputs have changed; the full workloads are not asserted
identical. The failed test remains relevant to CSH-050's current acceptance.

CSH-050 / #82 owns investigation of this new failure. Identify whether it is
a fixture, runtime or environment failure and supply a supported repair or a
separate reviewed disposition with appropriate validation. Passing retries
alone cannot close it, and the old retention decision cannot be reused for it.
Do not reopen CSH-057 solely on the basis of this different fixture's SIGALRM.

## Validation accounting

The JSON files retain exact retrieval times, source commits and job/step results.
These observations are intentionally separate:

| Run / source | Snapshot result |
| --- | --- |
| [36494608216](https://github.com/melliott18/cshell/actions/runs/36494608216), `d466c2d` | Complete success: Ubuntu, macOS and Docker normal/sanitizer workflows. |
| [36494579415](https://github.com/melliott18/cshell/actions/runs/36494579415), `53946e3` | Complete success on all three jobs. |
| [36495093736](https://github.com/melliott18/cshell/actions/runs/36495093736), `66f8900` | Ubuntu and Docker passed; macOS was cancelled. The prior review's pending macOS stage never became a full pass in this run. |
| [36497619126](https://github.com/melliott18/cshell/actions/runs/36497619126), `a561d63` | Failed macOS partial-kill fixture as described above; Ubuntu and Docker passed. |
| [36497702952](https://github.com/melliott18/cshell/actions/runs/36497702952), `b68654d` | Ubuntu and Docker passed; macOS in progress. |
| [36498371612](https://github.com/melliott18/cshell/actions/runs/36498371612) and [36498343483](https://github.com/melliott18/cshell/actions/runs/36498343483), `5b62d15` | Ubuntu and Docker passed; macOS in progress in both runs. |
| [36499777317](https://github.com/melliott18/cshell/actions/runs/36499777317), exact reviewed `07ee1cb` | Ubuntu and Docker passed; macOS queued. Not a complete current-main pass. |

No fresh local runtime or sanitizer run is claimed. This review neither
repeats tests until green nor infers a cause from the job's elapsed duration.
Hosted sanitizer options retain the previously documented environment/LeakSanitizer
limits. Earlier successful runs remain valid for their identified sources,
not proof against the new failure.

[checks.json](checks.json) records unchanged relevant source paths, integrated
disposition ancestry, 188 verified artifact entries across five inventories,
and all 11 forward/reverse scope IDs. This record's own files are hashed in
[artifacts.json](artifacts.json).

External utility gaps, missing locales/credentials and physical-terminal limits
remain individually sourced. [CSH-063](../../tickets/CSH-063-host-platform-residual-qualification.md)
is complete within its qualification scope, with residual external prerequisites
owned by [CSH-064](../../tickets/CSH-064-host-platform-external-prerequisites.md).
Qualified PATH evidence still does not qualify stock-host `kill` or turn a
capability skip into a pass. These owned boundaries do not create an automatic
requirement to leave every upstream audit open indefinitely.
