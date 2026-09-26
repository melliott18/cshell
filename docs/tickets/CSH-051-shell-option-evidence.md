# CSH-051: Close base shell-option evidence gaps

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: Assigned when work starts
- Issue: [#83](https://github.com/melliott18/cshell/issues/83)

## Goal

Build an explicit option by entry point/state/affected-environment map using current exact fixture names, classify unspecified reporting/tracing and permitted defaults, add missing combinations, and record native/Docker/PTY results for every applicable base branch. Preserve the existing UP exclusions.

## Explicit current limitation

The rows all cite the same selected option fixtures, without a per-clause record for invocation/set, enable/disable, reports/defaults and affected execution environments. Passing a selected effect or option parser case cannot verify a whole option family.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [O-001](../posix-utilities.md#o-001) | Option syntax, enabling/disabling, invalid options, defaults, named/letter equivalence; `set -o` report has unspecified format, `set +o` must be reusable. Separate sh invocation’s unspecified no-argument forms. |
| [O-002](../posix-utilities.md#o-002) | `-a` / allexport: assignments from syntax, expansions, cd/getopts/read and separate environments. |
| [O-004](../posix-utilities.md#o-004) | `-C` / noclobber: existing regular files and races, override using `>\|`, redirection errors. |
| [O-005](../posix-utilities.md#o-005) | `-e` / errexit: pipeline and substitution status, while/until/if/elif tests, non-final AND-OR commands, negation, compounds/functions and subshell exceptions. |
| [O-006](../posix-utilities.md#o-006) | `-f` / noglob: suppress pathname expansion without suppressing unrelated expansion stages. |
| [O-007](../posix-utilities.md#o-007) | `-h`: accept on/off; PATH-search optimization is optional and must preserve command-search semantics. |
| [O-009](../posix-utilities.md#o-009) | `-n` / noexec: read and parse without execution/side effects; permitted ignoring in interactive shells and their recursive subshells gets a documented fixture expectation. |
| [O-012](../posix-utilities.md#o-012) | `-u` / nounset: unset parameter/arithmetic expansion failure, exempt `@` and `*`, diagnostics and context-specific shell error consequences. |
| [O-013](../posix-utilities.md#o-013) | pipefail: derive pipeline status from all stages, capture setting at pipeline start, combine with `!`, errexit and asynchronous execution. |
| [O-014](../posix-utilities.md#o-014) | `-v` / verbose: input written to stderr as read, with parsing/evaluation and alias timing cases. |
| [O-016](../posix-utilities.md#o-016) | `-x` / xtrace: trace after expansion and before execution, stderr destination, PS4 when supported; do not assert whether `set +x` is traced. |
| [O-017](../posix-utilities.md#o-017) | Runtime/invocation options propagate or restore under functions, subshells, substitutions, eval/dot and aliases; each option’s required effect is tested in the affected environment. |
| [O-018](../posix-utilities.md#o-018) | Default option state is off unless invocation or an option description says otherwise; verify monitor interactive default and permitted -h default separately. |

Relevant documented choices: O-001 (invocation no-argument forms), O-007 (permitted hashing), O-009 (interactive noexec), O-016 (tracing disable), O-018 (UP monitor defaults excluded). Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/option_cases.py](../../tests/option_cases.py)
- [tests/input_fixture.c](../../tests/input_fixture.c)
- [tests/runtime_cases.py](../../tests/runtime_cases.py)

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
