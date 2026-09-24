# CSH-009: Add compound commands and shell functions

- Status: backlog
- Type: feat
- Kind: milestone
- Parent: None
- Depends on: CSH-005, CSH-006, CSH-008
- Children: CSH-027, CSH-028
- Branch: Assigned when work starts
- Issue: [#10](https://github.com/melliott18/cshell/issues/10)

## Goal

Support structured POSIX shell programs with conditionals, loops, pattern
selection, and reusable functions.

## Scope

- Extend parsing and execution for `if`, `for`, `while`, `until`, `case`, and
  function definitions using context-sensitive reserved words.
- Define function lookup, invocation, positional-parameter restoration, and
  function-definition lifetime.
- Implement control transfer for `break`, `continue`, and `return` through
  explicit execution results rather than terminating unrelated contexts.
- Apply redirections and exit-status rules to compound commands and functions.

## Acceptance criteria

- [ ] Nested conditionals, loops, and case patterns follow POSIX grammar and
  expansion rules.
- [ ] Loop control handles operands, nesting levels, and invalid contexts.
- [ ] Function calls establish and restore positional parameters.
- [ ] Function and compound-command redirections have the required lifetime.
- [ ] Subshell state changes do not escape into the parent shell.
- [ ] Syntax and runtime errors unwind AST, expansion, and redirection resources.

## Validation

Run small scripts that combine loops, functions, lists, and pipelines, with
observable status and output assertions. Cover zero loop iterations, nested
control transfer, function redefinition, failed redirections, and malformed
compound syntax.

## Completion gate

- [x] [CSH-027: Compound syntax](CSH-027-compound-syntax.md) is done.
- [ ] [CSH-028: Control flow and functions](CSH-028-control-flow-and-functions.md) is done.
- [ ] The original acceptance criteria above pass together, with recorded
  cross-feature evidence and all completion prerequisites satisfied.

Child dependencies control when each work item can start. The parent
dependencies are completion prerequisites; they are not inherited start gates.
Completing one child does not establish the milestone or POSIX compliance.

## Implementation notes/evidence

CSH-010 completes the required builtin inventory and options; control-flow
builtins are implemented here because their semantics depend on this executor.
