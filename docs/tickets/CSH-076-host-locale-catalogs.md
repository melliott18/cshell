# CSH-076: Qualify host locale and message catalog utilities

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: Assigned when work starts
- Issue: [#148](https://github.com/melliott18/cshell/issues/148)

## Goal

Qualify host locale and message catalog utilities for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Supply missing catalog providers, generated disposable locales/catalogs and independent encoding/translation expectations. Shared French/German/UTF-8/GB18030 provisioning is owned here; per-utility behavior remains with its named contract owner.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`gencat`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/gencat.html) | `/usr/bin/gencat` / `/bin/gencat`; [retained provider/contract row](../host-system-inventory.md#utility-gencat). Full applicable behavior remains unqualified. |
| [`gettext`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/gettext.html) | **missing** / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-gettext). Full applicable behavior remains unqualified. |
| [`iconv`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/iconv.html) | `/usr/bin/iconv` / `/bin/iconv`; [retained provider/contract row](../host-system-inventory.md#utility-iconv). Full applicable behavior remains unqualified. |
| [`locale`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/locale.html) | `/usr/bin/locale` / `/bin/locale`; [retained provider/contract row](../host-system-inventory.md#utility-locale). Full applicable behavior remains unqualified. |
| [`localedef`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/localedef.html) | `/usr/bin/localedef` / `/bin/localedef`; [retained provider/contract row](../host-system-inventory.md#utility-localedef). Full applicable behavior remains unqualified. |
| [`msgfmt`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/msgfmt.html) | **missing** / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-msgfmt). Full applicable behavior remains unqualified. |
| [`ngettext`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ngettext.html) | **missing** / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-ngettext). Full applicable behavior remains unqualified. |

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

Conditional prerequisite reports also owned here: `U-035/German-locale`, `U-040/GB18030-locale`, `U-040/UTF-8-locale`, `U-035/locale-errors`.

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
