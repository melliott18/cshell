# CSH-043: Define and verify redirection offset maximum

- Status: backlog
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-037
- Branch: Assigned when work starts
- Issue: [#74](https://github.com/melliott18/cshell/issues/74)

## Goal

Resolve the implementation-defined redirection offset maximum in
[SH-009](../posix-matrix.md#sh-009) and
[O-026](../posix-utilities.md#o-026) for each supported system.

## Scope

- Determine the effective maximum for shell redirections from the open file
  description, system `off_t`, filesystem capabilities and resource limits.
  State whether cshell adds any lower limit.
- Exercise a representative success and boundary/error case on native macOS
  and Linux/Docker using sparse files and bounded resource usage.
- Keep pathname expansion's file-size independence separate from redirection
  offset handling.

## Acceptance criteria

- [ ] The user documentation names the supported maximum or its precise
  per-file determination rule and the corresponding failure behavior.
- [ ] Cross-platform fixtures verify success and failure at the documented
  boundary with exact status, diagnostics and file effects.
- [ ] The matrix links the decision, implementation and passing run records.

## Validation

Run the focused sparse-file probes, full native/Docker suites and sanitizers.
Record `off_t`, filesystem limit data, selected resource limits, and exact
platform/kernel/libc versions. Never allocate the full sparse-file length.

## Implementation notes/evidence

[CSH-037](CSH-037-portability-audit.md) demonstrates pathname generation and
append past 2 GiB on two platforms. That observation does not locate the actual
maximum or its error boundary.
