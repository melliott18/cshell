# Architecture

## Current implementation

CSH-001 establishes source boundaries and a portable build. It does not complete
the shell language rewrite.

| Path | Responsibility |
| --- | --- |
| `src/main.c` | Entry point, prompt, input loop, and dispatch |
| `src/legacy/lexer.l` | Existing Flex token splitter |
| `src/legacy/execute.c` | Existing command execution and redirection helpers |
| `include/cshell/legacy.h` | Narrow internal interface between the input loop and legacy implementation |
| `build/` | Generated scanner and object files |
| `tests/smoke.py` | Bounded checks for the currently supported execution path |
| `Dockerfile` / `.dockerignore` | Linux build/test environment and source-only build context |

The legacy interface borrows scanner-owned argument storage. It is consumed
synchronously before the next read, and callers must not free it. Execution
currently mutates that argument array. This is a transitional contract, not the
API for the replacement parser.

Existing limitations include fixed scanner storage, incomplete quoting, no
grammar tree, incomplete descriptor/process management, and missing status and
EOF semantics. The safety and invocation tickets precede the language rewrite.

## Target module boundaries

Add modules when their implementation ticket starts; the following paths are
planned, not claims that these files exist today.

| Planned module | Owns | Must not own |
| --- | --- | --- |
| `input` | Source abstraction for strings, scripts, and stdin; positions; complete/incomplete/EOF results | Command execution |
| `lexer` | Tokens and word fragments with quote/escape provenance | Expansion into final argument strings |
| `parser` / `ast` | Grammar, syntax errors, command trees, ordered redirections, deferred here-documents | Forks or global shell mutation |
| `variables` / `state` | Shell variables and attributes, positional parameters, options, last status | Scanning input |
| `expand` | Context-sensitive word expansion and field generation | Pipeline process management |
| `execute` | Tree evaluation, execution environments, command lookup, pipeline lifecycle and status | Parsing strings by searching for operators |
| `redirect` | Ordered descriptor operations and restoration for parent execution | Deciding which commands need a fork |
| `builtins` | Builtin dispatch and shell-state operations | A second parser or independent process launcher |
| `signals` / `jobs` | Signal dispositions, pending events, process groups, terminal ownership, job state | Signal-handler access to arbitrary mutable structures |

Public-to-the-project headers live under `include/cshell/`. Keep module-private
helpers `static`. Introduce shared types only when multiple modules need the
same contract; avoid a header that exposes every internal structure.

## Processing model

```text
input -> lexer <-> parser -> command tree
                                |
                         tree evaluation
                                |
                 expansion + redirection + dispatch
                                |
                     builtin or child process
```

Parsing and execution proceed at appropriate complete-command boundaries.
Aliases and here-documents require parser/lexer cooperation, and input must not
consume bytes intended for a command that reads stdin. Avoid a design that
unconditionally tokenizes or expands an entire script before executing it.

The tree records simple commands, pipelines, AND/OR and sequential/background
lists, compound commands, and functions. A word retains quoted and unquoted
fragments until expansion. Redirections preserve source order: `>out 2>&1` and
`2>&1 >out` are distinct operations.

## Ownership and failure contracts

These are design requirements for replacement modules, to be made concrete in
their tickets:

- Each allocated object has one documented owner and a matching cleanup path.
  APIs state whether pointers are borrowed, transferred, or newly allocated.
- Parsing returns a command tree, an incomplete-input result, EOF, or an error
  with a source location. It does not terminate the process directly.
- The executor owns launched child IDs, pipeline descriptors, and status
  collection. All child failure paths terminate the child.
- Builtins that affect the current environment can run in the parent with
  reversible descriptor changes; subshell contexts isolate those changes.
- Error results preserve the information needed for a diagnostic and shell
  status. Internal helpers do not print duplicate errors at every layer.
- Cleanup after failed allocation, redirection, or process creation is part of
  the module's contract and validation.

## Replacement strategy

Keep the prototype isolated while the new input, lexer, parser, and executor
interfaces are implemented. Wire each usable path into the program in a bounded
ticket. Remove the obsolete legacy path once its replacement is integrated;
avoid indefinitely maintaining two independent shell implementations.

See the [ticket index](tickets/README.md) for sequencing and the
[POSIX tracking document](posix.md) for the behavior target.
