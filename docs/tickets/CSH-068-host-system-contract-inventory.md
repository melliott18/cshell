# CSH-068: Inventory the complete required host utility contract

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-068-host-contract-inventory
- Issue: [#137](https://github.com/melliott18/cshell/issues/137)

## Goal

Expand the system-wide host obligation into a reviewable inventory instead of treating the test harness utility subset as the complete POSIX utility collection.

## Scope

- XCU §1.6 and U-034/U-040. Inventory required utilities for the selected base profile, each applicability decision, selected executable/provider and missing package or behavior contract.
- Relate the shell fallback /bin/sh and default search path to the claimed execution environment.
- CSH-064 is complete for its bounded capability work and repaired probe cleanup. This ticket owns further qualification of its thirty retained residual conditions and conditional prerequisites; reference the exact CSH-064 evidence and vendor implementation owners rather than reopening that completed work or creating another sequence of platform tickets.
- Installation currently consists of a repository-local build with no install target; do not imply system replacement or a certified host distribution.

## Acceptance criteria

- [x] Enumerate the required utility collection for the selected POSIX.1-2024 profile with clause/page links and justified exclusions.
- [x] Link every applicable utility to a supplied provider plus qualifying evidence, or a concrete missing-contract owner and limitation.
- [x] Document PATH, packages, fallback shell, OS/libc/filesystem/credential assumptions and reproducible setup.
- [x] Keep stock-host gaps, qualified subset results and complete-system qualification distinct in the parent audit.

- [x] Qualify the remaining external utility contracts assigned here by the closure
  inventory, or transfer individual contracts to narrower open implementation owners.

## Validation

Review the normative §1.6 inventory independently of tests/host_utility_cases.py. Validate executable identities and representative public dispatch with zero gap allowances for any declared qualified subset; a successful selected suite does not qualify the full host.

## Inventory completion and remaining ownership

The [complete inventory](../host-system-inventory.md) supplies 155 indexed utility
pages, the `[` spelling and 15 special builtins with applicability, actual native
and Debian providers, exact executable identities and per-utility open contracts.
This completes inventory for CSH-012. The remaining criterion is satisfied by
transferring all 101 external contracts and all thirty retained conditions to
[CSH-070–078](../host-system-inventory.md#current-contract-ownership). Each ticket
names its utilities, normative pages, measured provider gaps, required capabilities,
strict validation and vendor implementation ownership. Eight conditional
prerequisite reports also have individual owners. No full utility qualification
is inferred from this transfer or from executable presence.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.


## Implementation and validation

Implemented on `test/CSH-068-host-contract-inventory` in a separate managed
worktree. [Completion evidence](../evidence/csh-068/README.md) records the current
ownership manifest, published CSH-070–078 implementation tickets, normative
index/§1.6 review, fresh native/Docker provider identities and exact strict profile
results. Historical source-qualified inventories and CSH-064 evidence are unchanged.

`make test-host-inventory` checks all 101 external contracts, thirty retained
conditions, eight conditional prerequisites and both directions of the utility
ledger, plus 10 regression tests. It runs in `make test` and
`make test-host-profile`, including Docker with the required documentation inputs.
Reports now name current qualification owners instead of completed CSH-064.

Native macOS and Docker/Linux each pass 1162 selected host assertions with zero
failures or gap allowances. The initial Docker missing-document failure is
retained alongside the repaired passing run. Requirement ownership, historical
artifact integrity, local Markdown links and `git diff --check` pass. No production
C changes or full-system qualification are claimed. Ready for review; `done`
requires integration under the repository workflow.
