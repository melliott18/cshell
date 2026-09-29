# CSH-074: Qualify host languages, editors and argument construction

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: Assigned when work starts
- Issue: [#146](https://github.com/melliott18/cshell/issues/146)

## Goal

Qualify host languages, editors and argument construction for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Supply clause-derived programs, regular expressions, editing sessions, patch effects and argument vectors; bound editor temporary-file and signal recovery tests and descendant cleanup.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`awk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/awk.html) | `/usr/bin/awk` / `/bin/awk`; [retained provider/contract row](../host-system-inventory.md#utility-awk). Full applicable behavior remains unqualified. |
| [`bc`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/bc.html) | `/usr/bin/bc` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-bc). Full applicable behavior remains unqualified. |
| [`ed`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html) | `/bin/ed` / `/bin/ed`; [retained provider/contract row](../host-system-inventory.md#utility-ed). Full applicable behavior remains unqualified. |
| [`expr`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/expr.html) | `/bin/expr` / `/bin/expr`; [retained provider/contract row](../host-system-inventory.md#utility-expr). Full applicable behavior remains unqualified. |
| [`grep`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/grep.html) | `/usr/bin/grep` / `/bin/grep`; [retained provider/contract row](../host-system-inventory.md#utility-grep). Full applicable behavior remains unqualified. |
| [`m4`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/m4.html) | `/usr/bin/m4` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-m4). Full applicable behavior remains unqualified. |
| [`patch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/patch.html) | `/usr/bin/patch` / `/bin/patch`; [retained provider/contract row](../host-system-inventory.md#utility-patch). Full applicable behavior remains unqualified. |
| [`xargs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/xargs.html) | `/usr/bin/xargs` / `/bin/xargs`; [retained provider/contract row](../host-system-inventory.md#utility-xargs). Full applicable behavior remains unqualified. |

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
| `U-040/ed-buffer-temp-signal` | A disposable temp-file/buffer failure or signal-recovery fixture with bounded expectations. |

## Acceptance criteria

- [ ] Select each required exec-accessible provider, supply missing packages/services,
  and retain exact PATH, realpath, executable hash, package and environment identity.
- [ ] Map every applicable page section and common default to clause-derived
  assertions or an individually justified disposition; repair required-contract
  failures. Selected examples alone do not complete a utility contract.
- [ ] Resolve each assigned retained condition with its required capability and
  strict evidence, or transfer that individual condition to a concrete open owner.
  Preserve vendor ownership, setup failures and failed assertions separately.
- [ ] Verify public cshell dispatch and direct exec access, exact output/status and
  relevant effects, with zero gap allowances for every declared qualified subset.
- [ ] Update the inventory, current ownership manifest and clause maps with the
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

Work has not started. CSH-068 transfers ownership only; it supplies no new vendor
implementation, service, privileged host or physical terminal. CSH-064 remains
done for its bounded capability work and repaired probe cleanup.
