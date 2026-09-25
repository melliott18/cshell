# Runtime behavior and exit statuses

[CSH-018](tickets/CSH-018-status-and-cli-integration.md) integrated invocation,
input, parser, executor, and shell state. CSH-026 integrates expansion.
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
lists, brace groups, parenthesized subshells, and asynchronous lists. Arguments
support tilde, parameter, arithmetic and command expansion, IFS splitting,
pathname generation, and quote removal. Assignment values and declaration
operands (`export`/`readonly`, including through `command`) use scalar expansion. Redirection operands omit
splitting and pathname generation, including in interactive mode. Quoted
here-document delimiters suppress expansion; unquoted bodies use body-specific
quoting and substitution rules. See [Value expansion](value-expansions.md).

Brace mutations persist; subshell, substitution, background, and multi-stage
pipeline mutations remain isolated. Background execution publishes `$!`.
[Conditionals, loops, case commands, and shell functions](control-flow.md) execute
in the current environment, with explicit `break`, `continue`, and `return`
results and invocation-time function redirections. Expansion is deferred until a command is reached, so
skipped branches and unselected parameter operands have no expansion effects.
There is no unsupported-AST fallback. The executor's existing `ENOEXEC` handling
of external text executables still uses `/bin/sh`.

[Evaluation and utility builtins](evaluation-builtins.md) add dot/eval, exec,
command lookup, runtime aliases, read/getopts, hash, umask, times and ulimit.
[Shell options](shell-options.md) connect invocation and `set` to expansion,
redirection, pipeline statuses and contextual error handling. Noexec parses
without effects; verbose/xtrace expose input and expanded commands.

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
failure and after an unterminated final physical line. With errexit disabled,
external command failure does not end a continuing parent shell. With errexit
enabled, the [failure-context rules](shell-options.md#failure-contexts-and-environment-lifetime)
determine whether the owning environment exits. Lookup uses 127 for not found and 126
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

A command with no command name returns the last substitution status, or zero
when no substitution ran. During expansion, `$?` retains the previous pipeline
status from the current shell environment. Otherwise the invoked command
determines the final status. Expansion errors prevent that command from dispatching, return status 2 (1 for resource
failures), and end non-interactive execution. Interactive execution resumes at
the next complete command. A failed substitution command contributes its status;
it does not itself abort the outer command. Earlier successful substitutions,
words and redirections may already have effects. The failing word restores its
state checkpoint across value expansion and final field generation.

These choices follow the required 0–255 and no-operand behavior in POSIX.1-2024
[`exit`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#exit)
and the context distinction for special-builtin errors in
[shell errors](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01).
Signed operands, modulo reduction outside 0–255, and numeric overflow diagnosis
are explicit project choices in otherwise unspecified operand cases. This
runtime runs [EXIT and signal traps](traps-and-signals.md) with saved status semantics.

## Interactive boundary

The invocation API recognizes a terminal on both stdin and stderr, or explicit
`-i`. For interactive stdin the parser's borrowed `before_read` hook requests a
fixed `$ ` primary prompt or `> ` continuation prompt on stderr, once per
physical read. Blank/comment lines restart the primary prompt; quoted multiline
words and here-document lines retain the continuation prompt. Prompt expansion,
startup files, and parser syntax-error recovery remain outside this runtime.
SIGINT during input resets the parser to a primary prompt. Other parser failures
are sticky and terminate even an interactive shell; execution or expansion errors can continue
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

## Remaining expansion boundaries

[CSH-041](tickets/CSH-041-arithmetic-substitution-replay.md) adds arithmetic-first
checkpoint/replay: `$((echo hi); )` and `$( (echo hi); )` both capture `hi`.
Grammar-valid arithmetic takes precedence, so `$((1/0))` remains an arithmetic
expansion error. Classification never evaluates nested expansions. Full `set`
option parsing and locale startup remain with their existing tickets. NUL output in command substitution
is diagnosed as an expansion error, an explicit choice for unspecified input.
