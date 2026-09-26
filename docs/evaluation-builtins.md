# Evaluation and utility builtins

[CSH-031](tickets/CSH-031-evaluation-builtins.md) connects evaluation and lookup to
runtime aliases and supplies `read`, `getopts`, `hash`, `umask`, `times`, and
`ulimit`. The dispatcher and nested parser loop are in
[`execute.c`](../src/execute.c); independent utility handlers are in
[`utility.c`](../src/utility.c).

## Evaluation and state

`eval` joins its arguments with one space and runs the result through the normal
complete-command parser in the current environment. No arguments, empty text,
and empty dot files succeed. A nonzero status from an ordinary evaluated command
is returned without being classified as an error in the evaluation builtin.
Syntax, expansion, and special-builtin errors retain the runtime's interactive
versus non-interactive policy. The nested loop stops on explicit exit, return,
or loop control transfer. Evaluation nesting is limited to 128 active calls.
`eval` does not interpret options, including `--`.

`. [--] file [arguments...]` searches PATH for a readable file when the
operand contains no slash; execute permission is unnecessary. No implicit current
directory search is added. Supplied arguments temporarily replace positionals
without changing `$0`; restoration is allocation-free, including after errors or
`return`. Without supplied arguments, changes to positionals persist. `return`
is valid in a dot script, including an inherited subshell environment, and stops
only the innermost active dot call. `eval` propagates return to its enclosing
function or dot script. Each source owns its input independently of command stdin.

Aliases belong to shell state and are copied independently by state cloning.
The runtime, dot/eval loops, and backquote parser attach that state's table.
Definitions take effect at the next complete-command read, so an alias defined
in a semicolon list does not rewrite the rest of the already parsed list.
Functions retain aliases substituted while their definitions were parsed.
Command substitutions inherit aliases with their isolated state.

## Search and exec

Search checks special builtins before functions, then intrinsic utilities, then
PATH. The internal `pwd` implementation is selected when PATH reaches `/bin/pwd`
or `/usr/bin/pwd`; other PATH entries can override it. `pwd` is not intrinsic.
The job-aware builtins and `trap` are described in [job control](job-control.md)
and [traps and signals](traps-and-signals.md). `type` is supplied as a convenience extension without
selecting the complete XSI profile.

`command [-p] [-v|-V] [--] name [arguments...]` suppresses function lookup and the
special assignment/error properties of its immediate target. Errors inside a
nested evaluation retain their own command classifications. Prefix assignments
on `command` are temporary. Declaration operands after `command export` and
`command readonly` receive scalar expansion, including through `-p` and `--`.
`-p` obtains the platform's standard utility search path through `confstr(_CS_PATH)`
and leaves the environment's PATH unchanged. External targets use the runtime
job manager for foreground ownership and waiting.

`command -v` reports reusable alias definitions, function/intrinsic/reserved
names, or absolute executable paths; absent names produce status 1. `-V` and
`type` describe the classification. Their prose is a project choice rather than
a reference-shell oracle. `hash name...` remembers executable paths, with
functions and builtins excluded; no operands prints remembered paths. `hash -r`
clears entries. PATH assignment/unset/restoration and `cd` invalidate the cache.
A missing or non-executable cached path triggers a fresh search.

`exec [--] [name arguments...]` replaces the current process, preserving its PID
and exporting command-prefix assignments into the replacement environment.
On failure, 127 means not found and 126 means found but not executable.
Non-interactive failure exits; interactive failure restores shell signal actions
and temporary descriptors. Prefix values persist with their original attributes.
Without a command, `exec` commits its own redirections and closes private
restoration backups. Redirections of enclosing groups/evaluations still unwind
at their enclosing boundary. Parser descriptors and the job manager's terminal
are relocated away from both enclosing and newly expanded descriptor operands.
Internal descriptors remain close-on-exec.

Executable text without an interpreter line uses the existing `/bin/sh` fallback.
The host supplies `printf`, `echo`, `test`, `[`, `true`, `false`, `pwd`, `kill`, and
other external standard utilities. Fixtures additionally use `sh`, `cat`, `chmod`,
`rm`, and `sleep`. Their complete utility semantics and platform availability
remain the host boundary under CSH-037; no full POSIX conformance is claimed.

## Stateful utilities

| Utility | Implemented behavior |
| --- | --- |
| `read [-r] [-d delim] var...` | Reads without input read-ahead; backslash protection and continuation; IFS whitespace/non-whitespace separators; final-variable remainder; empty fields; custom delimiter, including NUL for an empty delimiter; partial EOF assignment/status 1; operand, input and assignment errors/status 2. Interactive terminal continuations print PS2 or `> `. |
| `getopts optstring name [args...]` | Explicit or positional arguments; grouped options; attached/separate required arguments; OPTARG unset when absent; OPTIND initialized to 1; persistent group cursor and explicit OPTIND reset; leading-colon silent errors; unknown/missing options as successful `?`/`:` results; end status 1; usage/state/assignment errors status 2. Functions share its state. |
| `umask [-S] [mask]` | Octal masks, symbolic clauses with `+`, `-`, `=`, permission copying, numeric output and reusable `-S` output. Invalid operands leave the old mask intact. Process-local changes are inherited by children. |
| `times` | Two lines of accumulated shell and waited-child user/system CPU times, in minutes and seconds with six fractional digits in the POSIX locale. Output and operand failures return nonzero. |
| `ulimit [-H|-S] [-a] [-c|-d|-f|-n|-s|-v|-t] [limit]` | Soft/hard querying and mutation; default file-size resource; default soft query and both-limit mutation; `unlimited`; all-resource listing with resource descriptions and units; overflow/error validation; inherited process limits. File/core limits use 512-byte units, data/stack/address-space limits 1024-byte units, open files counts, and CPU time seconds. `-t` is an extension under the base-only profile. |

Unset PATH uses `/bin:/usr/bin`; unset IFS uses space, tab and newline. Empty IFS
suppresses field splitting. As elsewhere in the runtime, byte-oriented parsing
and C-locale output are the current profile. Traps and interactive signals use
the [selected base profile](traps-and-signals.md); full locale and profile
audits remain CSH-037 work. CSH-032 integrates
[shell option interactions](shell-options.md).

## Evidence

`make test-evaluation` runs the CSH-031 cases from
[`evaluation_cases.py`](../tests/evaluation_cases.py) and interactive invocations
in [`runtime_cases.py`](../tests/runtime_cases.py), through the bounded behavioral
runner. They assert stdout, stderr, status, file effects, and state restoration
across `-c`, file, and stdin modes. These cases are included in `make test`.
`make test-runtime-pty` includes evaluation error recovery, read continuation
prompts, and foreground interruption through `command`. `make test-control`
includes allocation sweeps over nested evaluation, temporary dot arguments,
read buffers, getopts state, and hash state, checking descriptor and allocation
baselines after every attempt. The ticket records native, Docker, and sanitizer
results.

Normative references: [special builtins and command search](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html),
[command](https://pubs.opengroup.org/onlinepubs/9799919799.2024edition/utilities/command.html),
[read](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/read.html),
[getopts](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/getopts.html),
[umask](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/umask.html),
and [ulimit](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ulimit.html).
The inventory retains Issue 8 features even where older reference shells differ
(`read -d`, intrinsic lookup, and base resource-limit options).

[CSH-048 clause evidence](state-builtin-evidence.md) maps exact runtime assertions, source conditions, policies and remaining utility gaps.
