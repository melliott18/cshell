# CSH-084: Supply residual filesystem environments and contract oracles

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-080
- Branch: test/CSH-084-filesystem-residual-environments
- Issue: [#178](https://github.com/melliott18/cshell/issues/178)

## Goal

Own the individual open contracts retained after CSH-080. Selected utility,
libc and platform vendors retain implementation ownership. Neither bounded
passing examples nor unavailable environments qualify an entire utility page.

## Original CSH-080 handoff contracts

Each row includes U-034 direct exec accessibility and U-040 common defaults.
The machine-readable ledger is `tests/host_filesystem_residuals.json`; the
normative section map is `tests/host_filesystem_contracts.json`.

| Utility | Remaining contract | Required environment / reason |
| --- | --- | --- |
| [`basename`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/basename.html) | Argument/stdio exhaustion and diagnostic locales remain unqualified. The selected empty-string and double-slash policy and UTF-8 suffix removal now have CSH-080 witnesses. | per-child limits and installed diagnostic locales. No argv/stdio exhaustion or localized error oracle is supplied. |
| [`dirname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dirname.html) | Write/resource errors, alternative double-slash policies and further locale repertoires remain unqualified. Empty/double/redundant slash cases and a UTF-8 path now have CSH-080 witnesses. | per-child resource controls and alternate locale definitions. The new path cases do not exercise write or allocator failure. |
| [`cp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cp.html) | Interactive overwrite, traversal cycles and remaining graph combinations, special files beyond FIFOs, cross-filesystem attributes, ACL/privileged ownership preservation, quota/ENOSPC/EIO and interrupted partial copies remain unqualified. Operand/nested-link -H/-L/-P, ordinary owner/mode/timestamps and bounded EFBIG have selected witnesses. | disposable credentials, two private filesystems, ACL/quota/capacity and fault profiles. Ordinary continuation does not supply privileged ownership, devices or filesystem faults. |
| [`dd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dd.html) | Additional block/unblock and noerror combinations, short/interrupted device I/O and signal statistics remain unqualified. CSH-080 adds ordinary block/unblock, C-locale case conversion, sync, block+sync, odd swab, seek/truncate/notrunc and skip/count. Darwin stock sync input counts fail; the selected GNU dd is required. EBCDIC/ascii/ibm are XSI-shaded, outside the selected base profile. | scoped short-read/EINTR/EIO controls and active-operation signal delivery. Regular-file conversions do not exercise interrupted or failing input recovery. |
| [`df`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/df.html) | Unspecified/default and 512-byte formats, all-filesystem enumeration, quotas, privilege-dependent availability and live capacity boundaries need a disposable filesystem oracle. | private bounded filesystem with independently measured allocation/quota and credentials. The host volume changes concurrently and must not be filled for an oracle. |
| [`du`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/du.html) | Recursive allocation totals, hard-link deduplication, -a/-s/-x/-H/-L, unreadable subtrees, shared extents and overflow need independent filesystem-specific accounting. | private filesystem accounting oracle for directories/hard links/shared extents. st_blocks for one regular file does not establish recursive allocation accounting. |
| [`file`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html) | Non-empty/magic/encoding classification, -d/-h/-i/-M/-m, magic-file parsing/precedence, symlink errors and locale-dependent descriptions require supplied magic databases and independent samples. | authored magic databases, independent nonempty/encoding samples and locale profiles. Empty/directory classifications do not qualify magic parsing or precedence. |
| [`find`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) | Other expressions/actions, timestamp boundaries, descriptor exhaustion and non-UTF-8 matching remain unqualified. CSH-080 adds exact byte/rounded-block size, numeric permissions, negation/grouping and bounded batched exec. | per-child descriptor limits, deeper trees, timestamps and non-UTF-8 matching oracles. Bounded expression cases do not establish exhaustion or arbitrary locale matching. |
| [`ln`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html) | Interactive replacement, remaining directory/symlink combinations, cross-device and permission errors, hard-link count limits and filesystem failures remain unqualified. Selected -L/-P precedence, symlink-inode hard links and existing-target preservation have witnesses. | automated prompt fixtures plus disposable cross-device/credential/link-limit profiles. Hard-link and continuation witnesses do not supply these environments. |
| [`ls`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html) | Long and numeric metadata, timestamps, size/block units, sorting switches, recursive graphs, terminal formatting, locale collation beyond C and I/O exhaustion remain unqualified. | authored metadata/time/block graphs, owned PTYs, non-C collation and I/O limits. The bounded C ordering switches do not qualify metadata formats or non-C ordering. |
| [`mkdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html) | Further symbolic modes/parents, total path limits, ACL inheritance, access denial and capacity exhaustion remain unqualified. CSH-080 adds final -m versus parent umask, existing mode preservation and continuation after an ENOTDIR prefix. | private ACL/credential and bounded capacity/path-limit profiles. Parent modes and ENOTDIR continuation are not ACL or access-denial evidence. |
| [`mkfifo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkfifo.html) | Additional symbolic/ACL behavior and capacity exhaustion remain unqualified. CSH-080 adds sequential symbolic copy/removal and existing-node error continuation; FIFO transfer remains outside creation. | private ACL/capacity profile and remaining symbolic-mode tables. Creation witnesses do not establish data transfer, ACLs or exhausted filesystems. |
| [`mv`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html) | Interactive decisions, directory replacement, cross-filesystem copy/remove fallback, metadata/ACL preservation and interrupted or exhausted destination remain unqualified. | private source/destination filesystems, ACL/credential profiles and interruption controls. Same-filesystem rename/continuation does not exercise copy/remove fallback. |
| [`pathchk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pathchk.html) | Inaccessible prefixes, path total limits and alternate filesystems/repertoires remain unqualified. CSH-080 adds -P and -p/-P order combinations with empty and dash-prefixed components. | controlled inaccessible prefixes and measured alternate filesystem limits. Portable spelling cases do not establish real path or credential boundaries. |
| [`pax`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pax.html) | pax/cpio formats and extended headers, remaining options/patterns, privileged identities, character-set conversion, multi-volume and recovery remain unqualified. The selected pinned pax repairs ustar mode encoding and final partial writes and requires the complete existing type-graph, truncation, EPIPE, EFBIG and Linux virtual-device ENOSPC assertions. Original Apple/Linux stock-provider failures remain separately retained. | independent pax/cpio/extended-header fixtures, credentials, encoding and multi-volume oracle. Ustar fixtures and selected repairs do not qualify other formats or recovery. |
| [`pwd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html) | Inaccessible ancestors, deleted directories, total PATH_MAX and allocation/stdio failures remain unqualified by this subset. CSH-080 adds -L/-P last-option precedence with an independently authored logical cwd. | disposable denied/deleted ancestors, path and libc fault controls. Option precedence does not supply permission or allocation boundaries. |
| [`readlink`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/readlink.html) | Other arbitrary byte/locale combinations, libc-internal allocation failures and true filesystem limits remain unqualified. CSH-080 adds UTF-8 link bytes and test-only provider call-site ENOMEM, distinct from production kernel evidence. | arbitrary byte/repertoire fixtures, real filesystem limits and libc-internal fault controls. Injected provider call-site ENOMEM does not qualify arbitrary bytes or kernel limits. |
| [`realpath`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/realpath.html) | Permission/namespace races, libc-internal allocation failures, double-leading-slash policy and exact resource boundaries remain unqualified. CSH-080 adds test-only provider call-site ENOMEM including dynamic links and relative/absolute missing-final fallback; it does not inject libc internals. | controlled namespace races/credentials, exact link/path limits and libc-internal faults. Call-site injection does not qualify libc internal recovery or races. |
| [`rm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | Recursive descriptor/depth exhaustion, disposable mount boundaries, operand continuation, permissions, races and prompt locale/recursive decisions remain unqualified; yes/no controlling-PTY decisions are bounded witnesses. | private mount/depth/credential profiles and automated recursive prompt/race controls. One-level continuation and yes/no PTY witnesses do not supply mount boundaries. |
| [`rmdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rmdir.html) | Ancestor permissions, total depth/path boundaries and other filesystem errors remain unqualified. CSH-080 adds symlink rejection and continuation after a nonempty operand. | private credentials, bounded path/depth and filesystem failure profiles. Symlink/continuation cases do not establish permission or capacity behavior. |
| [`touch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html) | Remaining -d date/time/zone forms, symlink handling, current-time tolerances, permission errors, unsupported timestamps and operand continuation remain unqualified. Selected -a/-m timestamp isolation has witnesses. | independent subsecond/current-clock/symlink/permission and timestamp-range fixtures. Two integral-second -d forms do not qualify full timestamp precision/range. |

## Retained conditions

These IDs and the original CSH-064 reasons remain immutable. CSH-072's
NAME_MAX cwd, 64-level UTF-8 find, 512-entry C ls and owned-PTY rm witnesses
remain retained. CSH-080's ordinary cases do not complete the residuals.

- `U-040/pwd-access-path-limits`: inaccessible ancestors, total PATH_MAX and independent permission checks.
- `U-040/find-depth-locale-limits`: descriptor/depth exhaustion and additional locale matching oracles.
- `U-040/ls-size-collation`: non-C collation and filesystem/size exhaustion.
- `U-040/rm-depth-mount-prompt`: disposable mount/depth exhaustion and recursive prompt decisions.

## Acceptance criteria

- [x] Supply each individual environment and a clause-derived independent oracle, or retain its explicit open disposition and next owner.
- [x] Preserve zero allowances in the selected profile, with exact provider and build provenance for any repair.
- [x] Retain separate native/Linux output, status, effects, setup failures and cleanup; keep call-site injection separate from libc-internal and real kernel faults.
- [x] Update the section map, ownership manifest and U-034/U-040 evidence without rewriting historical records.

## Validation

Run `make test-host-inventory`, `make test-host-profile`,
`make test-host-filesystem-allocation`, and
`make test-host-filesystem-provider-audit` on native macOS and Linux.
Run explicit stock `make test-host-filesystem-audit` and stock
`tests/host_filesystem.py --extended-only --provider-audit` separately;
nonzero stock audits retain defects and are not passing checks.
Add bounded setup/failure/timeout cleanup regressions for each capability.
No protected mounts or developer disk contents may be used as fixtures.
Quota, actual filesystem ENOSPC, EIO, credentials, and cross-device work require
separate disposable environments; Linux /dev/full is not filesystem exhaustion.
No manual prompting is required: owned PTYs supply scripted responses.
Provisioning privileged volumes/identities may require an isolated runner.


## Implementation and validation

CSH-084 supplies 26 cases / 104 assertions across 16 utilities: independently
verified owner-mode permission denials, authored magic databases, opaque link
bytes in C/UTF-8, and basename/dirname EBADF/EPIPE. All run through direct exec
and public cshell string/file/stdin modes with independent effects and cleanup.
The selected providers require no new repairs; stock readlink's missing denial
diagnostic remains a strict failure on both platforms.

[Evidence](../evidence/csh-084/README.md) records native **914 filesystem,
240 allocation, 1162 host integration** passes and Docker/Linux **930 filesystem,
200 allocation, 1162 host integration** passes, with zero selected failures/gaps.
Both platforms pass the 104 focused assertions, provider audit, inventory and
24 filesystem harness tests. Stock audits remain nonzero and separately retained.
All filesystem fixture cleanup records pass.

The table above preserves the original handoff scope. The current
[section map](../../tests/host_filesystem_contracts.json) and
[residual ledger](../../tests/host_filesystem_residuals.json) narrow the supplied
claims and name every unsupplied environment/reason. Each remaining contract
and all four original conditions transfer to open
[CSH-085](CSH-085-filesystem-isolated-contracts.md) ([#181](https://github.com/melliott18/cshell/issues/181)).
This uses the acceptance criteria's individual-disposition alternative, not a
claim that privileged filesystems, ACLs, quotas, actual ENOSPC/EIO, libc internals
or complete utility semantics have been supplied. No protected mount or host
disk content is used. CSH-080 is implemented but unmerged; this PR is stacked on
its exact head and remains in review until integration.
