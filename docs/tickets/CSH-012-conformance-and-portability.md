# CSH-012: Audit POSIX conformance and portability

- Status: in-progress
- Type: test
- Kind: milestone
- Parent: None
- Depends on: CSH-008, CSH-009, CSH-010, CSH-011
- Children: CSH-036, CSH-037
- Branch: Milestone; reconciliation on docs/CSH-012-evidence-reconciliation
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

- [ ] Each applicable requirement links to implementation and passing evidence,
  or an explicit open ticket and limitation.
- [x] Conditional, unspecified, and implementation-defined behavior is labeled;
  permitted implementation choices are documented.
- [ ] CI runs the documented checks from a clean checkout on supported systems.
- [ ] All discovered defects have regression coverage and resolved or linked
  tickets; waived tests include a reason and scope.
- [ ] Installation, invocation, architecture, and contribution docs are coherent
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
- [ ] The original acceptance criteria above pass together, with recorded
  cross-feature evidence and all completion prerequisites satisfied.

Child dependencies control when each work item can start. The parent
dependencies are completion prerequisites; they are not inherited start gates.
Completing one child does not establish the milestone or POSIX compliance.

## Implementation notes/evidence

Passing a differential suite is useful evidence but does not itself prove POSIX
conformance. External certification, if desired, is separate from this ticket.

### Evidence reconciliation (2026-09-28)

The [post-integration review](../evidence-reconciliation.md) records the
CSH-049/050 review dispositions, current matrix/owner accounting and an
independently built runtime sample at `8ffb99e`. Both children and all four
completion prerequisites (CSH-008/009/010/011) are done. That completes the
dependency gate, not this milestone's original acceptance criteria.

The classification/claim-policy boxes above reflect the existing base-profile,
D-001–D-008 and clause-map documentation. Remaining boxes still need a combined
requirement-level review: scoped passing fixtures and completed implementation
tickets are not complete-family evidence. CSH-049/050 retain their unchecked
platform criterion; CSH-057 owns the unresolved integration timeouts and CSH-061
owns the host residual inventory, including the unequal-ID ACL failure.
The linked review distinguishes historical CI passes from current-source
validation and preserves capability skips. No compliance claim is authorized.

### CSH-056 host-profile gate

The [qualified host profile](../host-contract-profile.md) resolves the five
CSH-052 stock-host gaps and records selected residual witnesses. This applies
only with the documented PATH and executable identities; stock macOS/Debian
are not promoted. [CSH-059](CSH-059-host-boundary-capabilities.md) and
[CSH-060](CSH-060-extended-host-environments.md) record subsequent bounded
qualification. [CSH-061](CSH-061-host-environment-residuals.md) now owns each
remaining host capability/limit in the linked inventory, including the strict
unequal-ID ACL grant failure. U-034/U-040 and the
system-wide §1.6 obligation remain open, so this completion gate stays closed.
