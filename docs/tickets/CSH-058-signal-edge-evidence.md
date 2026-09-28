# CSH-058: Complete signal inheritance and permission evidence

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-035
- Branch: test/CSH-058-signal-edge-evidence
- Issue: [#100](https://github.com/melliott18/cshell/issues/100)

## Goal

Own remaining signal edge conditions after [CSH-054](CSH-054-signal-contract-gaps.md):
[SIG-001](../posix-matrix.md#sig-001), [SIG-002](../posix-matrix.md#sig-002),
[SIG-003](../posix-matrix.md#sig-003), [U-015](../posix-utilities.md#u-015), and
[U-026](../posix-utilities.md#u-026), and [U-032](../posix-utilities.md#u-032).
The CSH-054 assertion map records implemented
subsets; this ticket is not evidence that every remaining condition is defective.

## Scope and acceptance criteria

- [x] Complete the inherited/overridden disposition cross-product for interactive
  and noninteractive INT, HUP, CHLD, QUIT, TERM and terminal-stop signals,
  including reset after an ignored action inside each forked environment.
- [x] Assert actual process dispositions and delivery in pipeline, background,
  and general substitution shapes beyond CSH-054's trap-table/default listing
  witnesses; retain the standalone-trap substitution exception separately.
- [x] Extend selected/no-operand trapped waits to the uninstrumented executable
  with a deterministic blocked-wait observation on each host. CSH-054's six
  tests use an explicitly labeled test-only sigsuspend boundary interposition;
  they are not proof that every public-runtime scheduling shape was exercised.
- [x] Check trap output failure for all-condition/plain/selected listing,
  continued operand processing after uninstallable host conditions, and host
  conditions beyond the current supported numeric range if exposed.
- [x] Deliver signals to isolated zero and negative process groups and assert
  each member, beyond CSH-054's signal-zero existence/permission probes.
- [x] Exercise kill permission errors with deliberately provisioned identities
  or controlled syscall interposition. Never signal arbitrary system processes.
- [x] Update exact assertions, platform evidence and forward/reverse links.

## Validation

Run native macOS, Linux Docker, sanitizers, focused jobs/trap and full suites.
Keep host external utility defects with [CSH-056](CSH-056-host-contract-gaps.md)
(the successor to CSH-052's residual inventory). Numeric trap conditions and
legacy `kill -SIGNAL` remain explicitly labeled extensions; full UP/XSI are
unselected. Capability skips leave these obligations open.


## Implementation and validation record

Review: [PR #108](https://github.com/melliott18/cshell/pull/108).

Production/test commit `74bcc04` adds the full disposition/delivery matrix and
fixes four defects reproduced on macOS and Linux: inherited ignored trap reset
baselines, ignored CHLD child collection in substitutions, monitored background
INT/QUIT inheritance, and terminal restoration with a caught TTOU action.
`0dbf8d6` removes a helper alarm from the public runtime's initial state, forwards
explicit sanitizer options, and budgets CI for the expanded matrix.

The [exact assertion map](../jobs-signals-evidence.md#csh-058) links SIG-001/002/003
and U-015/026/032 in both directions. [Retained evidence](../evidence/csh-058/README.md)
includes four failing-before probes on both hosts, source/binary identities,
full native/Docker passes (3,113 runtime cases and 71 harness tests), final
2,464 macOS / 2,495 Linux edge cases, and passing ASan/UBSan records on
both platforms. Native sanitizer jobs/control/PTY and legacy trap checks also
pass. The map separates
API handler queries from exec delivery, monitored/unmonitored backgrounds,
standalone-trap listing, public wait observation, real group delivery and
controlled EPERM interposition. Numeric conditions remain extensions; KILL/STOP
installation remains only a robustness assertion outside POSIX guarantees.

Initial loaded runs and the leak-enabled Docker fixture alarm failure remain
recorded failures. Final ASan/UBSan runs use the scoped settings described in
the evidence record; no Linux LeakSanitizer result is claimed. Existing host
utility gaps and invocation/locale capability skips retain their owners.
These scoped passes do not promote whole requirement families to verified.
