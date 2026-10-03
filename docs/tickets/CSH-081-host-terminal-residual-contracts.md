# CSH-081: Qualify residual terminal and session contracts

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-077
- Branch: Assigned when work starts
- Issue: [#159](https://github.com/melliott18/cshell/issues/159)

## Goal

Complete the individually unqualified contracts left by CSH-077's bounded PTY
profile. A passing selected profile does not qualify these contracts.

## Scope and concrete prerequisites

Each row retains its complete applicable normative page, U-034 access and U-040
defaults. Vendors own implementation; this ticket owns selecting providers,
supplying environments, strict assertions and repairs or vendor reports.

| Utility / normative page | Remaining contract and required capability |
| --- | --- |
| [`stty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/stty.html) | Serial control modes, baud rates and physical effects require supplied disposable hardware. CSH-077 now proves eleven selected PTY byte transformations; other flag combinations and physical effects remain open. Complete parity/combination modes, ek/sane semantics, -a token content, lower-case circumflex encodings, locales, signal and I/O failure partitions. |
| [`tabs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tabs.html) | Supply additional terminal capability models, unsupported-tab terminal, all single-digit intervals, tab/newline blank separators, type/default/environment precedence, limits and physical terminal effects. XSI language presets remain excluded by the base profile. |
| [`tput`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tput.html) | CSH-077 now supplies missing-operation/partial-capability models and verifies successful continuation plus attached/repeated -T. Unset/null TERM, remaining option/error partitions, initialization/reset side effects, write errors and signals remain open. The selected adapter deliberately exposes only clear/init/reset, not terminfo query extensions. |
| [`tty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tty.html) | Verify write-error statuses (>1), signal and locale/error partitions, descriptor exhaustion and multiple device-name aliases. Existing name/non-terminal/invalid-option witnesses remain bounded. |
| [`mesg`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mesg.html) | Distinct simultaneous PTY precedence is now witnessed by CSH-077. No-terminal status and diagnostic are now verified. Permission-denied operations and remaining sender/recipient credential combinations are open. Metadata changes alone do not prove accessibility for all credentials. |
| [`who`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/who.html) | CSH-077 witnesses private-record -m/-T and Linux isolated am i/I sessions. Remaining active-login combinations, -u idle times, TZ/LC_TIME matrices, database races/corruption and read errors are open. Named-file rows are controlled vendor-format witnesses; optional XSI reporting does not become a base requirement. |
| [`write`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/write.html) | CSH-077 supplies isolated registered sessions with dropped credentials and witnesses selected greeting/data/denial behavior. The new selected FreeBSD-derived provider repairs sender alerts and EOT. Linux witnesses cover full/partial EOF, direct/exec SIGINT, erase/kill, selected print/space/bell/nonprintable conversion and implicit selection. Remaining SIGINT shell paths, multibyte/locale and IEXTEN policy, additional login/credential combinations, I/O failures and native Darwin positive sessions remain open. Never send to real logged-in users. |

| Retained condition | Required capability |
| --- | --- |
| `U-040/stty-physical-terminal` | Explicitly supplied disposable physical serial/terminal hardware with known supported settings. A PTY cannot resolve this condition. |

For **each** utility, further U-040 work includes descriptor/I/O errors, signal
dispositions, finite resource/exec boundaries, unused-input offsets through all
shell paths, locale precedence and non-C diagnostics where applicable. XSI
NLSPATH is excluded. The [section map](../host-terminal-contracts.md) records
which normative sections have no requirements, unspecified/undefined behavior,
excluded optional shading, selected assertions or these open dispositions.

## Acceptance criteria

- [ ] Retain exact provider/package/build and environment identities for each run.
- [ ] Resolve each row with independent clause-derived oracles, repairs and strict
  failures; do not replace complete contracts with selected witnesses.
- [ ] Supply the physical-terminal condition or transfer it individually with its
  exact identifier and capability requirement.
- [ ] Exercise public cshell paths and direct exec, including timeout/failure
  cleanup for owned message sessions; retain native and Linux results separately.
- [ ] Update the current ownership manifest and section map without changing
  immutable earlier evidence or promoting full-system claims.

## Validation

Start with `make test-host-inventory test-host-terminal-profile` and
`make test-host-profile`. Add strict cases to the declared qualified subset only
when the required environment is supplied. Preserve failed attempts separately.
See [CSH-077 evidence](../evidence/csh-077/README.md).

## CSH-077 controlled extension boundary

CSH-077 now adds bounded real-byte PTY transformations, three-terminal mesg
selection, who -T/-m on private records, and a Linux isolated-session runner.
The subsequent repair pass selects a portable FreeBSD-derived write provider and
strictly requires EOT and both sender alerts in the Linux session subset.
Historical stock-vendor failures remain in the immutable extension evidence;
they are not current failures of the repaired selected provider. All untested
combinations remain here. No physical hardware was supplied.

See the [environment matrix](../host-terminal-contracts.md#remaining-environment-requirements)
for automated fixture work versus external capabilities. Most remaining cases
can run on the available native macOS and disposable Linux environments. Physical
serial effects need supplied hardware; real display effects need a specified
terminal/emulator; privileged Darwin session combinations need a disposable
macOS VM. Only hardware connection/identification inherently needs manual setup.
