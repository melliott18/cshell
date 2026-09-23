# CSH-024: Implement value expansions with quote provenance

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-004, CSH-022
- Branch: feature/value-expansions
- Issue: [#25](https://github.com/melliott18/cshell/issues/25)

## Goal

Expand tilde, parameter, and arithmetic expressions while retaining the quoting
and context information needed by later expansion stages.

## Scope

- Define expansion inputs, outputs, errors, and ownership using structured words
  and the shell-state API; distinguish argument, assignment, and pattern contexts.
- Decode the lexer's preserved dollar-single-quote escapes before word expansion,
  retaining quoted empty values and recording Issue 8 locale/unspecified choices.
- Implement parameter operators, positional parameters, and quoted `$@`/`$*`,
  including empty-field provenance; implement tilde and arithmetic expansion.
- Coordinate arithmetic grammar with CSH-005 for the Issue 8 arithmetic-first
  `$((` ambiguity and command-substitution fallback; CSH-004 only tracks the
  initial arithmetic context and delimiters.
- Expose explicit deferred substitution inputs for CSH-026. Field splitting,
  pathname expansion, and final quote removal belong to CSH-025.

## Acceptance criteria

- [x] Parameter default, alternate, assignment, error, length, and pattern-removal
  forms produce specified values and state changes in controlled fixtures.
- [x] Quoted and unquoted values retain distinguishable provenance, including
  empty values and positional parameters, across the public expansion interface.
- [x] Dollar-single-quote decoding follows Issue 8 before expansion, including
  embedded NUL handling and continued adjacent fragments.
- [x] Tilde expansion obeys its supported syntactic contexts and variable state.
- [x] Arithmetic follows the selected POSIX integer model and rejects invalid
  expressions without undefined C behavior or partial resource leaks.
- [x] Expansion errors release owned values and can be propagated to execution.

## Validation

Run module fixtures for unset versus empty variables, nested operators, positional
parameters, and arithmetic boundaries under sanitizers. Compare selected cases
against the POSIX requirements; record context and expected structured output.

## Implementation notes/evidence

Record API and validation evidence here. This module can land before full command
execution integration; CSH-026 must verify the results in executed scripts before
[CSH-008](CSH-008-word-expansion.md) is complete.


### Implemented contract

`include/cshell/expand.h` and `src/expand.c` consume lexer WORD fragments and
shell state, returning owned fields/spans with quote, origin, splitting, and
empty-value provenance. Argument, assignment-value, and pattern contexts are
explicit. Parameter operators expand selected operands lazily, preserve
null/unset distinctions, expose special and positional values, and honor
readonly/nounset/allexport state. Failed expansion releases output and restores
the word's full shell-state checkpoint without changing status or printing.

`include/cshell/quote.h` and `src/quote.c` provide a reusable Issue 8 decoder,
also coordinated with the concurrent CSH-005 parser for here-document delimiter
quote removal. Decoding precedes value expansion; a decoded NUL discards only
the rest of its region, preserving adjacent fragments. The
[value-expansion documentation](../value-expansions.md) records escape, locale,
unknown-home/login, scalar positional-context, and other unspecified choices.

`include/cshell/arithmetic.h` and `src/arithmetic.c` implement checked signed-long
arithmetic, assignments, short circuit evaluation, rollback, and a grammar-only
probe. The probe was coordinated with CSH-005: lexer checkpoint/replay and
command-parser fallback remain a documented joint CSH-005/CSH-026 integration
step. The pre-existing ambiguous `$((echo hi); )` limitation is explicit; the
module does not claim complete fallback handling. Recursion limits return
errors. Field splitting and pathname expansion remain CSH-025, command capture
and execution integration remain CSH-026, and the public executable cutover
remains CSH-039. This review does not complete the CSH-008 milestone.

### Validation evidence (2026-09-23)

Environment: macOS/Darwin arm64, Apple Clang 15.0.0, GNU Make 3.81; Docker
Engine 24.0.6, Linux aarch64, Debian Bookworm/GCC 12.2.0, unprivileged UID 10001.

- `make -j8` and `make test test-pty test-harness` passed natively: 63 input,
  61 lexer, both state suites, five expansion-related suites, four prototype
  pipe fixtures, one prototype PTY fixture, and all 50 harness self-tests.
  The unchanged generated legacy scanner retains its macOS signedness warning.
- A clean `make test-expand CC=clang` passed with
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`,
  `LDFLAGS='-fsanitize=address,undefined'`, `ASAN_OPTIONS=halt_on_error=1`, and
  `UBSAN_OPTIONS=halt_on_error=1`. All checks remain active under `-DNDEBUG`.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-024` passed the full module and
  prototype pipe suites. `docker run --rm --init cshell-test:csh-024 make
  test-pty test-harness` passed the terminal fixture and all 50 harness checks.
- A clean Linux GCC `make test-expand` passed the same strict sanitizer flags
  with `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` and UBSan halt-on-error.
  No sanitizer/leak diagnostics appeared. The final expanded fixture was also
  rerun against the unchanged implementation on both platforms.
- `tests/expand_fixture.c` inspects bytes and provenance, special/positional
  fields, quoted empties, lazy operators, assignment side effects, contexts,
  pattern removal, selected UTF-8 boundaries, deferred/lazy callbacks, copied
  callback buffers, failure rollback, nesting limits, and malformed tokens.
- `tests/quote_fixture.c` checks standard and unspecified escape choices,
  NUL truncation, byte lengths, adjacent-region handling, and owned output.
  `tests/arithmetic_fixture.c` checks required operators, precedence, branch
  laziness, long boundaries, readonly/nounset/allexport, grammar probing, and
  state isolation, including expressions aliasing borrowed state values.
- Fault sweeps instrument expansion/decoder allocations and arithmetic/state
  allocations separately, failing each allocation in successful and error
  paths. They assert zero leaks, cleared outputs, and restored values and
  attributes. Production objects contain no fault hooks.
- Independent review found and fixed hash-parameter length ambiguity,
  assignment-context tilde leakage into operator operands, multibyte removal
  boundaries, and a malformed arithmetic-token delimiter underflow. Regression
  fixtures cover each. Selected differential probes matched `/bin/sh` in 164
  nested scalar cases and 167 of 170 broader cases; the three differences use
  the documented scalar `$@` assignment choice. Issue 8, not reference-shell
  behavior, defines expectations (including assignment-operand quote removal).
- `make test` and native sanitizer CI include the new bounded suites. Changed
  Markdown links and `git diff --check` passed; diagrams are unchanged.

The ticket remained at `review` until integration. Validation establishes the
module contracts, not complete shell or POSIX conformance.

Integrated into `main` through [pull request #51](https://github.com/melliott18/cshell/pull/51)
on 2026-09-23. Implementation commit: `9ec8bf9`; merge commit: `49df5e1`.
GitHub closed issue #25 when the pull request merged. CSH-025 and CSH-026 retain
the remaining CSH-008 milestone work.
