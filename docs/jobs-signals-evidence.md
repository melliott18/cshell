# Jobs, signals and traps: CSH-050 and CSH-054 evidence

This is the clause/condition map for [CSH-050](tickets/CSH-050-jobs-signals-evidence.md),
reviewed against POSIX.1-2024 on 2026-09-26, with [CSH-054 corrections](#csh-054). It supersedes broad coverage claims,
not the implementation histories of CSH-034/035. The eleven parent requirements
remain **implemented subsets**. Only the assertions below have run evidence;
[remaining obligations](#remaining-obligations) keep the CSH-012 gate closed.

## Sources, applicability and policies

Reviewed normative sources are Shell Command Language
[2.9.3.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_03_02),
[2.11](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_11),
[2.12](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_12),
[2.13](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_13),
[exit](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_22_03),
[trap](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_29_03),
[sh ASYNCHRONOUS EVENTS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_09),
[kill](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/kill.html), and
[wait](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/wait.html).
For utilities, DESCRIPTION, OPTIONS, OPERANDS, output, status and error rules
were reviewed together. The base profile does not waive unshaded asynchronous,
signal, exit, trap, kill or wait rules. O-020/O-021 leave full UP/XSI unselected.
Monitor mode and the implemented job utilities are exercised as supported
conditional behavior; unmonitored job IDs are a supported optional facility.

D-007 chooses `128 + signal` for child/wait statuses, and separate child
processes for multi-stage pipelines. Tests compute host signal numbers; 143 is
used only for TERM on the two tested hosts. Multiple pending trap order and
coalescing are project policy witnesses, not mandatory POSIX ordering. Suspended
compound membership is partly unspecified; simple pipeline tests do not choose
an oracle for every compound form. Numeric trap signals and `kill -SIGNAL` are
XSI/extension observations; `trap 0` names EXIT in the base profile. Unsupported
numeric exit operands such as 256 and -1 have project-policy tests, not required
portable results. No trap installation oracle uses KILL or STOP. Sending KILL
for bounded cleanup and STOP to exercise job control is distinct from trapping
those signals.

## Exact assertion map

Runtime names below come from [trap_cases.py](../tests/trap_cases.py) (`T`) and
[runtime_cases.py](../tests/runtime_cases.py) (`R`), each suffixed `(string)`,
`(file)`, `(stdin)`. `J` identifies [jobs.py](../tests/jobs.py) by its literal
script, which is also printed in the generated name; numeric case indices may
change. `P` names [jobs_cases.py](../tests/jobs_cases.py) PTY cases.
`A` refers to assertions in [jobs_fixture.c](../tests/jobs_fixture.c).
These names, source bytes, helper arguments and expected bytes are authoritative;
this map explains their provenance rather than inventing planned fixture IDs.

<a id="exec-009"></a>

### EXEC-009 — asynchronous lists (2.9.3.1)

Implementation: [execute.c](../src/execute.c) asynchronous launch and redirection;
[jobs.c](../src/jobs.c) registration, announcement and wait; state/expansion `$!`.

| Clause / condition | Exact witnesses and assertions | Limit |
| --- | --- | --- |
| Launch without waiting; zero list status | J `/bin/sleep 60 & p=$!; echo "$?"; kill "$p"; wait "$p"` prints `0\n`, ends 128+TERM within 5 seconds | Sending TERM after launch also proves subsequent commands execute before the sleeper finishes |
| Known ID, final pipeline status and consumption | J `exit 23 & p=$!; wait "$p"` returns 23; repeat wait returns 127; `exit 11 \| exit 31 & wait %1` returns 31; A retained pipeline status 23 | CHILD_MAX exhaustion/eviction remains unverified |
| Unmonitored stdin is empty before explicit redirection | J `/bin/cat & wait "$!"; echo after` prints only `after\n`; redirected input case prints `x` | All three invocation modes, including script bytes arriving on stdin |
| Interactive launch message to stderr | A notification phases compare `[2] PID\n` and `[3] PID\n` against the actual published background PID | Exact format and PID predicate, not a normalized transcript |

<a id="job-001"></a>

### JOB-001 — startup (2.11)

Implementation: `csh_jobs_create` in [jobs.c](../src/jobs.c).
P `foreground Ctrl-C and restored terminal` and every PTY case start a session
leader with its own controlling terminal already assigned to that leader by the
harness; these cases exercise preserved foreground startup. New P `nested foreground startup and restoration` forks a
nonleader in the inherited foreground group. `nested background startup and
restoration` forks a separate group and requires an actual WIFSTOPPED/SIGTTIN
status before the parent transfers the terminal and sends CONT. The nested shell
must enable monitor, become its own group leader, and own the foreground group;
the helper checks PID/PGID equality after `exec`. Both require nested status 0,
outer foreground restoration and `terminal-ok`. See [jobs_helper.c](../tests/jobs_helper.c).
Explicit `-i` without a terminal is covered by J `fg`, `set -m` and the existing
`invalid options are atomic` case: unavailable monitor is diagnosed, not skipped.
The unusual controlling-session-leader startup with an initially different
foreground group remains untested.

<a id="job-002"></a>

### JOB-002 — groups, stop/resume and terminal settings (2.11)

Implementation: `csh_jobs_give_terminal`, `wait_job`, `restore_terminal`, `fg`/`bg`
in [jobs.c](../src/jobs.c), pipeline barriers in [execute.c](../src/execute.c).

| Conditional obligation | Exact P witness | Assertion |
| --- | --- | --- |
| One foreground pipeline group | `pipeline shares foreground group and Ctrl-C` | Producer's binary PGID equals consumer's PGID and terminal foreground; Ctrl-C returns prompt to shell |
| Retain stopped pipeline; CONT after handoff | `pipeline stop resume group and wait`, `Ctrl-Z jobs bg fg Ctrl-C` | Exact Stopped/Running/fg transcripts, terminal group predicates, final 128+INT |
| Save stopped modes and restore on fg | `stopped job modes saved and shell modes restored` | Job disables ICANON, stops, then sees it still disabled on resume; separate shell commands require canonical/no-echo modes before and after fg |
| Background terminal read stops | `background terminal reader stops and fg can read` | Stopped notification, fg ownership, exact file `reader-ready\nreader-done\n` after input |
| Preserve job ownership over option/descriptor changes | `stopped jobs survive monitor toggles`, `unmonitored job stays unmonitored after enabling monitor`, `terminal descriptor survives redirection operands` | Exact errors and successful later terminal checks |

The fault PTY case in [jobs-fault-pty.json](../tests/fixtures/jobs-fault-pty.json)
asserts group/terminal restoration, descriptor counts and child cleanup under
injected failures. Compound lists, background multi-stage group membership,
SIGSTOP of a shell executing a builtin, and completed-command non-replay still
need separate assertions; these pipeline passes do not close those clauses.

<a id="job-003"></a>

### JOB-003 — IDs and notifications (2.11)

Implementation: `csh_jobs_announce`, `csh_jobs_notify`, `csh_jobs_read_ready`,
`find_job` and retained results in [jobs.c](../src/jobs.c).
A `NOTIFY` phase runs twice: `set +b` and `set -b`. An observer only releases
input after the child is reaped. With `+b`, a nonblocking read must return EAGAIN
before the explicit before-prompt hook; with `-b`, completion must already be
reported during idle input. Each then compares exact `Done(17)` bytes and waits
for 17, proving reporting did not consume status. A launch-message comparison
separately verifies job number and published PID. P `current previous and
ambiguous job operands` and `Ctrl-Z jobs bg fg Ctrl-C` cover selectors and stop
notifications. The 32-cycle `repeated background resumes preserve prompt and
terminal` plus [prompt-faults.json](../tests/fixtures/prompt-faults.json) retain
CSH-044's deterministic retry and real PTY regressions. A 150-pipeline loop and
its deliberate watchdog stall retain CSH-045's progress and cleanup regression.
Notification timing during a running foreground utility, every jobs output form,
and every stop signal are not established by the idle-input tests.

<a id="sig-001"></a>

### SIG-001 — dispositions (2.12; sh ASYNCHRONOUS EVENTS)

Implementation: [jobs.c](../src/jobs.c) signal setup/child reset and
[traps.c](../src/traps.c) `csh_traps_after_fork`/exec handoff.
T `traps: asynchronous INT disposition is ignored` and the corresponding QUIT
case query `sigaction` in an external child, both printing `ignored\n` even with
a parent caught action. `traps: external signal dispositions` checks default
USR1, ignored USR1 and ignored CHLD. R `traps: idle Ctrl-C resets prompt`,
`traps: Ctrl-C discards continuation` and `traps: trapped idle Ctrl-C` assert
prompt recovery, status 130, discarded input and trap execution. The five
[traps.py](../tests/traps.py) entry probes require ignored INT/QUIT/CHLD to remain
ignored, including attempted reset and trap listing.
CSH-054 fixes interactive TERM and establishes the unmonitored stop policy,
with additional exact witnesses [below](#csh-054).
No full interactive disposition claim follows from Ctrl-C success.

<a id="sig-002"></a>

### SIG-002 — trap timing (2.12)

Implementation: command-boundary dispatch in [execute.c](../src/execute.c),
interruptible wait in [jobs.c](../src/jobs.c), flags in [traps.c](../src/traps.c).
T `traps: foreground defers action` requires `foreground\ntrapped\n` after the
foreground child signals its parent. CSH-050's `traps: wait interrupted before
action` used delay-based scheduling; CSH-054 replaces it with the six blocked
wait boundary tests [below](#csh-054). A's raw INT interrupted-wait phase retains
its separate robustness witness. `traps: pending signals use number order and
coalesce` checks the optional ordering/coalescing policy. Foreground deferral's
bounded helper delay is not used to establish blocked-wait state.

<a id="sig-003"></a>

### SIG-003 — environments (2.13; trap)

Implementation: [traps.c](../src/traps.c), context and exec transitions in
[execute.c](../src/execute.c).

| Condition | Exact T witness | Assertion |
| --- | --- | --- |
| Function, eval and dot share traps | `traps: function changes shell traps`, `traps: eval changes shell traps`, `traps: dot shares actions` | `function\n`, `eval\n`, `dot\n` after parent self-signal |
| Caught subshell actions reset | `traps: caught action resets in subshell` | Child terminates with 128+USR1, parent action does not run |
| Ignored actions retained | `traps: ignored action retained in subshell and substitution` | Both print the ignored USR1 action |
| Local EXIT and parent isolation | `traps: subshell owns EXIT action`, `traps: substitution owns EXIT action` | Child/parent action order and captured substitution output |
| Listing-only substitution exception | `traps: standalone substitution lists inherited actions` | Parent's saved caught action is printed |
| Successful exec default/ignore handoff | `traps: exec resets caught disposition`, `traps: exec retains ignored disposition` | `default\n`/`ignored\n`; no parent EXIT action after successful exec |

CSH-054 adds pipeline/background/general-substitution listing and failed
interactive exec witnesses [below](#csh-054); broader delivery remains CSH-058.

<a id="u-008"></a>

### U-008 — exit

Implementation: exit handler in [execute.c](../src/execute.c), finalization in
[main.c](../src/main.c) and [execute.c](../src/execute.c).
R `exit initially`, `exit preserves last status`, `exit numeric 0`, `42`, `255`,
`subshell exit isolated`, `brace exit stops list` and `signal retained ...`
assert status, environment termination and no subsequent command effects.
T `traps: EXIT sees and preserves status`, `traps: EXIT may replace status`,
`traps: subshell EXIT may replace status`, `traps: substitution EXIT may replace status`,
`traps: EXIT runs after errexit` and `traps: EXIT retains environment and omitted status`
cover final status 7/9/1, single action execution and the final variable value.
Unsupported numeric operands remain separate policy tests. CSH-054 covers the
full 0–255 space and fixes omitted exit status inside actions [below](#csh-054).

<a id="u-015"></a>

### U-015 — trap

Implementation: [traps.c](../src/traps.c) parsing, listing, installation and flags.
T `traps: listing and reset`, `traps: listing can be reinput`, `traps: ignored signal`,
`traps: signal action and saved status` and the SIG-003 cases establish the named
actions, quoting and saved status. New `traps: selected defaults can be restored`
and `traps: all defaults can be restored` restore default USR1/USR2/EXIT after
changing them. `traps: plain listing omits defaults` distinguishes plain trap
from `-p`. `traps: zero operand resets EXIT` covers the unsigned-first-operand
form. `traps: invalid condition returns nonzero and continues` requires diagnostic,
status 1 and `alive`, with no special-builtin abort. Entry-ignore listing is
checked separately in traps.py. The old `-p INT` reset expectation was incorrect:
it now requires a reinput-ready default command. KILL/STOP are omitted from
all-condition output. The implementation enumerates host-queryable signals,
including numeric host extensions; exhaustive host-signal listing and roundtrip
coverage, every invalid operand mix and output-failure path remain open.

<a id="u-026"></a>

### U-026 — kill

Implementation: `kill_builtin` in [jobs.c](../src/jobs.c), external host `/bin/kill`.
J default TERM to saved numeric PID, `/bin/kill -s TERM "$p"`, and internal `kill -l 143` / external `kill -l 15` assert 128+TERM and
`TERM\n`. External `kill -l 143` passes on macOS but fails in Debian
procps 4.0.2; CSH-052 retains that failure. Existing J `kill -s UNKNOWN 1`,
`kill -s`, `kill -- bad`, `kill %42` require nonzero diagnostics without signaling
an unintended process. Job selector/pipeline KILL and STOP/CONT/TERM cases are
supported XSI/extension witnesses. Both host binaries are identified in the run
record. Docker now explicitly installs `procps` to supply exec-accessible kill.
CSH-054 fixes case-independent `-s` and adds the name/status, group-zero probe
and operand-continuation witnesses [below](#csh-054); actual group delivery and
permission failures remain with CSH-058. No reference-shell vote was
used to set these expectations.

<a id="u-032"></a>

### U-032 — wait

Implementation: the wait branch of `csh_jobs_builtin`, `wait_job`, retained registry in [jobs.c](../src/jobs.c).
J numeric cases now cover single saved PID (23), reverse two-PID order (3),
unknown-before-known (3), known-before-unknown (127), repeat wait (127), and
no-operand wait consuming results (subsequent 127). Existing J no-child wait,
two-child no-operand wait and final pipeline wait assert 0/0/31. Unknown syntax
and IDs diagnose and return 127. Subshell/pipeline waits cannot consume parent
IDs. A retains completed and already-reaped statuses, leaves unrelated children
waitable, interrupts without consuming a live child, and reports without
consuming status. SIG-002 owns trapped-wait timing. Retention at CHILD_MAX,
fg removal from the known-ID set and selected wait interruption need more
coverage; all retained-status claims are limited to the exercised counts.

## Remaining obligations

[CSH-054](#csh-054) fixes the two reproduced defects and assigns each remaining
clause to CSH-057 or CSH-058 in the exact map below. This is a concrete residual inventory,
not a waiver and not a claim that all untested behavior is defective. CSH-050
supplies a reviewable map and run record; CSH-012 remains closed. The parent rows
are intentionally not promoted to verified, so no broad row obscures a narrower
failure. Stable anchors in this document separate each family's evidence.

CSH-044 and CSH-045 were integrated by PR #85 before this work's baseline. Their
old failures remain historical failures; this work reruns the fixed regressions
and does not treat retries as passes. A concurrent macOS validation run failed
the harness cleanup snapshot deadline; its distinct loaded-run failure is
retained in CSH-054 and the run record. PTY allocation/controlling-terminal
capability errors can produce scoped skips through the existing harness:
CSH-033 owns transport availability, CSH-054 owns missing behavioral evidence.
Any such skip leaves JOB-001/002/003 and terminal SIG-001 portions unverified.
Only C locale is exercised; non-C signal diagnostics remain CSH-042/052 scope.
No reference-shell comparisons are part of this record.

## Run record

See the [ticket validation record](tickets/CSH-050-jobs-signals-evidence.md#validation-record)
for source/binary identities, toolchains, exact commands, counts and residual
probe results. Runtime/PTY fixtures receive `PATH=os.defpath` (`/bin:/usr/bin`),
`LANG=C`, `LC_ALL=C`, per-case HOME/TMPDIR and optional MallocNanoZone; no TZ
is set. API/entry probes inherit the caller environment. The runner sets umask
077 and supplies per-case temporary directories, source files, process/session
limits, a five-second default bound and a 65,536-byte output limit. PTYs use
24x80, canonical input, ISIG, no echo, exact LF output and a new controlling
session. The API has five-second phase/progress watchdogs and a 60-second outer
bound. Harness self-tests independently check timeout/failure cleanup.

<a id="csh-054"></a>

## CSH-054 corrections and residual ownership

[CSH-054](tickets/CSH-054-signal-contract-gaps.md) fixes interactive TERM,
case-independent kill names, and omitted `exit` status inside trap actions.
It selects actual SIG_IGN for QUIT/TERM and the D-007 stop policy. During a
blocked fork window, temporary default dispositions keep the child's signals
pending; the parent restores its ignores before unblocking. This preserves
both interactive ignores and the existing launch-race contract. `POLL` is now
named where the POSIX host header defines it (including Darwin's value 7).
All eleven family rows remain implemented subsets.

`S` below means [signal_contracts.py](../tests/signal_contracts.py), with the
prefix `signal contracts:` and string/file/stdin suffixes, except interactive
cases, which explicitly use `-ic` with redirected stdin. `W` is the separate
[wait_handshake.py](../tests/wait_handshake.py) runtime interposing only jobs.c's
`sigsuspend`. This test-only boundary injects signals after asserting that they
are blocked and before the real atomic unblock/wait; no elapsed delay supplies
its scheduling oracle. It is deliberately not described as an uninstrumented
public-runtime observation. `P`/`A` retain the definitions above.

| Requirement / condition | Exact cases and assertions | Remaining owner |
| --- | --- | --- |
| SIG-001 interactive defaults, overrides and reset | S `interactive TERM ignored`, `interactive NAME override and reset` for TERM/QUIT/TSTP/TTIN/TTOU; exact `alive` and `caught/alive` bytes, zero status. P `interactive ignored signals with monitor +m` and `-m` send Ctrl-Z, Ctrl-\\, TERM and direct stop/QUIT signals, then assert foreground ownership and `terminal-ok`. A `interactive_dispositions` queries actual SIG_IGN, excluding false success due to an orphaned default stop or caught no-op. | Exhaustive remaining inherited/overridden combinations: CSH-058 |
| SIG-001/003 child inheritance and fork race | S `interactive child fork NAME defaults`, `interactive child exec NAME defaults`, `interactive explicit ignore reaches exec NAME`; 20 `traps.py` entry-ignore cases. `execute_faults.c:terminal_job_faults` injects INT/TSTP/TERM/QUIT inside the fork wrapper, before child reset; exact signal-derived result and mask/terminal restoration. | CSH-058 for additional environment/reset combinations |
| SIG-002/U-032 selected/all wait interruption | W USR1, TERM, both USR1+USR2, with selected PID and no operand: `wait-armed` on stderr, action and wait status 128+first signal, second wait 23, consumed third wait 127. The old delay-based trapped-wait runtime case is removed. Multiple distinct actions use the documented signal-number ordering choice. | CSH-058 for uninstrumented blocked-wait observation; CSH-057 for capacity and fg consumption |
| SIG-003 trap environments | S `caught action resets in pipeline`, `background`, `general substitution` require default USR1 listing; `failed interactive exec restores TERM action` requires the exec diagnostic, then `caught/alive`. | CSH-058 for actual delivery/disposition cross-product beyond these listings |
| U-008 operands and trap status | S `exit operands 0 through 15` through `240 through 255` assert every status in all three modes. `EXIT omitted status after ...` covers true/false, function and eval; `signal action omitted exit status` and `subshell inside EXIT uses its own status` distinguish action exit from child exit. | No residual from CSH-054's stated U-008 inventory: 128+host signal is <=255 on both hosts, so there are no applicable >256 signal-derived operands. Unsupported operands remain separately classified. |
| U-015 host listing and error continuation | S `host condition reinput NUMBER` for every catchable condition returned by host sigaction in 1..127, including numeric extensions; all `trap -p` lines checked as an exact set without duplicates against that host set plus EXIT. `mixed invalid trap operands continue` asserts both valid actions, two diagnostics and status 1; `trap output failure` asserts selected-listing status/diagnostic. | CSH-058 for other output-failure forms and uninstallable conditions |
| U-026 names, mapping and partial failures | S `lowercase TERM delivered` terminates by TERM; `kill mixed case NAME` delivers each catchable required host symbol; `kill name/status NAME` maps native and 128+signal numbers, including KILL/STOP without delivering them. `zero signal and group operands` probes this runner-owned session's group using 0 and -$$. `mixed invalid kill operands continue` diagnoses the invalid PID and delivers USR1 to the shell. | CSH-058 for actual group delivery and permission errors; external utilities remain CSH-056 |
| EXEC-009, JOB-001/002/003 | Existing CSH-050 assertions rerun; CSH-054 adds the signal-policy and launch-race assertions above. | CSH-057 explicitly owns CHILD_MAX/eviction, fg consumption, session-leader startup with another foreground group, background pipeline/compound and suspended compound membership, completed-command non-replay, builtin STOP/CONT, foreground notification timing, stop variants and jobs formats |

The [CSH-054 run record](evidence/csh-054/README.md) retains baseline failures,
implementation-time failures and final native/Docker/sanitizer results. The
follow-ups [CSH-057](tickets/CSH-057-job-lifecycle-boundaries.md) and
[CSH-058](tickets/CSH-058-signal-edge-evidence.md) explicitly own the remaining
clauses; full UP/XSI and unspecified choices are not folded into passing base
assertions. The conformance audit gate remains open.
