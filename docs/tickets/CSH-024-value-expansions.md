# CSH-024: Implement value expansions with quote provenance

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-004, CSH-022
- Branch: Assigned when work starts
- Issue: [#25](https://github.com/melliott18/cshell/issues/25)

## Goal

Expand tilde, parameter, and arithmetic expressions while retaining the quoting
and context information needed by later expansion stages.

## Scope

- Define expansion inputs, outputs, errors, and ownership using structured words
  and the shell-state API; distinguish argument, assignment, and pattern contexts.
- Implement parameter operators, positional parameters, and quoted `$@`/`$*`,
  including empty-field provenance; implement tilde and arithmetic expansion.
- Expose explicit deferred substitution inputs for CSH-026. Field splitting,
  pathname expansion, and final quote removal belong to CSH-025.

## Acceptance criteria

- [ ] Parameter default, alternate, assignment, error, length, and pattern-removal
  forms produce specified values and state changes in controlled fixtures.
- [ ] Quoted and unquoted values retain distinguishable provenance, including
  empty values and positional parameters, across the public expansion interface.
- [ ] Tilde expansion obeys its supported syntactic contexts and variable state.
- [ ] Arithmetic follows the selected POSIX integer model and rejects invalid
  expressions without undefined C behavior or partial resource leaks.
- [ ] Expansion errors release owned values and can be propagated to execution.

## Validation

Run module fixtures for unset versus empty variables, nested operators, positional
parameters, and arithmetic boundaries under sanitizers. Compare selected cases
against the POSIX requirements; record context and expected structured output.

## Implementation notes/evidence

Record API and validation evidence here. This module can land before full command
execution integration; CSH-026 must verify the results in executed scripts before
[CSH-008](CSH-008-word-expansion.md) is complete.
