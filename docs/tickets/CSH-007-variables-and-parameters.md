# CSH-007: Model variables, environments, and positional parameters

- Status: done
- Type: feat
- Kind: milestone
- Parent: None
- Depends on: CSH-003, CSH-006
- Children: CSH-022, CSH-023
- Branch: Implemented through child ticket branches; closure recorded in
  `docs/CSH-007-close-state-milestone`
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

- [x] Unset and empty variables remain distinguishable.
- [x] Exported values reach external commands without exporting all shell values.
- [x] Prefix assignment lifetime matches ordinary, special-builtin, and
  assignment-only command rules.
- [x] Readonly assignments fail with the specified diagnostic/error behavior.
- [x] Invocation parameters and last command/background statuses are accessible
  through documented shell-state interfaces.
- [x] State ownership and mutation boundaries are documented and tested.

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
- [x] The original acceptance criteria above pass at the state/execution API
  boundary, including command-category fixtures, and CSH-003 and CSH-006 are done.

CSH-022 can start after CSH-016 and run alongside language-front-end work.
CSH-023 joins the state and simple-command APIs. Full function and special-builtin
integration remains in CSH-009 and CSH-010; those consumers must preserve the
assignment rules verified here.


### Milestone completion evidence (2026-09-23)

CSH-022 and CSH-023 are integrated into `main` through
[pull request #46](https://github.com/melliott18/cshell/pull/46) and
[pull request #59](https://github.com/melliott18/cshell/pull/59). Both prerequisite
milestones, CSH-003 and CSH-006, are done, and all four GitHub issues are closed.

The storage fixtures verify unset/empty distinctions, export-only environment
snapshots, readonly errors, invocation and special-parameter storage, independent
clones, and allocation-free restoration. Assignment dispatch and external
helper fixtures verify persistent assignment-only/special-builtin prefixes,
temporary external/regular-builtin/function prefixes, exported empty values,
readonly diagnostics/status before dispatch, and nested restoration. Context
fixtures cover subshell isolation and background status ownership. The
[shell-state contract](../shell-state.md) and
[execution contract](../execution.md#assignment-categories-and-resolved-dispatch)
document the ownership and mutation boundaries.

Closure validation against `main` at `8e3fe44` on Darwin arm64 with Apple Clang
15.0.0: `make -j8 test-state test-execute test-context` passed both state suites,
73 execution behavior cases plus API/assignment/fault checks, and 60 context
behavior cases plus API/fault checks. The child tickets retain native/Docker
and sanitizer evidence; this documentation-only closure adds no runtime changes.

All original acceptance criteria are met at the state/execution API boundary.
End-to-end parameter expansion remains CSH-008 work; full function and remaining
special-builtin integration remain CSH-009/CSH-010 work as specified above.
