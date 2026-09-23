# CSH-009: Add compound commands and shell functions

- Status: backlog
- Type: feat
- Depends on: CSH-005, CSH-006, CSH-008
- Branch: Assigned when work starts

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

## Implementation notes/evidence

CSH-010 completes the required builtin inventory and options; control-flow
builtins are implemented here because their semantics depend on this executor.
