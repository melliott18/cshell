# CSH-057: Extend qualified host boundary capabilities

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-056
- Branch: Assigned when work starts
- Issue: [#101](https://github.com/melliott18/cshell/issues/101)

## Goal

Extend the bounded host integration profile without treating system resource
queries or a selected operation as certification of an entire utility page.
The [CSH-056 boundary inventory](../host-contract-profile.md#explicit-remaining-capability-limits)
is the condition-by-condition scope, source and environment record.

## Scope

- U-035/locale-catalogs and format/allocation limits: catalog absence in the
  standalone FreeBSD printf and untested locales beyond C/French.
- U-036/alternative-policies: user-selected implementations outside the explicit
  Apple/GNU policy sets and multibyte/large-argument boundaries.
- U-037/extended-permissions: ACLs, unequal effective/real identities, and device
  namespaces. Keep ordinary CI's absent block node/root identity/missing French
  locale limitations individually visible; dedicated CSH-056 runs already
  demonstrate non-root denial and stat-only positive block predicates.
- U-040/host-boundaries: per-utility remaining resource, locale, filesystem,
  interruption and physical terminal conditions in the linked inventory.
  No operation may use real disk contents or unrelated processes as fixtures.
- Investigate full printf byte/format semantics beyond CSH-056's selected cases
  before making any whole-page claim about the vendored host implementation.

## Acceptance criteria

- [ ] Each scoped condition has bounded assertions or a capability limitation
  naming the source, host environment, reason and next owner.
- [ ] Record actual selected executable identities and resource/query values;
  distinguish system ceilings, utility limits and harness protections.
- [ ] Run native/Docker qualification and existing utility-dependent fixtures
  after any profile change, with strict gaps preserved.
- [ ] Update stable condition rows without promoting parent utility families or
  opening CSH-012 while applicable requirements remain unmet.

## Validation

Use `make test-host-profile`, the explicit non-root block-node path documented
in CSH-056 evidence, and focused ASan/UBSan checks for changed host adapters.
Keep default-host failures separate from the opt-in profile. The environment
and capability limits are inherited evidence scope, not waived requirements.
