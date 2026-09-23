# CSH-012: Audit POSIX conformance and portability

- Status: backlog
- Type: test
- Depends on: CSH-008, CSH-009, CSH-010, CSH-011
- Branch: Assigned when work starts

## Goal

Establish an evidence-backed account of POSIX.1-2024 behavior, supported
platforms, and remaining gaps before making a compliance claim.

## Scope

- Audit every applicable Shell Command Language and `sh` utility requirement,
  plus the required utility behavior and selected option groups.
- Complete CI coverage for supported Linux/macOS toolchains, sanitizer builds,
  behavioral suites, and available pseudo-terminal checks.
- Include the documented Docker Linux test path and native macOS checks;
  record container architecture and toolchain/libc versions with results.
- Add differential coverage using installed reference shells, recording their
  versions and distinguishing extensions from standard requirements.
- Exercise locale-sensitive behavior, large inputs, resource failures, and
  parser/expansion robustness with bounded fuzz or generated cases.
- Update user and contributor documentation from verified final behavior.

## Acceptance criteria

- [ ] Each applicable requirement links to implementation and passing evidence,
  or an explicit open ticket and limitation.
- [ ] Conditional, unspecified, and implementation-defined behavior is labeled;
  permitted implementation choices are documented.
- [ ] CI runs the documented checks from a clean checkout on supported systems.
- [ ] All discovered defects have regression coverage and resolved or linked
  tickets; waived tests include a reason and scope.
- [ ] Installation, invocation, architecture, and contribution docs are coherent
  and link to the current evidence and limitations.
- [ ] Any compliance statement names the standard edition, selected scope, and
  evidence, and is withheld while applicable requirements remain unmet.

## Validation

Run the full documented validation procedure on each supported platform and
record compiler, libc, reference-shell, and test-suite versions. Review the
requirements matrix independently against the standard, then reproduce a
sample of its linked cases from a clean checkout.

## Implementation notes/evidence

Passing a differential suite is useful evidence but does not itself prove POSIX
conformance. External certification, if desired, is separate from this ticket.
