# Project documentation

Start with the [project README](../README.md) for installation and current status.

| Document | Purpose |
| --- | --- |
| [Contributing](../CONTRIBUTING.md) | Tickets, branch names, validation, and documentation workflow |
| [Architecture](architecture.md) | Current source layout and target module responsibilities |
| [Input and invocation](input-and-invocation.md) | Replacement input sources, invocation operands, ownership, positions, and errors |
| [Lexer and words](lexer-and-words.md) | Replacement tokens, quoting provenance, nested parser frames, and raw here-document handoff |
| [Parser and AST](parser-and-ast.md) | Complete-command parsing, owned syntax trees, ordered here-documents, and diagnostics |
| [Shell state](shell-state.md) | Owned variables, parameters, attributes, environment snapshots, copying, and restoration |
| [Value expansion](value-expansions.md) | Structured expansion contexts, parameters, tilde, arithmetic, decoding, and deferred substitutions |
| [Visual implementation plan](implementation-plan.md) | Dependencies, parallel tasks, and milestone completion |
| [Testing](testing.md) | Native and Docker commands, smoke coverage, and troubleshooting |
| [POSIX tracking](posix.md) | Specification target, gaps, and conformance evidence |
| [Requirements matrix](posix-matrix.md) | Language and invocation requirements, sources, owners, and planned evidence |
| [Utilities and options](posix-utilities.md) | Required shell utilities, host boundary, options, and profile decisions |
| [Evidence conventions](posix-evidence.md) | Fixture provenance, smoke limits, and differential example |
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
