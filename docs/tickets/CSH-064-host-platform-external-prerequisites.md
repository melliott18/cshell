# CSH-064: Supply external prerequisites for remaining host contracts

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-063
- Branch: Assigned when work starts
- Issue: [#127](https://github.com/melliott18/cshell/issues/127)

## Goal

Own the individually retained conditions from [CSH-063](CSH-063-host-platform-residual-qualification.md)
and `tests/host_capability_limits.py`. Utility, libc and platform vendors retain
implementation ownership. Bounded checks do not qualify a parent utility family
or open the CSH-012 gate.

## Scope

- Recheck strict unequal-ID ACL predicates when the selected vendor implementation
  changes, preserving actual read/write/execute controls and exact test/bracket/libc
  identities. Retain both false grants and rejected grants as failures.
- Supply a disposable privileged Darwin environment for ordered ACL entries,
  inheritance and controlled identities; retain its absence separately otherwise.
- Investigate the supplied `fakeowner` bind profile separately: socket-type
  predicates fail and cross-user chmod succeeds despite denial expectations.
- Supply additional ACL-capable filesystems or credential namespaces. Unsupported
  setup, unexpected ACL metadata and timeouts remain failures with diagnostics and
  actual mount identity. Never modify real accounts, protected mounts or disk contents.
- Individually qualify or retain the locale/catalog, printf libc/stack/full-format,
  echo policy/threshold, per-utility filesystem/resource/interruption and physical
  terminal conditions. Missing root, locales and stat-only block witnesses remain
  separate. Record a concrete new supplied capability before repeating qualification.

## Acceptance criteria

- [ ] Each residual has assertions or an individual source, actual environment and
  executable identity, reason, qualification owner and implementation owner.
- [ ] Predicate and setup failures remain strict and distinct from limitations.
- [ ] Claimed profiles pass runtime/PTY integration; changed C receives ASan/UBSan.
- [ ] Queries, measured credentials, fixture bounds and unmet requirements stay
  separate, with no parent utility promotion.

## Validation

Start with [CSH-063 evidence](../evidence/csh-063/README.md). Preserve normal,
strict unequal-ID and unsupported-setup records independently, including source
hashes and exact selected vendor identities. Only claim physical hardware or
privileged Darwin behavior when a disposable environment is actually supplied.
