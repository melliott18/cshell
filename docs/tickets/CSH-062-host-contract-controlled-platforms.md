# CSH-062: Supply remaining controlled host platforms

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-061
- Branch: test/CSH-062-controlled-platforms
- Issue: [#116](https://github.com/melliott18/cshell/issues/116)

## Goal

Own the individually sourced residual inventory retained by
[CSH-061](CSH-061-host-environment-residuals.md). Utility/libc vendors retain
implementation ownership; bounded evidence does not qualify utility families
or open the CSH-012 gate.

## Scope

- Recheck the strict unequal-ID GNU test/bracket ACL grant with updated
  utility/libc identities; retain the success expectation and vendor diagnosis.
- Supply a disposable privileged Darwin environment for ordered allow/deny and
  inherited ACLs with controlled identities; retain its absence separately.
- Extend Linux ACL filesystem and credential combinations beyond one named user
  or supplementary group, including unequal-ID supplementary groups.
- Qualify or individually retain every row in `tests/host_capability_limits.py`,
  including locale/catalog, printf libc/stack/format, echo policy/exec threshold,
  per-utility filesystem/resource/interruption and physical-terminal conditions.
- Preserve separate missing-root, missing-locale and stat-only block witnesses;
  use only private fixtures and owned processes, never real disk contents,
  protected mounts or modifications to real user accounts.

## Acceptance criteria

- [x] Each condition has independent assertions or machine-readable source,
  actual environment/executable identity, reason and next owner.
- [x] Rejected ACL grants remain failures, never allowances or expected denials.
- [x] Claimed profiles pass native/Docker runtime and PTY integration; changed C
  receives ASan/UBSan coverage and retained reproduction evidence.
- [x] Queries, measured credentials, fixture limits and unmet requirements remain
  distinct; no parent utility-family promotion.

## Validation

Start with [CSH-061 evidence](../evidence/csh-061/README.md). Run non-root block,
controlled root, strict unequal ACL, alternate BusyBox, runtime/PTY and focused
sanitizer scopes. Physical hardware and filesystem claims require an explicitly
supplied disposable environment.


## Implementation and validation

Implemented on `test/CSH-062-controlled-platforms` in a separate managed worktree.
[Retained evidence](../evidence/csh-062/README.md) covers 108 additional controlled
ACL cases (324 invocation assertions): multiple named users, two supplementary
groups, named-user precedence, unrelated groups and masks, for access/inherited
read/write/execute. Actual bytes and execution markers independently check the
permission predicates. `--fixture-root` selects a supplied disposable filesystem
and records its actual device/mount identity. Unsupported fixture setup now
retains command/status/diagnostic failures in the qualification JSON.

Native block and non-root Docker profiles pass 1168 assertions each. Debian 13
overlay and disposable ext4-volume controlled profiles pass 1849 each. BusyBox
passes 1144. The updated coreutils 9.7-3/libc6 2.41-12+deb13u4 still reject
unequal-ID ACL grants: each strict filesystem run retains 1735 passes and 114
failures, zero gaps, exit 1. Direct libc/kernel/actual-open probes retain the
vendor diagnosis and exact identities. Tmpfs on this Docker kernel has no ACL
support; 666 setup failures and 1183 passing unrelated assertions remain a
failed profile, never a qualification.

Native and Docker focused ASan/UBSan checks pass their normal profiles; the
instrumented unequal-ID run reproduces the same 114 predicate failures without
sanitizer diagnostics. Native, Docker GNU, BusyBox and ext4-volume integrations
each pass 3905 runtime, 30 jobs PTY, 32 runtime PTY, one job-notification and one
terminal-fault case. Native/Docker harness self-tests pass 80 each.

All 28 residual rows remain individually sourced, with actual environment,
executable identity, reason and next owner
[CSH-063 / #122](CSH-063-host-platform-residual-qualification.md). Missing root,
locales and stat-only block witnesses remain separate. No privileged Darwin or
physical terminal environment was supplied. Vendor ownership is unchanged;
parent utility families remain open and CSH-012 stays closed. Ready for review,
not yet integrated.
