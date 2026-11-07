# CSH-077: Qualify host terminal and session utilities

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-077-host-terminal-utilities
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

- [x] Select each required exec-accessible provider, supply missing packages/services,
  and retain exact PATH, realpath, executable hash, package and environment identity.
- [ ] Map every applicable page section and common default to clause-derived
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

Implemented the bounded PTY/session-record profile, standalone opt-in provider
repairs and [complete section accounting](../host-terminal-contracts.md). The
128 declared cases run through direct exec, cshell -c, file, stdin and explicit
exec (640 assertions). Independent termios/ioctl snapshots, an authored terminal
capability model, ttyname and private native-format session records supply the
oracles. All declared assertions are strict, with no gap allowance.

Four selected adapter repairs address blank-separated tabs operands, tput's
invalid-operand status and multiple operands, mesg error status, and missing who
database diagnostics. Exact adapter/vendor hashes, package/build identities,
PATH, environment, bounded failures and source identities are retained in the
[all-attempt evidence](../evidence/csh-077/README.md). System providers and real
login records are unchanged; Linux write is supplied by bsdextrautils in the
reproducible Docker/CI setup.

The section map explicitly dispositions unqualified portions to
[CSH-081](CSH-081-host-terminal-residual-contracts.md), including every utility's
remaining page/default requirements, untested registered-session behavior and the exact
`U-040/stty-physical-terminal` condition. No physical hardware was supplied. This
transfer is open work, not a full-contract or full-system qualification claim.
CSH-064's immutable historical evidence remains unchanged.

### Validation record

Native macOS and Docker/Debian runs separately cover the 640 terminal assertions,
six harness regressions and existing strict host-profile integration (1,162
assertions, zero gaps). The ownership checker retains 156 names, 101 external
contracts and 30 conditions with open owners. Native public runtime checks use the selected profile; the broader existing
job-terminal fault fixture timed out and its cleanup remains unresolved. Final
Docker logs pass, but subsequent Docker API failures prevented final raw artifact
retrieval. These limitations remain explicit in the evidence. Exact command results, failed preliminary attempts,
fixture corrections and the reproduced output/exit capture race are retained in
the evidence README; only completed final runs are claimed there.

Status remains review until integration; the full remaining contracts continue
under CSH-081 regardless of CSH-077 integration.

### Controlled PTY/session extension

The follow-up request explicitly supplies no physical hardware. The new
`test-host-terminal-effects` target checks real data transformations, three-PTY
mesg precedence, and private-record who -T/-m behavior in 90 strict cases.
An isolated Linux session runner adds registered sender/recipient delivery,
denial and who am i/I under dropped credentials, with a separate strict EOT/alert
audit. See the [section map](../host-terminal-contracts.md#controlled-data-and-session-extension)
for exact boundaries. Physical behavior remains unqualified under CSH-081.

At the extension stage, the complete-page repair criterion and the observed
`write/POSIX-EOT`/`write/two-sender-alerts` differences remained under CSH-081.
The subsequent repair pass below resolves these two differences for the selected
Linux profile; complete-page qualification is still open. The
[extension evidence](../evidence/csh-077-extension/README.md) records 730 strict
PTY assertions plus six harness tests on native macOS and hosted Linux, both
ordinary and sanitized, and 20 isolated Linux session assertions. These selected
passes do not close the remaining full-page requirements.

### Remaining-issue repair pass

The subsequent pass repairs selected write EOT/sender alerts with a portable
FreeBSD-derived standalone provider, and tightens missing-operation/attached-type
tput and no-terminal mesg behavior. The main PTY profile grows to 665 assertions
plus the 90 data-effect assertions. Linux registered sessions now strictly check
47 assertions (nine cases in five paths plus synchronized direct/exec SIGINT).
Historical vendor failures stay in their original evidence; they do not become
accepted gaps in the repaired profile. Current results and prerequisite needs
are recorded in the [repair evidence](../evidence/csh-077-repairs/README.md) and
[environment matrix](../host-terminal-contracts.md#remaining-environment-requirements).
The full-page criterion remains open under CSH-081.
