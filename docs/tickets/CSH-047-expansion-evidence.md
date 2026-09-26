# CSH-047: Close expansion, parameter and locale evidence gaps

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: Assigned when work starts
- Issue: [#79](https://github.com/melliott18/cshell/issues/79)

## Goal

Map existing exact case names to source clauses and input modes, classify selected parsing/numeric/encoding policies, add remaining scoped runtime cases, and retain unavailable locale configurations as reasoned skips with CSH-042 ownership. Record native/Docker execution identities and outcomes without promoting a family from selected witnesses.

## Explicit current limitation

Selected value, field, substitution, arithmetic and portability cases pass, but ordering/context, parameter/pattern breadth, locale and implementation-defined encoding/integer behavior have not been decomposed and verified for each applicable clause. CSH-042 owns specific locale semantics work; resolving it alone cannot verify all expansion families.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [ENV-002](../posix-matrix.md#env-002) | Maintain positional parameters and `@`, `*`, `#`, `?`, `-`, `$`, `!`, `0`, including quoting and subshell behavior. |
| [ENV-004](../posix-matrix.md#env-004) | Respect initial LC_CTYPE lexical interpretation, locale-sensitive patterns and diagnostic locale. |
| [EXP-001](../posix-matrix.md#exp-001) | Apply ordered, context-sensitive expansions; preserve field provenance, quoted empties and multi-field exceptions. |
| [EXP-002](../posix-matrix.md#exp-002) | Expand tilde prefixes for home/login names and assignments, treating the result as quoted. |
| [EXP-003](../posix-matrix.md#exp-003) | Implement parameter default, assign-default, error, alternate and null-versus-unset operators; expand operator words only when needed. |
| [EXP-004](../posix-matrix.md#exp-004) | Implement parameter length, shortest/longest prefix/suffix pattern removal and nested/quoted operands. |
| [EXP-005](../posix-matrix.md#exp-005) | Execute both command-substitution forms in the required environment; strip trailing newlines and preserve statuses. |
| [EXP-006](../posix-matrix.md#exp-006) | Evaluate arithmetic expressions, variables, required operators and diagnostics using supported integer semantics. |
| [EXP-007](../posix-matrix.md#exp-007) | Split only eligible expansion results with unset/empty IFS, separators, whitespace and empty-field rules. |
| [EXP-008](../posix-matrix.md#exp-008) | Expand matching pathnames, ordering and unmatched patterns; respect quoted patterns and noglob. |
| [EXP-009](../posix-matrix.md#exp-009) | Remove syntactic quotes last while retaining quoted expansion results and literal quote characters. |
| [EXP-010](../posix-matrix.md#exp-010) | Match single/multiple-character patterns, bracket expressions/classes, quoting, slashes and leading periods. |
| [EXP-011](../posix-matrix.md#exp-011) | Use assignment context for declaration-utility operands; defer context until applicable command-name processing. |

Relevant documented choices: D-003, D-004 (substitution parsing), D-005, D-006 (declaration recognition), D-008 (expansion extensions). Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/fixtures/expand.json](../../tests/fixtures/expand.json)
- [tests/fields.py](../../tests/fields.py)
- [tests/substitution_cases.py](../../tests/substitution_cases.py)
- [tests/substitution_fixture.c](../../tests/substitution_fixture.c)
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
