# CSH-007: Model variables, environments, and positional parameters

- Status: backlog
- Type: feat
- Depends on: CSH-003, CSH-006
- Branch: Assigned when work starts

## Goal

Give shell state an explicit data model for values, attributes, environments,
and invocation parameters.

## Scope

- Add a variable store with unset versus empty values and export/readonly
  attributes, initialized from the process environment.
- Model positional and special parameters, including `$0`, `$?`, `$#`, `$!`,
  `$$`, and shell option state.
- Apply assignment prefixes according to command category and execution context.
- Define state copying/restoration for functions, subshells, and builtins.
- Provide APIs for CSH-008 expansion and CSH-010 variable-related builtins.

## Acceptance criteria

- [ ] Unset and empty variables remain distinguishable.
- [ ] Exported values reach external commands without exporting all shell values.
- [ ] Prefix assignment lifetime matches ordinary, special-builtin, and
  assignment-only command rules.
- [ ] Readonly assignments fail with the specified diagnostic/error behavior.
- [ ] Invocation parameters and last command/background statuses are accessible
  through documented shell-state interfaces.
- [ ] State ownership and mutation boundaries are documented and tested.

## Validation

Use focused state tests and external environment-inspection commands, then add
end-to-end parameter tests when CSH-008 connects expansion. Cover variable
replacement, unsetting, empty values, readonly failures, and subshell isolation.

## Implementation notes/evidence

Do not use the process environment as the only variable store: unexported shell
variables and variable attributes require separate state.
