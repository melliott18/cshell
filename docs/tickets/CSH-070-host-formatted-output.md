# CSH-070: Qualify host printf and echo contracts

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-070-host-formatted-output
- Issue: [#142](https://github.com/melliott18/cshell/issues/142)

## Goal

Qualify host printf and echo contracts for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Select catalog-capable printf and declared echo policies; supply libc allocation/stack fault controls and bounded exec-threshold measurements.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`printf`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html) | `/usr/bin/printf` / `/bin/printf`; [retained provider/contract row](../host-system-inventory.md#utility-printf). Full applicable behavior remains unqualified. |
| [`echo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html) | `/bin/echo` / `/bin/echo`; [retained provider/contract row](../host-system-inventory.md#utility-echo). Full applicable behavior remains unqualified. |

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
| `U-035/locale-catalogs` | A selected printf implementation with catalog lookup and a supplied translated catalog; the current standalone source has no lookup. |
| `U-035/other-locales` | Additional installed locale/catalog identities with independently authored numeric and diagnostic expectations. |
| `U-035/format-allocation-limits` | A disposable libc allocation/stack-fault environment and bounded independent failure oracles beyond local strdup/realloc injection. |
| `U-035/full-format` | New bounded conversion combinations with independently authored byte/diagnostic expectations. |
| `U-036/alternative-policies` | A newly selected echo implementation/build policy, exact binary identity and independently authored policy expectations. |
| `U-036/argument-limits` | A bounded threshold-search environment controlling kernel, stack limit, argv layout and environment bytes; oversized rejection alone is insufficient. |

Conditional prerequisite reports also owned here: `U-035/allocation-injection`.

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

[CSH-070 evidence](../evidence/csh-070/README.md) records separately selected
repository builds, French/German catalogs, independent conversion/echo oracles,
controlled libc/stack failures and adjacent exec thresholds. The
[whole-page section map](../host-formatted-output.md) accounts for all behavior
sections and optional/unspecified input decisions. All six retained IDs and the
conditional allocation-helper prerequisite transfer individually to the concrete
open owner [CSH-079 / #157](CSH-079-formatted-output-residuals.md).

Four printf provider defects are repaired: ignored libc formatting failures,
input-sized stack allocation, silent trailing text in character constants, and
non-strtod floating operands. The external literal echo selection has a declared
base-profile policy and exact byte/status/catalog assertions; stock echo remains
separately inventoried. No cshell runtime code or host installation changes.

Final native and Docker/Linux full host profiles each pass 1162 assertions with
zero gaps. Focused profiles pass 351 native / 356 Linux assertions. Native
ASan/UBSan passes 346 ordinary assertions; resource limits run separately.
The evidence retains failed setup attempts, original-provider counterexamples,
Darwin low-stack exec cleanup failures and broader native runtime/PTY cleanup
failures. Passing subsets do not erase these failures; their diagnosis and
remaining environments are explicitly owned by CSH-079. Linux sanitizer completion could not be verified after Docker API errors;
queued Linux runtime/PTY stages were not observed to start. See the evidence
for exact results, cleanup limitations and not-run stages.

This ticket is ready for review of its supplied subset and individual transfers,
not full utility/system conformance. Mark done only after integration.
