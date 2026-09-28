# CSH-063: Qualify remaining supplied host platforms

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-062
- Branch: test/CSH-063-host-platform-residuals
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

- [x] Each condition has independent assertions or machine-readable source,
  actual environment/executable identity, reason and next owner.
- [x] Rejected grants and unsupported fixture setup never become passes or allowances.
- [x] Claimed profiles pass runtime/PTY integration; changed C receives ASan/UBSan.
- [x] System queries, measured credentials, fixture bounds and unmet requirements
  remain distinct; no parent utility promotion.

## Validation

Start with [CSH-062 evidence](../evidence/csh-062/README.md). Retain normal and
strict failing records independently, with source and executable hashes.
Physical hardware and privileged Darwin claims require a supplied disposable
environment.


## Implementation and validation

Implemented in a separate managed worktree on
`test/CSH-063-host-platform-residuals`. [Retained evidence](../evidence/csh-063/README.md)
contains source/executable/libc identities, complete normal and strict records,
compiler/platform details, independent operation controls and reproduction commands.

Added 144 Linux ACL cases (432 invocation assertions) for owner/owning-group
selection, denial without falling back to other permissions, owner/other access
outside the mask and default ACL creation-mode restrictions. Numeric ACL and
ownership mismatches fail fixture setup. Setup timeouts now retain diagnostics,
and failed setup records carry their fixture mount identity. Qualification JSON
embeds the current build/test source inventory; Docker includes its Dockerfile.

Native profiles pass 1162 assertions without a block witness and 1168 with one.
Debian sid non-root passes 1168 with a private stat-only block node. Controlled
Debian 13 and sid overlay profiles each pass 2281. The vendor recheck moves from
coreutils 9.7/glibc 2.41 to coreutils 9.10/glibc 2.43. Each strict unequal-ID profile
retains 2077 passes and 204 predicate failures: 132 rejected grants and 72 false
grants, with corresponding actual operations passing and no allowances. Direct
libc/kernel/open probes and exact imports/hashes support continued vendor ownership.

Tmpfs retains 1098 setup failures. The additional `fakeowner` host bind mount
retains 1110 setup failures and nine assertion failures (socket predicates and
cross-user chmod); neither filesystem is qualified. Source digests match across
all final records. Native, Debian 13 and sid each pass 3905 runtime assertions,
30 jobs PTY and 32 runtime PTY cases, notification/terminal-fault checks and 83
harness self-tests. Focused sid ASan/UBSan helpers reproduce all 204 strict vendor
failures without sanitizer diagnostics. No production C source changed.

Every residual remains individually sourced with actual environment/executable,
reason and [CSH-064 / #127](CSH-064-host-platform-external-prerequisites.md) as next
qualification owner; utility/libc/platform vendors retain implementation ownership.
Missing privileged Darwin, physical terminals, root/locale/block witnesses and
other unmet contracts stay separate. Parent utility families and CSH-012 are not
promoted. Ready for review; not yet integrated into `main`.
