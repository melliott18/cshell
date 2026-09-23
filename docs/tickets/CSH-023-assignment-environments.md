# CSH-023: Apply assignment prefixes by execution category

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-007
- Depends on: CSH-019, CSH-022
- Branch: Assigned when work starts
- Issue: [#24](https://github.com/melliott18/cshell/issues/24)

## Goal

Connect shell storage to command dispatch so assignment values, exported
environments, and restoration follow the selected command category.

## Scope

- Apply assignment-only commands and prefixes on ordinary external commands.
- Define category-aware assignment handling for builtins and function consumers.
- Enforce readonly errors before invalid mutations reach command execution.
- Integrate environment snapshots and explicit state save/restore operations.
- Document the boundary consumed by CSH-009 functions and CSH-010 builtins.

## Acceptance criteria

- [ ] Assignment-only commands persist values in shell state; ordinary external
  command prefixes reach the child environment without incorrectly persisting.
- [ ] Unit/dispatch fixtures verify ordinary and special-builtin assignment
  categories, including specified persistence and temporary-state restoration.
- [ ] Unexported shell values remain absent from external environments unless a
  command prefix supplies them; empty and overwritten values are covered.
- [ ] Readonly assignment failures produce the applicable diagnostic/status and
  execution-context behavior without partial state corruption or unintended exec.
- [ ] Save/restore and copied-state fixtures preserve values/attributes through
  success and failure, with documented handoffs for function and builtin work.

## Validation

Run native and Docker external environment-inspection fixtures and focused unit
tests for assignment categories, empty values, export attributes, readonly errors,
and nested save/restore. Use dispatch fixtures for command categories whose full
builtin/function implementation is pending; distinguish those from end-to-end
coverage. Run sanitizers on failure and restoration paths.

## Implementation notes/evidence

Use CSH-019's dispatch contract and CSH-022's storage APIs instead of adding a
second variable store. Expanded assignment values arrive through the CSH-008
adapter. Full function and special-builtin integration remains CSH-009/CSH-010;
their tests must preserve the command-category rules established at this boundary.
