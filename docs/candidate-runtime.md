# Candidate runtime and exit statuses

[CSH-018](tickets/CSH-018-status-and-cli-integration.md) connects the replacement
invocation, input, parser, literal command adapter, executor, and shell state in
[`src/candidate.c`](../src/candidate.c). Build the internal test executable with:

```sh
make build/cshell-candidate
./build/cshell-candidate -c 'exit 23'
./build/cshell-candidate script-file arg1 arg2
printf 'exit 23\n' | ./build/cshell-candidate
```

The candidate links no legacy objects and needs no Flex. The default `cshell`
executable remains the prototype until [CSH-039](tickets/CSH-039-legacy-retirement.md).
This is a tested bootstrap subset, not a POSIX compliance claim.

## Supported execution

The [invocation API](input-and-invocation.md) selects `-c`, a script file, or
stdin, copies `$0` and positional operands into state, and imports the process
environment. The candidate calls the parser at complete-command boundaries;
commands that read stdin receive the bytes after their command line. Script
files and command strings leave stdin available independently.

Each complete command must satisfy the existing [literal adapter](execution.md):
one foreground simple command or simple-command pipeline, literal quoting,
assignment prefixes, external lookup, state builtins, `exit`, and ordered
redirections including literal here-documents. Separate physical command lines
execute sequentially. Pipeline stages use child execution environments, while a
singleton state builtin can update the parent. Parameter/command/arithmetic
expansion, globbing, AND/OR lists, multi-command semicolon lists, background
commands, compound commands, and function definitions are rejected before any
part of that complete construct executes. Earlier complete commands may already
have executed. There is no unsupported-AST fallback. The executor's existing
`ENOEXEC` handling of external text executables still uses `/bin/sh`.

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
candidate with this status is an ordinary process exit, not a signal sent to
the candidate itself.

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
runtime does not implement traps, job control, or compound subshell syntax.

## Interactive boundary

The invocation API recognizes a terminal on both stdin and stderr, or explicit
`-i`. For interactive stdin the parser's borrowed `before_read` hook requests a
fixed `$ ` primary prompt or `> ` continuation prompt on stderr, once per
physical read. Blank/comment lines restart the primary prompt; quoted multiline
words and here-document lines retain the continuation prompt. Prompt expansion,
startup files, job control, signal handling for the shell itself, and parser
syntax-error recovery remain outside this candidate. Parser failures are sticky
and terminate even an interactive candidate; adapter rejection can continue
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
The existing native and Docker CI entry points run both, and native sanitizer
CI includes the candidate suites. Prototype smoke results remain separate.
