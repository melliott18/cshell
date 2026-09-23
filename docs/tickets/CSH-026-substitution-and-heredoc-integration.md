# CSH-026: Integrate substitutions and context-sensitive expansion

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-005, CSH-006, CSH-007, CSH-025
- Branch: Assigned when work starts
- Issue: [#27](https://github.com/melliott18/cshell/issues/27)

## Goal

Connect the expansion modules to execution, including command substitution and
here-document bodies, with observable output, status, and cleanup behavior.

## Scope

- Execute command substitutions through the parser/executor, capture output,
  remove the required trailing newlines, and propagate substitution status.
- Integrate command arguments, assignment values, redirection operands, pattern
  operands, and here-document-specific expansion through explicit contexts.
- Coordinate nested input, here-document collection, descriptors, and child
  ownership with the parser and executor; enforce expansion error behavior.

## Acceptance criteria

- [ ] Nested and large-output substitutions finish within bounded tests, preserve
  required bytes, remove trailing newlines, and expose the specified status.
- [ ] Substitution state changes remain isolated from the calling environment.
- [ ] Quoted here-document delimiters suppress expansion; unquoted delimiters
  select the body-specific rules, including backslashes and embedded substitutions.
- [ ] Argument, assignment, redirection, and pattern fixtures demonstrate the
  complete context-specific expansion sequence and empty-field behavior.
- [ ] Expansion failures prevent affected command execution, follow required
  interactive/script error behavior, and leave no children or descriptors behind.

## Validation

Run bounded native and Docker integration suites using an argument-inspection
fixture, temporary files, nested substitutions, and failing redirection/expansion
cases. Record stdout, stderr, status, state effects, and sanitizer results.

## Implementation notes/evidence

Record integration evidence here, including remaining gaps. Review every original
[CSH-008](CSH-008-word-expansion.md) criterion before completing that milestone;
passing substitution examples alone is insufficient.
