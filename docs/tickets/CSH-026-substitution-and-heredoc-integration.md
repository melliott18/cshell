# CSH-026: Integrate substitutions and context-sensitive expansion

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-005, CSH-006, CSH-007, CSH-025
- Branch: feature/CSH-026-substitution-and-heredoc-integration
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

- [x] Nested and large-output substitutions finish within bounded tests, preserve
  required bytes, remove trailing newlines, and expose the specified status.
- [x] Substitution state changes remain isolated from the calling environment.
- [x] Quoted here-document delimiters suppress expansion; unquoted delimiters
  select the body-specific rules, including backslashes and embedded substitutions.
- [x] Argument, assignment, redirection, and pattern fixtures demonstrate the
  complete context-specific expansion sequence and empty-field behavior.
- [x] Expansion failures prevent affected command execution, follow required
  interactive/script error behavior, and leave no children or descriptors behind.

## Validation

Run bounded native and Docker integration suites using an argument-inspection
fixture, temporary files, nested substitutions, and failing redirection/expansion
cases. Record stdout, stderr, status, state effects, and sanitizer results.

## Implementation notes/evidence

`src/prepare.c` replaces the literal adapter with phased value/field expansion:
arguments, ordered redirection expansion/application, then prefix assignments.
Assignment slices retain the parser's fragment identities. Declaration operands
use assignment context; later prefix values see earlier prefixes, with dispatch
retaining category-specific lifetime/export rules. Failing words restore a state
checkpoint across both expansion stages. Completed earlier words and filesystem
effects are not rolled back.

Dollar-form substitutions consume parser-owned ASTs; selected backquotes are
decoded and parsed lazily. Capture drains before waiting for the exact child,
removes all trailing newline bytes, preserves interior bytes, and rejects NUL
output. Capture allocation failures drain/discard output before reaping. Children
use isolated state/cwd, noninteractive execution and fresh child registries.
The last substitution determines an empty command's status; `$?` during word
expansion retains the previous pipeline status from the current environment.

Unquoted here-documents use dedicated lexer body mode and the ordinary nested
command parser. Quotes/operators/whitespace at body level remain literal;
quoted delimiters bypass body expansion. Skipped commands never parse/expand
their bodies. Pipeline stages expand after pipe connection in their own child.
Registered descriptor saves relocate around expanded descriptor operands and
close inherited private backups in new child contexts. Diagnostics retain owned
text and are reported once under the active redirections.

### Validation record — 2026-09-23

- Native: macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2.
- Docker: Docker 24.0.6, Debian bookworm aarch64, GCC 12.2.0, Python 3.11.2.
- `make clean` followed by `make -j8 test test-pty`: passed all module/API/fault
  suites, 429 public runtime cases and 10 controlling-terminal cases.
- `make test-harness`: all 62 harness self-tests passed on native and Linux.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-026-final`: all module/API/fault
  suites and 429 public runtime cases passed. Linux `make test-pty` passed.
- Full `make -j8 test test-pty` with the ASan/UBSan flags below passed on macOS.
  After the final status correction, `test-substitution test-runtime
  test-runtime-pty` passed again with 429 runtime and 10 terminal cases.

Sanitizer builds use a clean build, `ASAN_OPTIONS=halt_on_error=1`,
`UBSAN_OPTIONS=halt_on_error=1`, and `MallocNanoZone=0` on macOS:

```sh
make clean
make -j8 test test-pty \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

`tests/substitution_cases.py` asserts exact stdout/stderr/status and filesystem
effects through `-c`, file and stdin, including 1 MiB captures, a 512 KiB expanded
here-document, nested/backquote substitutions, lazy operands, empty fields,
scalar contexts, pattern quoting, status/isolation and error timing.
`tests/substitution_fixture.c` checks repeated captures, unrelated waitable
children, unchanged descriptor counts, all seven combinations of closed standard
descriptors, failing-word rollback, API-supplied option flags and pipeline stage
ownership. The bounded `test-substitution` runner also sweeps allocation, pipe,
fork, fcntl, read and wait failures in the execution/expansion path. Existing
parser, value, field and execution fault suites remain part of `make test`.

### CSH-008 original-criterion review

| Original criterion | Integrated evidence and remaining boundary |
| --- | --- |
| Quoting and empty fields | Runtime argument-inspection cases cover quoted/unquoted parameters, substitutions, adjacent spans and empty `$@`; value/field suites retain broader provenance checks. |
| IFS variants | CSH-025's 110 field checks cover unset, empty, whitespace and non-whitespace separators; runtime cases combine splitting with sorted pathname generation. |
| Filename/unmatched patterns | CSH-025's pathname fixtures remain in the full suite; runtime cases consume generated fields and keep scalar contexts unsplit/unglobbed. Locale startup remains separate work. |
| Parameter operators | Value fixtures cover default/alternate/assignment/error/length/removal; runtime fixtures prove lazy execution, state mutation/rollback and shared quote-aware removal patterns. |
| Arithmetic model/errors | Checked signed-long arithmetic and fault tests remain passing; runtime invalid-expression tests prevent dispatch. Arithmetic-first source replay remains CSH-041. |
| Here-document rules | Runtime fixtures cover quoted/partially quoted/dollar-quoted delimiters, body backslashes, literal quotes, tab stripping, continuations, ordering and nested substitutions. |
| Expansion error consequences | Script cases stop before dispatch; PTY cases recover at the next complete command; API/fault fixtures verify child/descriptor cleanup and nounset behavior. |

The [CSH-008 milestone](CSH-008-word-expansion.md) remains open. The inherited
arithmetic-first ambiguity now has an explicit ready child,
[CSH-041](CSH-041-arithmetic-substitution-replay.md), and no full POSIX claim is
made. Runtime option parsing, aliases, traps, locale startup and case/function
consumers retain their existing owners. The selected scalar `$@`/`$*`,
redirection, declaration-recognition and NUL-output policies are documented in
[value expansion](../value-expansions.md) and the
[conformance matrix](../posix-matrix.md#csh-026-integration-evidence).


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
case. CSH-026 now routes parameter-removal patterns through that shared encoder;
the integrated quoted-class and empty-pattern fixtures pass.
