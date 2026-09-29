# CSH-069: Disposition retained unexplained validation failures

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-046, CSH-047, CSH-048, CSH-049, CSH-051, CSH-055, CSH-058
- Branch: Assigned when work starts
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

- [ ] Triage the newly retained H11 assertion to a supported cause/fix or a
  further explicitly scoped disposition; retain recurrence ownership for H01–H11.

## Validation

Start from docs/conformance-acceptance-review.md#historical-observations. Reproduce only where needed to resolve a specific hypothesis; retain exact commands, identities and all attempts. Existing later passes remain separate positive evidence.

## Audit disposition and remaining ownership

[Per-observation dispositions](../defect-dispositions.md) accept H01–H11 only for
CSH-012 accounting. Available raw evidence, exact identities or explicit missing
details, existing strict regression paths and limits are recorded separately.
H11 is the new Docker `context_fixture.c:136` WNOWAIT assertion at `5b56328`;
its errno and cause are unknown. Independent passing CI is not its diagnosis.

This ticket remains open for causal investigation/triage and recurrence. The
parent audit does not require those repairs before closure, but its scoped
acceptance does not disable future assertions or declare these observations fixed.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.
