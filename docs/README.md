# Project documentation

Start with the [project README](../README.md) for installation and current status.

| Document | Purpose |
| --- | --- |
| [Contributing](../CONTRIBUTING.md) | Tickets, branch names, validation, and documentation workflow |
| [Architecture](architecture.md) | Current source layout and target module responsibilities |
| [Input and invocation](input-and-invocation.md) | Replacement input sources, invocation operands, ownership, positions, and errors |
| [Runtime behavior](candidate-runtime.md) | Public executable, cross-mode behavior, exit/status policy, and bootstrap limits |
| [Lexer and words](lexer-and-words.md) | Replacement tokens, quoting provenance, nested parser frames, and raw here-document handoff |
| [Parser and AST](parser-and-ast.md) | Complete-command parsing, owned syntax trees, ordered here-documents, and diagnostics |
| [Aliases](aliases.md) | Alias storage, handlers, parser eligibility, injected input, and read timing |
| [Shell state](shell-state.md) | Owned variables, parameters, attributes, environment snapshots, copying, and restoration |
| [Locale behavior](locales.md) | Startup/runtime precedence, patterns, IFS, diagnostics, host-qualified evidence and encoding limits |
| [Value expansion](value-expansions.md) | Structured value/final-field contexts, IFS, pathname generation, arithmetic, decoding, and deferred substitutions |
| [Simple-command execution](execution.md) | Owned prepared commands, phased expansion, lookup, child ownership, bootstrap builtins, and reversible redirections |
| [Execution clause evidence](execution-evidence.md) | Ordering, descriptors, lookup, pipelines, control flow and error assertions |
| [Evaluation builtins](evaluation-builtins.md) | Dot/eval, exec, lookup, aliases, input and resource utilities |
| [Control flow and functions](control-flow.md) | Selection, loops, function lifetimes, control transfer, and validation |
| [Job control](job-control.md) | Interactive groups, terminal ownership, job builtins, retained statuses, and signal boundaries |
| [Jobs/signal clause evidence](jobs-signals-evidence.md) | Exact requirement assertions, applicability and remaining obligations |
| [Traps and signals](traps-and-signals.md) | Trap command, pending actions, inheritance, input interrupts, and hangup policy |
| [Visual implementation plan](implementation-plan.md) | Dependencies, parallel tasks, and milestone completion |
| [Testing](testing.md) | Native and Docker commands, smoke coverage, and troubleshooting |
| [POSIX tracking](posix.md) | Specification target, gaps, and conformance evidence |
| [Requirements matrix](posix-matrix.md) | Language and invocation requirements, sources, owners, and planned evidence |
| [Shell options](shell-options.md) | Invocation/set behavior, failure contexts and inheritance |
| [Utilities and options](posix-utilities.md) | Required shell utilities, host boundary, options, and profile decisions |
| [Evidence conventions](posix-evidence.md) | Fixture provenance, smoke limits, and differential example |
| [Independent audit review](audit-review.md) | Reproduced runtime sample, matrix findings, and explicit remaining evidence owners |
| [Requirements by ticket](posix-owners.md) | Reverse lookup from implementation tickets to requirements |
| [Ticket index](tickets/README.md) | Implementation order and dependencies |
| [Ticket template](tickets/TEMPLATE.md) | Format for new implementation work |
| [Agent entry point](../AGENTS.md) | Project navigation for agents |

The ticket files are the source of truth for implementation status. Architecture
and POSIX documents describe the design and requirements; neither substitutes
for acceptance evidence in a completed ticket.

The architecture, implementation plan, and testing documents contain Mermaid
diagrams. GitHub renders these diagrams; each is accompanied by text or tables
so the information remains accessible in a plain Markdown reader.

- [State builtins](state-builtins.md): variables, positionals, directories, and special-builtin integration.

- [Invocation, lexical, grammar and alias clause evidence](invocation-syntax-evidence.md)

- [Shell state and builtin clause evidence](state-builtin-evidence.md): CSH-048 startup, environments, utility assertions and run records.

- [Base shell-option clause evidence](shell-option-evidence.md): CSH-051 entry, state, environment, policy and run mapping.
