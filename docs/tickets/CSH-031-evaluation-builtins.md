# CSH-031: Complete evaluation, lookup, and remaining utility builtins

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-008, CSH-009, CSH-029, CSH-030
- Branch: Assigned when work starts
- Issue: [#32](https://github.com/melliott18/cshell/issues/32)

## Goal

Complete command evaluation and the remaining non-option utility inventory using
the parser, expansion, execution, and shell-state interfaces.

## Scope

- Implement `.`, `eval`, `exec`, `command`, command-search behavior, and `type`
  where selected by the profile; finish inventoried non-option utilities.
- Own `read`, `getopts`, `hash`, `umask`, and `times`, plus any unallocated required
  utility identified by CSH-029; record host utility dependencies explicitly.
- Verify state/special-builtin interactions across full scripts and integrate
  the alias handlers from CSH-030.

## Acceptance criteria

- [ ] Sourced/evaluated text executes in the required environment with correct
  input ownership, positional parameters, control transfer, and error behavior.
- [ ] `exec` and lookup utilities obey command search, descriptor, and failure
  rules, including specified special-builtin precedence and assignment lifetime.
- [ ] Every assigned utility has operand, normal, error, and status fixtures;
  `read` covers EOF/backslashes/IFS, and `getopts` covers state and option errors.
- [ ] Each applicable remaining inventory entry has implementation and passing
  evidence, or a named owning ticket for the separate options/aliases/jobs scope.
- [ ] Special-builtin failures and nested evaluation follow interactive versus
  non-interactive rules without losing shell-state or descriptor ownership.
- [ ] Dot/eval and command lookup have passing cross-feature alias fixtures;
  these checks are complete before this ticket closes.

## Validation

Run table-driven native and Docker scripts per utility plus nested dot/eval,
lookup, redirection, and assignment cases. Record expected stdout, stderr, status,
and state effects; review standard requirements when reference shells disagree.

## Implementation notes/evidence

Record evidence and newly discovered inventory items here. This ticket owns
alias/evaluation integration; CSH-032 owns the subsequent option interactions.
