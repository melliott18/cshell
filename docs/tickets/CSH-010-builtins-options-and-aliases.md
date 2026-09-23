# CSH-010: Complete required builtins, options, and aliases

- Status: backlog
- Type: feat
- Depends on: CSH-007, CSH-008, CSH-009
- Branch: Assigned when work starts

## Goal

Complete the shell utility behavior outside the signals and job-control scope
of CSH-011, and make command categories and shell options explicit.

## Scope

- Inventory required special and regular builtins against the requirements
  matrix; implement the missing behavior, including `:`, `.`, `eval`, `exec`,
  `export`, `readonly`, `set`, `shift`, `unset`, `cd`, `pwd`, `read`, `getopts`,
  `command`, `type`, `hash`, `umask`, `alias`, and `unalias` as applicable.
- Complete non-job-control options and invocation operands, including `errexit`, `nounset`,
  `noclobber`, `noglob`, tracing, no-execution mode, and Issue 8 `pipefail`.
- Implement alias substitution at the proper token-reading stage, including
  recursion prevention and trailing-blank handling.
- Specify which utilities are internal and which depend on the host environment;
  integrate `trap` and job-related builtins with CSH-011.

## Acceptance criteria

- [ ] Every required builtin/option has an implementation and test mapping, an
  explicit profile applicability decision, or a linked CSH-011 entry for traps
  and job-control behavior. In-scope requirements are implemented and tested.
- [ ] Lookup precedence and `command` behavior follow POSIX command search rules.
- [ ] Special-builtin failures and assignment persistence follow their distinct
  interactive/non-interactive rules.
- [ ] `errexit` is tested in conditionals, pipelines, functions, and substitutions.
- [ ] Aliases respect parse timing and quoting, without unbounded recursion.
- [ ] Builtin diagnostics, operands, and statuses are documented and tested.

## Validation

Maintain table-driven behavioral cases per builtin and option, supplemented by
cross-feature scripts where interactions affect semantics. Resolve disagreements
with comparison shells against the targeted standard rather than copying a
single shell's behavior.

## Implementation notes/evidence

The inventory is an audit task, not an assumption that the list above is
exhaustive. Split large builtin families into linked tickets if needed without
dropping them from the requirements matrix.
