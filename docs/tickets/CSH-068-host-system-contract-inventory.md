# CSH-068: Inventory the complete required host utility contract

- Status: ready
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

- [ ] Enumerate the required utility collection for the selected POSIX.1-2024 profile with clause/page links and justified exclusions.
- [ ] Link every applicable utility to a supplied provider plus qualifying evidence, or a concrete missing-contract owner and limitation.
- [ ] Document PATH, packages, fallback shell, OS/libc/filesystem/credential assumptions and reproducible setup.
- [ ] Keep stock-host gaps, qualified subset results and complete-system qualification distinct in the parent audit.

## Validation

Review the normative §1.6 inventory independently of tests/host_utility_cases.py. Validate executable identities and representative public dispatch with zero gap allowances for any declared qualified subset; a successful selected suite does not qualify the full host.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.
