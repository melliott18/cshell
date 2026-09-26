# Shell options

CSH-032 connects invocation and `set` to the same option inventory and shell
state. This is implemented Issue 8 option behavior within the current shell
subset, not a full POSIX conformance claim.

```sh
./cshell -eu -o pipefail script
./cshell -n script                 # parse without executing
set -euf                          # enable letters
set +e +o noglob                   # disable letters or names
set -o                            # readable report
saved=$(set +o)                    # commands that restore the settings
set -- -value two                  # replace positional parameters
```

Both entry points accept grouped letters, separate or attached `-o name` /
`+o name`, and `--`. Invalid options fail before changing options or positional
parameters. `set` with options alone preserves the parameters; operands replace
them, and `set --` clears them. No-argument `set` retains the existing quoted
variable listing. Invocation `-c`, `-s`, `-i`, `$0` and input operands retain
[their mapping](input-and-invocation.md). A missing invocation `-o`/`+o` name
is diagnosed with status 2 (the standard leaves those forms unspecified).
A lone runtime `set -` disables verbose/xtrace and preserves positionals unless
followed by operands; this is a documented choice for an unspecified form.

## Inventory and effects

| Letter / name | Effect and evidence family |
| --- | --- |
| `-a` / allexport | Every variable assignment through shell state acquires export, including parameter/arithmetic assignments, `read`, `getopts`, `cd`, and loop variables. Turning it off preserves existing export attributes. O-002. |
| `-b` / notify | Job notifications with monitoring; invocation choices survive job setup. O-003 and job fixtures. |
| `-C` / noclobber | `>` refuses existing regular files. New files use exclusive creation; existing nonregular targets are opened without truncation and checked with `fstat`. `>\|` overrides; `>>` and `<>` retain their normal behavior. Dangling symlinks are refused. O-004. |
| `-e` / errexit | Stop the owning execution environment for an untested failing command, with the exceptions below. O-005. |
| `-f` / noglob | Suppress pathname generation while preserving parameter expansion, splitting and case/parameter patterns. O-006. |
| `-h` / hashall | Accepted and reported; the optional optimization setting has no additional effect on the existing lookup/cache implementation. `hashall` is an extension name for standard `-h`. O-007. |
| `-m` / monitor | Interactive terminal job-control default. Explicit `+m` overrides the default; unavailable job control is diagnosed on enabling `-m`. O-008 and job fixtures. |
| `-n` / noexec | Continue reading/parsing without expansion, assignments, redirection, launches or command execution. Takes effect immediately, even inside a loop or on a line containing further commands. Honored in interactive shells too; `set +n` cannot execute to reverse it. O-009. |
| ignoreeof | Interactive terminal EOF prompts for explicit `exit`; disabling restores normal EOF exit. Has no effect on files, command strings or nonterminal stdin. O-010. |
| nolog | Accepted and reported, with no effect: command history is not implemented. This is a permitted obsolescent option choice. O-011. |
| `-u` / nounset | Unset scalar parameter and arithmetic references produce expansion errors. `$@`/`$*` and the specified default/alternate/assignment operators retain their exceptions. Noninteractive errors terminate the environment; interactive shells can accept the next input line. O-012. |
| pipefail | Select the rightmost nonzero stage status, or zero when all succeed. Capture the setting at pipeline creation, including retained background job results; apply `!` after selection. O-013. |
| `-v` / verbose | Write physical input bytes to stderr as read, including comments, continuations and here-documents. `eval` and dot input use the same observer; alias replacement bytes are not reread source. Unterminated lines have no added newline. O-014. |
| `-x` / xtrace | Write expanded simple-command assignments/arguments to the current stderr before dispatch. Quote empty/special values for clarity. PS4 defaults to `+ ` when unset and uses here-document-style parameter, arithmetic and command-substitution expansion, without splitting/globbing. Suppress recursive tracing of PS4; failed PS4 expansion falls back to `+ `. O-016. |

All settable options default off, including `-h`, except the interactive terminal
monitor default. `$-` contains enabled letter options in the implementation's
stable inventory order, with `i` appended for interactive execution. The
unspecified invocation `c`/`s` letters are omitted; named-only
options have no letter. `set +o` reports all settable options, excluding the
invocation-only interactive flag. O-001/O-018.

## Failure contexts and environment lifetime

`errexit` is ignored in `if`/`elif`/`while`/`until` conditions, nonfinal AND/OR
commands, and negated pipelines. These contexts include function bodies,
`eval`, dot scripts and substitutions reached from the tested command. The
visible `-e` setting is unchanged, and `set -e` inside a tested function does not
remove that exception.

A compound command's status inherited from an exempt failure remains exempt,
except for a subshell command. A function, `eval`, or dot invocation is itself
a simple command, so its returned nonzero status is tested afresh at the call
site. Each forked environment enforces its own failures. For example,
`set -e; (false; echo never) | cat; echo after` suppresses `never` but prints
`after` when `cat` succeeds and pipefail is off. An assignment-only command
inherits its last substitution status; an ordinary utility's status comes from
that utility. Expansion and fatal special-builtin errors retain their own
[error rules](candidate-runtime.md), including in tested commands.

Functions, braces, eval and dot scripts share option changes with their caller.
Subshells, pipeline stages, background commands and substitutions inherit copied
non-job option state and keep changes local. Command substitutions retain
`errexit`. The [job manager](job-control.md) retains its existing child policy
for interactive/monitor/notify flags. Tested-context depth is separate state
metadata copied with the environment and restored on return; it is not a
user-visible option. O-017.

Low-level prepared-command APIs still dispatch commands already materialized by
the caller; the AST executor owns noexec and contextual errexit. Prepared `>`
redirections capture noclobber as `CSH_REDIRECT_NOCLOBBER`. Both prepared and AST
pipeline APIs select pipefail while retaining each raw stage result.

## Profile and validation

The current profile remains base Issue 8 with selected interactive features.
UP/XSI are not selected as complete profiles. `vi` is rejected; history/editing,
mail notifications, and full LINENO/PS1/PS2/history-variable semantics remain
open under O-015/O-020/O-022–O-025 and CSH-037. PS4 trace expansion is the
implemented O-025 subset. No conditional requirement is counted as passed merely
because its profile is unselected. Linked history/editing/mail tickets remain a
prerequisite to selecting full UP, as recorded in the existing profile decision.

`make test-options` materializes `tests/option_cases.py` through the bounded
runtime runner. Fixture names map O-001–O-018 to explicit stdout, stderr,
status and filesystem expectations, across `-c`, script and stdin modes.
Coverage includes concurrent exclusive file creation, FIFO/symlink handling,
option restoration, eval/dot/alias interactions, background wait snapshots and
nested noexec/errexit cases. `make test-runtime-pty` covers ignoreeof, monitor
invocation overrides, interactive nounset recovery and noexec. Existing state,
pipeline and fault suites cover option-copy metadata, allocation and child/fd
ownership; the pipeline API checks signalled stages with pipefail. All are part
of native/Docker `make test` and `make test-pty`.

Expected behavior is based on Issue 8 [set](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_26_03),
[pipelines](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_02),
[redirection](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_02),
and [sh invocation](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_04).
Reference-shell checks are diagnostic comparisons, not fixture oracles.

CSH-051 supplies the [per-clause option evidence map](shell-option-evidence.md),
including invocation/set forms, enabled/disabled effects, execution environments,
formatting and default choices, and [native/Docker run records](evidence/csh-051/README.md).
