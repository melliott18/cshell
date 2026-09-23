# POSIX target and tracking

## Target

cshell targets the shell language and `sh` behavior in POSIX.1-2024 (Issue 8).
It is currently a prototype. No complete conformance claim is made.

Normative references:

- [Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html)
- [sh utility](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html)
- [Shell and Utilities introduction](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html)

Use the selected edition when evaluating behavior. Issue 8 includes
dollar-single-quote syntax and the `pipefail` option. Track optional facilities
and implementation-defined choices explicitly as coverage grows. A shell
implementation's compliance is separate from certification of an entire system.

## Requirements and evidence

The [requirements matrix](posix-matrix.md) inventories the shell language and
`sh` contract using stable IDs, precise Issue 8 sources, scope decisions,
implementation owners, planned fixtures and current evidence. Its companion
[utility and option map](posix-utilities.md) covers special/intrinsic utilities,
host dependencies and conditional profiles. Use [requirements by ticket](posix-owners.md)
to find a ticket's rows, or follow a row's owner and evidence links in the other
direction.

[Evidence conventions](posix-evidence.md) define missing, implemented, verified
and inapplicable states, exact smoke-test limits, and a reproducible differential
example. Unimplemented requirements and pending scope decisions remain open.
Reference-shell output does not establish expected results or cshell conformance.
Ticket lifecycle status continues to live in the [ticket files](tickets/README.md).

## Runtime baseline

This summary describes the prototype at the matrix's recorded base revision.
The requirement rows are the detailed planning and evidence record.

| Area | Current evidence / gap | Owning tickets |
| --- | --- | --- |
| Build and source organization | Foundation only; no language conformance implied | [CSH-001](tickets/CSH-001-project-foundation.md) |
| Memory and process safety | Known prototype defects; replacement modules own safety coverage | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-004](tickets/CSH-004-lexer-and-words.md), [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-020](tickets/CSH-020-pipeline-lifecycle.md) |
| Invocation and input | [Replacement APIs](input-and-invocation.md) cover string/script/stdin sources, supported invocation operands, explicit EOF, and interactive detection; default executable integration and final runtime statuses remain pending | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-018](tickets/CSH-018-status-and-cli-integration.md), [CSH-039](tickets/CSH-039-legacy-retirement.md) |
| Token recognition and quoting | Flat token splitter; quotes retained in arguments | [CSH-004](tickets/CSH-004-lexer-and-words.md) |
| Grammar and command composition | No AST; semicolon dispatch unimplemented | [CSH-005](tickets/CSH-005-parser-and-ast.md) |
| Execution and redirections | Partial external command support; incomplete descriptor semantics | [CSH-006](tickets/CSH-006-execution-and-redirection.md) |
| Variables and execution state | Environment inherited, but shell state model missing | [CSH-007](tickets/CSH-007-variables-and-parameters.md) |
| Word expansion | Expansion subsystem missing | [CSH-008](tickets/CSH-008-word-expansion.md) |
| Compound commands and functions | Not implemented | [CSH-009](tickets/CSH-009-compounds-and-functions.md) |
| Builtins, aliases, and options | Only incomplete `cd` and `exit` paths | [CSH-010](tickets/CSH-010-builtins-options-and-aliases.md) |
| Signals, interactive mode, and jobs | Dedicated lifecycle and terminal management missing | [CSH-011](tickets/CSH-011-signals-and-job-control.md) |
| Conformance evidence and portability | Native/Docker smoke runner exists; conformance suite pending | [CSH-012](tickets/CSH-012-conformance-and-portability.md) |

Legacy syntax such as `|&` and `>>&` must not be used as evidence of POSIX
coverage or retained as compatibility requirements. New modules take their
contracts from the standard. [CSH-039](tickets/CSH-039-legacy-retirement.md)
removes the old runtime without waiting for full POSIX coverage; unsupported
constructs must fail explicitly until their implementation tickets are complete.

## Replacement value-expansion evidence

CSH-024 adds [module-level value expansion](value-expansions.md), with checked
parameter/tilde/arithmetic behavior, quote provenance, and dollar-single-quote
decoding. Field splitting, pathname expansion, real substitutions, and arithmetic
ambiguity replay remain integration gaps. The prototype table above remains a
runtime baseline; standalone API fixtures do not establish shell conformance.

## Evidence required

As a feature is implemented, link its specific specification section and tests
from the owning ticket. Record the supported behavior, remaining cases, and any
implementation-defined decisions. A passing example is evidence for that case,
not every requirement in a section.

The test harness should compare observable output, exit status, filesystem
effects, and completion within a timeout. Fix the locale and environment when
needed for deterministic cases. Use pseudo-terminals for terminal behavior.

Differential tests against other shells help find discrepancies. Their output is
not the authority: use the standard to resolve differences and avoid asserting
one result where behavior is unspecified. Record reference-shell versions,
especially when testing Issue 8 additions.

Before claiming the target is covered, refine each matrix family into its full
fixture inventory, link passing results, close documented gaps, and validate on
the supported systems. Sanitizers and Linux/macOS builds are complementary safety and
portability checks, not substitutes for language conformance tests.

See [Testing](testing.md) for the current native and Docker entry points and
their intentionally limited smoke coverage.
