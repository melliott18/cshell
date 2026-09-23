# CSH-005: Parse commands into an owned syntax tree

- Status: backlog
- Type: feat
- Depends on: CSH-004
- Branch: Assigned when work starts

## Goal

Represent command structure independently of argument expansion and execution.

## Scope

- Introduce parser and AST modules with explicit construction and destruction.
- Parse simple commands, assignment words, pipelines, `!`, sequential and
  asynchronous lists, `&&`/`||`, subshell groups, and brace groups.
- Preserve redirections in source order, including descriptor operands and
  here-document delimiter quoting.
- Collect multiple here-document bodies in source order using the lexer/input
  interface; defer body expansion to CSH-008.
- Reserve extensible nodes for the compound commands delivered by CSH-009.

## Acceptance criteria

- [ ] Precedence and associativity match the POSIX grammar.
- [ ] Assignments and redirections can be represented without a command name.
- [ ] Multiple redirections retain their source order and exact operator kind.
- [ ] Incomplete input is distinguishable from invalid syntax and clean EOF.
- [ ] Syntax errors prevent execution of the invalid construct and free its tree.
- [ ] AST ownership and parser error behavior are documented.

## Validation

Use structural fixtures for precedence, grouping, assignments, and ordered
redirections. Exercise invalid and incomplete constructs with source diagnostics.
Test quoted and unquoted here-document delimiters, `<<-`, multiple pending
documents, and premature EOF. Integrate behavioral execution tests in CSH-006.

## Implementation notes/evidence

Parsing must not execute substitutions or expand filenames. The parser must
leave room for context-sensitive reserved words and alias processing.
