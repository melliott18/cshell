# CSH-061: Resolve remaining host environment contracts

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-060
- Branch: test/CSH-061-host-environment-residuals
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

- [x] Address each residual with independent assertions or retain its source,
  actual environment, reason and next owner in machine-readable evidence.
- [x] Resolve or explicitly retain the unequal-ID ACL failure with exact
  executable/libc identities and the unchanged grant expectation.
- [x] Pass the claimed native/Docker profile scopes and dependent runtime/PTY
  suites; instrument changed C with ASan/UBSan.
- [x] Keep system queries, utility constraints, fixture bounds, actual credentials
  and unmet requirements distinct; do not promote parent utility families.

## Validation

Use CSH-060's [reproduction commands](../evidence/csh-060/README.md), including
non-root stat-only block devices, controlled root fixtures, the separate strict
unequal-ACL reproducer, BusyBox policy and focused sanitizers. Physical-terminal
and filesystem-specific work requires a supplied controlled environment.


## Implementation and validation

Implemented on `test/CSH-061-host-environment-residuals` in a separate managed
worktree. [Retained evidence](../evidence/csh-061/README.md) includes 108 new
controlled cases (324 assertions): access/default ACL read/write/execute,
named users and supplementary groups, with grant, unrelated-identity and mask
denials and independent actual operations. Numeric ACLs and actual credentials
are recorded. No shell runtime or production utility source changed.

Native and non-root Docker profiles pass 1168 assertions each; controlled
Docker passes 1525; BusyBox passes 1144. Focused ASan/UBSan profiles pass the same
native/controlled counts. Native, Docker and BusyBox runtime/PTY integrations
pass; native/Docker harnesses pass 75 self-tests each.

The strict unequal-ID reproducer retains six grant failures (1519 passes,
zero gaps). Exact binary/libc identities, dynamic linkage and direct access
probes trace the failure to glibc 2.36's mode-bit-only unequal-ID euidaccess
path. Success expectations remain unchanged. A diagnostic sanitizer re-exec
initially lost its environment options and hit LeakSanitizer's credential
limitation; a diagnostic build with the same Linux leak-scan exclusion passes
all three identity probes under ASan/UBSan. Both records are retained.

All 27 existing residual rows remain sourced and individually owned, with an
additional explicit unavailable Darwin ACL row. Privileged Darwin and broader
filesystem/identity/platform conditions belong to
[CSH-062 / #116](CSH-062-host-contract-controlled-platforms.md). Each run retains
actual environment, reason and next owner. Parent utility families and CSH-012
remain open; this ticket is ready for review, not yet integrated.
