# CSH-062: Supply remaining controlled host platforms

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-061
- Branch: Assigned when work starts
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

- [ ] Each condition has independent assertions or machine-readable source,
  actual environment/executable identity, reason and next owner.
- [ ] Rejected ACL grants remain failures, never allowances or expected denials.
- [ ] Claimed profiles pass native/Docker runtime and PTY integration; changed C
  receives ASan/UBSan coverage and retained reproduction evidence.
- [ ] Queries, measured credentials, fixture limits and unmet requirements remain
  distinct; no parent utility-family promotion.

## Validation

Start with [CSH-061 evidence](../evidence/csh-061/README.md). Run non-root block,
controlled root, strict unequal ACL, alternate BusyBox, runtime/PTY and focused
sanitizer scopes. Physical hardware and filesystem claims require an explicitly
supplied disposable environment.
