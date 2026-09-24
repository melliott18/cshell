# CSH-041: Resolve arithmetic-first command-substitution ambiguity

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-005, CSH-024
- Branch: `fix/CSH-041-arithmetic-substitution-replay`
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

- [x] `$((echo hi); )` parses as command substitution and prints `hi`, just as
  the currently supported `$( (echo hi); )` form does.
- [x] Valid arithmetic has precedence; grammar-valid evaluation errors such as
  division by zero remain arithmetic errors rather than command execution.
- [x] Nested substitutions, quotes, physical continuations, aliases and
  here-documents survive replay without duplicate execution or input reads.
- [x] EOF, malformed candidates, nesting limits and allocation failures release
  every speculative token, source snapshot and AST with accurate diagnostics.

## Validation

Run bounded lexer/parser fault suites and public `-c`, file and stdin cases on
native macOS and Linux/Docker, including ASan/UBSan. Inspect stdout, stderr,
status and files proving speculative parsing never executes substitutions.

### Validation record

Validated on macOS arm64 (Apple Clang 15) and Linux in the repository's
Debian bookworm Docker image, using the isolated ticket worktree.

| Environment | Command | Result |
| --- | --- | --- |
| Native macOS | `make -j4 test` | Pass: 71 lexer checks, 238 parser checks, all module/fault suites, and 471 public runtime cases across `-c`, file, and stdin. |
| Native macOS | `make test-pty` | Pass: job-control, injected job faults, and public runtime terminal suites. |
| Linux/Docker | `make docker-test DOCKER_IMAGE=cshell-test:csh-041` | Pass: all module/fault suites and 471 public runtime cases. |
| Native macOS ASan/UBSan | Clean build with `make -j4 test test-pty` and flags below | Pass, including both bounded allocation-failure sweeps; no sanitizer diagnostics. |
| Linux/Docker ASan/UBSan | Clean container build with `make -j4 test test-pty` and flags below | Pass: all module/fault, terminal, and 471 public runtime cases; no sanitizer diagnostics. |
| Linux/Docker | `make test-parser` with the final parser fixtures | Pass: 238 parser checks, fault sweep, and AST ownership fixture, including rejected enclosing commands with no speculative file effects. |

Sanitizer flags: `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror
-g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'` and
`LDFLAGS='-fsanitize=address,undefined'`, with `ASAN_OPTIONS=halt_on_error=1`,
`UBSAN_OPTIONS=halt_on_error=1`, and `MallocNanoZone=0` on macOS. Docker uses
`docker run --rm --init` and rebuilds all binaries with its own compiler.
The final native worktree is rebuilt with ordinary `make -j4` flags.

## Implementation notes/evidence

The lexer owns one source checkpoint per ambiguous opener: a copy of its
remaining source tape and alias stack, plus suspended word capture positions.
Physical feeds append to every live checkpoint; speculative aliases do not.
`csh_arith_probe()` sees opaque operands for nested expansions, including
concatenated operand spelling. A valid candidate commits to arithmetic;
invalid grammar restores the source and requests the existing command-parser
handshake. EOF in a still-possible candidate remains an incomplete-input error.
A grammar-prefix probe distinguishes that case from invalid arithmetic text
containing an unfinished here-document operand.

`CSH_LEX_REPLAY` identifies the first invalidated fragment. The parser destroys
speculative substitution ASTs from that point, preserving earlier substitutions
and outer here-document queues. Nested parser syntax errors unwind before replay;
allocation and nesting failures never retry. The checkpoint depth is limited to
128 across command frames. Expansion validation also accepts continuation
fragments inside the command-substitution opener.

Coverage includes full/line/byte feeds, continuation-split openers, quotes,
nested arithmetic and command substitutions, alias insertion and source
boundaries, recursive alias suppression, here-document queues and raw bodies,
EOF, syntax/resource failures, source diagnostics, and descriptor read boundaries.
Cross-mode runtime cases assert stdout, stderr, status, and files proving that
substitutions execute exactly once and speculative arithmetic assignments do
not change parent state. The signed-long evaluator and normal capture APIs are
retained.

The [CSH-008 milestone](CSH-008-word-expansion.md) remains open pending integration
and its original completion gates. Runtime aliases, full shell options, traps,
and control-flow execution remain with their existing tickets; these selected
checks do not establish complete POSIX conformance.
