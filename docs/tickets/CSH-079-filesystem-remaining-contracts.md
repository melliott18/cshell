# CSH-079: Qualify remaining filesystem provider and fault contracts

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-072
- Branch: Assigned when work starts
- Issue: [#158](https://github.com/melliott18/cshell/issues/158)

## Goal

Complete the individual open contracts retained after CSH-072's bounded native
and Linux qualification. This is not a whole-family passing claim. Preserve
[CSH-072 evidence](../evidence/csh-072/README.md) and its stock-provider failures;
selected utility/libc/platform vendors retain implementation ownership.

## Individual remaining contracts

Every row includes U-034 exec accessibility and U-040 common defaults. The
[section-by-section map](../../tests/host_filesystem_contracts.json) contains
source hashes, all normative headings, actual assertion IDs and explicit
unqualified dispositions. Informative sections are not runtime requirements.

| Utility / normative page | Required next work |
| --- | --- |
| [`basename`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/basename.html) | Empty and double-slash policy, multibyte suffixes, argument/stdio exhaustion and diagnostic locales remain unqualified. |
| [`dirname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dirname.html) | Empty/double-slash policy, redundant slash combinations, multibyte paths and write/resource errors remain unqualified. |
| [`cp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cp.html) | Interactive overwrite, -H/-L graph traversal, cycles, special files, cross-filesystem attributes, ACL/ownership preservation, quota/ENOSPC/EIO and interrupted partial copies remain unqualified. |
| [`dd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dd.html) | Remaining block/unblock, character-set/case conversions, seek/notrunc/sync/noerror combinations, short/interrupted I/O and signal statistics remain unqualified; RLIMIT_FSIZE is not disk exhaustion. |
| [`df`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/df.html) | Unspecified/default and 512-byte formats, all-filesystem enumeration, quotas, privilege-dependent availability and live capacity boundaries need a disposable filesystem oracle. |
| [`du`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/du.html) | Recursive allocation totals, hard-link deduplication, -a/-s/-x/-H/-L, unreadable subtrees, shared extents and overflow need independent filesystem-specific accounting. |
| [`file`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html) | Non-empty/magic/encoding classification, -d/-h/-i/-M/-m, magic-file parsing/precedence, symlink errors and locale-dependent descriptions require supplied magic databases and independent samples. |
| [`find`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) | Remaining expression/actions and precedence, batched exec, time/size/permissions, -H/-L cycles, descriptor exhaustion and non-UTF-8 locale matching remain unqualified. |
| [`ln`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html) | Interactive replacement, directory/symlink option combinations, cross-device and permission errors, hard-link count limits and filesystem failures remain unqualified. |
| [`ls`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html) | Long and numeric metadata, timestamps, size/block units, sorting switches, recursive graphs, terminal formatting, locale collation beyond C and I/O exhaustion remain unqualified. |
| [`mkdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html) | Symbolic modes, intermediate-parent umask details, maximum path totals, ACL inheritance, access denial and filesystem exhaustion remain unqualified. |
| [`mkfifo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkfifo.html) | Default/symbolic modes, operand continuation, ACL inheritance, existing-node errors and filesystem exhaustion remain unqualified; FIFO data transfer is outside creation witness. |
| [`mv`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html) | Interactive decisions, directory replacement, cross-filesystem copy/remove fallback, metadata/ACL preservation and interrupted or exhausted destination remain unqualified. |
| [`pathchk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pathchk.html) | -P and option combinations, inaccessible existing prefixes, empty operands, path total limits and alternate filesystems/character repertoires remain unqualified. |
| [`pax`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pax.html) | pax/cpio formats and extended headers, list/append/options, pattern substitution, hard links/special files, identities, character-set conversion, multi-volume, truncation and recovery remain unqualified. Only one-member ustar encoding/decoding and copy links are witnessed. |
| [`pwd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html) | Logical/physical option precedence, inaccessible ancestors, deleted directories, total PATH_MAX and allocation/stdio failures remain unqualified by this new subset; historical witnesses remain separate. |
| [`readlink`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/readlink.html) | The selected local provider repairs the stock nonlink diagnostic and checks dynamic 600-byte links, -n, --, invalid operands and closed stdout. Arbitrary byte/locale combinations, allocation failure and true filesystem limits remain unqualified. |
| [`realpath`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/realpath.html) | The selected local provider repairs -e/-E, validates directory components despite Darwin libc trailing-slash behavior, and checks dangling links, missing prefixes, dot-dot, loops, last-option precedence and closed stdout. Permission/namespace races, allocation faults, double-leading-slash policy and exact resource boundaries remain unqualified. Missing-final fallback permits at most 40 link expansions. |
| [`rm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | Recursive descriptor/depth exhaustion, disposable mount boundaries, operand continuation, permissions, races and prompt locale/recursive decisions remain unqualified; yes/no controlling-PTY decisions are bounded witnesses. |
| [`rmdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rmdir.html) | Symbolic-link/ancestor permissions, operand continuation, total depth/path boundaries and filesystem errors remain unqualified. |
| [`touch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html) | -a/-m isolation, -d date/time/zone forms, symlink handling, current-time tolerances, permission errors, unsupported timestamps and operand continuation remain unqualified. |

## Retained conditions

| Stable condition | Supplied CSH-072 witness; capability still required |
| --- | --- |
| `U-040/pwd-access-path-limits` | Physical cwd at measured NAME_MAX; still requires controlled inaccessible ancestors, total PATH_MAX and independently checked permission failures. |
| `U-040/find-depth-locale-limits` | UTF-8 single-character matching under 64 levels; still requires descriptor/depth exhaustion and further locale matching oracles. |
| `U-040/ls-size-collation` | 512 independently ordered C-locale entries; non-C collation and filesystem/size exhaustion remain open. |
| `U-040/rm-depth-mount-prompt` | Yes/no decisions on an owned controlling PTY, exact prompts and independent file effects; disposable mount/depth-exhaustion and recursive prompt combinations remain open. |

These original IDs and historical reasons remain immutable. Their ownership
transfer does not erase the supplied witnesses or turn missing capabilities into
passes. No privileged mounts or developer disk contents may be used as fixtures.

## Acceptance criteria

- [ ] Supply each row's missing capability and clause-derived independent oracle,
  or retain an individual, justified open disposition with an explicit next owner.
- [ ] Preserve zero allowances in the CSH-072 selected profile; repair any new
  required-contract failures with exact provider/build provenance.
- [ ] Retain native and Linux identities, strict outputs/status/effects, setup
  failures and cleanup records separately. Do not qualify a full utility from
  selected passing examples.
- [ ] Update the section map, current ownership manifest and U-034/U-040 maps.

## Validation

Run `make test-host-inventory`, `make test-host-profile`, and explicit stock
`make test-host-filesystem-audit` on both platforms. The stock audit is expected
to fail for the retained provider contracts; its nonzero status is evidence, not
a passing check. Add bounded failure/timeout cleanup regressions with each new
capability. Supply separate disposable quota/ENOSPC/EIO and credential profiles
before claiming those behaviors.
