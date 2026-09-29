# CSH-069: Disposition retained unexplained validation failures

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-046, CSH-047, CSH-048, CSH-049, CSH-051, CSH-055, CSH-058
- Branch: test/CSH-069-historical-failure-dispositions
- Issue: [#138](https://github.com/melliott18/cshell/issues/138)

## Goal

Resolve the finite historical observations listed in the CSH-012 defect ledger with supported diagnoses or explicit scoped dispositions.

## Scope

- Own the review ledger H01–H11, covering retained timeouts/cleanup failures in CSH-042/043/046/047/048/049/051/053/055/057/058 that have no demonstrated causal repair.
- First distinguish duplicate observations and known repaired harness/fixture mechanisms. Do not infer a common cause merely from a timeout, concurrency, or a later passing run.
- CSH-057 retention already has a formal scoped disposition and same-ticket recurrence ownership; it is excluded. CSH-050 self-stop/partial-kill repairs are also distinct and already integrated.
- This is finite historical accounting, not a demand to prove that scheduling failures can never recur.

## Acceptance criteria

- [x] Each H entry links immutable original evidence, observed failure, source/fixture revision and applicable bounds; missing original detail is labeled unavailable.
- [x] For a diagnosed defect, link causal reproduction, fix and enforced regression; otherwise retain unknown cause with an explicit reason/scope for any accepted disposition.
- [x] Preserve failed attempts and skipped/not-run stages; no retry-to-green or unsupported load attribution.
- [x] Record recurrence ownership and update CSH-012 without suppressing current strict tests.

- [x] Triage the newly retained H11 assertion to a supported cause/fix or a
  further explicitly scoped disposition; retain recurrence ownership for H01–H11.

## Validation

Start from docs/conformance-acceptance-review.md#historical-observations. Reproduce only where needed to resolve a specific hypothesis; retain exact commands, identities and all attempts. Existing later passes remain separate positive evidence.

## Audit disposition and remaining ownership

[Per-observation dispositions](../defect-dispositions.md) accept H01–H11 only for
CSH-012 accounting. Available raw evidence, exact identities or explicit missing
details, existing strict regression paths and limits are recorded separately.
The [CSH-069 triage and before/after evidence](../evidence/csh-069/README.md)
reproduces a fixture race: the launch-time poll can legitimately reap `exit 12 &`
before the fixture's unconditional WNOWAIT observation. Forced-ordering native
and Docker attempts abort with ECHILD. The repaired fixture checks early
collection and uses a pipe gate to prove next-boundary reaping separately;
both cases are enforced by `make test-context` without changing production code.

The original H11 job did not print errno, so its precise cause remains unknown.
Its further scoped disposition accepts that historical occurrence after repairing
the demonstrated mechanism, while preserving the failed job, not-run stages and
new recurrence diagnostics. H01–H10 retain their individual unknown-cause
dispositions; no later pass or unrelated repair is assigned as their cause.

The finite triage is ready for review. After integration, reopen this same ticket
for recurrence or new causal evidence for **any H01–H11 entry**. Completion does
not promise that failures cannot recur, waive strict tests, or reopen CSH-012
unless the new finding invalidates its audit accounting.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.

### CSH-069 implementation validation

Native macOS and Docker/Linux `make -j4 test-context test-execute test-pipeline`
pass: 60 context, 61 execution and 52 pipeline behaviors plus API/fault checks.
Both normal and forced-schedule context variants run in the default test target.
Native ASan/UBSan context checks pass. The first Docker sanitizer attempt fails
at compilation due to the evidence recorder's 2 MiB file limit; tests were not
run. The corrected-recorder attempt passes ASan/UBSan with Linux leak detection
enabled. Both attempts are retained in
[all-attempt evidence](../evidence/csh-069/README.md#validation-and-all-attempts).
Exact inputs, binary identities, commands, platform/compiler and actual outcomes
are recorded there; no hosted/full-suite result is newly claimed.
