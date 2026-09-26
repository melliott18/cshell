# Shell state API

[CSH-022](tickets/CSH-022-shell-state-storage.md) provides owned variable and
parameter storage in [`src/state.c`](../src/state.c), with the interface in
[`cshell/state.h`](../include/cshell/state.h). The public runtime and assignment/builtin dispatch use this state.
The separate parameter-expansion API also consumes it; expansion integration
remains CSH-008 work.

## Construction and ownership

`csh_state_create()` copies the invocation's `$0`, positional arguments,
source mode, and interactive flag, and imports a caller-supplied environment
vector. It captures the shell process ID once, starts the last status at zero,
and records no background process. It neither retains nor consumes the
invocation's input source. The caller can release or change the invocation and
environment strings after construction.

The state is opaque and owns its retained strings. Release it with
`csh_state_destroy()`, which also accepts NULL. Constructors, clones, and
saves require output pointers that do not already own an object and set those
outputs to NULL on failure. Environment snapshots have their own destruction
function. State objects are not thread-safe; callers must serialize access and
pass valid live objects.

`csh_state_get_variable()` and `csh_state_parameter()` return borrowed
strings. Their lifetime ends at the next successful mutation, restoration, or
destruction of that state. Copy a string if it must survive that boundary.
Parameter replacement accepts elements that alias the state's current variable
or parameter strings; it copies them before releasing the old parameter
vector.

## Variables and environment import

Names use `[A-Za-z_][A-Za-z0-9_]*`, independently of the locale. Values are
NUL-terminated byte strings; embedded NUL bytes cannot be represented. Lookups
distinguish unset values from empty values:

| Stored state | Lookup value | Attributes |
| --- | --- | --- |
| Missing name | NULL | Zero |
| Declared but unset | NULL | Retained attributes, if any |
| Set to an empty value | `""` | Preserved independently of the value |
| Set to a nonempty value | Borrowed value string | Preserved independently of the value |

`csh_state_set_variable()` assigns a non-NULL value. A new variable starts
unexported; replacement preserves existing attributes.
`csh_state_unset_variable()` removes both value and attributes, and succeeds
without a change for a missing name. Neither operation can modify a readonly
variable, including an assignment of its existing value.

`csh_state_update_attributes()` sets and clears attribute masks. The masks
must be disjoint and contain only `CSH_VAR_EXPORT` and `CSH_VAR_READONLY`.
Marking a missing name exported or readonly declares an unset variable without
assigning an empty value. Readonly cannot subsequently be cleared. The export
attribute can still change on a readonly variable.

Environment import accepts NULL as an empty environment. Entries must contain
`=` and a valid shell name before the first `=`; malformed entries and invalid
names are ignored. The remainder is the value, including an empty string or
additional `=` bytes. Imported variables are marked exported. If a valid name
occurs more than once, the last entry wins. This is a deterministic storage
policy for input whose duplicate-name consequences are undefined by the [POSIX
environment
definition](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html).
Valid-name import and export marking follow [POSIX shell
variables](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03).

No state operation reads or changes `environ`, calls `getenv()` or `setenv()`,
or synchronizes the host process environment. Special startup initialization
of `IFS`, `PPID`, and `PWD` remains
[CSH-029](tickets/CSH-029-state-builtins.md) work. In particular, raw import
does not perform the required invocation-time reset of `IFS` to space, tab,
and newline. Future runtime initialization must apply those rules separately.

## Child environment snapshots

`csh_state_environment()` allocates a NULL-terminated `name=value` vector for
exported variables whose values are set. Exported empty values appear as
`name=`; exported but unset declarations are omitted. Snapshot ordering is
unspecified. Even an empty snapshot is a valid vector with a terminating NULL.

The snapshot owns its vector and every string. It remains valid after any
mutation or destruction of the source state. Release it with
`csh_state_environment_destroy()`; the function also accepts NULL. The
snapshot is suitable for an executor's explicit environment argument, but this
API does not launch a process or apply command-prefix assignment rules.

## Parameters and metadata

`csh_state_parameter(state, 0)` returns `$0`. Indices one through the argument
count return positional parameters; an out-of-range index returns NULL. Empty
arguments remain empty strings. `csh_state_set_parameters()` copies a counted
array, without requiring a final NULL. A zero count clears the positionals and
allows a NULL array. Replacing positional parameters never changes `$0`.

`csh_state_get_info()` copies the following metadata into a caller-owned
record:

| Field | Consumer meaning |
| --- | --- |
| `argument_count` | `$#`, excluding `$0` |
| `last_status` | `$?`, initially zero |
| `shell_pid` | `$$`, captured at construction and preserved by clones |
| `background_pid` | `$!`; zero means no background command has been recorded |
| `mode` | Original stdin, string, or file invocation selection |
| `options` | Shared shell option bits initialized from invocation choices |

`csh_state_set_status()` stores any nonnegative `int`, including values
greater than 255. It does not convert a `waitpid()` status or choose shell
error behavior. `csh_state_set_background()` records a nonnegative background
process ID; zero clears the recorded ID. The executor and job modules own
producers of these values; the expansion engine owns their textual parameter
expansions. Preserving the original shell PID through a copy supports the
[POSIX special-parameter
rules](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_02).

`csh_state_update_options()` changes disjoint set/clear masks of the declared
`CSH_OPT_*` flags in the shared `options.h` inventory. Assignments through state
automatically acquire export when allexport is enabled. The executor, expansion
and input modules implement other [option effects](shell-options.md).
`errexit_ignored` records nested tested-command contexts independently of the
visible option bits; copies/checkpoints preserve it. The expansion layer owns
the `$-` representation using the same inventory.

## Copying, checkpoints, and restoration

`csh_state_clone()` makes an independently mutable deep copy of every
variable, attribute, parameter, and metadata field. `csh_state_save()` makes
an independent full-state checkpoint. Later source mutations cannot change
either copy.

`csh_state_restore()` replaces the entire destination state with the
checkpoint contents without allocating. A successful restore consumes the
checkpoint and sets the caller's checkpoint pointer to NULL. This internal
rollback can undo new readonly attributes; it is not a shell assignment.
Unused checkpoints can be released with `csh_state_checkpoint_destroy()`. A
checkpoint is restored or discarded exactly once, and callers control the
order of nested restoration.

Checkpoints cover only this module's data. They do not capture working
directories, file descriptors, traps, or job resources. Function name tables
are copied; immutable definition payloads are retained by reference. A
full-state rollback also restores status and positional parameters and
discards every intervening variable change. It must not be used as a
substitute for selective temporary-assignment restoration around a builtin
that can change unrelated state.
[CSH-023](tickets/CSH-023-assignment-environments.md) supplies category-aware
assignment lifetimes through a separate selective save:

- `csh_state_save_variables()` copies a counted list of variable names, including
  missing names and unset declarations. Duplicate names are saved once. A zero
  count produces a NULL save. Invalid names or allocation failure leave state
  unchanged and the output NULL.
- `csh_state_restore_variables()` consumes the save without allocating, replacing
  only the saved names and their attributes. It bypasses readonly for rollback,
  preserves unrelated variables and all metadata, and accepts a NULL save.
- `csh_state_variable_save_destroy()` discards an unused save (NULL is accepted).
  Saves own their contents independently of the source state. Restore nested
  scopes on the same state in reverse order. Borrowed views expire on restore.

CSH-028 adds `csh_state_push_parameters()` and `csh_state_pop_parameters()`: new
arguments are copied before moving aside the caller vector, and restoration
requires no allocation. `$0` and unrelated state remain intact. The function
registry retains executor-owned immutable payloads with a final-release callback,
so state does not depend on parser or executor implementation. Lookup borrows a
payload; setting retains it, and setting NULL removes its name. See
[Control flow and functions](control-flow.md) for invocation and ownership.

## Failure and validation

Operations return `CSH_STATE_OK`, `CSH_STATE_INVALID`, `CSH_STATE_NOMEM`, or
`CSH_STATE_READONLY`. They do not print diagnostics, exit the process, or set
the stored shell status on error. Failed mutations leave the state unchanged.
The caller translates a result into the execution context's diagnostic and
status.

Run `make test-state` for focused C fixtures, including controlled allocation
failures, without building the executor or scanner. See
[Testing](testing.md#shell-state-api-and-sanitizer-checks) for sanitizer and
Docker commands and the [ticket](tickets/CSH-022-shell-state-storage.md) for
the validation record. These tests establish storage and ownership behavior;
end-to-end expansion, assignments, startup variables, and builtin behavior
remain separate evidence.

## Active runtime locale

The public runtime calls `csh_state_manage_locale` after environment import.
Locale assignments/unset and variable/full-state rollback then refresh libc
from shell values, with LC_ALL/category/LANG precedence. Cloning preserves the
opt-in flag without changing libc while copying; module states remain inert
unless explicitly activated. This is one active shell state per process, not
thread-local locale management. Libc may allocate internally during refresh.
See [locale behavior](locales.md) for invalid-name policy and lexical boundaries.
