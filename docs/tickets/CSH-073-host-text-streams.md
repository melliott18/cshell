# CSH-073: Qualify host text and byte stream utilities

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-073-host-text-streams
- Issue: [#145](https://github.com/melliott18/cshell/issues/145)

## Goal

Qualify host text and byte stream utilities for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Supply deterministic byte/text/locale oracles, sparse/large-file fixtures, bounded interrupted I/O, space exhaustion and independent expected offsets. The shared interruption condition also covers ed in CSH-074; coordinate that witness explicitly.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`cat`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cat.html) | `/bin/cat` / `/bin/cat`; [retained provider/contract row](../host-system-inventory.md#utility-cat). Full applicable behavior remains unqualified. |
| [`cksum`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cksum.html) | `/usr/bin/cksum` / `/bin/cksum`; [retained provider/contract row](../host-system-inventory.md#utility-cksum). Full applicable behavior remains unqualified. |
| [`cmp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cmp.html) | `/usr/bin/cmp` / `/bin/cmp`; [retained provider/contract row](../host-system-inventory.md#utility-cmp). Full applicable behavior remains unqualified. |
| [`comm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/comm.html) | `/usr/bin/comm` / `/bin/comm`; [retained provider/contract row](../host-system-inventory.md#utility-comm). Full applicable behavior remains unqualified. |
| [`csplit`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/csplit.html) | `/usr/bin/csplit` / `/bin/csplit`; [retained provider/contract row](../host-system-inventory.md#utility-csplit). Full applicable behavior remains unqualified. |
| [`cut`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cut.html) | `/usr/bin/cut` / `/bin/cut`; [retained provider/contract row](../host-system-inventory.md#utility-cut). Full applicable behavior remains unqualified. |
| [`diff`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/diff.html) | `/usr/bin/diff` / `/bin/diff`; [retained provider/contract row](../host-system-inventory.md#utility-diff). Full applicable behavior remains unqualified. |
| [`expand`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/expand.html) | `/usr/bin/expand` / `/bin/expand`; [retained provider/contract row](../host-system-inventory.md#utility-expand). Full applicable behavior remains unqualified. |
| [`fold`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/fold.html) | `/usr/bin/fold` / `/bin/fold`; [retained provider/contract row](../host-system-inventory.md#utility-fold). Full applicable behavior remains unqualified. |
| [`head`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/head.html) | `/usr/bin/head` / `/bin/head`; [retained provider/contract row](../host-system-inventory.md#utility-head). Full applicable behavior remains unqualified. |
| [`join`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/join.html) | `/usr/bin/join` / `/bin/join`; [retained provider/contract row](../host-system-inventory.md#utility-join). Full applicable behavior remains unqualified. |
| [`od`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/od.html) | `/usr/bin/od` / `/bin/od`; [retained provider/contract row](../host-system-inventory.md#utility-od). Full applicable behavior remains unqualified. |
| [`paste`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/paste.html) | `/usr/bin/paste` / `/bin/paste`; [retained provider/contract row](../host-system-inventory.md#utility-paste). Full applicable behavior remains unqualified. |
| [`pr`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pr.html) | `/usr/bin/pr` / `/bin/pr`; [retained provider/contract row](../host-system-inventory.md#utility-pr). Full applicable behavior remains unqualified. |
| [`sed`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sed.html) | `/usr/bin/sed` / `/bin/sed`; [retained provider/contract row](../host-system-inventory.md#utility-sed). Full applicable behavior remains unqualified. |
| [`sort`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sort.html) | `/usr/bin/sort` / `/bin/sort`; [retained provider/contract row](../host-system-inventory.md#utility-sort). Full applicable behavior remains unqualified. |
| [`split`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/split.html) | `/usr/bin/split` / `/bin/split`; [retained provider/contract row](../host-system-inventory.md#utility-split). Full applicable behavior remains unqualified. |
| [`strings`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html) | `/usr/bin/strings` / `/bin/strings`; [retained provider/contract row](../host-system-inventory.md#utility-strings). Full applicable behavior remains unqualified. |
| [`tail`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tail.html) | `/usr/bin/tail` / `/bin/tail`; [retained provider/contract row](../host-system-inventory.md#utility-tail). Full applicable behavior remains unqualified. |
| [`tee`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tee.html) | `/usr/bin/tee` / `/bin/tee`; [retained provider/contract row](../host-system-inventory.md#utility-tee). Full applicable behavior remains unqualified. |
| [`tr`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tr.html) | `/usr/bin/tr` / `/bin/tr`; [retained provider/contract row](../host-system-inventory.md#utility-tr). Full applicable behavior remains unqualified. |
| [`tsort`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tsort.html) | `/usr/bin/tsort` / `/bin/tsort`; [retained provider/contract row](../host-system-inventory.md#utility-tsort). Full applicable behavior remains unqualified. |
| [`unexpand`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unexpand.html) | `/usr/bin/unexpand` / `/bin/unexpand`; [retained provider/contract row](../host-system-inventory.md#utility-unexpand). Full applicable behavior remains unqualified. |
| [`uniq`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uniq.html) | `/usr/bin/uniq` / `/bin/uniq`; [retained provider/contract row](../host-system-inventory.md#utility-uniq). Full applicable behavior remains unqualified. |
| [`wc`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/wc.html) | `/usr/bin/wc` / `/bin/wc`; [retained provider/contract row](../host-system-inventory.md#utility-wc). Full applicable behavior remains unqualified. |

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
| `U-040/cat-filesystem-limits` | A disposable filesystem I/O fault or capacity environment beyond the existing 1024-byte child RLIMIT_FSIZE witness. |
| `U-040/sed-space-limits` | A new controlled memory/space boundary or multibyte-expression oracle beyond existing finite witnesses. |
| `U-040/head-count-interruption` | An owned interrupted-input fixture or independently bounded count-boundary witness. |
| `U-040/cmp-offset-interruption` | An owned interrupted-input fixture or independently bounded larger-offset witness. |
| `U-040/other-interruptions` | Per-utility owned read/write interruption and recovery fixtures for cat, head, cmp and ed; sleep TERM is insufficient. |

## Acceptance criteria

- [x] Select each required exec-accessible provider, supply missing packages/services,
  and retain exact PATH, realpath, executable hash, package and environment identity.
- [ ] Map every applicable page section and common default to clause-derived
  assertions or an individually justified disposition; repair required-contract
  failures. Selected examples alone do not complete a utility contract.
- [ ] Resolve each assigned retained condition with its required capability and
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

The [implementation and clause map](../host-text-contracts.md) supplies strict
independent byte/text oracles for all 25 utilities, four execution modes,
per-page section accounting, owned signal fixtures shared with CSH-074, a
2 GiB sparse offset, and disposable Linux filesystem exhaustion. The
[machine section ledger](../../tests/host_text_contracts.json) is checked by
`make test-host-inventory`; `tests/host_contracts.json` links that map without
rewriting immutable earlier evidence.

This change is ready for review as qualification infrastructure and bounded
evidence. **Full ticket acceptance remains open.** The unchecked criteria retain
required-contract failures and unavailable native capacity/write-observation
capabilities; they are not waived by subset success. CSH-073 remains the concrete
open qualification owner for every utility and condition listed above. Selected
vendors own implementation repairs; CSH-074 shares the ed recovery repair.
The individually described remaining contracts are in the section ledger and
clause map. No wholesale utility or U-034/U-040 promotion is made.

The [all-attempt record](../evidence/csh-073/README.md) distinguishes exploratory
fixture corrections, strict vendor failures, passing subsets and unavailable
capabilities. Use `make test-host-text-audit` to reproduce the unqualified
requirements without changing expectations. CSH-064 remains done for its
historical bounded work and repaired probe cleanup.


### Validation results

Final focused subset: native macOS **532 pass, 0 fail, 8 unavailable**;
Docker/Linux **540 pass, 0 fail**. Final strict audit: native **548 pass,
14 fail, 8 unavailable**; Docker **552 pass, 18 fail**. Both retain nonzero
statuses for failed audits. Both pass inventory/section accounting and all
eight new harness regression tests. Native `make test-host-profile` retains
one existing PTY cleanup `ps` timeout (1161 pass, 1 fail); Docker's full profile
passes (1162 prior assertions plus 540 text assertions). The final ed prompt
handshake/capture hardening is validated by the later focused completion runs.
Exact commands, source/provider identities, all attempts and diagnoses are in
the linked evidence. No native full-profile pass or complete utility
qualification is claimed.


### Transformation, offset, large-input and interruption extension

The [four-group qualification](../host-text-contracts.md#transformation-offset-large-input-and-interruption-qualification)
adds 194 strict assertions: 68 transformations, 56 offsets, 48 large-input
assertions and 22 owned signal assertions. Large byte-for-byte comparisons
include 8 MiB copies, 1 MiB transformations and one million lines. SIGINT,
SIGPIPE, measured STOP/CONT resumption and tee -i continued copying are distinct
from earlier TERM termination and failed ed recovery. Native SIGPIPE now has
portable write evidence; already-blocked write observation remains a separate
unavailable capability. Exact qualification and new retained attempts are in
[extension evidence](../evidence/csh-073-extensions/README.md).

Final extension subset results: macOS 14.8.7 **726 pass, 0 fail, 8 unavailable**;
Ubuntu **732 pass, 0 fail, 2 unavailable**; Debian **734 pass, 0 fail,
0 unavailable**. All 194 added assertions pass in each environment, with no
unavailable extension rows. All 12 harness regressions pass. Final Linux strict
audits retain 18 vendor failures each; the retained native audit has 14.
The dedicated [hosted run](https://github.com/melliott18/cshell/actions/runs/36644920521)
completed Ubuntu and Debian successfully; macOS 15 was queued at evidence
capture. Local Docker API failure is retained separately from hosted Debian
success. Full ticket acceptance remains open.
