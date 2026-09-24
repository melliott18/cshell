# CSH-041: Resolve arithmetic-first command-substitution ambiguity

- Status: ready
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-005, CSH-024
- Branch: Assigned when work starts
- Issue: [#64](https://github.com/melliott18/cshell/issues/64)

## Goal

Interpret ambiguous `$((` input according to the Issue 8 arithmetic-first rule,
including command substitutions that begin with a subshell command.

## Scope

- Add owned lexer checkpoint/replay across physical input feeds, quote contexts,
  alias sources and nested command-parser handoffs.
- Use `csh_arith_probe()` without evaluating substitutions or mutating state.
  Represent nested shell expansions as arithmetic operands during the probe.
- Replay an invalid arithmetic candidate as command substitution, discarding
  speculative fragments/ASTs while preserving source positions and here-documents.
- Cover [EXP-005/EXP-006](../posix-matrix.md#exp-005), retaining the existing
  arithmetic evaluation model and normal execution/capture APIs.

## Acceptance criteria

- [ ] `$((echo hi); )` parses as command substitution and prints `hi`, just as
  the currently supported `$( (echo hi); )` form does.
- [ ] Valid arithmetic has precedence; grammar-valid evaluation errors such as
  division by zero remain arithmetic errors rather than command execution.
- [ ] Nested substitutions, quotes, physical continuations, aliases and
  here-documents survive replay without duplicate execution or input reads.
- [ ] EOF, malformed candidates, nesting limits and allocation failures release
  every speculative token, source snapshot and AST with accurate diagnostics.

## Validation

Run bounded lexer/parser fault suites and public `-c`, file and stdin cases on
native macOS and Linux/Docker, including ASan/UBSan. Inspect stdout, stderr,
status and files proving speculative parsing never executes substitutions.

## Implementation notes/evidence

This is the explicitly recorded joint lexer/parser gap handed from CSH-024 and
CSH-005 to [CSH-026](CSH-026-substitution-and-heredoc-integration.md). CSH-026
connects value expansion and substitution execution but does not supply source
replay. The lexer still reserves `$((` for arithmetic, so the first acceptance
example currently reports `unterminated arithmetic expansion` with status 2.
The [CSH-008 milestone](CSH-008-word-expansion.md) remains open until this
follow-up and its original completion gates are satisfied.
