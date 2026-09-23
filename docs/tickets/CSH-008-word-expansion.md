# CSH-008: Implement context-sensitive word expansion

- Status: backlog
- Type: feat
- Depends on: CSH-004, CSH-006, CSH-007
- Branch: Assigned when work starts

## Goal

Turn structured shell words into the fields and values required by POSIX for
each syntactic context.

## Scope

- Implement tilde, parameter, command, and arithmetic expansion; field splitting;
  pathname expansion; and quote removal in the required order.
- Cover parameter operators, positional parameters, and quoted `$@`/`$*`.
- Separate expansion contexts for command arguments, assignment values,
  redirection operands, pattern operands, and here-document bodies.
- Execute substitutions using the executor with defined status and resource
  ownership, including trailing-newline removal for command substitution.

## Acceptance criteria

- [ ] Quoting controls expansion and preserves required empty fields.
- [ ] `IFS` splitting handles unset, empty, whitespace, and non-whitespace values.
- [ ] Filename patterns and unmatched patterns follow the specification.
- [ ] Parameter default, alternate, assignment, error, length, and pattern-removal
  forms produce the specified results.
- [ ] Arithmetic uses the specified integer model and reports invalid expressions
  without undefined C behavior.
- [ ] Quoted here-document delimiters suppress body expansion, and unquoted
  bodies use here-document-specific expansion rules.
- [ ] Expansion failures prevent the affected command from executing and obey
  the required interactive/non-interactive error behavior.

## Validation

Use temporary directories with controlled filenames and a stable locale for
deterministic cases. Check fields with an argument-inspection fixture, including
embedded whitespace and empty values. Test nested substitutions, large output,
substitution statuses, redirection operands, and here-document expansion.

## Implementation notes/evidence

Keep expansion provenance until field splitting and quote removal are complete.
A single string-to-argv helper cannot implement every expansion context.
