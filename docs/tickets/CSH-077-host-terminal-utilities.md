# CSH-077: Qualify host terminal and session utilities

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: Assigned when work starts
- Issue: [#149](https://github.com/melliott18/cshell/issues/149)

## Goal

Qualify host terminal and session utilities for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Supply controlled PTYs, session records and terminal capabilities; physical serial/terminal assertions require supplied hardware. Message fixtures must use disposable owned sessions.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`stty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/stty.html) | `/bin/stty` / `/bin/stty`; [retained provider/contract row](../host-system-inventory.md#utility-stty). Full applicable behavior remains unqualified. |
| [`tabs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tabs.html) | `/usr/bin/tabs` / `/bin/tabs`; [retained provider/contract row](../host-system-inventory.md#utility-tabs). Full applicable behavior remains unqualified. |
| [`tput`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tput.html) | `/usr/bin/tput` / `/bin/tput`; [retained provider/contract row](../host-system-inventory.md#utility-tput). Full applicable behavior remains unqualified. |
| [`tty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tty.html) | `/usr/bin/tty` / `/bin/tty`; [retained provider/contract row](../host-system-inventory.md#utility-tty). Full applicable behavior remains unqualified. |
| [`mesg`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mesg.html) | `/usr/bin/mesg` / `/bin/mesg`; [retained provider/contract row](../host-system-inventory.md#utility-mesg). Full applicable behavior remains unqualified. |
| [`who`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/who.html) | `/usr/bin/who` / `/bin/who`; [retained provider/contract row](../host-system-inventory.md#utility-who). Full applicable behavior remains unqualified. |
| [`write`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/write.html) | `/usr/bin/write` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-write). Full applicable behavior remains unqualified. |

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
| `U-040/stty-physical-terminal` | Explicitly supplied disposable physical serial/terminal hardware with known supported settings. |

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
