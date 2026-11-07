# CSH-074: Qualify host languages, editors and argument construction

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-074-host-languages-editors
- Issue: [#146](https://github.com/melliott18/cshell/issues/146)
- Pull request: [#241](https://github.com/melliott18/cshell/pull/241)

## Acceptance review (2026-11-07)

Not accepted. Complete-page coverage remains open, including further patch prompts, locale/default behavior and additional language/editor contracts. This ticket still owns those remainders. See the [acceptance review](acceptance-review-2026-11-07.md) for validation and limitations.

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

The [operation qualification](../host-languages-evidence.md) supplies 191 fixtures
in four execution modes plus nine synchronized editor signal checks (773 checks,
including separate test-only backing-store failures and supplemental XSI cases).
The [normative heading map](../../tests/host_language_contracts.json) accounts for
every selected fixture and retains the remaining page obligations.

The private profile now builds GNU ed, GNU M4, GNU patch and FreeBSD-derived xargs from pinned,
licensed sources. ed emits the exact SIGINT stdout marker; xargs preserves empty
NUL arguments, handles empty-input invocation, enforces/clamps byte limits and
reports exec failures portably. M4 preserves wrap registration order and
nonzero numeric/temporary-file error status. System executables remain untouched. The
instrumented editor separately verifies backing-store creation/write failures
and input preservation. SIGINT and both SIGHUP recovery paths are required by
the default suite.

[Expanded attempts](../evidence/csh-074/expanded/README.md) retain the native
provider failures and corrections. Dedicated native Linux/macOS CI jobs retain
ordinary and sanitizer records independently of the broad runtime suites.
Final ordinary and ASan/UBSan runs each pass all 705 checks on both local macOS
and hosted Ubuntu 24.04, with an identical source-input digest in all four records.
The final native selected profile passes 1162 existing checks plus 705 language
checks, and the selected-PATH runtime passes 3950 checks. Earlier native PTY
failures remain retained and are not claimed resolved.
The [original evidence](../evidence/csh-074/README.md), including prior Linux
signal races and native cleanup failures, remains unchanged. The earlier local Docker
HTTP 500 limitation is historical: the daemon is available for this continuation.

Full-page acceptance remains open for contracts beyond the declared subset,
including remaining patch prompts, broad locale/default handling and additional
resource/signal paths. The three native m4 failures are now repaired by the
selected private provider and required in the default suite, alongside new
wrap-order and temporary-file regressions. The provider/dispatch checkboxes
apply to the declared subset, not complete utility conformance. Keep this ticket
open; CSH-068 remains an ownership transfer and CSH-064 history is unchanged.


### Terminal and backup continuation

The next 68 assertions cover ed help/dirty-buffer warnings/EOF/SIGQUIT,
xargs controlling-terminal confirmations with separate argument data, and patch
conditional output, operand precedence and backup interactions. They exposed
macOS patch replacing the first backup and GNU patch omitting the `-b -o`
output backup. The private GNU patch 2.8 provider repairs these paths without
changing system executables. Its archive, license and local correction are
retained under `tools/host-profile/vendor/patch`.

The [environment assessment](../host-languages-evidence.md#remaining-work-and-environment-requirements)
distinguishes routine automated work, generated locales, isolated physical
storage tests and the still-failing native macOS 14 job-control fixture. Neither
prompt testing nor the remaining identified CSH-074 contracts require manual
terminal typing. The latter fixture needs a clean macOS comparison; sampled
kernel wait and failed cleanup are retained, not converted to a pass.

[Continuation records](../evidence/csh-074/terminal-backup/README.md) retain both
backup failures before repair and separate native/Docker qualification results.
The final ordinary and ASan/UBSan runs each pass all 773 checks on both native
macOS and Debian 12 Docker with the same source-input digest. Both ordinary
profiles additionally pass 1162 existing checks; the native selected-PATH
runtime passes 3950 checks. Full-page acceptance and this ticket remain open.

### Historical CSH-073 stock interruption observation

[CSH-073's signal fixtures](../host-text-contracts.md#retained-conditions-and-signals)
explicitly supply ed changed-buffer HUP saving and a strict SIGINT response/
recovery audit. The selected macOS ed writes the response to stderr with an
extra newline; GNU ed adds a leading newline on stdout. Both fail the strict
`?\n` stdout assertion. HUP saving is a separate bounded pass. CSH-074 owns the
ed provider repair and full-page qualification; CSH-073 retains the shared
`U-040/other-interruptions` condition and fixture. No passing sleep or cat signal
case qualifies ed recovery. See [retained results](../evidence/csh-073/README.md).

## Contract continuation (2026-11-07)

Added 15 patch cases (60 assertions) for progress/prompt streams, locale-specific
affirmative responses, filename precedence and repeated/interleaved output
versions. The private provider repairs these paths, including empty intermediate
output and ed scripts. Native ordinary qualification passes 833 assertions;
all 136 patch assertions also pass ASan/UBSan.

The [continuation evidence and review](../evidence/host-contract-continuation-2026-11-07/README.md)
retain the original failures and exact validation boundaries. Complete-page
coverage of the eight owned utilities remains open. This ticket is not accepted.

## Streaming and multibyte follow-up (2026-11-07)

Repaired M4 multibyte len/index/substr/translit operations and signed overflow
for INT_MAX substring counts. Eleven new cases add 44 assertions; the native
language/editor suite passes 877 assertions and M4 passes 148 assertions under
ASan/UBSan and in Debian. The separate multibyte audit retains 16 native failures
(awk, expr and ed) and 12 Debian failures (awk). Required provider repairs and
full-page coverage remain open; this ticket is not accepted.

See the [follow-up evidence and acceptance review](../evidence/host-contract-continuation-2026-11-07/streaming-multibyte/README.md) for commands, identities, failures and remaining work.

## Language provider repairs (2026-11-07)

Pinned GNU Awk in POSIX mode, GNU coreutils expr, and GNU-regex ed repair all
previously retained multibyte failures. The Awk adapter also returns command exit
status from system() instead of raw wait bits. All old multibyte cases are now
required in the ordinary repaired profile; fifteen additional locale, regex and
status cases bring the native and Debian suites to 981 passing assertions.
Full-page/common-default coverage remains incomplete, so this ticket is not
accepted. See the [provider repair review](../evidence/host-contract-continuation-2026-11-07/provider-repairs/README.md)
for source identities, sanitizer results, retained failures and remaining scope.

## Coverage and CI continuation (2026-11-07)

Added 27 grammar, arithmetic, scope, record/field and editor-state cases.
The selected private bc repairs the POSIX empty return production.
The [coverage and CI review](../evidence/host-contract-continuation-2026-11-07/coverage-ci/README.md)
records validation and remaining obligations. This ticket remains unaccepted.
