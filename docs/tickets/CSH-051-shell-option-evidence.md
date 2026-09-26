# CSH-051: Close base shell-option evidence gaps

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: `test/CSH-051-shell-option-evidence`
- Issue: [#83](https://github.com/melliott18/cshell/issues/83)

## Goal

Build an explicit option by entry point/state/affected-environment map using current exact fixture names, classify unspecified reporting/tracing and permitted defaults, add missing combinations, and record native/Docker/PTY results for every applicable base branch. Preserve the existing UP exclusions.

## Audit baseline limitation

At allocation, the rows all cited the same selected option fixtures, without a per-clause record for invocation/set, enable/disable, reports/defaults and affected execution environments. Passing a selected effect or option parser case cannot verify a whole option family.

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

- [x] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [x] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [x] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [x] Matrix rows and reverse ownership links reflect only the verified scope;
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


## Implementation and validation record

Source/test commit: `e1091a5fd818a85ec6a7b2ddc90a54cf1fdd8c9d`.
The [clause/condition map](../shell-option-evidence.md) replaces the baseline
family-level links with exact entry/state/effect, exception and environment
assertions for all 13 owned rows. It explicitly separates report/tracing
formats, permitted h/noexec defaults, hashall extension naming and unchanged
UP exclusions. The matrix and reverse ownership links point to that map.
CSH-012 remains closed to a compliance claim while other applicable work is open.

Added 843 noninteractive option cases and three option PTY cases. The option
suite now has 1,101 cases, all also present in the full 2,299-case runtime suite.
The runtime PTY suite has 30 cases, eight concerning options. No C runtime
changes were needed. The runtime fixture generator now writes compact JSON so
long worktree helper paths fit the existing 1 MiB harness limit.

[Retained evidence](../evidence/csh-051/README.md) includes full per-case logs,
exact native/Docker suite snapshots, source fingerprints, binary hashes,
compiler/flags, OS/libc/architecture, Python, Docker/base image IDs, command
statuses and scoped capability skips. Native macOS and Linux/Docker ran
`make -j4 test test-pty test-harness`; focused ASan/UBSan runs exercise
`make -j4 test-options test-runtime-pty` natively and the same suites through
the recorded `sanitizer.py` environment adapter in Docker. Both pass all
1,101 option and 30 runtime PTY cases. The Docker pass disables leak scanning;
the initial leak-scanning run had two timeouts and was stopped, with its
partial log retained. No Linux LeakSanitizer pass is claimed. No option case is
skipped. Native/Linux source fingerprints match.

The first native runtime load failed the suite byte limit; compact serialization
fixes it without weakening the bound. One parallel Docker harness self-test
missed its 150 ms process-setup deadline; the unchanged isolated 64-test rerun
passes. Both failed attempts remain in the evidence, separate from passing
results. The two non-root invocation skips pass in the Docker root run; the
native translated-libc-message skip is scoped to CSH-042 and covered in Docker.
