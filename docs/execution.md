# Command execution, pipelines, and redirections

[CSH-019](tickets/CSH-019-simple-command-redirections.md) supplies standalone
replacement execution and redirection modules;
[CSH-020](tickets/CSH-020-pipeline-lifecycle.md) adds concurrent pipelines. Their interfaces are
[`execute.h`](../include/cshell/execute.h) and
[`redirect.h`](../include/cshell/redirect.h). They use the replacement parser,
AST, and shell state without the legacy scanner or executor. The default
`cshell` executable still runs the prototype; CSH-018 integrates the replacement
runtime and CSH-039 switches the executable.

## Owned command boundary

`struct csh_command` contains final arguments, assignments, and ordered
redirections. Its pointers are owned by the command, counts describe initialized
entries, and a nonempty argument vector ends with a null pointer. Zero
initialization represents an empty command. `csh_command_destroy()` releases all
owned entries and resets the command. An empty command may still carry
redirections.

This is the handoff for CSH-008 expansion integration. Argument strings and file
paths are already prepared; `csh_execute_command()` does not expand them. The
assignment array contains final name/value pairs in source order. CSH-023 applies
these pairs according to the resolved execution category.

`csh_command_from_ast()` borrows an AST and creates an owned command. Its output
must be empty on entry and remains empty on failure. The temporary adapter
accepts a simple-command node or the parser's singleton foreground list around
one simple command. It removes literal quotes and escapes while preserving
quoted empty arguments; dollar-single-quoted words use the shared
[quote decoder](value-expansions.md). It rejects expansions, any
unquoted `*`, `?`, `[`, or `~` byte, pipelines, compound commands, and unsupported
lists
before executing any part of that construct. Quoting an otherwise special
character permits its literal value. Literal assignment prefixes, including quoted
empty values, pass through this adapter; general expansion remains CSH-008 work.

The adapter is deliberately separate from the existing value-expansion module.
Parsing a construct successfully does not mean this execution subset supports
it. CSH-008 replaces the adapter with expansion integration.
`csh_execute_pipeline_ast()` prepares every simple stage of one foreground
pipeline through this adapter, rejecting the entire construct if any stage is
unsupported. `csh_execute_ast()` accepts the same subset and discards stage details.

## Dispatch, ownership, and results

`csh_execute_command()` borrows the command and mutable shell state.
`csh_execute_ast()` performs simple-command or pipeline adaptation, dispatch,
and cleanup as one operation.
Both initialize `struct csh_execution` and update the state's last status. The
result records the execution category, numeric status, and an `exit_requested`
flag. The category distinguishes empty commands, external commands, regular
builtins, special builtins, and functions for assignment handling.

The API return value and shell status have different meanings:

| Return | Meaning |
| --- | --- |
| `0` | Dispatch completed, including a nonzero command status or a child redirection/exec failure. |
| `-1` | Preparation, parent redirection, fork, wait, or another internal operation failed; `error` contains a static diagnostic. |

The executor owns exactly the child it forks for an external command and waits
with `waitpid()` for that PID. A child that cannot execute reports its error
once and terminates; it never resumes the caller's input loop. A signal-terminated
child produces `128 + signal_number`. The library does not exit the parent;
the caller must honor `exit_requested` after descriptor restoration.
For errors returned to the caller, print the returned diagnostic once after the
API returns. Child failures already print in the child under its active
redirections; a child redirection failure has status 1.

External lookup uses the state's `PATH` variable and execution uses its exported
environment snapshot. The module does not modify process-global `environ`.
Names containing a slash are executed directly. Lookup distinguishes status 127
for a missing command from status 126 for an applicable execution failure.
Unset `PATH` uses `/bin:/usr/bin`; an empty component searches the current
directory. An existing script whose interpreter is missing produces status 126
as a project choice.

An `ENOEXEC` result invokes the host `/bin/sh` with the resolved script path and
remaining arguments. This is the executable-format fallback, so the contents of
such a script use the host shell's language. It does not route unsupported AST
constructs to the host shell. That fallback remains a host dependency until the
replacement runtime can interpret scripts itself.

[State builtins](state-builtins.md) run in the parent under reversible descriptors.
The existing `exit [status]` handler uses the previous status if omitted, or the
low eight bits of a decimal value representable by `long`. Invalid/excess
operands return status 2 without requesting exit. CSH-018 owns full exit/status
integration. `special_builtin_error` reports special-category failures for the
future runtime's context-dependent policy; it does not itself request exit.

## Assignment categories and resolved dispatch

CSH-023 implements the category boundary described by POSIX
[variable assignments](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_02).
The selected policies are:

| Category | Prefix lifetime and export attributes |
| --- | --- |
| No command name | Persist values, preserving existing attributes. |
| External command | Export prefixes to the child; restore the shell values and attributes. Prefix `PATH` controls this command's lookup. |
| Regular builtin | Export prefixes while the handler runs; restore only prefixed names afterward. |
| Special builtin | Persist prefixes and further handler changes; preserve existing export attributes. |
| Function | Export prefixes while the handler runs; restore only prefixed names afterward. This is the project's choice where POSIX leaves lifetime/export unspecified. |

When `CSH_OPT_ALLEXPORT` is set, this assignment boundary also marks persistent
prefix assignments exported. This does not implement all `set -a` effects in
other modules. Repeated names apply in order; the last value wins. Empty values
are distinct from missing values. Exported but unset declarations revert to
unset after temporary use. Unexported variables without a prefix remain absent
from the child environment.

`csh_execute_resolved()` is the CSH-009/CSH-010 consumer entry point. The resolver
passes the category, a handler, and an opaque context. Parent builtin/function
categories require a handler; empty/external categories require NULL. A standard
utility implemented as a function must use the regular-builtin category. The
handler returns 0 with `status` and `exit_requested`, or -1 with `error` populated.
It must return normally, retain no borrowed inputs, and leave `category` unchanged.
Function parameter frames, lookup precedence, and complete builtin semantics
remain with their owning tickets. `csh_execute_command()` uses this same entry
point for bootstrap `cd`, `exit`, and external commands.

All names and readonly attributes are checked before assignments, redirections,
or dispatch. A readonly prefix returns -1, status 1, and the static diagnostic
`cannot assign to readonly variable`. It requests exit when the state is
noninteractive; an interactive caller can continue. The caller prints the
returned diagnostic once and honors `exit_requested` even on -1. A subshell or
copied execution context must apply that request to its own context only.
Malformed prepared names or NULL values return status 2 without requesting exit.

Selective saves stage the original values and attributes before the first write.
Allocation failures during saving or applying a batch roll back every prefix.
Temporary saves are restored on handler success, handler failure, redirection
failure, and launch failure, without allocating. Even readonly attributes added
by a handler are undone for prefixed names. Unrelated variables, option changes,
and parameters survive; the final command status is stored after restoration.
Nested invocations restore scopes in reverse order. These operations are
serialized along with descriptor mutation.

Persistent batches commit before redirections (an allowed ordering for empty
and special-builtin commands), so a later redirection or handler failure does
not undo them. External launch preparation copies the prefixed `PATH` and
exported environment, then restores shell variables before forking. No path
changes the host process environment. Command values must be independently
owned as required by `struct csh_command`, not borrowed from mutable shell state.

## Pipeline lifecycle and stage results

`csh_execute_pipeline()` borrows an array of prepared commands, a nonzero count,
a negation flag, and shell state. `csh_execute_pipeline_ast()` accepts a simple
command or one foreground pipeline (including `!`) and prepares all stages
before dispatch. Neither API accepts compound stages, background execution, or
AND/OR/sequential lists; CSH-021 owns those contexts. Both APIs initialize an
empty `csh_pipeline_result`; the caller must call
`csh_pipeline_result_destroy()` after success **or failure**, before reusing it.
The destructor is safe on a zeroed or already destroyed result.

A multi-stage pipeline runs every stage in its own child. External commands exec
directly in that child; state builtins use the same handlers as ordinary
commands. Prefix assignments are applied within the stage, including the
exported environment and `PATH` used to prepare an external stage, without
changing the caller's variables. Consequently `cd directory | command` and
`command | cd directory` leave the caller's directory unchanged, and a pipeline
`exit` cannot request that the caller exit. A single stage uses the ordinary
execution environment: `! cd directory` changes the caller's directory. A
singleton `exit` preserves its requested exit status and exit request, including
under `!`.

The parent keeps only the preceding read end and the next pipe while launching.
Pipe descriptors are CLOEXEC and relocated above standard descriptors, so
initially closed stdin/stdout/stderr remain closed in the parent. Each child
connects stdin/stdout, closes all private pipe ends, and then applies its ordered
redirections. Explicit redirection therefore overrides a pipe connection, and
private pipe descriptors cannot accidentally satisfy user duplication operands.
The parent closes each unused end immediately, launches all stages before its
first wait, and waits for every owned child using its positive PID with EINTR
retry. Pipeline length does not require keeping every pipe open at once.

`result.execution` holds the summary. On success its status is the last stage's
status, logically inverted to 0/1 for `!`; an earlier failure does not implement
`pipefail`. A signal status is `128 + signal_number`. Multi-stage results have
category `CSH_EXEC_PIPELINE` and no parent exit request. The state's last status
is updated to the summary after completion.

`result.stages` contains one entry per command in source order, including stages
that were not launched if setup failed:

| Field | Meaning |
| --- | --- |
| `pid` | Owned direct child identity, or zero for an unlaunched stage or singleton parent builtin. |
| `category` | Empty, external, regular builtin, or special builtin command. |
| `completed`, `status` | `status` is valid when `completed` is set; it is never negated. |
| `reaped`, `wait_status` | Raw `waitpid` result is valid when `reaped` is set; inspect with `WIFEXITED`/`WIFSIGNALED` and related macros. |

All valid PIDs are historical after return: callers must not signal or wait for
them again. CSH-010 can derive `pipefail` from the ordered, unnegated statuses.
CSH-011 must extend the launch/wait boundary for process groups, terminal control,
and suspended jobs; this synchronous API does not transfer live children or
pretend that stopped children have completed. Callers must serialize descriptor
mutation, refrain from reaping executor children elsewhere, and leave SIGCHLD
waitable (no ignored SIGCHLD or `SA_NOCLDWAIT`).

Preparation errors return `-1` before launch. Pipe, descriptor-setup, fork, or
wait errors in the parent return `-1` with the original diagnostic and status 1,
without applying negation. After partial launch the parent closes its remaining
pipes, sends SIGKILL to all unreaped owned children, and reaps them before
returning. This handles even a stage that sleeps or ignores termination signals;
it does not roll back files or other effects already performed by a child.
Descendants created by external programs are outside this direct-child boundary;
job/process-group lifecycle belongs to CSH-011.

Child connection/redirection failures instead print once in the child and
produce stage status 1; lookup/exec failures keep statuses 126/127. Other stages
finish normally, with EOF/SIGPIPE from the closed ends, and their statuses remain
available. No child can return into the caller's input loop.

These choices follow the POSIX.1-2024
[pipeline](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_02)
and [execution-environment](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_12)
boundaries within the supported subset; process groups, options, and signal/trap
policy remain separate work.

## Ordered redirection boundary

Each `struct csh_redirect` has a destination descriptor and one operation. File
operations own a path, duplication operations specify a source descriptor, and
here-documents own already prepared bytes plus their exact length. Prepared
here-document data may contain NUL bytes. The redirection module does not parse
or expand these operands.

| Kind | Operation |
| --- | --- |
| `CSH_REDIRECT_READ` | Open a file for reading. |
| `CSH_REDIRECT_WRITE`, `CSH_REDIRECT_CLOBBER` | Create or truncate a file for output. |
| `CSH_REDIRECT_APPEND` | Create or open a file for appended output. |
| `CSH_REDIRECT_READ_WRITE` | Create or open a file for reading and writing. |
| `CSH_REDIRECT_DUP_READ`, `CSH_REDIRECT_DUP_WRITE` | Duplicate a descriptor open in the requested direction. |
| `CSH_REDIRECT_CLOSE` | Close the destination, including an already closed descriptor. |
| `CSH_REDIRECT_HEREDOC` | Provide the prepared bytes as input. |

`csh_redirect_validate()` checks prepared input without descriptor or filesystem
side effects. `csh_redirect_apply()` borrows the array, saves each target's
original open or closed state and descriptor flags, then applies operations in
array order. Saved private descriptors cannot alias any redirection operand.
Thus `2>&1 >file` leaves stderr attached to the original stdout, while
`>file 2>&1` sends both streams to the file.

On success, the caller must call `csh_redirect_restore()` even if the command
fails. Restore consumes and clears the saved state. On apply failure, the module
restores acquired descriptor state and clears the save pointer itself. Both the
save and error output pointers are required. Redirection helpers return errors
without printing diagnostics. Do not overwrite an outstanding save token by
calling apply again with that pointer. Descriptor mutation must be serialized,
including across signal handlers. Restore attempts every saved target, returning
the first failure if restoration cannot be completed.

Restoration concerns descriptors, not filesystem transactions: a file already
created or truncated stays changed, and offsets shared with other descriptors
cannot be rewound automatically. Parent builtin execution uses this restoration
boundary on both success and failure.

## Scope and validation

The supported subset has no general expansion, compound command, job-control,
pipefail/noclobber option behavior, or full builtin
semantics.
Both `>` and `>|` currently create or truncate output files. The AST front end
collects here-documents; CSH-008 owns their general expansion. Direct API clients
can supply prepared byte data independently of the literal adapter's limits.
The adapter accepts quoted-delimiter bodies literally and rejects any unquoted
body containing `$`, a backquote, or a backslash. Bodies without those bytes pass
through unchanged. Large bodies use temporary-file input rather than requiring
a pipe reader to run while the parent writes them.

Run `make test-execute test-pipeline` for the replacement execution fixtures, independently of
the prototype. See [Testing](testing.md#execution-api-and-sanitizer-checks) for
focused sanitizer and Docker commands. The fixtures establish this module
contract; they do not establish that the default executable implements it or
that the project is POSIX-compliant.
