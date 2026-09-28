# CSH-063: Qualify remaining supplied host platforms

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-062
- Branch: Assigned when work starts
- Issue: [#122](https://github.com/melliott18/cshell/issues/122)

## Goal

Own the individually sourced residual conditions retained by
[CSH-062](CSH-062-host-contract-controlled-platforms.md). Utility and libc
vendors retain implementation ownership. No bounded result qualifies a parent
utility family or opens CSH-012.

## Scope

- Recheck the strict unequal-ID ACL grants after a vendor change, retaining
  exact test/bracket/libc identities and independent actual operations.
- Supply a disposable privileged Darwin environment for ordered allow/deny,
  inheritance and controlled identities, or retain its absence separately.
- Extend filesystem/credential coverage beyond the recorded Linux fixtures;
  retain unsupported ACL setup as failures with diagnostics and mount identity.
- Qualify or individually retain every residual in `tests/host_capability_limits.py`,
  including locales/catalogs, printf allocation/stack/format combinations,
  echo policies/exec thresholds, per-utility resource/filesystem/interruption
  contracts and physical terminals.
- Keep missing root, locales and stat-only block witnesses separate. Use private
  fixtures and owned processes, never real disk contents, protected mounts or
  modifications to real user accounts.

## Acceptance criteria

- [ ] Each condition has independent assertions or machine-readable source,
  actual environment/executable identity, reason and next owner.
- [ ] Rejected grants and unsupported fixture setup never become passes or allowances.
- [ ] Claimed profiles pass runtime/PTY integration; changed C receives ASan/UBSan.
- [ ] System queries, measured credentials, fixture bounds and unmet requirements
  remain distinct; no parent utility promotion.

## Validation

Start with [CSH-062 evidence](../evidence/csh-062/README.md). Retain normal and
strict failing records independently, with source and executable hashes.
Physical hardware and privileged Darwin claims require a supplied disposable
environment.
