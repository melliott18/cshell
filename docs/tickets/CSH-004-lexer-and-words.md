# CSH-004: Preserve shell tokens and quoting

- Status: review
- Type: feat
- Kind: implementation
- Parent: None
- Depends on: CSH-016, CSH-017
- Branch: feat/CSH-004-quote-aware-lexer
- Issue: [#5](https://github.com/melliott18/cshell/issues/5)

## Goal

Replace the legacy flat argument lexer with tokens and structured words that
retain the information required by parsing and expansion.

## Scope

- Introduce a lexer module and owned token/word interfaces with source locations.
- Recognize POSIX operators, comments, escaped newlines, and word boundaries.
- Preserve unquoted, single-quoted, double-quoted, and dollar-single-quoted word
  fragments without performing field splitting or pathname expansion.
- Track nested substitution syntax and incomplete input across source reads.
- Define the lexer/parser handshake for here-document collection and alias
  replacement; implement aliases in CSH-010.

## Acceptance criteria

- [x] Adjacent quoted and unquoted fragments form one word and preserve empties.
- [x] Operators are recognized by grammar rules without requiring spaces.
- [x] Quoted operators and comment markers remain word content.
- [x] Escaping, nested substitutions, and incomplete quotes retain their context.
- [x] Tokens carry sufficient provenance for actionable syntax diagnostics.
- [x] Lexer storage has documented ownership and is released on failure.
- [x] Lexer fixtures build and run without the legacy scanner or header; the
  word/token API does not expose the prototype argument-array contract.
- [x] Long tokens, many words, repeated scans, and allocation failures have
  bounded, sanitizer-checked cleanup without truncation or stale token reuse.
- [x] Runtime integration is assigned to CSH-018 and complete legacy deletion
  to CSH-039; no adapter to the old executor is needed to complete this ticket.

## Validation

Use lexer-level fixtures for token kinds, word fragments, and source positions,
with runtime behavioral cases delivered by CSH-018. Cover long input, empty quotes, adjacent
fragments, newline continuations, nested constructs, and EOF in an open quote.
Compare behavior only where POSIX specifies the result.

## Implementation notes/evidence

Use the POSIX.1-2024 token recognition and quoting sections as the contract.
Removing quotes from raw strings at this stage would lose expansion semantics.


### Implemented contract

`include/cshell/lexer.h` and `src/lexer.c` provide independent, incremental
lexing over copied source bytes. Tokens own their raw physical spelling, source
name, positions, and a preorder fragment tree. Empty quotes, adjacent quote
modes, escaped characters, continuations, parameters, arithmetic, and backquotes
retain their provenance without expansion. POSIX operators include Issue 8
`;&` and recognize continuations inside multi-character spellings.

A root lexer owns shared source storage and nested command frames. On `$(` it
requests a parser handoff; CSH-005 chooses the grammatical closing `)` instead
of relying on parenthesis counting. Raw consumption supports ordered
here-document collection while retaining physical bytes in an enclosing
command fragment. Alias eligibility, insertion, recursion suppression, and
trailing-blank policy are defined as CSH-030 extensions. The
[API contract](../lexer-and-words.md) documents ownership, errors, source reads,
quote contexts, and these handoffs.

This module reserves `$((` for arithmetic context; arithmetic grammar and its
ambiguous command-substitution fallback need CSH-005/CSH-024 integration.
CSH-024 explicitly owns decoding preserved dollar-single-quote escapes before
expansion. Runtime integration remains CSH-018, default executable cutover and
legacy deletion remain CSH-039, and multibyte locale interpretation remains
open under ENV-004/CSH-037. No legacy adapter or conformance claim is introduced.

### Validation evidence (2026-09-23)

Native environment: Darwin 23.6.0 arm64, Apple Clang 15.0.0, GNU Make 3.81,
Python 3.12.2. Docker environment: Linux aarch64, Debian Bookworm, GCC 12.2.0,
GNU Make 4.3, Python 3.11.2, Docker Engine 24.0.6; tests run as UID 10001.

- `make clean`, `make -j8`, `make test test-harness`: 61 lexer checks,
  63 input/invocation checks, four prototype fixtures, and 23 harness self-tests
  passed. Handwritten code compiled without warnings; the unchanged generated
  legacy scanner retains its native signedness warning.
- Clean strict Clang builds of `make test-input test-lexer` used
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`
  and `LDFLAGS='-fsanitize=address,undefined'`. All input checks and lexer checks
  passed; the final lexer changes were rerun with the same sanitizer flags.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-004` passed all 61 lexer,
  63 input, and four prototype checks. The Docker image also passed
  `make test-harness` (23 checks).
- A clean GCC Linux build with the same strict ASan/UBSan flags passed all
  61 final lexer checks with `ASAN_OPTIONS=detect_leaks=0:halt_on_error=1` and
  `UBSAN_OPTIONS=halt_on_error=1`; the allocation-failure executable then passed
  separately with `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`. An earlier full
  60-case lexer suite and all 63 input checks also passed with leak detection
  enabled before the final hash-parameter context and diagnostic refinements.
  No sanitizer or leak diagnostics appeared.
- A temporary source-only snapshot containing Makefile, the lexer source,
  lexer/input type headers, and the lexer fixtures passed
  `make test-lexer LEX=false` with `-Werror`, with no legacy header, scanner,
  executor, or input implementation present.
- Fixtures compare whole-source, physical-line, and byte feeds; inspect token
  and fragment spans; and check quote contexts, empty fragments, operator
  adjacency, nested substitutions, invalid NULs, and incomplete EOF. Stress
  cases cover 200 KB words, 10,000 words, 600 parameter frames, 200 nested
  command frames, and 10,000 continued physical lines in an expansion opener.
- The allocator fixture fails every allocation in construction, buffer/fragment
  growth, token publication, and nested command frames in turn. It checks
  zero live allocations after destruction and sticky failures without stale
  output. Checks stay enabled with `-DNDEBUG`.
- Independent ownership/specification reviews included 2,014 full/byte feed
  comparisons, 700 randomized ASan/UBSan streaming comparisons, and targeted
  nesting/backquote/long-continuation cases. Changed Markdown links resolve;
  `git diff --check` passed. Existing Mermaid diagrams are unchanged.


### Integration validation

Integrated the CSH-033 controlling-terminal harness from `main` (`a7c4e8b`),
resolving shared Makefile and contributor documentation while retaining both
lexer and PTY targets. No lexer source or interface changed. A clean native
build followed by `make test test-pty test-harness` passed all 61 lexer checks,
63 input checks, four prototype pipe fixtures, one prototype PTY fixture, and
50 combined harness self-tests.
