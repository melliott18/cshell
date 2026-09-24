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


### CSH-024 integration handoff

Consume [the structured expansion contract](../value-expansions.md), preserving
field/span provenance through CSH-025 and resolving lazy command/backquote
callbacks from parser-owned ASTs. CSH-024 provides `csh_arith_probe()` and the
shared `csh_quote_decode()` helper. CSH-005 coordination identified that the
lexer also needs input checkpoint/replay before the probe can enable Issue 8
arithmetic-first command-substitution fallback. Track that joint parser/lexer
integration explicitly here; module arithmetic tests do not resolve the existing
`$((echo hi); )` limitation. Verify execution-level expansion errors, callback
status/isolation, and field handling before closing the CSH-008 milestone.


### CSH-025 integration handoff

Call `csh_expand_fields()` after value expansion for counted owned argument
strings, honoring explicit assignment/pattern contexts and the documented
whole-word checkpoint boundary. Do not flatten spans before field generation.
When integrating parameter-removal operators, reuse the final pattern encoder's
quote-aware POSIX bracket-subexpression handling: the older private `flatten()`
in `src/expand.c` does not protect quoted class names such as `[[:'alpha':]]`.
CSH-025's final pattern and pathname APIs have regression coverage for that
case; the existing parameter-removal consumer still needs the same protection.
