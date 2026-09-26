# CSH-058: Complete signal inheritance and permission evidence

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-035
- Branch: Assigned when work starts
- Issue: [#100](https://github.com/melliott18/cshell/issues/100)

## Goal

Own remaining signal edge conditions after [CSH-054](CSH-054-signal-contract-gaps.md):
[SIG-001](../posix-matrix.md#sig-001), [SIG-002](../posix-matrix.md#sig-002),
[SIG-003](../posix-matrix.md#sig-003), [U-015](../posix-utilities.md#u-015), and
[U-026](../posix-utilities.md#u-026), and [U-032](../posix-utilities.md#u-032).
The CSH-054 assertion map records implemented
subsets; this ticket is not evidence that every remaining condition is defective.

## Scope and acceptance criteria

- [ ] Complete the inherited/overridden disposition cross-product for interactive
  and noninteractive INT, HUP, CHLD, QUIT, TERM and terminal-stop signals,
  including reset after an ignored action inside each forked environment.
- [ ] Assert actual process dispositions and delivery in pipeline, background,
  and general substitution shapes beyond CSH-054's trap-table/default listing
  witnesses; retain the standalone-trap substitution exception separately.
- [ ] Extend selected/no-operand trapped waits to the uninstrumented executable
  with a deterministic blocked-wait observation on each host. CSH-054's six
  tests use an explicitly labeled test-only sigsuspend boundary interposition;
  they are not proof that every public-runtime scheduling shape was exercised.
- [ ] Check trap output failure for all-condition/plain/selected listing,
  continued operand processing after uninstallable host conditions, and host
  conditions beyond the current supported numeric range if exposed.
- [ ] Deliver signals to isolated zero and negative process groups and assert
  each member, beyond CSH-054's signal-zero existence/permission probes.
- [ ] Exercise kill permission errors with deliberately provisioned identities
  or controlled syscall interposition. Never signal arbitrary system processes.
- [ ] Update exact assertions, platform evidence and forward/reverse links.

## Validation

Run native macOS, Linux Docker, sanitizers, focused jobs/trap and full suites.
Keep host external utility defects with [CSH-056](CSH-056-host-contract-gaps.md)
(the successor to CSH-052's residual inventory). Numeric trap conditions and
legacy `kill -SIGNAL` remain explicitly labeled extensions; full UP/XSI are
unselected. Capability skips leave these obligations open.
