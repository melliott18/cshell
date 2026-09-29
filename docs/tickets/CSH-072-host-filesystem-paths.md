# CSH-072: Qualify host filesystem and pathname utilities

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-072-host-filesystem-paths
- Issue: [#144](https://github.com/melliott18/cshell/issues/144)

## Goal

Qualify host filesystem and pathname utilities for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Supply isolated filesystem fixtures for traversal, links, metadata, archive round trips, collation, quotas and I/O faults; measure boundaries without touching protected mounts or real disk contents.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`basename`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/basename.html) | `/usr/bin/basename` / `/bin/basename`; [retained provider/contract row](../host-system-inventory.md#utility-basename). Full applicable behavior remains unqualified. |
| [`dirname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dirname.html) | `/usr/bin/dirname` / `/bin/dirname`; [retained provider/contract row](../host-system-inventory.md#utility-dirname). Full applicable behavior remains unqualified. |
| [`cp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cp.html) | `/bin/cp` / `/bin/cp`; [retained provider/contract row](../host-system-inventory.md#utility-cp). Full applicable behavior remains unqualified. |
| [`dd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dd.html) | `/bin/dd` / `/bin/dd`; [retained provider/contract row](../host-system-inventory.md#utility-dd). Full applicable behavior remains unqualified. |
| [`df`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/df.html) | `/bin/df` / `/bin/df`; [retained provider/contract row](../host-system-inventory.md#utility-df). Full applicable behavior remains unqualified. |
| [`du`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/du.html) | `/usr/bin/du` / `/bin/du`; [retained provider/contract row](../host-system-inventory.md#utility-du). Full applicable behavior remains unqualified. |
| [`file`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html) | `/usr/bin/file` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-file). Full applicable behavior remains unqualified. |
| [`find`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) | `/usr/bin/find` / `/bin/find`; [retained provider/contract row](../host-system-inventory.md#utility-find). Full applicable behavior remains unqualified. |
| [`ln`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html) | `/bin/ln` / `/bin/ln`; [retained provider/contract row](../host-system-inventory.md#utility-ln). Full applicable behavior remains unqualified. |
| [`ls`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html) | `/bin/ls` / `/bin/ls`; [retained provider/contract row](../host-system-inventory.md#utility-ls). Full applicable behavior remains unqualified. |
| [`mkdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html) | `/bin/mkdir` / `/bin/mkdir`; [retained provider/contract row](../host-system-inventory.md#utility-mkdir). Full applicable behavior remains unqualified. |
| [`mkfifo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkfifo.html) | `/usr/bin/mkfifo` / `/bin/mkfifo`; [retained provider/contract row](../host-system-inventory.md#utility-mkfifo). Full applicable behavior remains unqualified. |
| [`mv`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html) | `/bin/mv` / `/bin/mv`; [retained provider/contract row](../host-system-inventory.md#utility-mv). Full applicable behavior remains unqualified. |
| [`pathchk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pathchk.html) | `/usr/bin/pathchk` / `/bin/pathchk`; [retained provider/contract row](../host-system-inventory.md#utility-pathchk). Full applicable behavior remains unqualified. |
| [`pax`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pax.html) | `/bin/pax` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-pax). Full applicable behavior remains unqualified. |
| [`pwd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html) | `/bin/pwd` / `/bin/pwd`; [retained provider/contract row](../host-system-inventory.md#utility-pwd). Full applicable behavior remains unqualified. |
| [`readlink`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/readlink.html) | `/usr/bin/readlink` / `/bin/readlink`; [retained provider/contract row](../host-system-inventory.md#utility-readlink). Full applicable behavior remains unqualified. |
| [`realpath`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/realpath.html) | `/bin/realpath` / `/bin/realpath`; [retained provider/contract row](../host-system-inventory.md#utility-realpath). Full applicable behavior remains unqualified. |
| [`rm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | `/bin/rm` / `/bin/rm`; [retained provider/contract row](../host-system-inventory.md#utility-rm). Full applicable behavior remains unqualified. |
| [`rmdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rmdir.html) | `/bin/rmdir` / `/bin/rmdir`; [retained provider/contract row](../host-system-inventory.md#utility-rmdir). Full applicable behavior remains unqualified. |
| [`touch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html) | `/usr/bin/touch` / `/bin/touch`; [retained provider/contract row](../host-system-inventory.md#utility-touch). Full applicable behavior remains unqualified. |

Providers above are the retained macOS / Debian standard-PATH observations,
not new measurements. Their hashes and qualified-PATH alternatives are in the
[immutable machine inventory](../evidence/csh-012/closure-5b56328/utility-inventory.json).
Select and record actual package/version/build identities before qualification;
missing providers require an explicit package/build choice and reproducible setup.
Selected utility/libc/platform vendors retain implementation ownership; this
ticket owns supplying and verifying the execution environment and reporting or
repairing the selected provider contract. No host installation is implied.

## Retained conditions

These exact condition IDs transfer from the [CSH-064 prerequisite ledger](../evidence/csh-064/prerequisites.json).
The [original evidence](../evidence/csh-064/README.md), including strict failed
profiles and executable/environment identities, remains unchanged.

| Condition | Required capability before further qualification |
| --- | --- |
| `U-040/pwd-access-path-limits` | A controlled inaccessible-ancestor and pathname-boundary filesystem with bounded, independently checked expectations. |
| `U-040/find-depth-locale-limits` | Controlled descriptor/depth exhaustion or new locale matching oracles beyond 32 levels. |
| `U-040/ls-size-collation` | A supplied locale/collation oracle or bounded larger directory beyond 256 C-locale entries. |
| `U-040/rm-depth-mount-prompt` | A disposable mount/depth-exhaustion or terminal-prompt fixture; never protected mounts. |

## Acceptance criteria

- [x] Select each required exec-accessible provider, supply missing packages/services,
  and retain exact PATH, realpath, executable hash, package and environment identity.
- [x] Map every applicable page section and common default to clause-derived
  assertions or an individually justified disposition; repair required-contract
  failures. Selected examples alone do not complete a utility contract.
- [x] Resolve each assigned retained condition with its required capability and
  strict evidence, or transfer that individual condition to a concrete open owner.
  Preserve vendor ownership, setup failures and failed assertions separately.
- [x] Verify public cshell dispatch and direct exec access, exact output/status and
  relevant effects, with zero gap allowances for every declared qualified subset.
- [x] Update the inventory, current ownership manifest and clause maps with the
  exact qualification boundary; keep stock-host, qualified subset and full-system
  claims separate.

## Validation

Run `make test-host-inventory` to check exhaustive ownership and retained IDs.
Add focused bounded fixtures for the listed contracts, with independent normative
oracles, then run `make test-host-profile` for the supplied selected profile.
Retain native macOS and Docker/Linux results separately with commands, identities,
capabilities, limits and failures. If the needed capability is absent, report it
as unqualified; do not call an unavailable or failed profile passing. Use owned
processes and disposable files/services and verify cleanup after failure/timeout.

## Implementation notes/evidence

CSH-072 supplies the [strict filesystem profile](../host-filesystem-evidence.md),
[section-by-section clause map](../../tests/host_filesystem_contracts.json), and
[separate native/Linux evidence](../evidence/csh-072/README.md). The declared
qualification is the exact passing case set, not complete utility pages.

- All 21 selected providers are inventoried and directly executed as well as
  dispatched by public cshell. Docker/Linux CI now supply file and pax packages.
- Local opt-in readlink/realpath providers repair measured stock diagnostic and
  Issue-8 option failures, with strict path, symlink, error and output tests.
- Files, metadata, links and ustar archives use independently authored oracles;
  a 512-byte child limit supplies bounded write failure without filling a disk.
- The retained find/ls/rm conditions gain 64-level UTF-8 matching, 512 C-locale
  entries and controlled-terminal yes/no witnesses. Physical pwd is checked at
  a measured component-length boundary.
- Each unqualified page section and remaining portion of all four retained
  conditions transfers to concrete open [CSH-079](CSH-079-filesystem-remaining-contracts.md)
  ([#158](https://github.com/melliott18/cshell/issues/158)). Vendor ownership and
  original CSH-064 evidence are preserved. Quotas, mount boundaries, inaccessible
  ancestors and actual EIO/ENOSPC are not declared supplied.

Validation commands, totals, source/provider identities, strict stock failures
and integration limitations are retained in the evidence directory. Review
status records implemented scoped qualification and individual dispositions;
it does not promote U-034/U-040, a full utility contract or full-system compliance.
