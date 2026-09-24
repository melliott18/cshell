# Command execution, contexts, pipelines, and redirections

[CSH-019](tickets/CSH-019-simple-command-redirections.md) supplies standalone
replacement execution and redirection modules;
[CSH-020](tickets/CSH-020-pipeline-lifecycle.md) adds concurrent pipelines, and
[CSH-021](tickets/CSH-021-lists-and-execution-contexts.md) adds execution contexts. Their interfaces are
[`execute.h`](../include/cshell/execute.h) and
[`redirect.h`](../include/cshell/redirect.h). They use the replacement parser,
AST, and shell state. The public `cshell` executable uses these modules through
the runtime integrated by CSH-018 and promoted by CSH-039.

## Owned command boundary

`struct csh_command` contains final arguments, assignments, and ordered
redirections. Its pointers are owned by the command, counts describe initialized
entries, and a nonempty argument vector ends with a null pointer. Zero
initialization represents an empty command. `csh_command_destroy()` releases all
owned entries and resets the command. An empty command may still carry
redirections.

Argument strings, assignment values and file paths are already prepared;
`csh_execute_command()` does not expand them. CSH-023 applies the final assignment
pairs according to the resolved execution category. `substitution_status` holds
the last substitution status (zero when none ran), used by empty commands.

`csh_command_from_ast(state, tree, out, error)` materializes a simple command or
singleton foreground list. It performs value and field expansion, can execute
selected substitutions, and leaves output empty on failure. It does not apply
redirections while preparing values. Library callers choosing this helper own
that preparation boundary and any completed expansion effects.

Runtime AST execution uses the phased preparation in `src/prepare.c`: arguments,
then expansion/application of each redirection, then prefix values and dispatch.
Consequently assignment substitutions see the command's redirected descriptors.
Every reached word uses current state. Skipped list branches and parameter
operands remain unevaluated. Argument fields retain quote provenance through IFS
splitting and pathname expansion. Assignment, redirection, pattern, and
here-document contexts have separate policies; see [Value expansion](value-expansions.md).

`csh_execute_pipeline_ast()` and `csh_execute_ast()` accept a foreground simple
command or pipeline, including group stages. They preflight supported syntax,
then expand stages in their actual execution environments after pipe connection.
The latter API discards stage details.

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
| `-1` | Preparation, parent redirection, fork, wait, or another internal operation failed; `error` contains a diagnostic selected by `csh_error_message()`. |

The executor owns exactly the child it forks for an external command and waits
with `waitpid()` for that PID. A child that cannot execute reports its error
once and terminates; it never resumes the caller's input loop. A signal-terminated
child produces `128 + signal_number`. The library does not exit the parent;
the caller must honor `exit_requested` after descriptor restoration.
For errors returned to the caller, print `csh_error_message(error)` once after
the API returns unless `error.reported` is set. Child failures already print in the child under its active
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

The [runtime](candidate-runtime.md) consumes this error classification:
special-builtin errors end non-interactive input processing but allow an
interactive shell to continue. Invalid `exit` operands follow the same
context rule directly through `exit_requested`.

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

Prepared-command dispatch commits persistent batches before its redirections
(an allowed ordering for empty and special-builtin commands). Runtime AST
execution expands/applies redirections before prefix values; later prefix values
see earlier ones through a temporary selective save, before dispatch commits
the category-specific batch. Unrelated expansion side effects persist. External launch preparation copies the prefixed `PATH` and
exported environment, then restores shell variables before forking. No path
changes the host process environment. Command values must be independently
owned as required by `struct csh_command`, not borrowed from mutable shell state.

## Pipeline lifecycle and stage results

`csh_execute_pipeline()` borrows an array of prepared commands, a nonzero count,
a negation flag, and shell state. `csh_execute_pipeline_ast()` accepts a simple
command or one foreground pipeline (including `!` and group stages), expanding
each stage in its child. The prepared API accepts only final simple commands.
Use `csh_execute_context_ast()` for background execution and AND/OR/sequential lists. Both APIs initialize an
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
| `category` | Resolved category for prepared commands and singleton simple ASTs; `CSH_EXEC_UNRESOLVED` for AST multi-stage pipelines, whose command names resolve in children. |
| `completed`, `status` | `status` is valid when `completed` is set; it is never negated. |
| `reaped`, `wait_status` | Raw `waitpid` result is valid when `reaped` is set; inspect with `WIFEXITED`/`WIFSIGNALED` and related macros. |

All valid PIDs are historical after return: callers must not signal or wait for
them again. CSH-010 can derive `pipefail` from the ordered, unnegated statuses.
CSH-034 adds process groups and suspended jobs through an optional runtime
context manager (see [Job control](job-control.md)); this synchronous API does
not transfer live children or pretend that stopped children have completed. Callers must serialize descriptor
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

## Lists, groups, and background contexts

`csh_execute_context_ast()` borrows a parser tree and a persistent
`csh_execution_context`. Initialize the context with `{0}`, then assign its
`state` pointer to the shell's live state. The context owns background child
records; state stores variables, options, parameters, last status and the last
background identifier. Do not copy a context or reap its children elsewhere.
The older `csh_execute_ast()` and `csh_execute_pipeline_ast()` remain synchronous
foreground simple-command/pipeline convenience APIs.

Preparation builds a structural execution plan borrowing the AST. Unsupported
compound syntax anywhere in that tree is rejected before effects, even in a
branch that would be skipped. Words and here-document bodies expand only when
execution reaches their command, and lazy substitution bodies are preflighted
when selected. A maximum nesting depth of 256 bounds
recursive preparation/execution. Preparation does not resolve future commands
against current state: earlier `cd`, assignment, and export operations can still
change later command lookup and environments. The plan is freed after dispatch;
background children inherit their own copy through `fork()`.

| Construct | State, descriptors, children and status |
| --- | --- |
| Sequential list | Executes in order in the current context; final command status wins. |
| AND/OR list | Uses the parser's left-associative, equal-precedence tree; runs the right side only when selected by the left status. |
| Brace group | Shares current state and cwd; applies ordered group redirections for the body and restores them on every return. |
| Parenthesized group | Forks and waits for its owned context PID; copied state, cwd and descriptors cannot mutate the parent. Exit requests terminate only that child. |
| Multi-stage pipeline | Launches all stages before waiting; each stage has isolated state. Group stages use the same recursive evaluator. Last-stage status and `!` match ordinary pipelines. |
| Asynchronous item | Returns status 0 once registered, without waiting for completion. A background pipeline registers every stage and publishes the final stage PID. Other lists/groups publish their context PID; a simple external command execs directly in that process. |

A singleton negated group keeps ordinary group semantics: `! { cd directory; }`
changes the current directory, while `! (cd directory)` does not. Explicit
`exit` preserves its requested status under negation. Current-context exit and
noninteractive special-builtin errors stop enclosing lists; copied contexts do
not propagate exit requests back to the parent. Ordinary redirection failures
are diagnosed once and become command statuses, so `group || recovery` can run.
Other internal errors return -1. Group backup descriptors exclude all
redirection operands throughout the prepared tree, so private saved descriptors
cannot make an otherwise closed nested duplication operand valid.

Without job control, asynchronous execution ignores SIGINT/SIGQUIT and initially
connects stdin to `/dev/null` (only the first stage for a pipeline). Explicit
redirections override this input. The parent retains its own descriptors and
signal dispositions. Contexts without a job manager provide no terminal transfer
or jobs/wait builtins; the runtime attaches the CSH-034 manager described below.

`csh_execution_context_reap(context, wait, error)` polls with `wait=0` or waits
for all registered children with `wait=1`. Both use positive owned PIDs, retry
EINTR, preserve last status and the last background identifier, and leave
unreaped records owned on error for retry. Execution polls at command boundaries;
contexts without a manager install no SIGCHLD handler, and idle library hosts
must call their reaper themselves. The CSH-034 runtime manager also reaps during
idle input, retains completed statuses for `wait`, and returns from blocking
reaping when a monitored job stops.

Destroying a context polls once and releases its registry, detaching any still
running children. This lets shell exit avoid waiting for background jobs; a
long-lived library host that requires complete reaping must call the blocking
reaper before destruction. Forked contexts start with empty ownership registries
and do not wait for the original parent's children. Nested asynchronous children
are owned by the context that launched them until that context exits.

Pipe/fork/wait failures during partial pipeline launch close private descriptors,
kill and reap direct children, and free pending records. This direct-child
boundary is extended to process-group cancellation when the context has an
attached CSH-034 manager and monitor mode is enabled. Failed group
redirections restore parent descriptors and do not execute the body; files
already opened/truncated remain filesystem effects.

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

Conditional/loop/function execution, job control, pipefail/noclobber option
behavior, and full builtin semantics remain incomplete. Both `>` and `>|`
currently create or truncate output files. The AST front end collects
here-documents; CSH-026 expands unquoted bodies when reached and preserves
quoted-delimiter bodies literally. Direct API clients can supply prepared byte
data. Large bodies use temporary-file input rather than requiring a pipe reader
to run while the parent writes them.

Run `make test-execute test-pipeline test-context` for the replacement execution
fixtures and public-runtime context behavior. See
[Testing](testing.md#execution-api-and-sanitizer-checks) for focused sanitizer
and Docker commands. These fixtures establish this module contract and its
runtime integration; they do not establish that the project is POSIX-compliant.

### Runtime job manager

CSH-034 attaches an owned `csh_jobs` manager to the persistent runtime context.
The context launcher transfers direct PIDs to that manager; its registry replaces
the context's older `children` list for those launches. Prepared-command API
callers and contexts without a manager retain their synchronous/nonterminal
contracts. `csh_execution_context_destroy` destroys an attached manager and
restores its saved signal dispositions. See [Job control](job-control.md) for
terminal handoff, status retention, builtin dispatch, and the input wait hook.

### Private descriptors during expansion

Descriptor saves are registered for their lifetime under the existing serialized
mutation contract. Before applying a new redirection, any enclosing backup that
collides with a newly expanded operand is relocated, leaving the original
private descriptor closed. This preserves errors for `1>&$fd` when `$fd` names a
closed user descriptor. After fork, a fresh shell context closes inherited
backups; the parent retains its own restoration tokens. Saves restore in reverse
order on execution, expansion, assignment and redirection failure.
