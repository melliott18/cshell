# CSH-037: Audit integrated conformance and platform portability

- Status: backlog
- Type: test
- Kind: implementation
- Parent: CSH-012
- Depends on: CSH-008, CSH-009, CSH-010, CSH-011, CSH-036
- Branch: Assigned when work starts
- Issue: [#38](https://github.com/melliott18/cshell/issues/38)

## Goal

Review the complete shell against its requirements map and reproduce evidence on
supported platforms before publishing final behavior or compliance statements.

## Scope

- Audit integrated requirements and evidence, covering supported Linux/macOS
  toolchains, Docker architecture/libc, sanitizers, and applicable PTY cases.
- Exercise locales, large input, resource failures, and bounded parser/expansion
  robustness cases; compare versioned reference shells against the standard.
- Reconcile installation, invocation, architecture, tests, limitations, and
  contribution docs with observed behavior and unresolved findings.

## Acceptance criteria

- [ ] Every applicable requirement links to passing implementation evidence or an
  explicit defect/limitation ticket; selected scope and permitted choices are clear.
- [ ] Clean-checkout native and Docker validation reproduces documented results,
  with compiler, libc, architecture, suite, and reference-shell versions recorded.
- [ ] CI covers supported platforms and applicable behavior; skipped/waived cases
  include a concrete reason and scope, with follow-up owners where needed.
- [ ] Discovered defects have regression coverage and resolved or linked tickets;
  independent review checks the matrix and reproduces a sample of evidence.
- [ ] User/developer docs reflect verified behavior; compliance claims remain
  withheld while applicable requirements are unmet and otherwise name the edition,
  selected profile, and evidence without implying external certification.

## Validation

Run the full documented validation procedure across supported platforms, inspect
CI from a clean checkout, and record bounded robustness/differential results.
Reproduce selected evidence independently and review the original CSH-012 criteria.

## Implementation notes/evidence

Record audit findings and exact results here. Closing the audit records its outcome;
open conformance defects remain visible. [CSH-012](CSH-012-conformance-and-portability.md)
requires its own completion review and does not imply certification.
