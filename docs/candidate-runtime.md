# Runtime behavior and exit statuses

[CSH-018](tickets/CSH-018-status-and-cli-integration.md) integrated invocation,
input, parser, literal command adapter, executor, and shell state.
[CSH-039](tickets/CSH-039-legacy-retirement.md) promotes that runtime to the only
public executable, with its entry point in [`src/main.c`](../src/main.c):

```sh
make
./cshell -c 'exit 23'
./cshell script-file arg1 arg2
printf 'exit 23\n' | ./cshell
```

There is no alternate candidate executable or legacy runtime. The handwritten
lexer needs no Flex. This is a tested bootstrap subset, not a POSIX compliance
claim. This document retains its original filename so historical ticket links
remain valid.

## Supported execution

The [invocation API](input-and-invocation.md) selects `-c`, a script file, or
stdin, copies `$0` and positional operands into state, and imports the process
environment. The runtime calls the parser at complete-command boundaries;
commands that read stdin receive the bytes after their command line. Script
files and command strings leave stdin available independently.

Each complete command uses the [execution context API](execution.md#lists-groups-and-background-contexts):
simple commands, pipelines (including group stages), sequential lists, AND/OR
lists, brace groups, parenthesized subshells, and asynchronous lists. Literal
quoting, assignment prefixes, external lookup, state builtins, `exit`, and
ordered redirections including literal here-documents are supported. Brace
mutations persist; subshell, background, and multi-stage pipeline mutations
remain isolated. Background execution publishes an identifier in shell state;
parameter expansion, including spelling `$!` in a command, still awaits CSH-008.

Parameter/command/arithmetic expansion, globbing, conditionals, loops, case
commands, and function definitions are rejected before any part of that complete
construct executes. Earlier complete commands may already have executed.
There is no unsupported-AST fallback. The executor's existing `ENOEXEC` handling
of external text executables still uses `/bin/sh`.

The runtime keeps one execution context and [job manager](job-control.md) across
parser reads. It reaps owned children at execution boundaries and during idle
input, retains results for `wait`, and supports `jobs`, `fg`, `bg`, and `kill`.
Interactive terminals enable monitor mode, foreground process groups, and saved
terminal settings. Shell exit releases the registry without waiting for jobs.

Syntax and incomplete-EOF errors include source, line, and column. Invocation
errors identify an offending argument when available. Command diagnostics are
printed once, by the child or builtin handler, or by the runtime for a returned
module error. Non-interactive execution prints no banner or prompt.

## Status and exit policy

State starts at status 0. Each attempted command replaces the last status;
blank lines and comments do not. EOF returns that status, including EOF after
failure and after an unterminated final physical line. External command failure
does not end a continuing parent shell. Lookup uses 127 for not found and 126
for found but unexecutable. A child killed by a signal produces
`128 + signal_number`; the parent stores this integer and can continue. On the
supported macOS/Linux platforms, SIGTERM therefore produces 143. Exiting the
shell with this status is an ordinary process exit, not a signal sent to
the shell itself.

The exit handler supports `exit [--] [status]`:

| Input | Outcome |
| --- | --- |
| No operand, including `exit --` | Exit with the current last status; initially 0 |
| Decimal integer in `long` range, with optional `+` or `-` | Exit with its low eight bits; `256` becomes 0, `-1` becomes 255 |
| Empty, nonnumeric, whitespace-containing, or overflowing operand | Print `numeric status required`, set status 2 |
| More than one operand after optional `--` | Print `too many arguments`, set status 2; operand count is checked first |

For either operand error, non-interactive shells exit; interactive shells
continue. A subsequent no-operand `exit` preserves the error's status 2.
Redirection failure for `exit`, or another special-builtin error, similarly ends
a non-interactive shell and continues an interactive shell with its failure
status. A special builtin in a multi-stage pipeline affects only its stage.
Redirection failure for a regular builtin or external command allows the next
complete command to run.
Descriptors are restored before honoring a parent builtin's exit request.

These choices follow the required 0–255 and no-operand behavior in POSIX.1-2024
[`exit`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#exit)
and the context distinction for special-builtin errors in
[shell errors](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01).
Signed operands, modulo reduction outside 0–255, and numeric overflow diagnosis
are explicit project choices in otherwise unspecified operand cases. This
runtime does not implement traps.

## Interactive boundary

The invocation API recognizes a terminal on both stdin and stderr, or explicit
`-i`. For interactive stdin the parser's borrowed `before_read` hook requests a
fixed `$ ` primary prompt or `> ` continuation prompt on stderr, once per
physical read. Blank/comment lines restart the primary prompt; quoted multiline
words and here-document lines retain the continuation prompt. Prompt expansion,
startup files, full trap/signal semantics, and parser
syntax-error recovery remain outside this runtime. Parser failures are sticky
and terminate even an interactive shell; adapter rejection can continue
because its parser remains usable. `-i` with a string or file selects interactive
error behavior without printing stdin prompts.

## Validation

`make test-runtime` builds and runs the cross-mode cases; `make test-runtime-pty`
runs real controlling-terminal cases. Both use the existing bounded
[`tests/smoke.py`](../tests/smoke.py) runner with exact output/status and file
assertions, no prompt stripping, and its unchanged process/session cleanup.
[`tests/runtime_cases.py`](../tests/runtime_cases.py) generates replacement JSON
suites under `build/tests/`, expanding shared expectations across the three
input modes and resolving the external helper path and platform errno strings.
Inspect those suites or select a single generated case directly with `smoke.py`.

`make test` includes the pipe cases; `make test-pty` includes the terminal cases.
Native and Docker CI entry points run both. Their ASan/UBSan checks also run the
public executable and module suites.
