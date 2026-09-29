# CSH-012 audit closure

**Audit complete; known gaps are documented and owned; POSIX conformance remains
unclaimed.** This closure supplements the [earlier acceptance review](conformance-acceptance-review.md)
without changing its source-qualified results. PR #139 integrated this closure as
`0bf8b0220abc5e06b5751382bf68bdc225feaef9` on 2026-09-29 UTC. CSH-012 is done.

## Original acceptance criteria

| Criterion | Final audit decision | Concrete evidence |
| --- | --- | --- |
| Every applicable requirement has evidence or an explicit open ticket/limitation | Satisfied as accounting | [131-family ledger](requirement-review-ledger.md), seven linked clause maps, and [complete utility inventory](host-system-inventory.md): 155 indexed utility pages, `[` alias, 15 special builtins. Every applicable external contract is assigned through the [current CSH-070–078 ownership ledger](host-system-inventory.md#current-contract-ownership), preserving narrower passing evidence and unqualified CSH-064 residuals. Shell defects/qualification limits remain CSH-065–067. |
| Conditional, unspecified and implementation-defined behavior is labeled | Satisfied | Existing D decisions and base/UP/XSI classification retained; full utility inventory also explicitly identifies conditional CD/SD/FR/UU entries and mixed base/optional forms. No base requirement is excluded because one option is shaded. |
| CI runs documented clean-checkout checks on supported systems | Satisfied for audited baseline, with later outcomes disclosed | Exact `c8c1c91` Ubuntu/GCC, macOS/Clang and Docker normal/PTY/profile/harness/ASan/UBSan jobs all pass; fresh clean native normal run passes. At identical production/test bytes in `5b56328`, the subsequent Docker push fails H11 and the PR macOS job is cancelled. These are retained separately, not called passes. |
| Defects have regression coverage and resolved or linked tickets; waivers state reason/scope | Satisfied as accounting | [Defect dispositions](defect-dispositions.md) link integrated fixes, runnable strict failing reproducers, enforced existing tests, explicit missing historical details and eleven finite observations owned by CSH-069. Scoped acceptance waives a causal-repair demonstration for past observations only, never current/future assertions. |
| Installation, invocation, architecture and contribution docs are coherent | Satisfied | Earlier corrections retained; the new inventory specifies repository-local build, actual PATH/provider selection, `/bin/sh` fallback, package and OS/locale/filesystem/credential limits. Current indexes link this closure. |
| Claims identify edition/scope/evidence and remain withheld while applicable requirements are unmet | Satisfied | POSIX.1-2024 base Shell Command Language/sh remains the target. No system or shell compliance claim; required providers and behavior still have measured gaps. |

Both children (CSH-036/037) and all four completion prerequisites (CSH-008–011)
are done. Their integration and the original cross-feature evidence were already
reconciled; no new children or dependency gates are invented here.

The earlier review treated repair/default-suite integration and complete
qualification as additional audit gates. The original criteria permit explicit
open tickets and limitations. Runnable required-success reproducers, scoped
historical dispositions and complete requirement ownership therefore allow the
audit to close while those implementation tickets remain open.

## Work that remains open

| Owner | Remaining obligation |
| --- | --- |
| [CSH-070–078](host-system-inventory.md#current-contract-ownership), with [completed CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md) | Qualification of thirty retained selected host residuals and conditional prerequisites; CSH-064's bounded capability work and project probe-cleanup repair are done. |
| [CSH-065 / #134](tickets/CSH-065-interactive-parser-recovery.md) | Repair interactive main-parser recovery and integrate its strict reproducers into the normal regression suite. |
| [CSH-066 / #135](tickets/CSH-066-resource-bounded-nesting.md) | Remove arbitrary parser/executor/evaluation/expansion limits with safe resource handling. |
| [CSH-067 / #136](tickets/CSH-067-shell-locale-pathname-qualification.md) | [Finite qualification](locale-pathname-qualification.md) supplies public and instrumented witnesses, applicability decisions and external prerequisites P1–P6; broader host capability claims remain conditional. |
| [CSH-070–078](host-system-inventory.md#current-contract-ownership) | Supply and qualify 101 explicitly enumerated external utility contracts transferred by CSH-068; availability does not establish these contracts. |
| [CSH-069 / #138](tickets/CSH-069-historical-failure-dispositions.md) | Finite H01–H11 triage ready for review; [CSH-069 evidence](evidence/csh-069/README.md) repairs a demonstrated fixture race while retaining unknown historical attribution. Same-ticket recurrence ownership continues after integration. |

Native standard-PATH inventory lacks four base names: gettext, msgfmt, ngettext
and timeout. The recorded Debian image lacks sixteen exec-required base names,
listed individually in the machine inventory. No missing provider was installed
or utility invoked for its side effects to make this review pass.

## Verification and integration

[Closure evidence](evidence/csh-012/closure-5b56328/README.md) and
[final integration checks](evidence/csh-012/integration-008c1f9/README.md) retain official
source and executable inventories, platform/package identities, both subsequent
CI snapshots and all completed job logs, exact failed outcomes, disposition
hashes and reproducible consistency checks. Production C source is unchanged from the audited baseline. During integration,
main advanced to `008c1f9` with the separately reviewed CSH-064 probe-cleanup
repair (`65ca752`, PR #140) and scoped acceptance (PR #141). Those test/Makefile/CI
changes and their [passing integration/regression evidence](evidence/csh-064-completion/README.md)
are preserved. The final document-only closure changes are checked against that
new main baseline; earlier snapshots still identify their original source bytes.

No new full runtime run is needed for these documentation/inventory edits:
passing baseline evidence and the later failed/cancelled attempts are all
included, with their exact revisions. Strict runtime tests remain enabled and
unchanged. Closure is an audit decision, not a claim that every CI attempt passed.

PR #139 is merged; the ticket is marked `done` in `main` and issue #13 is
synchronized and closed as completed. Recurrence goes to the explicit
owner; omitted or falsely characterized requirements/evidence reopen the audit.

## Integration reconciliation (`008c1f9`)

CSH-064 is now done and issue #127 is closed. Its added project-owned timeout
cleanup defect has causal before/after coverage: two failing cases become three
passing cases, with all owned descendants reaped and unrelated children preserved.
Fresh native/Linux integration results and retained strict fakeowner failures are
linked above. This is an additional resolved defect, separate from H11's
context-fixture assertion. H11 remains unknown cause.

The original thirty host conditions remain unqualified where recorded. CSH-070–078
are their [current qualification owners](host-system-inventory.md#current-contract-ownership), using the retained CSH-064
records and concrete capability prerequisites; vendor implementation ownership
remains unchanged. Closing the bounded CSH-064 work does not qualify those
conditions or leave the audit pointing only to a closed implementation ticket.

## CSH-069 triage follow-up

[CSH-069](evidence/csh-069/README.md) reproduces a concrete early-reaping race in
the H11 fixture on native macOS and Linux, repairs its synchronization, and adds
forced-schedule coverage to the strict default context suite. The historical
job's missing errno remains unavailable; its exact cause is not retroactively
claimed. H01–H10 dispositions and all original failed/skipped outcomes remain
unchanged. CSH-069 owns recurrence for all eleven observations after integration;
this finite triage does not change CSH-012's audit closure or conformance claims.
