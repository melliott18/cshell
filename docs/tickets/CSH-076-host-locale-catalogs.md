# CSH-076: Qualify host locale and message catalog utilities

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-076-host-locale-catalogs
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

- [x] Select each required exec-accessible provider, supply missing packages/services,
  and retain exact PATH, realpath, executable hash, package and environment identity.
- [ ] Map every applicable page section and common default to clause-derived
  assertions or an individually justified disposition; repair required-contract
  failures. Selected examples alone do not complete a utility contract.
- [x] Resolve each assigned retained condition with its required capability and
  strict evidence, or transfer that individual condition to a concrete open owner.
  Preserve vendor ownership, setup failures and failed assertions separately.
- [ ] Verify public cshell dispatch and direct exec access, exact output/status and
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

Implementation is in progress on the branch above. The [bounded profile](../host-locale-catalogs.md)
supplies GNU catalog providers with native option/escape adapters, private Linux
locales, independent catalog consumers and byte oracles, all five dispatch modes,
strict failure reproducers and per-section accounting. Full contracts remain open;
this ticket must not be closed from these selected witnesses.

[Separate native and Linux evidence](../evidence/csh-076/README.md) records the
current native subset (355 passing cases), current existing host profile
(1,162 passes, zero gaps), and an intermediate Linux subset (395 passes) with
five verified private locales. Hosted Ubuntu and Docker CI subsequently passed the native C adapter commit
4460922, including sanitizer checks; hosted macOS sanitizer execution was
cancelled. The evidence page retains exact job metadata separately from the
intermediate local Linux results.

The four conditional locale prerequisites are supplied on the recorded hosts;
that does not qualify printf, sed or find behavior owned by other tickets.
The [machine clause map](../../tests/host_catalog_clauses.json) and
[scope manifest](../../tests/host_catalog_scope.json) keep every remaining
section and provider defect owned here. Required strict failures include native
gencat stream operands/escape diagnostics, iconv `-s`
on both hosts, and glibc gencat deletion of existing sets. No failure is converted
to a passing assertion. Darwin generated categories beyond LC_NUMERIC, further normative
sections/defaults remain outstanding.

`make test-runtime` passed 3,950 native cases under the selected PATH. The first
PTY run and focused retry fail in the unchanged terminal handoff fault fixture;
logs retain the five-second timeout and cleanup diagnostics. This is a distinct
validation failure, not a claimed catalog defect or a passing PTY result.

The remaining native `make test-runtime-pty` target passes 33 cases when run
independently. A stock-PATH control reproduces the terminal handoff timeout;
its cause remains unestablished.

Shared fixture publication is available through `make host-catalog-fixtures`.
Dependent tracks consume `build/host-profile/fixtures.json` with the shared
`load_fixtures` Python helper; locale-only users can run `make host-locales`
without the full host profile. Both catalog and Linux locale generations are
retained across reprovisioning. See the bounded fixture checks and consumer
contract in [the shared-interface documentation](../host-locale-catalogs.md).

The follow-up native locale adapter fixes environment-report quoting and adds
precedence/empty-value assertions. The catalog subset now passes 405 native and 425 Docker/Linux cases,
including native private LC_NUMERIC generation/consumption via PATH_LOCALE,
stdin generation and failure effects. Native libc consumes these private
categories without administrative access. The remaining provider defects and
public-installation environment requirements are recorded in the shared profile
documentation. System-wide installation is not performed on the developer host.
