# CSH-064: Supply external prerequisites for remaining host contracts

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-063
- Branch: docs/CSH-064-acceptance-reconciliation
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

- [x] Each residual has assertions or an individual source, actual environment and
  executable identity, reason, qualification owner and implementation owner.
- [x] Predicate and setup failures remain strict and distinct from limitations.
- [x] Claimed profiles pass runtime/PTY integration; changed C receives ASan/UBSan.
- [x] Queries, measured credentials, fixture bounds and unmet requirements stay
  separate, with no parent utility promotion.
- [ ] Acceptance-review regression: a probe timeout terminates and reaps the
  complete owned process tree before reporting or removing fixtures, with a
  regression through the nested `_chmod-child`/selected-utility path.

## Validation

Start with [CSH-063 evidence](../evidence/csh-063/README.md). Preserve normal,
strict unequal-ID and unsupported-setup records independently, including source
hashes and exact selected vendor identities. Only claim physical hardware or
privileged Darwin behavior when a disposable environment is actually supplied.


## Implementation and validation

Implemented in a separate managed worktree on
`test/CSH-064-host-platform-prerequisites`. [Retained evidence](../evidence/csh-064/README.md)
includes reproduction, exact source/executable/libc identities, complete normal,
strict and unsupported records, integration logs, a prerequisite inventory and
a machine-readable audit.

Supplied a new disposable Linux user namespace mapping fixture IDs 10001..10005
to outer IDs 30001..30005, without modifying accounts. Qualification JSON now
records UID/GID maps, setgroups policy and user/mount namespace links. Numeric
ACL metadata validation covers every controlled ACL fixture; malformed and
duplicate metadata remain setup failures.

The independent fakeowner probe reproduces socket stat EINVAL while a one-byte
AF_UNIX transfer succeeds. Both external chmod and direct os.chmod allow a
non-owner mode change with empty groups and no effective capabilities. The same
probe passes all eight assertions on overlay; fakeowner retains five failures.
Two separate residual conditions retain these platform failures.

Native macOS passes 1162 host assertions and ordinary Debian sid passes 2281.
The mapped namespace passes 2269 with twelve private-device setup failures;
its complete profile is not qualified. Both ordinary and mapped strict runs
retain 204 predicate failures (132 rejected grants, 72 false grants), separately
from the twelve namespace setup failures. Exact coreutils 9.10/libc 2.43 hashes
are unchanged from CSH-063; this is a namespace recheck, not a vendor update.
Tmpfs retains 1098 setup failures. Fakeowner retains 1110 setup and nine
assertion failures. All runs have zero gap allowances.

Native, ordinary Linux and mapped Linux each pass 3905 runtime assertions,
30 jobs PTY and 32 runtime PTY cases, notification and terminal-fault checks,
and 86 harness self-tests. No C source changed; no new sanitizer result is claimed.

All thirty stable residual conditions retain individual sources, actual
environment/executable identities, reasons and concrete required capabilities.
CSH-064 retains qualification ownership pending those capabilities; selected
utility/libc/platform vendors retain implementation ownership. Privileged Darwin,
physical terminals and other unavailable requirements remain separate. Queries,
measured credentials, fixture bounds and unmet requirements are not conflated.
No parent utility or CSH-012 gate is promoted. The implementation was integrated
by [PR #131](https://github.com/melliott18/cshell/pull/131) as `3e82c1d`;
acceptance remains open under the reconciliation below.


## Acceptance reconciliation

[The acceptance review and retained reproduction](../evidence/csh-064-acceptance/README.md)
review exact PR head `c0e61ef`, independently of later main changes. The source
and artifact audit passes; recomputing 12,616 saved non-setup assertion verdicts
agrees with their records. Fresh review checks pass 86 native harness self-tests
and eight focused Linux overlay controls. Original runtime/PTY results retain
their original provenance; this review does not claim another full profile run.

Acceptance is held for **P2: the probe timeout leaves its selected utility
running**. `tests/host_platform_probe.py:command` kills only its direct child.
The outer `_chmod-child` wrapper's deadline starts before its nested selected
chmod deadline, so the wrapper can die while chmod survives. The disposable
Linux reproducer records a five-second timeout and the still-sleeping utility's
PID, UID/GID and capabilities, then explicitly kills its own process.

CSH-064 / #127 owns the repair, and the **cshell test-harness implementation**
is its implementation owner. This project defect is separate from the thirty
utility/libc/platform residual conditions and needs no new external capability
to fix. Use one deadline and cleanup owner for the complete process tree,
terminate/reap descendants before returning or removing fixtures, retain a
strict timeout failure, and add a regression through the actual nested path.

The original four criteria retain their supported evidence; the newly discovered
cleanup regression is an explicit additional open acceptance gate. Status is
`in-progress` and #127 stays open until the repair, regression and validation are
integrated. A merged implementation, passing ordinary cases or hosted check
completion do not discharge this gate. External capability/vendor ownership and the
closed CSH-012 completion gate remain unchanged. This reconciliation records the
review; it does not implement the repair.
