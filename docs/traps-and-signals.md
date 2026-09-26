# Traps and signal behavior

[CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) adds `trap` to the
runtime. This page describes the selected base Issue 8 profile and the signal
choices exercised by the runtime and terminal fixtures. It does not claim full
shell conformance.

## Trap command

`trap [--] action condition...` installs an action; `-` resets a condition and
an empty action ignores it. `trap` and `trap -p [--] [condition...]` print
actions as quoted, reinput-ready commands. `-p` includes default actions,
whereas plain `trap` lists only non-default
actions, including signals ignored on entry. All-condition `-p` omits KILL/STOP.
`EXIT` and `0` name the exit action; `trap 0` resets it.
Signal names accept an optional uppercase `SIG` prefix and case-independent
names as extensions. The kill builtin accepts case-independent names without
a prefix, and signal zero for existence/permission checks. Numeric signal
conditions are an extension while full XSI remains unselected. Unknown, unsupported, or
uninstallable conditions produce a diagnostic and nonzero status; processing
continues for other conditions. These operand errors do not force a
non-interactive shell to exit. SIGKILL and SIGSTOP cannot acquire a caught or
ignored disposition on the supported hosts.

For a non-interactive shell, a signal inherited as ignored at shell entry
remains ignored: later `trap` operands for that signal have no effect. The job
manager preserves inherited ignores when it resets dispositions in children.

Actions are parsed when dispatched, in the shell's current environment. They
can change variables, functions, options, traps, and the working directory.
The action sees the status immediately before dispatch in `$?`; unless it
explicitly exits, its own last command does not replace that status. `EXIT`
runs once after the command loop with the shell's final status. An `exit` with
no operand that ends a trap action uses the status from before the action, even
after intervening commands. An explicit operand still selects its own status.
A `return`,
`break`, or `continue` action transfers control through the containing function
or loop when that context permits it. An explicit
`exit` in that action can replace it. A normal shell exit detaches background
jobs without waiting for them.

## Delivery and environments

The process signal handlers only assign `volatile sig_atomic_t` flags. They
never parse commands, allocate, use stdio, or reap children. The job manager
continues to collect only owned positive PIDs while SIGCHLD is blocked around
status scans. Coalesced delivery may cause fewer action invocations than
signals sent; multiple distinct pending actions run in signal-number order,
which is an implementation choice where the standard does not require an
order. A signal raised by an action is deferred to a later command boundary,
so a CHLD action that starts another child cannot recursively dispatch itself
without a boundary.

The executor dispatches pending actions after commands and after interrupted
input. A trapped signal received while a foreground command runs is deferred
until that command completes. A signal interrupting `wait` returns
`128 + signal_number` before its action runs; the job remains available for a
later wait. The same `128 + signal_number` mapping is used for signalled child
statuses. This mapping is the documented implementation-defined status choice
for the supported macOS and Linux platforms.

Functions, `eval`, and dot scripts share the caller's trap table. Forked
subshells, pipeline stages, background commands, and command substitutions
start with caught actions reset to default and ignored dispositions retained.
They may install local actions, including EXIT. A command substitution that
contains only one `trap` command can list the parent's saved actions without
executing them. External utilities and a successful `exec` receive default
dispositions for caught signals and inherited ignored dispositions. A failed
interactive `exec` restores the shell's installed actions.

## Interactive dispositions and D-007

Interactive shells ignore untrapped QUIT and TERM. D-007 chooses to ignore
TSTP, TTIN and TTOU with monitor disabled, as well as when it is enabled. These
are actual SIG_IGN dispositions; an installed trap can override them, and a
reset restores the interactive policy. Noninteractive shells retain default
or inherited ignored actions. Children restore entry defaults or inherited
ignores before executing; explicit ignored trap actions remain ignored.

The executor blocks launch signals and temporarily prepares default actions
around fork so a child cannot discard a signal solely because it inherited the
interactive shell's ignore. Before unblocking, the parent restores its actions
and the child establishes its own actions. This also applies on failed launch.
The API fixture inspects actual dispositions, the fault fixture delivers signals
inside fork, and PTY cases exercise direct and terminal-generated delivery with
monitor both enabled and disabled. See [exact evidence](jobs-signals-evidence.md#csh-054).

## Input, interrupt, and hangup policy

An interactive SIGINT during an idle or continuation read discards the partial
command, sets status 130, and starts a new primary prompt. An installed INT
action runs before that prompt. The same transient parser reset is used when a
caught signal interrupts descriptor input; a normal read error remains sticky
and exits the input loop. A foreground job receives terminal interrupts in its
own process group; the shell regains the terminal and remains usable.

An interactive untrapped SIGHUP causes status 129, sends HUP and CONT to live
registered jobs, then runs the EXIT action. An installed HUP action handles the
signal without forcing shell exit. A non-interactive shell retains the host's
default HUP termination unless it installs a trap. Ordinary exit does not
signal background jobs. No terminal line editor is selected; the UP editing
requirements and full XSI profile remain open under
[shell options](shell-options.md#profile-and-validation).

## Evidence

`tests/trap_cases.py` adds strict cases in all three runtime input modes for
installation, reset, ignore, listing/reinput, invalid conditions, status,
EXIT, functions, `eval`, subshells, substitutions, foreground deferral,
interrupted `wait`, CHLD, and inherited ignore. `make test-traps` checks
signals ignored before shell startup. `tests/runtime_cases.py` adds
terminal cases for idle and continuation Ctrl-C, trapped INT, and interactive
hangup. The bounded harness owns process/session cleanup on failure or timeout.
The existing `make test-jobs` and `make test-jobs-pty` suites cover rapid job
completion, unique reaping, process groups, and terminal restoration. Run
`make test`, `make test-pty`, `make docker-test`, and `make docker-test-pty`
for the combined native and Linux-container evidence.

[CSH-050 clause evidence](jobs-signals-evidence.md) maps exact cases and platform
results. [CSH-054](jobs-signals-evidence.md#csh-054) fixes interactive TERM, lowercase
kill and omitted trap exit status, and establishes the unmonitored stop policy.
CSH-057/058 retain the explicitly listed remaining obligations.
