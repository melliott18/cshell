# POSIX target and tracking

## Target

cshell targets the shell language and `sh` behavior in POSIX.1-2024 (Issue 8).
It currently implements a bootstrap subset. No complete conformance claim is made.

## Selected profile

The current target is the base Shell Command Language and `sh` utility. The
optional User Portability Utilities (UP) and XSI groups are not selected. cshell
already implements some job-control and XSI-associated commands, but those
features do not establish either complete option group. The conditional rows
remain in the [utility and option map](posix-utilities.md); selecting either
group later reopens its full linked set of requirements. This profile decision
does not exclude base requirements or make the current shell conforming.

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

This summary describes the public replacement runtime after CSH-039. The
requirement matrix retains its recorded historical baseline and detailed planning;
standalone module evidence does not establish runtime feature support.

| Area | Current evidence / gap | Owning tickets |
| --- | --- | --- |
| Build and source organization | One runtime; legacy sources and scanner dependencies removed | [CSH-039](tickets/CSH-039-legacy-retirement.md) |
| Memory and process safety | Module ownership, allocation failures, descriptor restoration, and child cleanup fixtures | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-020](tickets/CSH-020-pipeline-lifecycle.md) |
| Invocation and input | String/script/stdin, EOF, interactive detection, strict output, and final statuses | [CSH-018](tickets/CSH-018-status-and-cli-integration.md), [Runtime behavior](candidate-runtime.md) |
| Token recognition and quoting | Structured words, quote provenance, and integrated expansion | [CSH-004](tickets/CSH-004-lexer-and-words.md) |
| Grammar and command composition | Lists, groups, control flow and functions run through the replacement AST; full conformance audit remains open | [CSH-005](tickets/CSH-005-parser-and-ast.md), [CSH-021](tickets/CSH-021-lists-and-execution-contexts.md), [CSH-028](tickets/CSH-028-control-flow-and-functions.md) |
| Execution and redirections | Literal commands, external lookup/statuses, ordered redirections, concurrent pipelines | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-020](tickets/CSH-020-pipeline-lifecycle.md) |
| Variables and execution state | Owned state, environment import, literal assignments, state builtins | [CSH-007](tickets/CSH-007-variables-and-parameters.md) |
| Word expansion | Integrated value/field expansion, substitutions, here-documents, and arithmetic-first replay; milestone complete | [CSH-008](tickets/CSH-008-word-expansion.md) |
| Compound commands and functions | Parsing and runtime control flow, function lifetimes, and control transfer fixtures | [CSH-009](tickets/CSH-009-compounds-and-functions.md) |
| Builtins, aliases, and options | State/evaluation builtins, aliases and [shell options](shell-options.md); full conformance audit remains open | [CSH-010](tickets/CSH-010-builtins-options-and-aliases.md) |
| Signals, interactive mode, and jobs | Process groups, terminal handoff, job builtins, traps, input interrupt recovery, and hangup policy; full conformance audit pending | [CSH-034](tickets/CSH-034-job-control.md), [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) |
| Conformance evidence and portability | Native/Docker module and runtime fixtures, plus [locale, large-input and sparse-file probes](testing.md#portability-audit-probes); full requirement-level verification remains open | [CSH-037](tickets/CSH-037-portability-audit.md), [CSH-042](tickets/CSH-042-locale-semantics.md), [CSH-043](tickets/CSH-043-redirection-offset.md), [CSH-044](tickets/CSH-044-intermittent-bg-prompt.md) |

Legacy syntax such as `|&` and `>>&` must not be used as evidence of POSIX
coverage or retained as compatibility requirements. New modules take their
contracts from the standard. [CSH-039](tickets/CSH-039-legacy-retirement.md)
removes the old runtime without waiting for full POSIX coverage; unsupported
constructs must fail explicitly until their implementation tickets are complete.

## Replacement compound-syntax evidence

CSH-027 extends the [parser/AST API](parser-and-ast.md) to conditionals, loops,
case clauses (including POSIX.1-2024 `;&`), and function definitions. Structural
fixtures preserve words, redirections, source positions, and nested here-documents;
allocation-failure checks cover partial compound trees. CSH-028 adds
[execution evidence](control-flow.md) for control flow, function storage and
invocation, expansion, redirection lifetimes, and error cleanup. Full conformance
and later dot-script/trap integration remain separate work.

## Replacement value-expansion evidence

CSH-024 adds [module-level value expansion](value-expansions.md), with checked
parameter/tilde/arithmetic behavior, quote provenance, and dollar-single-quote
decoding. CSH-025 adds IFS field splitting, pathname generation, protected empty
fields, and explicit failure/interruption cleanup at the module level. CSH-026
integrates these APIs with substitutions, context-sensitive command preparation
and here-documents; [its evidence](tickets/CSH-026-substitution-and-heredoc-integration.md)
covers public runtime behavior and resource cleanup. CSH-041 adds arithmetic
ambiguity replay with lexer/parser fault sweeps and public cross-mode cases.
Standalone API fixtures and selected integration cases do not establish shell
conformance.

## Replacement execution evidence

CSH-019 adds [module-level simple-command execution](execution.md), with
lookup/status conversion, owned children, ordered file/descriptor/here-document
redirections, and parent builtin restoration. CSH-026 replaces its initial literal
adapter with context-sensitive preparation. CSH-023 adds prefix
assignment categories, selective restoration, and readonly error handling, with
real external environment probes and resolved builtin/function dispatch fixtures.
CSH-029 adds the state builtin family and utility inventory. Remaining builtin
and function semantics remain separate tickets.
The public runtime uses integrated expansion and state builtins.

CSH-020 adds replacement pipeline API evidence through `make test-pipeline`:
concurrent multi-stage execution, default last-stage status and negation,
builtin subshell isolation, explicit redirection precedence, and partial-launch
child/descriptor cleanup. Every stage's raw and converted status is retained.
These API checks use `build/tests/execute_fixture`; CSH-018/CSH-039 also test
pipelines through the public `cshell` in all input modes. `pipefail` remains with CSH-010; CSH-034 adds runtime process groups and job control. CSH-021 adds compound
stages as described below.

## Replacement context evidence

CSH-021 adds public-runtime and API evidence through `make test-context` for sequential and
AND/OR lists, brace/subshell state isolation, group redirection lifetimes,
compound pipeline stages, asynchronous return and background PID ownership.
Synchronization-based reaping checks and allocation/pipe/fork/wait injection
cover cleanup. Background PID storage is implemented; general `$!` expansion remains outside
this subset. CSH-034 adds retained wait statuses, idle SIGCHLD reaping and job
control through the optional runtime job manager. See [Execution contexts](execution.md#lists-groups-and-background-contexts).

## Replacement alias evidence

CSH-030 adds [alias storage, direct handlers, and token/AST substitution](aliases.md),
including recursive suppression and complete-command timing fixtures. CSH-031
adds [executed-script validation](evaluation-builtins.md) through the dispatcher,
nested dot/eval, functions, command lookup, and substitutions.

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

## Job-control evidence

CSH-034 adds [job control](job-control.md) through the persistent runtime context.
Native and Docker script/PTY checks cover job builtins, process groups, terminal
signals, stopping/resuming, terminal modes, idle reaping, and failure cleanup.
CSH-035 adds [trap and signal evidence](traps-and-signals.md) for inheritance,
parser interruption, and exit/hangup policy. The combined tests do not by
themselves establish full conformance for the CSH-011 milestone.
