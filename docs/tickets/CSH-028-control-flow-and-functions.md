# CSH-028: Execute control flow and shell functions

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-009
- Depends on: CSH-027, CSH-006, CSH-007, CSH-008
- Branch: Assigned when work starts
- Issue: [#29](https://github.com/melliott18/cshell/issues/29)

## Goal

Execute compound-command AST nodes and reusable functions with correct control
transfer, variable/parameter lifetimes, redirections, and exit statuses.

## Scope

- Execute conditionals, loops, case selection, and function definitions/calls.
- Implement `break`, `continue`, and `return` as explicit control-transfer results,
  including operand validation and invalid-context behavior.
- Integrate function lookup/redefinition, positional-parameter restoration,
  compound redirections, and subshell isolation with existing module interfaces.

## Acceptance criteria

- [ ] Nested compounds, zero-iteration loops, and case patterns execute with
  specified expansion behavior, command order, and resulting status.
- [ ] Loop/function control handles operands and nesting levels without escaping
  unrelated execution contexts; invalid uses have tested diagnostics and statuses.
- [ ] Function calls restore caller positional parameters and release replaced
  definitions while preserving the required function/variable environment.
- [ ] Function and compound redirections have the required lifetime; subshell
  state changes do not escape to the parent shell.
- [ ] Syntax/runtime/expansion failures unwind AST, state, and descriptor resources.

## Validation

Run native and Docker scripts combining functions, loops, lists, substitutions,
and pipelines; assert output, status, parameter restoration, and filesystem
effects. Cover failed redirections and resource cleanup with sanitizer builds.

## Implementation notes/evidence

Record results and review every original [CSH-009](CSH-009-compounds-and-functions.md)
criterion before completing the milestone. CSH-031 and CSH-032 subsequently test
evaluation builtins and options against these control-transfer semantics.
