# CSH-012 audit closure

**Audit complete; known gaps are documented and owned; POSIX conformance remains
unclaimed.** This closure supplements the [earlier acceptance review](conformance-acceptance-review.md)
without changing its source-qualified results. Integration is pending PR #139;
the milestone remains `review` until that change lands in `main`.

## Original acceptance criteria

| Criterion | Final audit decision | Concrete evidence |
| --- | --- | --- |
| Every applicable requirement has evidence or an explicit open ticket/limitation | Satisfied as accounting | [131-family ledger](requirement-review-ledger.md), seven linked clause maps, and [complete utility inventory](host-system-inventory.md): 155 indexed utility pages, `[` alias, 15 special builtins. Every applicable external contract is linked to CSH-068 unless covered by narrower passing evidence/CSH-064 residuals. Shell defects/qualification limits remain CSH-065–067. |
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
| [CSH-064 / #127](tickets/CSH-064-host-platform-external-prerequisites.md) | Thirty stable selected host residuals, conditional prerequisites, strict ACL/namespace/fakeowner failures. |
| [CSH-065 / #134](tickets/CSH-065-interactive-parser-recovery.md) | Repair interactive main-parser recovery and integrate its strict reproducers into the normal regression suite. |
| [CSH-066 / #135](tickets/CSH-066-resource-bounded-nesting.md) | Remove arbitrary parser/executor/evaluation/expansion limits with safe resource handling. |
| [CSH-067 / #136](tickets/CSH-067-shell-locale-pathname-qualification.md) | Qualify the finite shell locale/pattern/pathname conditions and repair demonstrated violations. |
| [CSH-068 / #137](tickets/CSH-068-host-system-contract-inventory.md) | Supply and qualify the explicitly enumerated external utility contracts, or transfer individual contracts to narrower open owners. Inventory work is complete; availability does not establish these contracts. |
| [CSH-069 / #138](tickets/CSH-069-historical-failure-dispositions.md) | Diagnose/triage H01–H11 and recurrence; audit-only acceptance does not establish root causes or repair the context-fixture assertion. |

Native standard-PATH inventory lacks four base names: gettext, msgfmt, ngettext
and timeout. The recorded Debian image lacks sixteen exec-required base names,
listed individually in the machine inventory. No missing provider was installed
or utility invoked for its side effects to make this review pass.

## Verification and integration

[Closure evidence](evidence/csh-012/closure-5b56328/README.md) retains official
source and executable inventories, platform/package identities, both subsequent
CI snapshots and all completed job logs, exact failed outcomes, disposition
hashes and reproducible consistency checks. Production source, tests, Makefile,
Dockerfile and CI workflow bytes are unchanged from the audited baseline.

No new full runtime run is needed for these documentation/inventory edits:
passing baseline evidence and the later failed/cancelled attempts are all
included, with their exact revisions. Strict runtime tests remain enabled and
unchanged. Closure is an audit decision, not a claim that every CI attempt passed.

After PR #139 integrates, record its merge commit, mark the ticket `done` in
`main`, synchronize issue #13 and close it. Recurrence goes to the explicit
owner; omitted or falsely characterized requirements/evidence reopen the audit.
