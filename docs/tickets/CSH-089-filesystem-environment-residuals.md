# CSH-089: Supply remaining filesystem environments after metadata qualification

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-088
- Branch: `test/CSH-089-filesystem-environments`
- Issue: [#189](https://github.com/melliott18/cshell/issues/189)

## Goal

Own the individually open contracts after CSH-088. Preserve the existing
CSH-072/080/084/085/086/087/088 assertions, exact selected-provider provenance and stock
failures. Utility/libc/platform vendors retain implementation ownership.

## Individual open dispositions

Every utility includes U-034 direct exec and U-040 common defaults. The current
machine-readable ledger is `tests/host_filesystem_residuals.json`; the normative
section map is `tests/host_filesystem_contracts.json`.

| Utility | Remaining contract | Required environment and reason |
| --- | --- | --- |
| [`basename`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/basename.html) | Argument/allocator exhaustion, diagnostic locales and output failures beyond independently armed EBADF/EPIPE remain unqualified. | per-child limits and installed diagnostic locales. Argument/allocator failure and diagnostic locale oracles are not supplied; CSH-084 covers only two stdout errors. |
| [`dirname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dirname.html) | Allocator/resource errors beyond stdout EBADF/EPIPE, alternative double-slash policies and further locale repertoires remain unqualified. | per-child resource controls and alternate locale definitions. Two stdout faults do not exercise allocation, argument limits or alternate locale/slash policies. |
| [`cp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cp.html) | Further recursive/multiple-operand graphs and non-C interactive overwrite, traversal cycles and remaining graph combinations, special files beyond FIFOs, cross-filesystem attributes, ACL/privileged ownership preservation, quota/ENOSPC/EIO and interrupted partial copies remain unqualified. Operand/nested-link -H/-L/-P, ordinary owner/mode/timestamps and bounded EFBIG have selected witnesses. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. CSH-086 supplies C-locale single-file yes/no and both -f/-i orders on an owned PTY; stock Darwin declines incorrectly return 1. CSH-087 adds all four yes/no combinations for two operands, missing-middle continuation, and one-child recursive overwrite yes/no; arbitrary graphs remain open. | disposable credentials, two private filesystems, ACL/quota/capacity and fault profiles. Ordinary continuation does not supply privileged ownership, devices or filesystem faults. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. Owned C-locale terminal decisions do not supply multiple operands, recursive graphs or other locales. CSH-087 supplies bounded C-locale multi-operand and recursive decisions only, not arbitrary graphs or locales. |
| [`dd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dd.html) | Additional block/unblock and noerror combinations, short/interrupted device I/O and signal statistics remain unqualified. CSH-080 adds ordinary block/unblock, C-locale case conversion, sync, block+sync, odd swab, seek/truncate/notrunc and skip/count. Darwin stock sync input counts fail; the selected GNU dd is required. EBCDIC/ascii/ibm are XSI-shaded, outside the selected base profile. | scoped short-read/EINTR/EIO controls and active-operation signal delivery. Regular-file conversions do not exercise interrupted or failing input recovery. |
| [`df`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/df.html) | Unspecified/default and 512-byte formats, all-filesystem enumeration, quotas, privilege-dependent availability and live capacity boundaries need a disposable filesystem oracle. | private bounded filesystem with independently measured allocation/quota and credentials. The host volume changes concurrently and must not be filled for an oracle. |
| [`du`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/du.html) | Recursive allocation totals, -a/-s, operand -H, nested -L, last-option precedence and a same-directory hard-link pair now have bounded private-graph witnesses. Cross-device -x, unreadable subtrees, shared extents, arbitrary graphs and overflow remain unqualified. | disposable cross-device/denied/shared-extent filesystems and bounded overflow controls. Pre-exec lstat block/inode measurements supply only the authored graph. They do not measure shared physical extents, mount boundaries, inaccessible traversal or overflow. |
| [`file`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html) | Numeric byte equality/comparisons/bit tests, hexadecimal/octal masks and native short equality have matching and nonmatching samples. Other numeric types/ranges, database precedence and -d/-M/-i, default nonempty/encoding classification, symlink errors and localized descriptions remain unqualified. | additional authored type/range/precedence databases, independent encoding samples and locale profiles. The authored byte/short continuation rules do not establish every type, signed boundary, default database, classification or locale. |
| [`find`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) | Strict -newer comparisons at equal and adjacent representable nanoseconds and -H/-L reference-symlink following now have measured private witnesses. Other expressions/actions, wall-clock age boundaries, descriptor/depth exhaustion and non-UTF-8 matching remain unqualified. CSH-080 expression and batched-exec witnesses and CSH-084 ordinary owner-mode EACCES remain bounded. | per-child descriptor limits, deeper trees, timestamps and non-UTF-8 matching oracles. Bounded expression cases do not establish exhaustion or arbitrary locale matching. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`ln`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html) | remaining directory/symlink combinations, cross-device and permission errors, hard-link count limits and filesystem failures remain unqualified. Selected -L/-P precedence, symlink-inode hard links and existing-target preservation have witnesses. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. ln -i is a vendor extension absent from the selected POSIX base synopsis/options, not an open base requirement. | disposable cross-device/credential/link-limit profiles. Hard-link and continuation witnesses do not supply these environments. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`ls`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html) | Long numeric listings for regular files, hard links, directories, FIFOs and symlinks, plus C-locale size/mtime/atime sorting with ties and reversal now have measured private witnesses. Name-based owner/group rendering, recent timestamps, block units, remaining sorting switches, recursive graphs, terminal formatting, non-C collation and I/O exhaustion remain unqualified. CSH-084 ordinary owner-mode EACCES remains bounded. | authored metadata/time/block graphs, owned PTYs, non-C collation and I/O limits. The bounded C ordering switches do not qualify metadata formats or non-C ordering. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`mkdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html) | Further symbolic modes/parents, total path limits, ACL inheritance, access denial and capacity exhaustion remain unqualified. CSH-080 adds final -m versus parent umask, existing mode preservation and continuation after an ENOTDIR prefix. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. | private ACL/credential and bounded capacity/path-limit profiles. Parent modes and ENOTDIR continuation are not ACL or access-denial evidence. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`mkfifo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkfifo.html) | Additional symbolic/ACL behavior and capacity exhaustion remain unqualified. CSH-080 adds sequential symbolic copy/removal and existing-node error continuation; FIFO transfer remains outside creation. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. | private ACL/capacity profile and remaining symbolic-mode tables. Creation witnesses do not establish data transfer, ACLs or exhausted filesystems. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`mv`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html) | Further multiple-operand and non-C interactive decisions, directory replacement beyond the authored empty/nonempty targets, cross-filesystem copy/remove fallback, metadata/ACL preservation and interrupted or exhausted destination remain unqualified. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. CSH-086 supplies C-locale single-file yes/no and last -f/-i precedence on an owned PTY. CSH-087 adds two-operand yes/no combinations, missing-middle continuation and same-device empty/nonempty directory replacement. | private source/destination filesystems, ACL/credential profiles and interruption controls. Same-filesystem rename/continuation does not exercise copy/remove fallback. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. Owned C-locale terminal decisions do not supply multiple operands, recursive graphs or other locales. CSH-087 supplies only the authored operand decisions and same-device directory targets; EXDEV fallback and other graphs remain open. |
| [`pathchk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pathchk.html) | Inaccessible prefixes, path total limits and alternate filesystems/repertoires remain unqualified. CSH-080 adds -P and -p/-P order combinations with empty and dash-prefixed components. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. | controlled inaccessible prefixes and measured alternate filesystem limits. Portable spelling cases do not establish real path or credential boundaries. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`pax`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pax.html) | pax/cpio formats and extended headers, remaining options/patterns, privileged identities, character-set conversion, multi-volume and recovery remain unqualified. The selected pinned pax repairs ustar mode encoding and final partial writes and requires the complete existing type-graph, truncation, EPIPE, EFBIG and Linux virtual-device ENOSPC assertions. Original Apple/Linux stock-provider failures remain separately retained. | independent pax/cpio/extended-header fixtures, credentials, encoding and multi-volume oracle. Ustar fixtures and selected repairs do not qualify other formats or recovery. |
| [`pwd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html) | Inaccessible ancestors, deleted directories, total PATH_MAX and allocation/stdio failures remain unqualified by this subset. CSH-080 adds -L/-P last-option precedence with an independently authored logical cwd. | disposable denied/deleted ancestors, path and libc fault controls. Option precedence does not supply permission or allocation boundaries. |
| [`readlink`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/readlink.html) | Byte/repertoire combinations beyond the selected three invalid UTF-8 bytes, libc-internal allocation failures and true filesystem limits remain unqualified. | arbitrary byte/repertoire fixtures, real filesystem limits and libc-internal fault controls. CSH-084 covers opaque link bytes in C/UTF-8 and an independently proved EACCES prefix. This does not qualify all byte combinations, libc internals or kernel resource limits. |
| [`realpath`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/realpath.html) | Permission/namespace races, libc-internal allocation failures, double-leading-slash policy and exact resource boundaries remain unqualified. CSH-080 adds test-only provider call-site ENOMEM including dynamic links and relative/absolute missing-final fallback; it does not inject libc internals. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. | controlled namespace races/credentials, exact link/path limits and libc-internal faults. Call-site injection does not qualify libc internal recovery or races. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`rm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | Recursive descriptor/depth exhaustion, disposable mount boundaries, further operand continuation, permissions, races and prompt locales/recursive graphs remain unqualified; yes/no controlling-PTY decisions are bounded witnesses. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. CSH-087 adds negative descent with operand continuation, affirmative leaf removal followed by yes/no final directory removal, recursive symlink non-traversal, and last -f/-i precedence. Negative child responses, nested branching and other prompt graphs remain open. | private mount/depth/credential profiles and automated recursive prompt/race controls. One-level continuation and yes/no PTY witnesses do not supply mount boundaries. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. CSH-087 supplies one-child recursive C-locale decisions only, not arbitrary recursion, declined children, mount or depth limits. |
| [`rmdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rmdir.html) | Ancestor permissions, total depth/path boundaries and other filesystem errors remain unqualified. CSH-080 adds symlink rejection and continuation after a nonempty operand. CSH-084 now supplies ordinary owner-mode EACCES at a private unsearchable prefix; other permission/credential and listed contracts remain open. | private credentials, bounded path/depth and filesystem failure profiles. Symlink/continuation cases do not establish permission or capacity behavior. The bounded search-denial witness does not supply privileged identities, ACLs, races or other filesystem errors. |
| [`touch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html) | Period/comma subsecond dates, T/space separators, UTC/local fixed-offset TZ and -a/-m nanosecond isolation now have bounded witnesses. Remaining date/range forms, arbitrary symlink graphs, current-time tolerances, permission/ACL errors and timestamp range failures remain unqualified. | independent clock/range/symlink and permission/ACL environments. The exact .002-second target and .125-second baseline are independently proved representable before execution. They do not qualify unsupported ranges, current-clock behavior, ACLs or arbitrary date precision. |

## Retained conditions

Keep the original CSH-064 evidence and reasons immutable, and preserve the
CSH-072 bounded witnesses. All four conditions remain open:

- `U-040/pwd-access-path-limits`: inaccessible ancestors, total PATH_MAX and independent permissions.
- `U-040/find-depth-locale-limits`: descriptor/depth exhaustion and additional locale matching.
- `U-040/ls-size-collation`: non-C collation and filesystem/size exhaustion.
- `U-040/rm-depth-mount-prompt`: disposable mount/depth exhaustion, arbitrary recursive graphs and negative child responses.

## Acceptance criteria

- [x] Supply each environment and a clause-derived independent oracle, or retain its explicit open disposition and next owner.
- [x] Require zero selected-profile allowances and exact provider/build provenance.
- [x] Record native/Linux output, status, effects, setup errors and cleanup separately; distinguish call-site/libc injection, kernel faults and actual filesystem exhaustion.
- [x] Update the current section map, ownership manifest and U-034/U-040 evidence without rewriting historical evidence.

## Validation

Run `make test-host-inventory test-host-profile test-host-filesystem-allocation
test-host-filesystem-provider-audit test-host-filesystem-residual
test-host-filesystem-isolated test-host-filesystem-interactive
test-host-filesystem-decisions test-host-filesystem-metadata` on native macOS and Linux as an unprivileged
fixture identity. Retain separate nonzero stock `make test-host-filesystem-audit`
and stock `tests/host_filesystem.py --extended-only --provider-audit` records.
Add bounded setup/failure/timeout cleanup regressions for new environments.
Use only private disposable filesystems and credentials. Never fill the host
volume or use protected mounts; `/dev/full` is not filesystem exhaustion.
Privileged provisioning requires an isolated runner; prompts require owned PTYs.

CSH-087 supplies bounded C-locale recursive and multi-operand decisions and
same-device empty/nonempty directory replacement. These do not supply arbitrary
graphs, declined recursive children, non-C prompts, mount boundaries or depth
exhaustion. All four retained conditions remain open under this ticket.

CSH-088 adds measured ls numeric metadata and size/time ordering, plus exact
find -newer and reference-symlink comparisons. These cases do not qualify whole
utilities or close any of the four retained conditions.

## Implementation and current dispositions

CSH-089 adds ten cases / 30 assertions for declined children, nested traversal
and final parent decisions on owned C-locale PTYs, including errors after
accepting a still nonempty parent and continuation to a later operand. Private
one-child chains avoid traversal-order assumptions. Exact transcripts, output
channels, status, bytes/link text and directory effects are independently checked.
Five new harness regressions cover bad transcripts/effects/status/channels,
partial setup, timeout cleanup in every terminal mode and provider prompt dialects.

The pinned selected GNU rm provider restores the final explicit `-i` parent
prompt that GNU suppresses after declining nested traversal. Both platforms
select this patched source, with exact archive/patch/build/executable provenance.
All older assertions remain mandatory and all original stock failures are
preserved. The original table above records incoming scope; the current section
map and residual ledger record the new bounded witnesses and assign every
unsupplied environment and all four retained conditions to
[CSH-090](CSH-090-filesystem-environment-residuals.md) ([#191](https://github.com/melliott18/cshell/issues/191)).
This uses the explicit-disposition acceptance alternative. Arbitrary graphs,
mount/depth/locale environments and whole utility contracts remain open.

The complete requested command set plus `make test-host-filesystem-recursive`
passes on macOS UID 501 and Debian Linux Docker UID 10001: 1227/1243 selected
filesystem assertions, 1162 integration assertions, 10 inventory tests and
49 filesystem harness tests. The focused recursive target has 30 passes on
each. Separate stock audits retain 73 native and 42 Linux failures (the latter
includes six new missing-parent-prompt failures); stock provider audits retain
16/8 failures. Every filesystem case records successful cleanup. Native
selected-PATH runtime and PTY suites also pass. See
[CSH-089 evidence](../evidence/csh-089/README.md) for raw results, source identity,
provider provenance, setup corrections and exact command/exit records.

The branch is stacked on CSH-088 published commit
`3bb23df15fd49456f2bfc38606fc8813ec111ec4`. That dependency is implemented but
unmerged; integration remains gated on CSH-088. The shared allocator reserved
CSH-090/#191, and live ticket identity validation passes.
