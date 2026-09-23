# CSH-022: Define shell variable and parameter storage

- Status: ready
- Type: feat
- Kind: implementation
- Parent: CSH-007
- Depends on: CSH-016
- Branch: Assigned when work starts
- Issue: [#23](https://github.com/melliott18/cshell/issues/23)

## Goal

Provide an owned shell-state model that the parser, executor, expansion engine,
and builtins can use without relying on the process environment as their store.

## Scope

- Import environment values into a variable store with unset/empty distinctions.
- Model export/readonly attributes and snapshot environment vectors for children.
- Store invocation operands, positional parameters, and special-parameter state.
- Define APIs for last status, background identifier, process ID, and options.
- Add copying/restoration primitives with explicit allocation and mutation rules.

## Acceptance criteria

- [ ] Unit fixtures distinguish unset and empty values through create, replace,
  lookup, and unset operations, with no ownership or allocation leaks.
- [ ] Environment snapshots include only exported variables, preserve empty
  values, and remain valid independently of later mutations to the variable store.
- [ ] Readonly mutation/unset attempts return defined errors without altering
  stored values or attributes; invalid inputs and allocation failures are tested.
- [ ] Invocation mapping preserves `$0` and positional arguments, and documented
  APIs expose `$?`, `$#`, `$!`, `$$`, and option state to future consumers.
- [ ] Copied states and save/restore operations preserve ownership and isolation,
  with sanitizer-backed unit tests that do not require the new executor.

## Validation

Run focused C unit tests natively and in Docker, including environment import,
empty values, attribute transitions, parameter replacement, snapshot lifetime,
copy isolation, and controlled allocation failures. Use ASan/UBSan for ownership
checks. End-to-end expansion and assignment behavior is validated in later work.

## Implementation notes/evidence

This ticket can run alongside lexer/parser work after CSH-016 supplies invocation
data. Export stable interfaces for CSH-019 and CSH-023 before integrating either.
Represent status/background fields now; their producers are integrated by the
invocation and executor tickets. Function call semantics remain CSH-009 work.
