# Architecture

## Current implementation

CSH-001 establishes source boundaries and a portable build. It does not complete
the shell language rewrite.

The input loop asks the legacy scanner for an argument array, then dispatches
that array to the legacy executor. This is the current path:

```mermaid
flowchart LR
    main["src/main.c: input loop"] -->|"read arguments"| lexer["src/legacy/lexer.l: scanner"]
    lexer -->|"borrowed argument array"| main
    main -->|"dispatch arguments"| execute["src/legacy/execute.c: executor"]
```

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
EOF semantics. The original implementation is reference material, not a required
foundation for the replacement. Its safety-repair tickets CSH-002, CSH-014, and
CSH-015 are superseded; new input and runtime work does not wait for repairs to
code that will be deleted. These known defects still require regression coverage
in the replacement modules.

## Current replacement modules

CSH-016 adds standalone input and invocation APIs, CSH-004 adds the lexer and
structured token/word API, CSH-005 adds parser/AST ownership, CSH-022 adds
shell-state storage, CSH-024 adds value expansion, CSH-025 adds final field
generation, and CSH-027 extends the parser with compound commands and function
definitions. They have no dependency on the legacy header, scanner, or executor,
and the default
executable does not call them yet.

| Path | Responsibility |
| --- | --- |
| `src/input.c` / `include/cshell/input.h` | Owned string, script, and descriptor sources; physical lines, byte positions, explicit EOF, and sticky errors |
| `src/invocation.c` / `include/cshell/invocation.h` | Supported invocation options, owned `$0` and positional operands, interactive detection, and prompt selection |
| `src/lexer.c` / `include/cshell/lexer.h` | Owned tokens and fragment trees, incremental quote/substitution contexts, shared-cursor nested command lexers, and raw here-document handoff |
| `src/parser.c` / `include/cshell/parser.h` | Complete-command grammar, contextual words, nested command parsing, ordered here-document collection, and source diagnostics |
| `src/ast.c` / `include/cshell/ast.h` | Owned syntax nodes, words, substitutions, and ordered redirections with allocation-safe cleanup |
| `src/expand.c` / `include/cshell/expand.h` | Structured value expansion, quote/empty provenance, context restrictions, and lazy substitution handoff |
| `src/fields.c` / `src/pathname.c` | IFS field splitting, protected filename matching, owned final fields, and cooperative interruption |
| `src/arithmetic.c` / `include/cshell/arithmetic.h` | Checked signed-long arithmetic and grammar-only parser probe |
| `src/quote.c` / `include/cshell/quote.h` | Reusable dollar-single-quote decoding before expansion or delimiter quote removal |
| `src/state.c` / `include/cshell/state.h` | Owned variables and attributes, copied invocation parameters, option/status metadata, environment snapshots, and full-state copying/restoration |

See [Input and invocation](input-and-invocation.md) for the concrete ownership,
descriptor, position, and error contracts. Physical input lines do not establish
command completeness; that remains the lexer/parser's responsibility. CSH-018
integrates replacement-runtime fixtures and CSH-039 switches the executable.
See [Lexer and words](lexer-and-words.md) for the feed contract and the parser
handshake: the parser decides which `)` closes a command substitution; the lexer
preserves its raw source and surrounding word context.

See [Parser and AST](parser-and-ast.md) for complete-command read boundaries,
error results, and tree ownership. This parser does not execute commands or
expand words.

See [Shell state](shell-state.md) for variable ownership, readonly errors, and
allocation-free checkpoint restoration. State stores option bits without
implementing their runtime behavior, and leaves special startup variable
initialization to CSH-029. Full-state checkpoints do not implement selective
temporary assignments; CSH-023 owns their execution-category rules. The state
module neither reads nor modifies the process environment.

See [Value expansion](value-expansions.md) for intermediate fields, quoted empty
values, transactional expansion errors, arithmetic limits, and the parser/executor
handoffs, final IFS fields, pathname generation, and interruption cleanup.
Execution and here-document integration remain CSH-026 work.

## Target module boundaries

The input, invocation, lexer, parser/AST, quote, state, and value-expansion
modules above exist. Add the remaining modules when their implementation
tickets start. This table defines target
responsibilities and does not claim that every listed module is implemented.

| Module | Owns | Must not own |
| --- | --- | --- |
| `input` | Source abstraction for strings, scripts, and stdin; byte positions; physical-line/EOF/error results | Command completeness, syntax interpretation, or execution |
| `invocation` | Input-mode and option selection, operand mapping, interactive detection, prompt selection | Parameter expansion, prompt output, or execution |
| `lexer` | Tokens and word fragments with quote/escape provenance | Expansion into final argument strings |
| `parser` / `ast` | Grammar, syntax errors, command trees, ordered redirections, deferred here-documents | Forks or global shell mutation |
| `alias` | Owned alias table and direct alias/unalias handlers; lexer/parser cooperate on substitution | Executing commands or reading descriptors |
| `variables` / `state` | Shell variables and attributes, positional parameters, options, last status | Scanning input |
| `expand` | Context-sensitive word expansion and field generation | Pipeline process management |
| `execute` | Tree evaluation, execution environments, command lookup, pipeline lifecycle and status | Parsing strings by searching for operators |
| `redirect` | Ordered descriptor operations and restoration for parent execution | Deciding which commands need a fork |
| `builtins` | Builtin dispatch and shell-state operations | A second parser or independent process launcher |
| `signals` / `jobs` | Signal dispositions, pending events, process groups, terminal ownership, job state | Signal-handler access to arbitrary mutable structures |

Public-to-the-project headers live under `include/cshell/`. Keep module-private
helpers `static`. Introduce shared types only when multiple modules need the
same contract; avoid a header that exposes every internal structure.

New modules must not import `cshell/legacy.h`, call legacy functions, or depend
on the scanner's flat argument vector. Do not copy the old dispatcher into a new
filename or preserve its assumptions in new interfaces. POSIX requirements and
the ownership contracts below determine the design; existing quirks and
unsupported operator spellings are not compatibility requirements.

## Processing model

The following diagram is the proposed replacement, not the current execution
path. Input, lexer, and parser construct a command tree (AST). The executor
evaluates that tree and coordinates expansion, shell state, builtins,
redirections, and child processes. Arrows below the executor show collaborating
modules, not a fixed execution sequence.

```mermaid
flowchart TB
    input["Input sources"] --> lexer["Lexer and words"]
    lexer <-->|"syntax context"| parser["Parser"]
    parser --> ast["Command tree"]
    ast --> execute["Executor"]
    execute --> expand["Expansion"]
    execute --> builtins["Builtins"]
    execute --> redirect["Redirections"]
    execute --> children["Child processes"]
    execute --> jobs["Signals and jobs"]
    expand --> state["Shell state"]
    builtins --> state
    execute --> state
    jobs <-->|"signals and process state"| children
```

Parsing and execution proceed at appropriate complete-command boundaries.
Aliases and here-documents require parser/lexer cooperation, and input must not
consume bytes intended for a command that reads stdin. Avoid a design that
unconditionally tokenizes or expands an entire script before executing it.
The module table above defines ownership even when a Markdown viewer cannot
render the diagram.

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

Build replacement modules independently of the prototype. CSH-016 defines
input and invocation APIs; CSH-004 and CSH-005 establish tokens, words, and the
syntax tree. API fixtures validate these modules before the replacement can run
commands. CSH-019 adds command execution and redirections, and CSH-020 adds
pipelines. Input, allocation, descriptor, and child-process safety belong to
those modules from their first implementation.

CSH-018 integrates invocation modes and statuses through a test driver for the
replacement runtime. This driver is temporary test infrastructure, not another
public shell mode. The initial literal-word adapter in CSH-019 is a bounded
replacement-module stub pending CSH-008 expansion; it neither calls legacy code
nor flattens syntax for the old dispatcher. Unsupported syntax or expansion must
fail before the affected construct produces side effects, with no legacy
fallback.

[CSH-039](tickets/CSH-039-legacy-retirement.md) owns the explicit cutover after
CSH-018 and CSH-020. It switches the default `cshell` executable to the new path
and verifies its documented bootstrap subset through native and Docker tests:
input modes, external commands, `cd`, `exit`, redirections, and pipelines. This
is an intermediate shell implementation; full builtin semantics and the
remaining POSIX features continue in their tickets.

Cutover is complete only when:

- `src/legacy/`, `include/cshell/legacy.h`, and the old input/dispatch loop are
  deleted from the current source tree.
- Legacy scanner generation, compilation rules, object files, linked symbols,
  and legacy-only build dependencies are absent from a clean build.
- The default executable has one runtime path; temporary migration drivers,
  fallback paths, feature switches, and compatibility adapters are removed.
- Prototype-specific test allowances, including non-interactive prompt
  stripping, are removed, and documentation describes the replacement's actual
  capabilities and limitations.
- The implementation contains no renamed or copied legacy dispatcher hidden
  behind the new module interfaces.

Git history and historical ticket evidence remain intact. Removal concerns the
current implementation and its dependencies, and requires no history rewrite.
The larger POSIX roadmap proceeds on the replacement after cutover; finishing
every later feature is not a prerequisite for deleting the prototype.

See the [ticket index](tickets/README.md) for sequencing and the
[POSIX tracking document](posix.md) for the behavior target.
