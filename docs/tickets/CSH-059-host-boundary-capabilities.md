# CSH-059: Extend qualified host boundary capabilities

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-056
- Branch: test/CSH-059-host-boundary-capabilities
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

- [x] Each scoped condition has bounded assertions or a capability limitation
  naming the source, host environment, reason and next owner.
- [x] Record actual selected executable identities and resource/query values;
  distinguish system ceilings, utility limits and harness protections.
- [x] Run native/Docker qualification and existing utility-dependent fixtures
  after any profile change, with strict gaps preserved.
- [x] Update stable condition rows without promoting parent utility families or
  opening CSH-012 while applicable requirements remain unmet.

## Validation

Use `make test-host-profile`, the explicit non-root block-node path documented
in CSH-056 evidence, and focused ASan/UBSan checks for changed host adapters.
Keep default-host failures separate from the opt-in profile. The environment
and capability limits are inherited evidence scope, not waived requirements.


## Implementation and validation

Implemented in a separate managed worktree on
`test/CSH-059-host-boundary-capabilities`. The [condition map](../host-contract-profile.md)
and [retained evidence](../evidence/csh-059/README.md) record 32 new bounded cases
(96 invocation assertions), child resource and fixture-filesystem queries, and
27 individually sourced residual limitations. Remaining work is owned by
[CSH-060](CSH-060-extended-host-environments.md) ([#106](https://github.com/melliott18/cshell/issues/106)).

The printf investigation reproduced a `%b` defect: decoded NUL bytes truncated
libc `%s` output and corrupted padding/precision. A declared local vendor patch
writes decoded bytes with their length; binary/numbered/precision/stop and
UTF-8 regression assertions pass. The upstream license and pinned provenance
remain visible. Shell runtime sources are unchanged.

Native macOS 14.8.7 arm64 and Debian 12 Docker arm64 each pass 1015 strict
profile assertions with non-root denial and stat-only block nodes. Focused
ASan/UBSan qualification also passes 1015 assertions on both hosts. Profile
PATH reruns pass 3113 runtime cases, 48 PTY cases and 73 harness self-tests per
host. Stock-host runs retain their 12 native / 9 Docker known gaps separately.
Exact commands, source/binary hashes, queried values and the corrected Docker
evidence-collector retry are recorded in the linked evidence. No whole utility
family is promoted and CSH-012 remains closed.
