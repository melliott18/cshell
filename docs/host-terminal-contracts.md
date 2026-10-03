# Terminal and session utility qualification (CSH-077)

`make test-host-terminal-profile` qualifies **only the 133 cases, in five dispatch
modes**, declared in `tests/host_terminal.py`. Every declared case is strict;
there are no gap signatures, skips or expected failures. Stock-host execution is
separate (`make test-host-terminal`) and fails for the reproduced provider
contracts. [Run evidence](evidence/csh-077/README.md) retains both.

The environment is an isolated runner session, per-command process groups,
disposable PTYs, C locale/UTC, private `tic`-compiled terminal definitions and
private native-format utmpx records. It changes no real login database or terminal.
`write` receives no recipient; no message is delivered by this subset. Physical
serial hardware was not supplied. Full contracts and the exact retained condition
`U-040/stty-physical-terminal` have the concrete open owner
[CSH-081](tickets/CSH-081-host-terminal-residual-contracts.md).

## Normative section accounting

Sources are the POSIX.1-2024 pages linked below and
[U-034/U-040](posix-utilities.md#u-034). Names/synopses identify invocation forms;
the table accounts for all behavioral sections. Application Usage, Examples,
Rationale, Future Directions and Change History are informative, not additional
conformance assertions. Optional XSI shading retains the
[inventory's base-profile decisions](host-system-inventory.md).

| Page | DESCRIPTION, OPTIONS, OPERANDS | STDIN / INPUT FILES | STDOUT / STDERR / OUTPUT FILES | ENVIRONMENT / ASYNCHRONOUS EVENTS / EXIT STATUS / CONSEQUENCES OF ERRORS / EXTENDED DESCRIPTION |
| --- | --- | --- | --- | --- |
| [stty](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/stty.html) | `stty/<flag>` independently sets the opposite state then verifies all 12 base input flags, OPOST and 9 local flags, both directions. Nine control slots exercise literal, ^C, ^?, undef and ^-; MIN/TIME, window rows/cols and saved-state restoration have termios/ioctl oracles. Other control/combination modes, -a completeness and remaining circumflex encodings: CSH-081. | Owned stdin PTY, no data consumed by design; unread file offset checked in direct unused-stdin cases. Serial input effects and all-mode offset proofs: CSH-081. No input files. | Setters produce no output; size is byte-exact. Default/-a must be nonempty and preserve state, not a full token-content claim. -g is one portable printable token excluding glob metacharacters; reuse must restore the independent snapshot. Errors require diagnostics. No output files. | C locale selected; missing/invalid operands must fail, with no diagnostic-format assertion beyond nonempty. Other locales, signals, resource and I/O faults: CSH-081. Extended description has no requirements. |
| [tabs](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tabs.html) | Zero/default/8 spacing; ascending absolute comma and relative blank lists; -T overrides TERM. Authored CLEAR_TABS/SET_TAB/CR sequences are interpreted by an independent column/stop model. Other intervals, unsupported capabilities, hardware effects: CSH-081; XSI presets excluded. | No input files; direct regular-file offset remains zero. | Output goes to an actual PTY. Exact bytes retained; unspecified format judged by the authored terminal model, not by comparing vendors. Nonterminal stdout is undefined, excluded. Diagnostics on unknown type. No output files. | TERM and -T/C-locale selected; unknown type is a strict positive status. Null/unset TERM default is unspecified; chosen default, other locales, signals, I/O/resource failures remain CSH-081. Extended description: none. |
| [tput](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tput.html) | clear/init/reset and all three in one invocation; -T overrides TERM. Private capabilities give independent exact strings. Absent operations are successful no-ops and continue through remaining operands; attached/repeated -T are checked. Other option forms and terminal side effects: CSH-081. | No input files; direct unused-stdin offset zero. | Actual PTY stdout, exact authored capability bytes. Pipe stdout is undefined and excluded. Invalid operand diagnostic, unknown-type diagnostic. No output files. | Unknown type status 3; invalid operand status 4; successful sequence status 0. Other errors and status 2/>4, null/unset TERM, locales/signals: CSH-081. Init/reset effects are implementation-defined; witnesses cover selected strings only. Extended description: none. |
| [tty](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tty.html) | Name independently obtained from ttyname(slave); regular-file stdin returns the normative nonterminal message. Invalid-option case. Other device-name aliases and errors: CSH-081. | Direct file offset stays zero; PTY name lookup. No input files. | Exact pathname/newline or `not a tty`/newline; empty stderr on valid calls; diagnostic on invalid option. No output files. | C locale; statuses 0/1 and >1 for invalid option. Write-error >1, locale and signal/resource partitions: CSH-081. Extended description: none. |
| [mesg](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mesg.html) | y/n independently verified against device write permission bits, separately when the only available terminal is fd 0, 1 or 2. Query must preserve permissions. Multiple-terminal priority and credential/access combinations: CSH-081. | No input files; direct unused-file offset zero where fd0 is not terminal. | Selected Apple/util-linux query format is pinned byte-exactly (`is y`/`is n` plus newline), but the normative format is unspecified. Other valid calls have no output. Invalid operand diagnoses. No output files. | Status 0 permits, 1 denies; invalid operand must return >1. No-terminal requires status >1 and a diagnostic. Chmod failure, locales/signals and other sender credentials: CSH-081. Extended description: none. |
| [who](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/who.html) | Two authored user records on an owned PTY and an empty private database. Fixed timestamp and names are independently checked; default whitespace is unspecified, retained raw. File operand is a selected XSI/vendor fixture facility, not a new base requirement. Current terminal, -T/-u and live registration: CSH-081. | Private native-format records are selected explicitly; default user database is never read by the positive cases. Direct unused stdin offset zero. | Independently authored user/line/time fields, raw bytes retained. Missing file must fail with diagnostic. No output files. | C locale/TZ=UTC0 and success/error witnessed. LC_TIME/TZ variations, inaccessible/corrupt databases, races and signals: CSH-081. Remaining XSI options excluded; extended description none. |
| [write](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/write.html) | Missing-user invocation verifies access and required-operand error only. All recipient/message behaviors individually remain CSH-081; provider presence is not qualification. | No message input supplied. Full line/control-character behavior needs owned registered sessions. No input files. | Missing-user diagnostic and nonzero status only. Greeting, sender alerts, selection messages and recipient terminal effects: CSH-081. | C locale selected for the error witness. EOF/SIGINT EOT, default signals, LC_CTYPE/LC_MESSAGES, denial and statuses for actual delivery: CSH-081. Extended description none. |

For every row, LANG/LC_ALL/LC_CTYPE/LC_MESSAGES precedence beyond the selected C
locale remains open under CSH-081; XSI NLSPATH is excluded. The private fixtures
exercise no claim for the full default asynchronous-event contract. Common U-040
syntax/operand, unused-input, byte transparency, offset, resource and error
requirements are covered only by the explicitly named cases; the remainder is
individually retained in CSH-081's per-utility rows and shared-default paragraph.

## Selected provider repairs

`tools/host-profile/terminal.c` builds four standalone opt-in adapters, invoking
the fixed `/usr/bin/<utility>` vendor paths without PATH recursion:

- tabs normalizes blanks inside a numeric tab list to commas; Apple accepts the
  equivalent comma representation. Type names are never normalized.
- tput exposes the three POSIX operands and diagnoses invalid operands with
  status 4. It accepts attached/repeated -T and invokes each operand in order;
  an independently queried absent clear capability is a successful no-op.
  Executed vendor failures remain errors. Generic
  terminfo query extensions are outside this profile interface.
- mesg validates its no-operand/y/n interface and reports operand errors as 2,
  rather than util-linux's status 1 (which means receiving is denied).
- who checks a supplied database's accessibility before dispatch, so a missing
  file is no longer silently reported as an empty database. This precheck does
  not eliminate open races or qualify corrupt-file handling.

The [profile provisioning](../tools/host-profile/README.md) records adapter and
vendor hashes; system/package identities and exact PATH are in each run JSON.
Stock host providers remain unchanged. Vendors continue to own their underlying
implementations. These finite repairs do not resolve CSH-081's whole-page gaps.

## Bounds and reproducibility

Each invocation has a 3-second wall deadline, 64 KiB output threshold, core files
disabled, CPU deadline plus one second, 1 MiB file limit and 64 descriptors. Group
kill, leader reap and Linux descendant reap each have a separate 1-second bound.
Linux uses temporary child-subreaper status and group-specific waitpid; unrelated
children are never reaped. Captured output can include the final read chunk that
crosses the threshold; crossing it is always failure. Seven harness regressions
exercise exact status/output, invalid tab sequences, unique strict cases, output
flood, forced output/exit ordering, synchronized signal delivery, and forked timeout
cleanup with an unrelated surviving child.

Temporary PTYs/files/databases are removed after success, assertion failure and
exception. The evidence records removal of the fixture directory. `tic` and
session-fixture setup failures are distinct from utility assertions. Only the
complete unfiltered invocation claims this declared subset; `--case` selects
additional diagnosis, not a full-profile pass.

## Controlled data and session extension

`make test-host-terminal-effects` adds 90 strict witnesses, separate from the
original 640. Eleven independently authored byte transformations cover ICRNL,
INLCR, IGNCR, eight-bit input, ISTRIP, canonical erase/kill/EOF, echo on/off and
unprocessed output. Four distinct-three-PTY cases verify mesg's fd0/fd1/fd2
precedence for allow and deny, including fd1 fallback. Two private records on
different owned PTYs verify who -T permission state and -m current-terminal
selection. Each case runs through all five dispatch modes. The user explicitly
supplied no physical hardware; no serial device is opened or configured.

The Linux-only `tests/host_registered_sessions.py` requires root in a private
mount namespace with private propagation. It mounts a disposable tmpfs at /run,
creates only owned sender/recipient records, and drops supplementary groups and
root credentials to nobody/tty before dispatch. The selected subset checks
message bytes, denied-recipient behavior and who am i/I. It sends only to its
explicit owned recipient PTY; the developer's real login database is inaccessible
inside that private /run. Both PTYs, temporary files and the mount are cleaned up.

Invoke only through the isolating command, after building the profile:

```sh
sudo unshare --mount --propagation private --fork \
  python3 tests/host_registered_sessions.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-registered-sessions.json
```

The default session policy now selects a locally built FreeBSD-derived write,
with repaired EOT, sender alerts, greeting, bell/newline handling and selection
output. Nine cases run in all five modes (45 assertions): full and partial EOF,
erase/kill, control characters, implicit recipient selection, denial, unknown
login and who am i/I. SIGINT after confirmed sender alerts adds direct/exec
witnesses (47 total). EOT and exactly two sender alerts are strict requirements,
not optional audits. The historical `--write-policy vendor` expects
the old 20-case wire representation with a stock-provider PATH; with `--strict-eot` it remains a failing
reproducer against the old vendor. Historical evidence is not rewritten.

The [provider provenance and policy](../tools/host-profile/README.md#standalone-write-provenance)
describes the portable source changes and retained implementation choices.
Registered-session qualification currently covers Linux only; native macOS
build and missing-operand dispatch are checked, but a privileged disposable
macOS session environment has not been supplied.

The focused `Terminal qualification` workflow runs ordinary and ASan/UBSan PTY
subsets on Linux/macOS, supplies the isolated Linux sessions, and uploads JSON
on failure as well as success. Child environments preserve the supplied sanitizer
controls; prior macOS CI's ten terminal-output mismatches lacked raw captures, so
no specific sanitizer diagnostic is retroactively assigned as their cause.

## Remaining environment requirements

Most remaining cases need automated fixtures, not manual operation: error and
resource injection, additional terminfo models, locale matrices, signal timing,
credential combinations and corrupt/private login databases. The available
native macOS host and disposable Linux containers/CI can cover these within
their recorded platform boundaries.

| Capability | Required environment or manual work |
| --- | --- |
| Physical baud/parity/flow control and serial delivery (`U-040/stty-physical-terminal`) | Supplied disposable serial devices, known supported settings, and a loopback or peer. A person must connect/identify hardware; subsequent byte checks can be automated. PTYs cannot establish these effects. |
| Actual terminal initialization/tab/display effects beyond authored capability strings | A specified terminal/emulator with an observable state, or supplied physical terminal. Emulator state checks can be automated; visual/manual checks are needed only where no state API exists. |
| Privileged Darwin login/session and cross-user permission combinations | A disposable macOS VM with administrative access and controlled accounts. Linux namespace results do not qualify Darwin; do not modify the developer's real login database. |
| Additional locales and credential/I/O fault cases | Reproducible locale packages and isolated identities/fault fixtures. These are software setup tasks; no physical equipment or routine manual testing is required. |

The repaired subsets do not close every page/default requirement in CSH-081.
