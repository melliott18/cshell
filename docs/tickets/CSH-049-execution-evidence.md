# CSH-049: Close execution, redirection and control-flow evidence gaps

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: Assigned when work starts
- Issue: [#81](https://github.com/melliott18/cshell/issues/81)

## Goal

Map existing exact fixtures and their implementation revisions; decompose ordering, descriptors, concurrency/status, lookup, loops/functions and error consequences. Document and test descriptor, assignment, pipeline and signal-status policies; integrate CSH-043 boundary evidence and CSH-042 relevant case findings without treating those fixes as complete family verification.

## Explicit current limitation

Execution/control and descriptor fixtures pass selected assertions, but the complete assignment/redirection/search/pipeline/control-flow/error families are not mapped to all relevant clause-level runtime cases across supported platforms. The exact redirection offset boundary remains a CSH-043 limitation and locale-dependent case behavior retains CSH-042.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [SH-009](../posix-matrix.md#sh-009) | Do not fail pathname expansion because of file size; document redirection offset maximum. |
| [RED-001](../posix-matrix.md#red-001) | Apply redirections left to right, expand targets in context, use default descriptor numbers and restore parent descriptors. |
| [RED-002](../posix-matrix.md#red-002) | Open `<`, `>` and `>\|` with specified creation/truncation and noclobber handling. |
| [RED-003](../posix-matrix.md#red-003) | Append using `>>`, creating missing files without truncating existing data. |
| [RED-004](../posix-matrix.md#red-004) | Deliver here-documents with quoted/unquoted delimiters, tab stripping, expansion and evaluation timing. |
| [RED-005](../posix-matrix.md#red-005) | Duplicate/close input and output descriptors using `<&` and `>&`, including invalid-descriptor failures. |
| [RED-006](../posix-matrix.md#red-006) | Open read/write redirections with `<>`, creation and offset behavior. |
| [EXEC-001](../posix-matrix.md#exec-001) | Process simple-command expansion, redirection and assignment in the specified order and permitted alternatives. |
| [EXEC-002](../posix-matrix.md#exec-002) | Apply prefix assignment lifetime by no-name/external/special/function category; enforce readonly errors. |
| [EXEC-003](../posix-matrix.md#exec-003) | Handle assignment/redirection-only commands and last-substitution status without corrupting parent state. |
| [EXEC-004](../posix-matrix.md#exec-004) | Search commands with correct special-builtin/function/intrinsic/PATH precedence; execute pathname commands and format fallback. |
| [EXEC-005](../posix-matrix.md#exec-005) | Pass argv, environment and open descriptors to external commands; apply rules for initially closed standard descriptors. |
| [EXEC-006](../posix-matrix.md#exec-006) | Connect concurrent pipeline stages before command redirections and wait for required completion. |
| [EXEC-007](../posix-matrix.md#exec-007) | Compute pipeline status and `!` negation, including Issue 8 pipefail selection. |
| [EXEC-008](../posix-matrix.md#exec-008) | Execute sequential, AND and OR lists with short-circuiting, precedence and final status. |
| [EXEC-010](../posix-matrix.md#exec-010) | Execute brace groups in the current environment and parenthesized groups in subshell environments. |
| [EXEC-011](../posix-matrix.md#exec-011) | Execute for loops, including positional-parameter defaults, expansion timing and zero-iteration status. |
| [EXEC-012](../posix-matrix.md#exec-012) | Execute case matching, pattern expansion, no-match status, `;;` termination and `;&` fall-through. |
| [EXEC-013](../posix-matrix.md#exec-013) | Execute if/elif/else, while and until with condition-controlled evaluation and specified statuses. |
| [EXEC-014](../posix-matrix.md#exec-014) | Define/invoke functions with call-time redirections, argument restoration, status, scope and separate function/variable namespaces. |
| [EXEC-015](../posix-matrix.md#exec-015) | Apply interactive/non-interactive consequences for syntax, expansion, assignment, utility, redirection and read errors. |
| [EXEC-016](../posix-matrix.md#exec-016) | Retain zero/nonzero statuses; report 126/127 execution failures and documented signal-derived values above 128. |
| [U-003](../posix-utilities.md#u-003) | `break [n]`: default depth, nested/outermost loop transfer, same-environment enclosure, status; isolate non-lexical enclosure cases. |
| [U-004](../posix-utilities.md#u-004) | `continue [n]`: default depth, nested/outermost loop continuation, enclosure and status; isolate non-lexical enclosure cases. |
| [O-026](../posix-utilities.md#o-026) | Document shell redirection offset maximum and demonstrate representative boundary/error behavior on each supported system. CSH-019 chooses/documents the descriptor policy; CSH-037 records platform limits. |

Relevant documented choices: D-002, D-006, D-007. Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/execute.py](../../tests/execute.py)
- [tests/pipeline.py](../../tests/pipeline.py)
- [tests/contexts.py](../../tests/contexts.py)
- [tests/control_flow_cases.py](../../tests/control_flow_cases.py)
- [tests/runtime_cases.py](../../tests/runtime_cases.py)
- [tests/substitution_cases.py](../../tests/substitution_cases.py)
- [tests/portability.py](../../tests/portability.py)

These are starting points for inspection, not claims that the complete rows
already pass. Reuse exact case names and assertions where they are sufficient;
add or split fixtures only for a concrete coverage gap.

## Acceptance criteria

- [ ] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [ ] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [ ] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [ ] Matrix rows and reverse ownership links reflect only the verified scope;
  broad rows are split where necessary and the CSH-012 compliance gate remains
  closed while any applicable requirements are unmet.

## Validation

Run the applicable focused suites above and the integration paths documented in
[Testing](../testing.md), including `make test test-pty test-harness`, Docker
and ASan/UBSan checks where the changed paths require them. Record exact case
names and results following the [evidence rules](../posix-evidence.md).
Reference-shell comparisons are separate observations, never normative oracles.

## Implementation notes/evidence

Allocated by the CSH-037 follow-up audit at baseline `58ca5c3`. The explicit
limitation and complete row list above replace reliance on already-completed
implementation tickets as owners of remaining verification work.
