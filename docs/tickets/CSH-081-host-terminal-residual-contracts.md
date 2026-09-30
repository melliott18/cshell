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
| [`stty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/stty.html) | Serial control modes, baud rates and physical effects require supplied disposable hardware. PTY flags are storage witnesses, not input/output delivery proofs. Complete parity/combination modes, ek/sane semantics, -a token content, lower-case circumflex encodings, locales, signal and I/O failure partitions. |
| [`tabs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tabs.html) | Supply additional terminal capability models, unsupported-tab terminal, all single-digit intervals, tab/newline blank separators, type/default/environment precedence, limits and physical terminal effects. XSI language presets remain excluded by the base profile. |
| [`tput`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tput.html) | Supply missing-operation and partially capable terminals; verify no-error and continue-through-remaining-operands behavior, unset/null TERM, additional -T option forms, initialization/reset side effects, write errors and signals. The selected adapter deliberately exposes only clear/init/reset, not terminfo query extensions. |
| [`tty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tty.html) | Verify write-error statuses (>1), signal and locale/error partitions, descriptor exhaustion and multiple device-name aliases. Existing name/non-terminal/invalid-option witnesses remain bounded. |
| [`mesg`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mesg.html) | Supply distinct simultaneous PTYs for descriptor-priority checks, permission-denied operations, no-terminal errors and real sender/recipient credentials. Metadata changes alone do not prove accessibility for all credentials. |
| [`who`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/who.html) | Supply owned active login sessions, current-terminal selection (-m, am i/I), -T permissions, -u idle times, TZ/LC_TIME matrices, database races/corruption and read errors. Named-file rows are controlled vendor-format witnesses; optional XSI reporting does not become a base requirement. |
| [`write`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/write.html) | Supply disposable registered sender/recipient sessions in an isolated host/container with controlled credentials. Verify greeting, both sender alerts, lines, EOF/SIGINT EOT, erase/kill, print/space/bell/nonprintable/multibyte conversion, IEXTEN policy, multiple-logins selection, denial, diagnostics and cleanup. Never send to real logged-in users. |

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
These witnesses narrow the corresponding rows above only when their recorded
strict runs pass; all untested combinations remain here. In particular,
`write/POSIX-EOT` and `write/two-sender-alerts` remain explicit vendor obligations,
with a separate `--strict-eot` audit. No physical hardware was supplied.
