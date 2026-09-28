# CSH-060: Qualify remaining host environments and limits

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-059
- Branch: Assigned when work starts
- Issue: [#106](https://github.com/melliott18/cshell/issues/106)

## Goal

Extend the [CSH-059 condition inventory](../host-contract-profile.md#explicit-remaining-capability-limits)
with controlled environments and independent expectations. This owns the next
qualification step; utility vendors remain responsible for their implementations.
No system query or successful finite operation certifies a complete utility page.

## Scope

- U-035: other locales/catalogs, allocation/format failure and full defined format
  combinations. Retain the CSH-059 binary `%b` regression and local source provenance.
- U-036: independently documented alternative policies and exec-size boundaries.
- U-037: controlled ACLs, unequal real/effective identities and device namespaces;
  preserve separate root/no-block-node/missing-locale limitations in ordinary CI.
- U-040: all residual per-utility filesystem/resource/locale/interruption and
  physical-terminal conditions in `tests/host_capability_limits.py`. Each has a
  source, environment, reason and owner in the retained qualification JSON.
- Use private fixtures and owned children only; never use real disk contents,
  protected mounts or unrelated processes as test data.

## Acceptance criteria

- [ ] Each residual condition is addressed with bounded independent assertions
  or retained with an explicit environment, reason, source and next owner.
- [ ] Native/Docker strict qualification and existing profile-dependent suites
  pass after profile changes; changed C code receives focused ASan/UBSan checks.
- [ ] Actual identities, system queries, utility limits and harness bounds stay
  distinct; parent utility families and CSH-012 stay open while requirements remain.

## Validation

Use `make test-host-profile`, dedicated non-root stat-only block-node runs,
profile PATH `make test-runtime test-pty`, and `make test-harness`. Add controlled
failure checks and environment-specific runs for each newly claimed condition.
