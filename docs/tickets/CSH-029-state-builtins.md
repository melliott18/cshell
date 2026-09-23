# CSH-029: Implement state builtins and allocate the utility inventory

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-019, CSH-022
- Branch: Assigned when work starts
- Issue: [#30](https://github.com/melliott18/cshell/issues/30)

## Goal

Provide builtins that inspect or change shell state, and make ownership of every
required builtin explicit before the remaining utility families are implemented.

## Scope

- Inventory required utilities against the selected POSIX profile; record internal
  versus host implementations and assign every remaining requirement to a ticket.
- Implement `:`, `cd`, `pwd`, `export`, `readonly`, `unset`, `shift`, and the state
  and positional-parameter portion of `set`, plus any inventoried state family.
- Allocate evaluation/lookup and remaining non-option utilities to CSH-031,
  aliases to CSH-030, options to CSH-032, control transfer to CSH-028, and
  signals/jobs to CSH-034/035; link existing `exit` work instead of duplicating it.

## Acceptance criteria

- [ ] The inventory has an owner and evidence target for every applicable utility,
  including `read`, `getopts`, `hash`, `umask`, and `times` under CSH-031.
- [ ] State builtins apply changes in the required environment and honor temporary
  redirection lifetimes; directory tests cover logical/physical state and errors.
- [ ] Variable attributes, listing output, positional shifts, and invalid operands
  have table-driven fixtures with explicit expected state and exit status.
- [ ] Special-builtin assignment persistence and failure behavior are represented
  in the interface and tested wherever current execution support permits.

## Validation

Run direct builtin/state fixtures plus available simple-command integration tests
under native and Docker builds. Record unsupported cross-feature cases as forward
checks owned by CSH-031/032, without waiving this ticket's scoped criteria.

## Implementation notes/evidence

Record inventory and validation here. Full special-builtin error interactions and
command syntax are milestone gates in [CSH-010](CSH-010-builtins-options-and-aliases.md);
module-level state coverage alone cannot close that milestone.
