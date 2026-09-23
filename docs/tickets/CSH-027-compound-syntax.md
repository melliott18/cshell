# CSH-027: Parse compound commands and function definitions

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-009
- Depends on: CSH-005
- Branch: Assigned when work starts
- Issue: [#28](https://github.com/melliott18/cshell/issues/28)

## Goal

Represent structured shell programs in the AST before implementing their runtime
semantics, enabling parser work alongside execution and expansion development.

## Scope

- Extend grammar and AST nodes for `if`, `for`, `while`, `until`, `case`, and
  function definitions, including nesting and attached redirections.
- Recognize reserved words only in their grammatical contexts; preserve structured
  words and source positions for subsequent expansion and diagnostics.
- Add parser fixtures only; CSH-028 owns control flow and function execution.

## Acceptance criteria

- [ ] Valid nested compound programs and function definitions produce expected
  AST shapes, preserving ordered commands, words, and redirections.
- [ ] Reserved words used as ordinary arguments remain words in valid contexts.
- [ ] Malformed compounds produce location-aware diagnostics; incomplete input
  is distinguished from a terminal syntax error where the input API requires it.
- [ ] Parser cleanup releases all partial AST resources after syntax or allocation
  failures, including nested function and here-document structures.

## Validation

Run table-driven AST fixtures for each grammar production, nesting, separators,
redirections, and malformed/incomplete forms under sanitizers. Fixtures must not
claim runtime support for a successfully parsed compound command.

## Implementation notes/evidence

Record grammar choices, AST ownership, and validation here. Coordinate node
contracts with CSH-028 before either implementation begins. Runtime acceptance in
[CSH-009](CSH-009-compounds-and-functions.md) remains a later integration gate.
