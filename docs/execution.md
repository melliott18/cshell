# Simple-command execution and redirections

[CSH-019](tickets/CSH-019-simple-command-redirections.md) supplies standalone
replacement execution and redirection modules. Their interfaces are
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
assignment array reserves the CSH-023 assignment-lifetime boundary. A nonempty
assignment array currently fails before redirection or dispatch.

`csh_command_from_ast()` borrows an AST and creates an owned command. Its output
must be empty on entry and remains empty on failure. The temporary adapter
accepts a simple-command node or the parser's singleton foreground list around
one simple command. It removes literal quotes and escapes while preserving
quoted empty arguments; dollar-single-quoted words use the shared
[quote decoder](value-expansions.md). It rejects assignments, expansions, any
unquoted `*`, `?`, `[`, or `~` byte, pipelines, compound commands, and unsupported
lists
before executing any part of that construct. Quoting an otherwise special
character permits its literal value.

The adapter is deliberately separate from the existing value-expansion module.
Parsing a construct successfully does not mean this execution subset supports
it. CSH-008 replaces the adapter with expansion integration; CSH-020 adds
pipeline execution.

## Dispatch, ownership, and results

`csh_execute_command()` borrows the command and mutable shell state.
`csh_execute_ast()` performs adaptation, dispatch, and cleanup as one operation.
Both initialize `struct csh_execution` and update the state's last status. The
result records the execution category, numeric status, and an `exit_requested`
flag. The category distinguishes empty commands, external commands, regular
builtins, and special builtins for later assignment rules.

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

Bootstrap `cd` runs in the parent and changes its working directory once, without
falling through to external execution. Bootstrap `exit` requests that the caller
leave its input loop. Their present operand rules are:

- `cd [--] [directory]` uses the supplied directory, or a nonempty `HOME` when
  omitted. It calls `chdir()` directly. Options, `cd -`, `CDPATH`, logical-path
  processing, and `PWD`/`OLDPWD` updates are pending.
- `exit [--] [status]` uses the previous status if omitted, or the low eight bits
  of a decimal value representable by `long` (optional sign, no whitespace).
  Invalid or excess operands set status 2 and request exit only when the
  state's interactive option is clear. A failed special-builtin redirection
  likewise requests exit only for a non-interactive shell.

These are the initial handlers needed for runtime cutover;
CSH-018 supplies [candidate exit/status integration](candidate-runtime.md), and
CSH-029 owns full state-builtin semantics.

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

The supported subset has no assignment lifetime, general expansion, compound
command, pipeline, job-control, noclobber option behavior, or full builtin
semantics.
Both `>` and `>|` currently create or truncate output files. The AST front end
collects here-documents; CSH-008 owns their general expansion. Direct API clients
can supply prepared byte data independently of the literal adapter's limits.
The adapter accepts quoted-delimiter bodies literally and rejects any unquoted
body containing `$`, a backquote, or a backslash. Bodies without those bytes pass
through unchanged. Large bodies use temporary-file input rather than requiring
a pipe reader to run while the parent writes them.

Run `make test-execute` for the replacement execution fixtures, independently of
the prototype. See [Testing](testing.md#execution-api-and-sanitizer-checks) for
focused sanitizer and Docker commands. The fixtures establish this module
contract; they do not establish that the default executable implements it or
that the project is POSIX-compliant.
