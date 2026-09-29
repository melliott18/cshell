# CSH-012: Audit POSIX conformance and portability

- Status: review
- Type: test
- Kind: milestone
- Parent: None
- Depends on: CSH-008, CSH-009, CSH-010, CSH-011
- Children: CSH-036, CSH-037
- Branch: Milestone; review on docs/CSH-012-requirement-defect-review
- Issue: [#13](https://github.com/melliott18/cshell/issues/13)

## Goal

Establish an evidence-backed account of POSIX.1-2024 behavior, supported
platforms, and remaining gaps before making a compliance claim.

## Scope

- Audit every applicable Shell Command Language and `sh` utility requirement,
  plus the required utility behavior and selected option groups.
- Complete CI coverage for supported Linux/macOS toolchains, sanitizer builds,
  behavioral suites, and available pseudo-terminal checks.
- Include the documented Docker Linux test path and native macOS checks;
  record container architecture and toolchain/libc versions with results.
- Add differential coverage using installed reference shells, recording their
  versions and distinguishing extensions from standard requirements.
- Exercise locale-sensitive behavior, large inputs, resource failures, and
  parser/expansion robustness with bounded fuzz or generated cases.
- Update user and contributor documentation from verified final behavior.

## Acceptance criteria

- [x] Each applicable requirement links to implementation and passing evidence,
  or an explicit open ticket and limitation.
- [x] Conditional, unspecified, and implementation-defined behavior is labeled;
  permitted implementation choices are documented.
- [x] CI runs the documented checks from a clean checkout on supported systems.
- [x] All discovered defects have regression coverage and resolved or linked
  tickets; waived tests include a reason and scope.
- [x] Installation, invocation, architecture, and contribution docs are coherent
  and link to the current evidence and limitations.
- [x] Any compliance statement names the standard edition, selected scope, and
  evidence, and is withheld while applicable requirements remain unmet.

## Validation

Run the full documented validation procedure on each supported platform and
record compiler, libc, reference-shell, and test-suite versions. Review the
requirements matrix independently against the standard, then reproduce a
sample of its linked cases from a clean checkout.

## Completion gate

- [x] [CSH-036: Conformance matrix](CSH-036-conformance-matrix.md) is done.
- [x] [CSH-037: Portability audit](CSH-037-portability-audit.md) is done.
- [x] The original acceptance criteria above pass together, with recorded
  cross-feature evidence and all completion prerequisites satisfied.

Child dependencies control when each work item can start. The parent
dependencies are completion prerequisites; they are not inherited start gates.
Completing one child does not establish the milestone or POSIX compliance.

## Implementation notes/evidence

Passing a differential suite is useful evidence but does not itself prove POSIX
conformance. External certification, if desired, is separate from this ticket.

### Final audit acceptance and integration

The [closure record](../conformance-closure.md) satisfies all six original
acceptance criteria. The [complete utility inventory](../host-system-inventory.md)
accounts for 155 utility pages, the `[` spelling and 15 special builtins.
The [defect dispositions](../defect-dispositions.md) retain every observed
failure, exact strict tests/reproducers, available identities and missing detail,
including the new Docker context-fixture assertion H11.

CSH-064–069 remain open for explicitly owned implementation/qualification and
diagnosis work. Their repair is not a new dependency of this audit. Acceptance
of unresolved historical observations applies only to audit closure; assertions,
time limits and future CI failure enforcement remain unchanged.

All prerequisites and both children are done. Ready to integrate in PR #139;
status becomes done only after the closure record is on main. The original
criteria above are satisfied as evidence/ownership accounting, not as a POSIX
conformance claim. Audit complete; known gaps are documented and owned;
POSIX conformance remains unclaimed.

### Earlier requirement, defect, platform and documentation review (`c8c1c91`)

The [acceptance review](../conformance-acceptance-review.md) and
[131-family ledger](../requirement-review-ledger.md) supersede the earlier
snapshot's current-state conclusions. CSH-050's repair is integrated and done;
CSH-064 retains thirty stable host residuals and conditional prerequisites.
New open tickets CSH-065–069 own interactive main-parser recovery, arbitrary
nesting limits, shell locale/pathname qualification, the complete host utility
inventory and finite historical failure dispositions.

Fresh strict probes report 15 PASS and 10 FAIL, retaining required-success
oracles. A clean native full normal run passes, while explicitly preserving
stock-host gaps and unavailable capabilities. Baseline Linux and Docker CI jobs
and macOS 15 CI jobs pass all stages, including ASan/UBSan.
[Commands, identities, logs and results](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained independently of earlier evidence.

At that earlier snapshot, documentation and supported-platform CI acceptance were checked; classification
and claim policy remained checked. Requirement accounting and defect
regression/disposition were unchecked for the concrete reasons in
the review. Those accounting gates are now satisfied by the final closure record.

### Historical evidence reconciliation (`07ee1cb`)

At that snapshot, the [reconciliation](../evidence-reconciliation-current.md) superseded
stale lifecycle and residual-owner statements in the
[earlier snapshot](../evidence-reconciliation.md), while preserving its results.
Both children and all four completion prerequisites are done. CSH-046–049,
CSH-051/052 and CSH-057/061/062/063 are scoped completions; CSH-050 remains in
review and CSH-064 owns current host qualification residuals.

The audit accounts for all 131 families (115 applicable, 16 profile exclusions)
and all 416 forward/reverse ownership pairs. Of 640 retained artifact entries,
638 match exactly; two README changes are traced to their original matching
Git blobs and later documented corrections. Historical manifests and failed
runs are preserved. The fresh clean-archive native sample and separately
identified CI snapshots are linked from the review; pending CI is not a pass.

At that snapshot, classification and claim-policy criteria stayed checked. The other four
criteria and combined completion gate were unchecked for the specific reasons
in the review's acceptance table. This reconciliation does not supply a new
sentence-level normative audit or full supported-platform qualification.
No POSIX compliance claim is authorized.

### Qualified host-profile limitation

The [qualified host profile](../host-contract-profile.md) resolves the five
CSH-052 stock-host gaps only with its documented PATH and executable identities.
CSH-059/060/061/062/063 add bounded qualification; stock macOS/Debian are not
promoted. [CSH-064](CSH-064-host-platform-external-prerequisites.md) now owns the
30 stable host residuals plus conditional limits, including strict unequal-ID
ACL predicate failures and unqualified tmpfs/`fakeowner` profiles. U-034/U-040,
other incomplete utility contracts and the system-wide §1.6 obligation remain
open for implementation/qualification after audit completion. CSH-057's
[formal retention disposition](../evidence/csh-057-retention-disposition/README.md)
accepts only the historical observation for its scoped completion; #99 retains
recurrence ownership and the unchanged retention test stays enforced.
