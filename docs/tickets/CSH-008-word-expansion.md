# CSH-008: Implement context-sensitive word expansion

- Status: done
- Type: feat
- Kind: milestone
- Parent: None
- Depends on: CSH-004, CSH-006, CSH-007
- Children: CSH-024, CSH-025, CSH-026, CSH-041
- Branch: Implemented through child ticket branches; closure recorded in
  `docs/CSH-008-close-expansion-milestone`
- Issue: [#9](https://github.com/melliott18/cshell/issues/9)

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

- [x] Quoting controls expansion and preserves required empty fields.
- [x] `IFS` splitting handles unset, empty, whitespace, and non-whitespace values.
- [x] Filename patterns and unmatched patterns follow the specification.
- [x] Parameter default, alternate, assignment, error, length, and pattern-removal
  forms produce the specified results.
- [x] Arithmetic uses the specified integer model and reports invalid expressions
  without undefined C behavior.
- [x] Quoted here-document delimiters suppress body expansion, and unquoted
  bodies use here-document-specific expansion rules.
- [x] Expansion failures prevent the affected command from executing and obey
  the required interactive/non-interactive error behavior.

## Validation

Use temporary directories with controlled filenames and a stable locale for
deterministic cases. Check fields with an argument-inspection fixture, including
embedded whitespace and empty values. Test nested substitutions, large output,
substitution statuses, redirection operands, and here-document expansion.

## Completion gate

- [x] [CSH-024: Value expansions](CSH-024-value-expansions.md) is done.
- [x] [CSH-025: Field and pathname expansion](CSH-025-field-and-pathname-expansion.md) is done.
- [x] [CSH-026: Substitution and here-document integration](CSH-026-substitution-and-heredoc-integration.md) is done.
- [x] [CSH-041: Arithmetic-first replay](CSH-041-arithmetic-substitution-replay.md) resolves the recorded lexer/parser ambiguity.
- [x] The original acceptance criteria above pass together, with recorded
  cross-feature evidence and all completion prerequisites satisfied.

Child dependencies control when each work item can start. The parent
dependencies are completion prerequisites; they are not inherited start gates.
Completing one child does not establish the milestone or POSIX compliance.

## Implementation notes/evidence

Keep expansion provenance until field splitting and quote removal are complete.
A single string-to-argv helper cannot implement every expansion context.

CSH-026 integrates the value and field APIs with execution. CSH-041 resolves
the arithmetic-first ambiguity and is integrated into `main`. Case/function
consumers and full option/signal semantics retain their own tickets; the
integrated tests describe the supported execution contexts.


### Milestone completion evidence (2026-09-24)

All four child tickets and prerequisites CSH-004, CSH-006, and CSH-007 are
`done`; their GitHub issues are closed. CSH-026 integrated through
[pull request #65](https://github.com/melliott18/cshell/pull/65) (`227b408`),
and CSH-041 through
[pull request #67](https://github.com/melliott18/cshell/pull/67) (`4298188`).
The GitHub parent issue retains all four native sub-issue relationships.

| Original acceptance criterion | Completion evidence |
| --- | --- |
| Quoting and empty fields | Value/field fixtures preserve quote provenance and protected empties; integrated argument-inspection cases cover parameters, substitutions, adjacent spans, and empty quoted `$@`. |
| IFS variants | All 110 final-field checks pass, including unset, empty, whitespace, and non-whitespace IFS; runtime fixtures combine splitting with pathname generation. |
| Filename patterns | Controlled-directory fixtures cover sorted matches, unmatched patterns, quoted metacharacters, and restricted scalar contexts. |
| Parameter operators | Value fixtures cover default, alternate, assignment, error, length, and removal forms; runtime cases verify lazy substitutions, state effects, and quote-aware removal patterns. |
| Arithmetic | Checked signed-long evaluation and invalid-expression checks pass; CSH-041 adds arithmetic-first replay, evaluation-error precedence, and exactly-once substitution evidence. |
| Here-documents | Integrated cases cover quoted and partially quoted delimiters, literal quotes, body backslashes, tab stripping, continuations, ordering, and nested substitutions. |
| Expansion failures | Cross-mode cases prevent dispatch and stop noninteractive execution; terminal cases recover at the next complete command; ownership and fault checks verify child/descriptor cleanup. |

Closure validation against `main` at `2d272e8` on macOS arm64:
`make -j4 test-expand test-substitution test-runtime test-runtime-pty` passed
all selected value/arithmetic/quote and allocation-failure suites, 110 final-field
checks, substitution ownership/fault checks, 471 public runtime cases across
command strings, script files, and stdin, and 10 runtime terminal cases.
The child tickets retain full native/Linux/Docker and ASan/UBSan evidence.
This documentation-only closure adds no runtime changes.

The original acceptance and completion gates are satisfied for the implemented
execution contexts. Full POSIX conformance, locale startup, case/function
consumers, remaining shell options, and signal semantics retain their existing
owners and audit requirements.
