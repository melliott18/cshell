# CSH-061: Resolve remaining host environment contracts

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-060
- Branch: Assigned when work starts
- Issue: [#110](https://github.com/melliott18/cshell/issues/110)

## Goal

Own the residual conditions retained by [CSH-060](CSH-060-extended-host-environments.md).
A passing bounded profile does not qualify a utility page or satisfy CSH-012.
Utility/libc vendors remain responsible for their implementations.

## Scope

- Investigate the Debian 12 GNU test/bracket ACL grant failure with unequal
  real/effective IDs. Keep `--controlled-identities --unequal-acl` strict: a
  rejected grant must fail, never become an expected success or known-gap pass.
- Extend named-user ACL coverage to default/inherited ACLs, writes/execute,
  supplementary groups and Darwin ACLs using controlled identities.
- Retain or qualify every individually sourced condition in
  `tests/host_capability_limits.py`: other locales/catalogs, printf libc/stack
  failures and full format combinations, other echo policies and exact exec
  thresholds, filesystem/resource/interruption and physical-terminal contracts.
- Keep unavailable root, locale and stat-only block witnesses separately visible.
  Use only private fixtures and owned children; never real disk contents,
  protected mounts or unrelated processes.

## Acceptance criteria

- [ ] Address each residual with independent assertions or retain its source,
  actual environment, reason and next owner in machine-readable evidence.
- [ ] Resolve or explicitly retain the unequal-ID ACL failure with exact
  executable/libc identities and the unchanged grant expectation.
- [ ] Pass the claimed native/Docker profile scopes and dependent runtime/PTY
  suites; instrument changed C with ASan/UBSan.
- [ ] Keep system queries, utility constraints, fixture bounds, actual credentials
  and unmet requirements distinct; do not promote parent utility families.

## Validation

Use CSH-060's [reproduction commands](../evidence/csh-060/README.md), including
non-root stat-only block devices, controlled root fixtures, the separate strict
unequal-ACL reproducer, BusyBox policy and focused sanitizers. Physical-terminal
and filesystem-specific work requires a supplied controlled environment.
