# Job control

[CSH-034](tickets/CSH-034-job-control.md) adds job control to the public runtime.
Interactive shells with an available controlling terminal enable monitor mode
by default. This does not select the complete UP or XSI option groups for a
conformance claim. Scripts and redirected input use the same job/status registry with
monitor mode disabled. Explicit `-i` without a usable terminal retains
interactive error behavior but does not enable monitor mode.

## Commands and options

| Command | Supported behavior |
| --- | --- |
| `jobs [-l\|-p] [--] [%job ...]` | Show running, stopped, and newly completed jobs; `-l` includes direct stage PIDs, `-p` prints the group leader PID (the associated final-stage PID for unmonitored jobs). |
| `fg [--] [%job]` | Give a monitored job the terminal, restore its saved terminal settings, continue it, and return its foreground status. |
| `bg [--] [%job ...]` | Continue monitored jobs without giving them the terminal. |
| `wait [--] [pid\|%job ...]` | Return the last requested job's status. With no operands, wait for all jobs and return zero. Unknown operands return 127; SIGINT interrupting an interactive wait returns 130 without discarding the job. |
| `kill [-s signal\|-signal] [--] pid\|%job ...` | Signal a monitored job's process group, an unmonitored job's direct stages, or numeric process/group operands. The default signal is TERM; zero checks existence/permission. |
| `kill -l [status ...]` | List supported symbolic signal names, or convert a signal number or shell signal status to a name. |
| `set -m`, `set +m`, `set -o monitor`, `set +o monitor` | Enable/disable grouping for subsequent launches. Enabling monitor requires a usable terminal. |
| `set -b`, `set +b`, `set -o notify`, `set +o notify` | Enable/disable reporting background status changes during foreground waits and while waiting for input. Otherwise changes are reported before the next prompt. |
| `set -o`, `set +o` | Show all implemented shell options, or print commands restoring their settings (CSH-032). |

`%number`, `%%`, `%+`, `%-`, `%prefix`, and `%?substring` select jobs. Omitted
`fg`/`bg` operands select the current job. Stopped jobs take precedence over
running jobs; within each class the most recently launched/resumed/stopped job
is current and the next eligible job is previous. Ambiguous, missing, completed, or
unmonitored operands cannot be foregrounded or continued by `fg`/`bg`.
Quote substring specifications such as `'%?sleep'` to prevent pathname expansion.
Numeric `wait` operands identify
the asynchronous command PID published as `$!` (the final pipeline stage).
The runtime expands `$!`; module clients can also read it from shell state.

Interactive asynchronous launches print `[job-number] last-stage-pid` to stderr.
Job descriptions use prepared argument text and pipeline/group separators; they
are display text, not a round-trippable shell command. Status lines show
`Running`, `Stopped` (TSTP), `Stopped (SIGSTOP/SIGTTIN/SIGTTOU)`,
`Done`, `Done(status)`, or `Terminated (SIGname)` with current/previous markers.
The default format is `[number] marker state command`; `-l` inserts the leader
or associated PID before the state and lists additional stages on `PID command` lines.
Completed jobs disappear from listings after reporting, while their result
remains available to `wait`. Explicit waits consume completed results. The
registry retains at least the platform's `_SC_CHILD_MAX` completed results
(256 if unknown), then may discard older completed results on a new
asynchronous launch. Running/stopped records are kept in addition to this
capacity; foreground launches never evict retained asynchronous statuses.

If a foreground job exits before its continuation signal can be delivered,
`fg` collects and returns that job's exit status. A rejected SIGCONT is accepted
only after every owned child has completed. On Darwin, group departure can
precede a reportable exit: `getpgid` returning ESRCH for an owned PID permits a
final blocking wait for that child. Errors for live or stopped jobs
still fail without discarding their state.

Job builtins execute under the executor's normal assignment/redirection rules.
`set` is a special builtin; the others are regular builtins. Invalid `set`
operands are validated before changing options or positional parameters.
CSH-032 integrates [the shared option parser](shell-options.md), including
invocation `-m`/`-b` and disabling forms. Job tables are isolated in subshells, background compound commands,
and pipeline stages. A `wait` in one cannot consume its parent's statuses.

A stopped compound originally launched in the background remains intact when
foregrounded and resumed. For a compound originally launched in the foreground,
cshell retains its stopped pipeline and discards other pending commands in that
foreground list. This is the selected membership policy within POSIX's permitted
and unspecified choices. Completed commands are not replayed. A suspended job
has a separate internal flag from its numeric status, so an ordinary command
exiting with 128+stop-signal does not discard subsequent commands.

## Process and terminal ownership

The runtime creates one `csh_jobs` manager attached to its persistent
`csh_execution_context`. `src/execute.c` prepares all launches before forking,
registers each direct child in source order, and delegates all collection to
`src/jobs.c`. `waitpid` always targets a positive, owned PID. No handler reaps
children or accesses the registry.

A controlling session leader claims its terminal even when another group
initially owns it. A nested nonleader instead stops with TTIN until its parent
foregrounds it. For monitored jobs both parent and child call `setpgid`. A close-on-exec pipe
barrier holds every child until all stages share the group and foreground
terminal transfer succeeds. This prevents fast leaders from exiting before
later stages join and prevents early terminal reads from stopping a foreground
job. Terminal signals are blocked across fork until children reset their
inherited dispositions and cross the barrier, so an immediate interrupt cannot
run the shell's handler in an unprepared child. Every pipe is closed before
command redirections. The private terminal
descriptor is moved away from all descriptor operands before parent execution.

The manager collects exits, stops, and continuations for every stage. A pipeline
is stopped when every surviving direct stage is stopped; its status is
`128 + stop-signal`. Normal pipeline status uses the final stage, with logical
negation for `!`. On completion or stop, the shell regains terminal ownership
and its saved settings. A stopped foreground job retains its own settings for
`fg`. Existing grouped jobs remain recorded across monitor toggles; `fg`/`bg`
require monitor mode to be enabled when invoked.

Without monitor mode, children stay in the inherited process group and
asynchronous commands receive `/dev/null` input before explicit redirections,
with SIGINT/SIGQUIT ignored. With monitor mode, background terminal reads stop
naturally through SIGTTIN. External foreground commands receive terminal
signals using their default dispositions; the interactive shell survives them.

SIGCHLD merely interrupts an atomic `pselect`/`sigsuspend` wait. The normal
execution path scans the registry with SIGCHLD blocked before sleeping, avoiding
missed/coalesced exit events and reaping while input is idle. An optional input
wait hook integrates descriptor sources without read-ahead or dependencies from
the input module to jobs. SIGINT sets only a `sig_atomic_t` flag for interrupted
interactive `wait` calls. A process has one signal-owning manager; destruction
restores the saved signal dispositions. Forked contexts release their copied
parent registry without waiting for or signalling those PIDs.

Allocation, pipe, fork, process-group, wait, and terminal-handoff failures close
owned descriptors, kill the partially launched group/direct children, reap them,
and restore terminal ownership/settings. No launch-side effects occur before
the barrier is released. Errors after release cannot undo command effects.
The synchronous prepared-command APIs retain their existing direct-child contract
and do not acquire a terminal; hosts wanting jobs opt into the context manager.

## Trap and hangup integration

[CSH-035](traps-and-signals.md) adds pending actions, input interrupt recovery,
child disposition reset, and an interactive hangup policy. Ordinary shell exit
still detaches background jobs; HUP signals live jobs before exit. The combined
job and trap tests do not claim full POSIX shell conformance.

## Evidence

`make test-jobs` checks direct-child ownership, retained pipeline statuses,
150 rapid asynchronous pipelines, reaping during idle input, interactive wait
interruption, allocation/pipe/fork/wait failures, and builtin behavior in all
three input modes. API/fault fixtures use the existing bounded process-group
runner, so failures/timeouts cannot leave their descendants running.
Each API phase/pipeline has a five-second progress watchdog and a 60-second
outer bound; a deliberate stall checks diagnostics and descendant cleanup.
`make test-jobs-pty` uses CSH-033's bounded terminal runner
for Ctrl-C, Ctrl-Z, bg/fg, grouped pipelines, background reads, job selectors,
monitor toggles, descriptor reservations, and terminal settings. Injected
process-group, handoff, mode-restoration, and wait failures verify terminal
ownership and absence of live direct children/descriptors. These targets join
`make test` and `make test-pty`, respectively, including Docker and sanitizer CI.
The PTY suite repeats 32 full stop/bg/fg/Ctrl-C cycles. Prompt writes use the
shared interrupted/partial-write retry helper; `make test-prompt` independently
injects both faults into primary and continuation prompts. The
[CSH-037 follow-up record](tickets/CSH-037-portability-audit.md) links the
CSH-044/045 regressions and platform results. The
[CSH-050 clause map](jobs-signals-evidence.md) adds nested startup,
notification timing and numeric-PID coverage, with [CSH-054 signal corrections](tickets/CSH-054-signal-contract-gaps.md) and
[CSH-057 lifecycle boundaries](jobs-signals-evidence.md#csh-057).
The latter adds bounded CHILD_MAX/fallback exhaustion, old live/stopped records,
all supported jobs formats, controlling-session startup, background/compound
membership, non-replay, builtin STOP/CONT, and notification timing during an
active foreground wait. [Retained runs](evidence/csh-057/README.md) distinguish
controlled API tests from public PTY observations.

Internal job waits preserve the caller's signal mask. On Darwin, cleanup uses
a zero-time terminal-independent `pselect` to clear deferred mask restoration
before restoring that mask; it does not clear intentionally inherited blocks.
The parent assigns new process groups before releasing the launch barrier,
avoiding concurrent parent/child assignments on affected Darwin kernels.
