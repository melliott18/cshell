# Implementation tickets

These tickets break the POSIX shell work into reviewable changes. Start with the
first unfinished prerequisite, then choose a ticket whose dependencies are done.
The status in each ticket is authoritative; this index records only scope and
dependencies. Completing one ticket does not establish POSIX compliance.

Read the [contribution workflow](../../CONTRIBUTING.md) before starting work. Use the
[ticket template](TEMPLATE.md) for additional work, including defects discovered
during implementation. Split a ticket if its acceptance criteria cannot be
reviewed together; preserve explicit dependencies between the smaller tickets.

| Ticket | Purpose | Depends on |
| --- | --- | --- |
| [CSH-001](CSH-001-project-foundation.md) | Establish executable, project workflow, and native/Docker smoke checks | None |
| [CSH-002](CSH-002-legacy-safety.md) | Contain known memory and process defects in the legacy implementation | CSH-001 |
| [CSH-003](CSH-003-invocation-and-test-harness.md) | Establish invocation modes, input lifecycle, and behavioral tests | CSH-002 |
| [CSH-004](CSH-004-lexer-and-words.md) | Preserve lexical structure and quoting in shell words | CSH-003 |
| [CSH-005](CSH-005-parser-and-ast.md) | Parse command lists, pipelines, and redirections into an AST | CSH-004 |
| [CSH-006](CSH-006-execution-and-redirection.md) | Centralize execution, descriptors, child ownership, and status | CSH-005 |
| [CSH-007](CSH-007-variables-and-parameters.md) | Model shell variables, environments, and positional parameters | CSH-003, CSH-006 |
| [CSH-008](CSH-008-word-expansion.md) | Implement context-sensitive POSIX word expansion | CSH-004, CSH-006, CSH-007 |
| [CSH-009](CSH-009-compounds-and-functions.md) | Add compound commands and shell functions | CSH-005, CSH-006, CSH-008 |
| [CSH-010](CSH-010-builtins-options-and-aliases.md) | Complete required builtins, shell options, and aliases | CSH-007, CSH-008, CSH-009 |
| [CSH-011](CSH-011-signals-and-job-control.md) | Implement traps, signals, and interactive job control | CSH-006, CSH-009, CSH-010 |
| [CSH-012](CSH-012-conformance-and-portability.md) | Audit conformance and complete portability and interactive checks | CSH-008, CSH-009, CSH-010, CSH-011 |

Build checks and regression tests grow with every ticket. CSH-012 audits that
evidence; it is not the first testing milestone. Requirements whose behavior is
unspecified, implementation-defined, or conditional in POSIX must be recorded as
such rather than inferred from another shell.
