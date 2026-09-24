# CSH-007: Model variables, environments, and positional parameters

- Status: backlog
- Type: feat
- Kind: milestone
- Parent: None
- Depends on: CSH-003, CSH-006
- Children: CSH-022, CSH-023
- Branch: Assigned when work starts
- Issue: [#8](https://github.com/melliott18/cshell/issues/8)

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

## Completion gate

- [x] [CSH-022: Shell state storage](CSH-022-shell-state-storage.md) is done.
- [x] [CSH-023: Assignment environments](CSH-023-assignment-environments.md) is
  done.
- [ ] The original acceptance criteria above pass at the state/execution API
  boundary, including command-category fixtures, and CSH-003 and CSH-006 are done.

CSH-022 can start after CSH-016 and run alongside language-front-end work.
CSH-023 joins the state and simple-command APIs. Full function and special-builtin
integration remains in CSH-009 and CSH-010; those consumers must preserve the
assignment rules verified here.
