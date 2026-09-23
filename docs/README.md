# Project documentation

Start with the [project README](../README.md) for installation and current status.

| Document | Purpose |
| --- | --- |
| [Contributing](../CONTRIBUTING.md) | Tickets, branch names, validation, and documentation workflow |
| [Architecture](architecture.md) | Current source layout and target module responsibilities |
| [Input and invocation](input-and-invocation.md) | Replacement input sources, invocation operands, ownership, positions, and errors |
| [Visual implementation plan](implementation-plan.md) | Dependencies, parallel tasks, and milestone completion |
| [Testing](testing.md) | Native and Docker commands, smoke coverage, and troubleshooting |
| [POSIX tracking](posix.md) | Specification target, gaps, and conformance evidence |
| [Ticket index](tickets/README.md) | Implementation order and dependencies |
| [Ticket template](tickets/TEMPLATE.md) | Format for new implementation work |
| [Agent entry point](../AGENTS.md) | Project navigation for agents |

The ticket files are the source of truth for implementation status. Architecture
and POSIX documents describe the design and requirements; neither substitutes
for acceptance evidence in a completed ticket.

The architecture, implementation plan, and testing documents contain Mermaid
diagrams. GitHub renders these diagrams; each is accompanied by text or tables
so the information remains accessible in a plain Markdown reader.
