# CSH-068: Inventory the complete required host utility contract

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: Assigned when work starts
- Issue: [#137](https://github.com/melliott18/cshell/issues/137)

## Goal

Expand the system-wide host obligation into a reviewable inventory instead of treating the test harness utility subset as the complete POSIX utility collection.

## Scope

- XCU §1.6 and U-034/U-040. Inventory required utilities for the selected base profile, each applicability decision, selected executable/provider and missing package or behavior contract.
- Relate the shell fallback /bin/sh and default search path to the claimed execution environment.
- CSH-064 continues to own its thirty stable residual conditions and conditional prerequisites for the already selected host utilities; reference that work rather than opening another sequence of equivalent platform tickets.
- Installation currently consists of a repository-local build with no install target; do not imply system replacement or a certified host distribution.

## Acceptance criteria

- [x] Enumerate the required utility collection for the selected POSIX.1-2024 profile with clause/page links and justified exclusions.
- [x] Link every applicable utility to a supplied provider plus qualifying evidence, or a concrete missing-contract owner and limitation.
- [x] Document PATH, packages, fallback shell, OS/libc/filesystem/credential assumptions and reproducible setup.
- [x] Keep stock-host gaps, qualified subset results and complete-system qualification distinct in the parent audit.

- [ ] Qualify the remaining external utility contracts assigned here by the closure
  inventory, or transfer individual contracts to narrower open implementation owners.

## Validation

Review the normative §1.6 inventory independently of tests/host_utility_cases.py. Validate executable identities and representative public dispatch with zero gap allowances for any declared qualified subset; a successful selected suite does not qualify the full host.

## Inventory completion and remaining ownership

The [complete inventory](../host-system-inventory.md) supplies 155 indexed utility
pages, the `[` spelling and 15 special builtins with applicability, actual native
and Debian providers, exact executable identities and per-utility open contracts.
This completes inventory for CSH-012. This ticket stays open as the concrete
owner for the unqualified external contracts named there; qualification is not
inferred from executable presence. CSH-064's narrower conditions retain their
existing owner. Complete or transfer those contracts before closing this owner.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.
