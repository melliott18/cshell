# State builtins

[CSH-029](tickets/CSH-029-state-builtins.md) adds replacement module handlers in
[`builtin.c`](../src/builtin.c), with the public contract in
[`builtin.h`](../include/cshell/builtin.h). They are available through the
public `cshell` executable and the standalone executor fixtures.

`:` ignores arguments and succeeds. `export` and `readonly` accept names and
name=value operands, with atomic value/attribute updates per operand; an error
leaves that operand unchanged and processing continues. `-p` and no operands
produce reusable single-quoted declarations, including attribute-only unset
names. `unset` removes variable values and attributes; `-v` selects variables.
Readonly values cannot be assigned or unset. CSH-028 adds function removal with `unset -f`; an absent name succeeds. Plain
`unset` and `unset -v` select only the variable namespace.

`set` without operands prints set variables in `strcoll` order in the process's
active locale. `set --` clears positionals; `set -- args` or `set args` replaces
them without changing `$0`. Option syntax is rejected pending CSH-032. `shift`
defaults to one, accepts zero, and rejects negative, overflowing, nondecimal or
excess counts without changing positionals. These builtin failures return status
1 and print a diagnostic. Startup locale selection belongs to runtime integration.

`cd` accepts grouped `-L`, `-P`, `-e` and `--`; the last L/P option wins, with L
the default. HOME omission uses a nonempty HOME; unset/empty HOME is an error
(the implementation-defined choice). `cd -` uses OLDPWD and prints the new path.
CDPATH searches apply to relative operands other than dot/dot-dot prefixes;
a nonempty selected component causes output. Logical paths eliminate dot and
dot-dot before changing directory, checking components before removing them.
Physical paths follow filesystem links before obtaining the resulting cwd.
An empty explicit directory is an error.

PWD is trusted only when absolute, free of dot/dot-dot components, and naming
the current directory by device/inode. Otherwise the module obtains the physical
cwd. `pwd -L` uses that validated logical value; `pwd -P` always obtains physical
cwd. `cd` stores the previous logical directory in OLDPWD and the new directory
in PWD, preserving their existing attributes. New entries are unexported. State
update failures roll back both cwd and variable state; a failure to restore cwd
is diagnosed. For `cd -P` without `-e`, failure to obtain the new cwd may succeed
with PWD unset, unless output is required. With `-e`, failure is reported and cwd
is restored. Output errors after a successful change return failure without
undoing the change. No fixed PATH_MAX buffer is imposed.

All handlers run under the executor's temporary redirections and in the caller's
state/cwd. They never exit. The executor identifies special builtins before
applying prepared assignments. Assignments persist on success and subsequent
redirection/builtin failure; earlier assignments persist if a later one fails.
`special_builtin_error` reports a failure under special classification, separate
from the existing explicit `exit_requested` field. The runtime must interpret
this together with the command and execution context; it is not an unconditional
request to exit (for example, shift errors may continue). [CSH-031](evaluation-builtins.md) supplies final
interactive/noninteractive policy and `command` suppression. CSH-023 still owns
assignment syntax, regular-command temporary environments and declaration-word
expansion; CSH-032 owns option effects. CSH-026 connects assignment syntax and expansion to the runtime dispatcher.

`make test-builtins` runs table-driven state/status checks and 24 behavioral
cases through the replacement executor. It includes quoting/listing, logical
and physical directories, CDPATH, readonly directory rollback, invalid operands,
redirection restoration, special categories and prepared assignment persistence.
`make test-execute` retains the existing exit and descriptor/failure coverage.
