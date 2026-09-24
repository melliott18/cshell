# Input and invocation APIs

[CSH-016](tickets/CSH-016-input-and-invocation.md) provides replacement modules
in [`src/input.c`](../src/input.c) and
[`src/invocation.c`](../src/invocation.c). The public `cshell` entry point uses these APIs through the
[runtime](candidate-runtime.md), integrated by CSH-018 and promoted by CSH-039. The APIs acquire input and describe invocation; they
do not execute commands, expand parameters, print diagnostics, or exit.

## Invocation contract

[`cshell/invocation.h`](../include/cshell/invocation.h) exposes
`csh_invocation_parse()`. Pass `argc`, `argv`, the input descriptor, the error
descriptor used for terminal detection, a destination invocation, and an error
object. The destination must not already own an invocation. `argc` must be at
least one and every entry through `argv[argc - 1]` must be non-NULL. The parser
returns zero on success or -1 on failure; failure clears the destination and
releases any partially acquired resources. The error object is required.

The supported invocation subset follows the operand mapping in the Issue 8
[`sh` specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html).
Here `shell` represents the original `argv[0]`; brackets indicate optional
operands.

| Invocation arguments | Source | `arg0` (`$0`) | Positional arguments |
| --- | --- | --- | --- |
| `shell` | Stdin | `shell` | Empty |
| `shell -s [args...]` | Stdin | `shell` | All `args` |
| `shell file [args...]` | Script file | `file` | All `args` |
| `shell -c text` | Copied command string | `shell` | Empty |
| `shell -c text name [args...]` | Copied command string | `name` | All `args` |

`-i` forces interactive mode with any source. Options can be grouped, such as
`-ic text`, or supplied separately, such as `-c -i text`. `-c` selects a mode;
its command string is the first operand after option parsing. An empty command
string is valid and produces EOF. A missing command string is a usage error.

`--` ends option parsing. A lone `-` also ends option parsing and is ignored.
After the first operand, subsequent strings are operands even if they resemble
options. Use `--` before a first operand beginning with `-` or `+`. POSIX leaves
combinations of the lone `-` and `--`, and a lone `-` after other operands,
undefined; callers should avoid those forms.

Combining `-c` and `-s` is diagnosed as invalid usage. Other shell switches,
including options beginning with `+`, are diagnosed as unsupported; CSH-032
owns general shell options. Script operands are opened directly from the given
path, including relative paths. There is no optional `PATH` search.

## Ownership

A successful `struct csh_invocation` owns its input source, `arg0`, and every
string in `arguments`. `argument_count` excludes the terminating NULL. Even an
empty argument vector is allocated and contains a terminating NULL. Parsing
copies all retained strings, so the caller can change or release `argv`
afterward. Treat the invocation fields as read-only and release them together
with `csh_invocation_destroy()`. That function also accepts a zero-initialized
invocation, clears its fields, and can be called again safely. CSH-022 must copy
any strings it retains beyond the invocation's lifetime.

[`cshell/input.h`](../include/cshell/input.h) also allows standalone sources:

| Constructor | Owned data and resources |
| --- | --- |
| `csh_input_from_string()` | Copies the NUL-terminated text and source name |
| `csh_input_from_file()` | Copies the path as its name and owns an opened descriptor |
| `csh_input_from_fd()` | Copies the name and owns a duplicate of the borrowed descriptor |

Constructors require valid output and error pointers. They return zero on
success or -1 on failure, setting the output source to NULL on failure.
`csh_input_destroy()` releases a standalone source and accepts NULL. Do not
separately destroy the source owned by an invocation.

Owned descriptors are at least 10 and have close-on-exec set. Duplicating a
descriptor does not close the original, but shares its underlying file offset
and file status flags. Serialize reads from the original and the source: bytes
read through either affect the other. For FIFO or terminal input,
`csh_input_from_fd()` clears `O_NONBLOCK` as required by the
[`sh` stdin rules](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_06).
This changes the shared open file description, so the caller's descriptor also
observes blocking mode. Other file status flags are preserved.

Using descriptors at least 10 avoids standard descriptor slots but does not
prevent a future shell redirection from selecting the same number. Close-on-exec
prevents inheritance across `exec`; it does not protect input from parent-shell
redirections. [CSH-019](tickets/CSH-019-simple-command-redirections.md) must
extend the current opaque input interface to protect or relocate private source
descriptors before applying user redirections. That executor integration is
outside CSH-016.

## Reading and positions

`csh_input_read_line()` returns exactly one physical line, including its newline
if present. It does not read ahead past that newline on descriptor sources, so
a subsequent command can consume its own stdin. A final unterminated line is
returned once before EOF. Empty sources immediately return EOF.

| Result | Output contract |
| --- | --- |
| `CSH_INPUT_LINE` | `line.data` contains `line.length` bytes; `start` and `end` describe the byte interval |
| `CSH_INPUT_EOF` | The line object is cleared; repeated reads return EOF |
| `CSH_INPUT_ERROR` | The line object is cleared; repeated reads return the same stored error |

The line buffer is borrowed until the next read or source destruction. Copy
bytes that must outlive that boundary. Use `length`, not `strlen()`; descriptor
input preserves embedded NUL bytes, and the buffer also has a convenience NUL
after the data. String constructors accept C strings and therefore cannot carry
embedded NUL bytes. The buffer grows dynamically without a fixed line limit,
subject to allocation and representable position limits. On allocation or read
failure, a partial line is discarded and never returned as successful input.

`csh_position.offset` is a zero-based byte offset. `line` and `column` are
one-based physical line and byte-column numbers, not Unicode character counts
or display columns. A newline increments the line and resets the column to
one. `csh_input_position()` gives the next unread byte's position, and each
returned line's `end` is exclusive. `csh_input_name()` returns a borrowed name
valid until source destruction; invocation uses `-c` for string sources and
`stdin` for stdin sources.

A physical line is not a complete shell command. Quotes, escaped newlines,
compound syntax, and here-documents require lexer/parser state. Those consumers
own complete/incomplete-command decisions and request additional lines as
needed; the input layer does not discard continuations or join syntax itself.

## Interactivity and prompting

Without `-i`, an invocation is interactive exactly when its source is stdin and
both supplied stdin and stderr descriptors are terminals. This includes `-s`
with positional arguments. Stdout does not participate in terminal detection.
`-i` selects interactive mode even for strings, scripts, or redirected stdin.
These rules follow Issue 8's
[`sh` options](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_04).

The current prompt-selection policy returns a prompt only for an interactive
stdin source. `csh_invocation_prompt()` returns the caller's already-expanded
PS1, or PS2 when the lexer/parser indicates continuation; otherwise it returns
NULL. The stdin restriction is a project policy for this initial API, not a
claim that POSIX explicitly restricts every interactive prompt to stdin.

Call prompt selection before a physical read. The caller owns expansion,
default values, and writing the selected string to stderr; this module only
borrows and selects the provided strings. See POSIX
[PS1 and PS2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03)
for the eventual expansion and interactive behavior requirements. No source or
invocation operation prints a startup banner or prompt.

## Errors and suggested statuses

`struct csh_error` has no allocated members. `message` points to a static
diagnostic description, `system_errno` records an applicable system error or
zero, and `argument_index` identifies an invocation operand or option when
known (zero otherwise). Read failures record the next unread source position.
Successful operations clear the error object. The caller decides how to format
and emit one diagnostic and how to apply the suggested status.

| Failure | Suggested status |
| --- | --- |
| Invalid usage, missing command string, unsupported option | 2 |
| Allocation, descriptor setup, or other script-open failure | 1 |
| Script not found (`ENOENT` or `ENOTDIR`) | 127 |
| Unrecoverable input read error | 128 |

Read status 128 and missing-script status 127 follow the
[`sh` exit-status requirements](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_14).
They describe errors at this API boundary, not completed command execution.
Final runtime status integration belongs to CSH-018 and CSH-039.

## Minimal consumer

This example traverses the selected source without executing it. A lexer can
consume or copy each line before the next call.

```c
#include <unistd.h>
#include "cshell/invocation.h"

int inspect_invocation(int argc, char **argv)
{
    struct csh_invocation invocation = {0};
    struct csh_input_line line;
    struct csh_error error;
    enum csh_input_result result;
    int status;

    if (csh_invocation_parse(&invocation, argc, argv, STDIN_FILENO,
            STDERR_FILENO, &error) == -1)
        return error.status;
    while ((result = csh_input_read_line(invocation.input, &line, &error))
            == CSH_INPUT_LINE) {
        /* Consume line.data[0..line.length) here; copy retained bytes. */
    }
    status = result == CSH_INPUT_ERROR ? error.status : 0;
    csh_invocation_destroy(&invocation);
    return status;
}
```

See [Testing](testing.md) and the
[CSH-016 validation record](tickets/CSH-016-input-and-invocation.md#validation)
for fixtures and limits of the current evidence.
