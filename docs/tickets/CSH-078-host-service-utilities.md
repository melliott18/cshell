# CSH-078: Qualify host scheduling, mail and service utilities

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: Assigned when work starts
- Issue: [#150](https://github.com/melliott18/cshell/issues/150)

## Goal

Qualify host scheduling, mail and service utilities for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Supply disposable scheduler, mail transport, print spool and logging services plus controlled time; verify queue/delivery/output effects and cleanup. mailx send mode remains base. Never enqueue jobs, deliver mail or change clocks on the developer host.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`at`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/at.html) | `/usr/bin/at` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-at). Full applicable behavior remains unqualified. |
| [`batch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/batch.html) | `/usr/bin/batch` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-batch). Full applicable behavior remains unqualified. |
| [`crontab`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/crontab.html) | `/usr/bin/crontab` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-crontab). Full applicable behavior remains unqualified. |
| [`date`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/date.html) | `/bin/date` / `/bin/date`; [retained provider/contract row](../host-system-inventory.md#utility-date). Full applicable behavior remains unqualified. |
| [`logger`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/logger.html) | `/usr/bin/logger` / `/bin/logger`; [retained provider/contract row](../host-system-inventory.md#utility-logger). Full applicable behavior remains unqualified. |
| [`lp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/lp.html) | `/usr/bin/lp` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-lp). Full applicable behavior remains unqualified. |
| [`mailx`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mailx.html) | `/usr/bin/mailx` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-mailx). Full applicable behavior remains unqualified. |
| [`uudecode`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uudecode.html) | `/usr/bin/uudecode` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-uudecode). Full applicable behavior remains unqualified. |
| [`uuencode`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uuencode.html) | `/usr/bin/uuencode` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-uuencode). Full applicable behavior remains unqualified. |

Providers above are the retained macOS / Debian standard-PATH observations,
not new measurements. Their hashes and qualified-PATH alternatives are in the
[immutable machine inventory](../evidence/csh-012/closure-5b56328/utility-inventory.json).
Select and record actual package/version/build identities before qualification;
missing providers require an explicit package/build choice and reproducible setup.
Selected utility/libc/platform vendors retain implementation ownership; this
ticket owns supplying and verifying the execution environment and reporting or
repairing the selected provider contract. No host installation is implied.

## Retained conditions

No stable CSH-064 residual is assigned to this ticket; the full utility
contracts above are still open.

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
