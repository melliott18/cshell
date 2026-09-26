# CSH-047: Close expansion, parameter and locale evidence gaps

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: `test/CSH-047-expansion-evidence`
- Issue: [#79](https://github.com/melliott18/cshell/issues/79)

## Goal

Integrated in [PR #96](https://github.com/melliott18/cshell/pull/96).
Combined revision `5fc4657` passed native Linux, macOS, and Docker CI in
[run 36254005069](https://github.com/melliott18/cshell/actions/runs/36254005069).
Local integration passed 3,045 runtime cases, terminal suites and 65 harness
self-tests; this does not extend the scoped conformance claims below.

Map existing exact case names to source clauses and input modes, classify selected parsing/numeric/encoding policies, add remaining scoped runtime cases, and retain unavailable locale configurations as reasoned skips with CSH-042 ownership. Record native/Docker execution identities and outcomes without promoting a family from selected witnesses.

## Explicit current limitation

The [clause/condition map](../expansion-evidence.md) now links all 13 families
with exact runtime/API assertions and classified policies. It adds 118 runtime
scenarios (354 input-mode cases) while retaining narrower limits: non-C pattern
breadth, permission/error permutations, expansion nesting and cross-feature
interactions. CSH-042 owns unavailable locale capabilities and CSH-053 the
concrete multibyte lexical defect. No broad family is promoted to verified.

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


## Implementation result

Added `tests/expansion_cases.py`, generated `build/tests/expansion.json` and
`make test-expansion`; all new cases also run through the normal runtime suite,
Docker and existing CI sanitizer jobs. The parameter table tests all eight
operators across unset/null/value states with present/omitted words and checks
both resulting fields and stored values. Other cases cover lazy effects,
positional and subshell parameters, tilde protection, expansion order, required
arithmetic operators and signed-long boundaries, IFS provenance, patterns,
quote removal and declaration-utility recognition policies.

The existing substitution lifecycle/fault wrapper now requires empty stderr in
addition to exact stdout/status. Locale capability skips explicitly name
CSH-042. No runtime implementation change was needed for the scoped new cases.
The matrix, choice register, reverse-owner links and documentation navigation
now point to the clause partitions and retain the closed CSH-012 gate.

## Validation record

Source/suite revision: `2153c39` (based on `daa1be1`). Normal runs preceded the
source commit using identical source/test bytes; later changes record evidence
and do not change the tested implementation. Makefile/src/include/tests SHA-256:
`05419e13b400797a3942eb4575e64c90ff915825a6284f564e721f951fd16266`.

[Machine-readable identities](../evidence/csh-047/validation.json) record the
complete source manifest, binary/suite hashes, compiler flags, OS/libc/CPU,
Python, helper hashes, long width and host login data. [Logs and reproduction
commands](../evidence/csh-047/README.md) retain exact case outcomes and the
Docker base/image identities. Collection dates are UTC 2026-09-26 and do not
purport to be exact run-start timestamps.

| Environment / command | Result |
| --- | --- |
| Native macOS 14.8.7 build 23J520, Darwin 23.6.0 arm64, Apple Clang 15.0.0, Python 3.12.2; `make -j4 test test-pty test-harness` | Pass: 1,810 public runtime cases including all 354 new cases; all module/fault suites; 110 final-field checks; 15 job and 27 runtime PTY cases; 64 harness self-tests. Locale/portability: 162 passed, one catalog capability skip. Invocation: 49 passed, two Linux-root identity skips. |
| Debian bookworm, Linux 6.4.16-linuxkit aarch64, GCC 12.2.0, glibc 2.36-9+deb12u14, Python 3.11.2; `docker run --rm --init ... cshell-test:csh-047 make -j2 test test-pty test-harness test-expansion` | Pass: same full runtime/module/PTY/harness assertions plus focused 354 expansion cases. Locale/portability: 174 passed, zero skips. Invocation: 49 passed, two Linux-root identity skips. |
| Native ASan/UBSan clean build; `make -j4 test-expand test-substitution test-expansion test-portability` | Pass: 354 expansion cases, 110 final-field checks, value/arithmetic/quote/fault and substitution ownership/fault contracts; 162 locale/portability passes and the same one catalog skip. No sanitizer diagnostics. |
| Docker ASan/UBSan clean build; same focused targets at `-j2` | Two existing cases timed out at the unchanged five-second deadline: `nested arithmetic depth 1 (string)` and F `adjacent expansion punctuation`. Portability: 173 passed/one failed; fields: 109 passed/one failed. No sanitizer diagnostic. Make did not start expansion recipes, substitution or the new runtime suite after prerequisite failures. |
| Docker ASan/UBSan serial retry; same focused targets and flags | Pass: 354 expansion cases, 110 final-field checks, value/arithmetic/quote/fault and substitution ownership/fault contracts; 174 locale/portability cases, zero skips. No sanitizer diagnostics. Rebuilt binary SHA-256 matches the initial sanitizer binary. |

The native catalog skip reports that installed candidate locales have no
translated ENOENT message and cshell has no internal message catalogs; owner
CSH-042. Docker executes the translated-libc branch. Both platforms execute
UTF-8 character/IFS/removal and distinct non-C collation probes. The two
ordinary-run invocation skips require Linux root setresuid/setresgid and remain
CSH-046; they do not affect the new expansion scope. No PTY capability skip.

Normal and sanitizer flags, exact commands, and descriptor-helper instrumentation
policy are retained with the run artifacts. Python warning-as-error compilation
and `git diff --check` pass. No new reference-shell comparison supplied the
runtime oracle. This record does not claim an ILP32 build, a native Linux host
outside Docker, other encodings, arbitrary nesting or the unexecuted combinations
listed in the clause map.

The initial Docker sanitizer failure is retained, not replaced by a successful
normal run. Concurrent test containers were present; CPU contention is a
plausible explanation for the two timeouts, not a proven root cause. The serial
retry keeps the same source, flags, five-second deadlines and exact assertions.
