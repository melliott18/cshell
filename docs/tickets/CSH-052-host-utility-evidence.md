# CSH-052: Close host utility and intrinsic lookup evidence gaps

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: `test/CSH-052-host-utility-evidence`
- Issue: [#84](https://github.com/melliott18/cshell/issues/84)

## Goal

Name the exact required host integration scope, inventory paths/version identities and unavailable tools per supported image, map lookup/argv/environment/status assertions for printf/echo/test/[/true/false and other scoped helpers, and verify the documented intrinsic allocation and utility syntax exceptions. Distinguish external utility responsibility from shell dispatch; retain missing tools as explicit image limitations.

## Audit baseline limitation

Internal/host allocation is documented but U-035 through U-041 still have only planned fixture/allocation entries. Availability of a small host utility sample is not utility semantic or integration coverage, the Docker image lacks ed, and the actual intrinsic-set/no-extra-intrinsics choice is not connected to case-level results.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [U-026](../posix-utilities.md#u-026) | External host kill provisioning and status-to-signal mapping; CSH-050 reproduced a Debian procps `-l 143` failure. Internal/job-aware kill remains CSH-054. |
| [U-034](../posix-utilities.md#u-034) | Other standard utilities (for example cat, env, find, ls, stty, ed): retain exec accessibility and declare fixture dependencies. CSH-029 finalizes allocation; CSH-037 checks platform packages/executables. No claim to reimplement their full contracts. |
| [U-035](../posix-utilities.md#u-035) | `printf`: formatted output, format reuse/missing operands, escapes, numeric conversions and errors. Record whether a fixture invokes host printf or a builtin; selected host behavior is fixture infrastructure, not shell expansion evidence. |
| [U-036](../posix-utilities.md#u-036) | `echo`: ordinary arguments/newline and literal `--`; backslashes and leading combinations of e/E/n after `-` require a documented base choice or XSI rules. CSH-029 allocates implementation; avoid using ambiguous echo as an oracle. |
| [U-037](../posix-utilities.md#u-037) | `test` and `[`: expression primaries/argument-count evaluation, closing `]`, status 0/1/>1 and argument boundaries; distinguish unspecified expression forms. |
| [U-038](../posix-utilities.md#u-038) | `true`: no output and successful status; identify resolved executable/builtin when used in control-flow tests. |
| [U-039](../posix-utilities.md#u-039) | `false`: no output and non-zero status; do not assume a particular non-zero value from the standard. |
| [U-040](../posix-utilities.md#u-040) | Utility defaults: invalid-option/missing-argument diagnostics and status, operand order, eight-bit-transparent arguments/input, unused stdin, seekable input offsets, documented resource limits and environment effects. Apply special-builtin, echo and test exceptions instead of a universal `--` rule. |
| [U-041](../posix-utilities.md#u-041) | Verify intrinsic commands bypass PATH lookup and remain distinct from special builtins/functions. CSH-029 documents the exact intrinsic set; resolve any additional-name proposal as an explicit implementation choice and extension, with lookup fixtures. |

Relevant documented choices: U-036 (echo implementation-defined cases), U-041 (no additional intrinsics). Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/evaluation_cases.py](../../tests/evaluation_cases.py)
- [src/execute.c](../../src/execute.c)
- [src/utility.c](../../src/utility.c)
- [docs/posix-utilities.md#csh-029-allocation-decision](../posix-utilities.md#csh-029-allocation-decision)

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

### CSH-050 host kill finding

The CSH-050 Debian bookworm arm64 image supplies `/bin/kill` from procps-ng
4.0.2. `/bin/kill -l 143` returns status 0 but no stdout and writes
`/bin/kill: unknown signal name 143\n` to stderr, instead of `TERM\n`.
This failed all three invocation-mode probes. Direct signal-number mapping
(`-l 15`) and `-s TERM` delivery pass separately. macOS 14.8.7 `/bin/kill` passes
both mappings. Resolve the Linux host provision/mapping gap before claiming
complete U-026 evidence; [CSH-050](CSH-050-jobs-signals-evidence.md#validation-record)
records the exact image, binary hashes and commands.


## Validation record

Implemented on `test/CSH-052-host-utility-evidence` in a separate worktree.
The [clause map](../host-utility-evidence.md) names all scoped utilities,
conditions, policies and exact assertions. The [artifact record](../evidence/csh-052/README.md)
contains final source/binary identities, native/Docker results and sanitizer
validation. `make test-host-utilities` is integrated into `make test`; the
strict-gap mode retains normative expectations and exits unsuccessfully for
known host defects.

The evidence work is review-ready, not a whole-family verification claim.
[CSH-056](CSH-056-host-contract-gaps.md) owns Debian's missing ed, kill status
mapping and printf numbered/%b-precision gaps, macOS's missing-file timestamp
comparisons, and individually named remaining host conditions. These defects
remain explicit unmet requirements; no acceptance checkbox waives them.
The intrinsic map covers all 15 implemented names, excludes UP-only fc, and
confirms no additional intrinsic allocation. Runtime source is unchanged.
The existing concurrent native harness timeout is retained with its successful
isolated retry; no timeout or behavioral assertion was relaxed. The CSH-012
compliance gate remains closed.
