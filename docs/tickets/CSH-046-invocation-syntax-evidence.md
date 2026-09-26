# CSH-046: Close invocation, lexical, grammar and alias evidence gaps

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: `test/CSH-046-invocation-syntax-evidence`
- Issue: [#78](https://github.com/melliott18/cshell/issues/78)

## Goal

Inventory source clauses and map the existing module/runtime case names before adding missing public-runtime cases. Record required versus unspecified invocation and alias behavior, syntax boundaries, nonblocking-input invariants and chosen extensions. Cross-link every assertion, implementation and native/Docker run; do not classify module-only assertions as runtime coverage.

## Explicit current limitation

The [clause/condition map](../invocation-syntax-evidence.md) now reconciles all
21 rows with exact public-runtime and module witnesses. New tests cover the
named PATH, identity, descriptor, syntax-boundary and alias-policy gaps.
The recursive parser/executor size guard remains a known limitation; the map
also identifies API-only source-read-error and heredoc end-of-string boundaries
and encoding/cross-feature coverage owned by related tickets. No broad family
is promoted to verified and the CSH-012 compliance gate remains closed.

This is the implementation/evidence record for the
[CSH-037 independent review](../audit-review.md) follow-up. Ticket review status
does not assert unrestricted grammar support or complete POSIX conformance.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [SH-001](../posix-matrix.md#sh-001) | Read commands from stdin, a script, or `-c`; keep command input distinct from utility stdin. |
| [SH-002](../posix-matrix.md#sh-002) | Map `command_name`, script name, arguments, `$0`, and implicit `-s`; honor the standalone `-` operand. |
| [SH-003](../posix-matrix.md#sh-003) | Read non-executable scripts; resolve slash and slashless script operands. |
| [SH-004](../posix-matrix.md#sh-004) | Detect interactive mode using `-i` or stdin plus terminal stdin/stderr; handle invocation errors. |
| [SH-005](../posix-matrix.md#sh-005) | Empty strings, blank/comment-only files exit zero; EOF preserves applicable last-command status. |
| [SH-006](../posix-matrix.md#sh-006) | Preserve bytes for commands reading stdin; allow all input types with a character-only, NUL-free parsed prefix; remove shell-imposed line limits. |
| [SH-007](../posix-matrix.md#sh-007) | Enable blocking reads when input is a nonblocking FIFO or terminal, including after completion. |
| [SH-008](../posix-matrix.md#sh-008) | Avoid non-interactive prompt output; send diagnostics to stderr and apply shell exit/error rules. |
| [LEX-001](../posix-matrix.md#lex-001) | Recognize words, longest operators, comments, newlines, and nested substitutions without early expansion. |
| [LEX-002](../posix-matrix.md#lex-002) | Apply backslash escaping and remove escaped newlines before token boundaries. |
| [LEX-003](../posix-matrix.md#lex-003) | Preserve literal single-quoted text, empty words, and adjacent quoted/unquoted fragments. |
| [LEX-004](../posix-matrix.md#lex-004) | Preserve double-quote context for dollar/backquote/backslash and parameter/substitution nesting. |
| [LEX-005](../posix-matrix.md#lex-005) | Decode Issue 8 dollar-single-quote escapes and retain resulting quoting. |
| [LEX-006](../posix-matrix.md#lex-006) | Substitute eligible aliases recursively with recursion prevention and correct token/parse timing. |
| [GRAM-001](../posix-matrix.md#gram-001) | Recognize reserved words only in their grammatical positions; preserve names and assignment words. |
| [GRAM-002](../posix-matrix.md#gram-002) | Parse pipelines, lists, groups, redirections and complete commands with specified precedence. |
| [GRAM-003](../posix-matrix.md#gram-003) | Collect multiple here-documents in order; preserve delimiter quoting, `<<-`, and incomplete-input state. |
| [GRAM-004](../posix-matrix.md#gram-004) | Parse every compound command and function definition, including Issue 8 case fall-through `;&`. |
| [GRAM-005](../posix-matrix.md#gram-005) | Distinguish syntax errors from incomplete input; execute only valid complete commands, without arbitrary command-size limits. |
| [U-017](../posix-utilities.md#u-017) | `alias`: create/redefine/query/list with reusable quoting; affect current shell/subshells; token substitution and read timing. |
| [U-031](../posix-utilities.md#u-031) | `unalias`: named removal and `-a`, nonexistent names/error status, current environment and future token-read effects. |

Relevant documented choices: D-001, D-002 (IO_LOCATION syntax only), D-003 (dollar-single-quote encoding only), D-004 (aliases), D-008. Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/input.py](../../tests/input.py)
- [tests/lexer.py](../../tests/lexer.py)
- [tests/parser.py](../../tests/parser.py)
- [tests/alias_parser.c](../../tests/alias_parser.c)
- [tests/runtime_cases.py](../../tests/runtime_cases.py)
- [tests/evaluation_cases.py](../../tests/evaluation_cases.py)

These are starting points for inspection, not claims that the complete rows
already pass. Reuse exact case names and assertions where they are sufficient;
add or split fixtures only for a concrete coverage gap.

## Acceptance criteria

- [x] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [x] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [x] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [x] Matrix rows and reverse ownership links reflect only the verified scope;
  broad rows are split where necessary and the CSH-012 compliance gate remains
  closed while any applicable requirements are unmet.

## Validation

Run the applicable focused suites above and the integration paths documented in
[Testing](../testing.md), including `make test test-pty test-harness`, Docker
and ASan/UBSan checks where the changed paths require them. Record exact case
names and results following the [evidence rules](../posix-evidence.md).
Reference-shell comparisons are separate observations, never normative oracles.

## Implementation notes/evidence

Allocated by the CSH-037 follow-up audit at baseline `58ca5c3`. The explicit
limitation and complete row list above replace reliance on already-completed
implementation tickets as owners of remaining verification work.


## Implementation result

Added 34 syntax/alias scenarios across all three input modes (102 strict runtime
cases), and 51 process-level invocation probes. They run through `make test`,
with focused `make test-syntax` and `make test-invocation` targets. The Docker
CI job explicitly runs the two privileged identity probes as root after the
unprivileged suites. No setuid executable or host credential change is needed.

The nine nonblocking-input probes exposed a defect in string/file invocation:
only stdin command mode cleared O_NONBLOCK. `csh_input_prepare_stdin()` now
normalizes FIFO/terminal stdin for all command sources, without consuming bytes
or changing other flags. Tests assert the flags during utility reads and after
exit, preserve regular-file flags and permit closed stdin for independent
command sources. Six native pre-fix string/file probes failed the flags
assertion; the same cases pass after the fix.

The [inventory](../invocation-syntax-evidence.md) links normative clauses,
implementation, exact assertions, source-permitted policies and remaining
limitations. Matrix and reverse-owner links point to those scoped claims.

## Validation record

Source and suite revision: `5e77577e892192567c091d0c20658ce4f01f6327`, based on
`b692aa5`. Normal runs executed on the identical implementation before it was
committed; subsequent validation changes affect documentation and CI routing.
Makefile/src/include/tests fingerprint:
`77d2071d105c26b0d94013ed2097be5f0dab5276a1225aa4fca27f7c4866bfb1`.

Full [machine-readable identities](../evidence/csh-046/validation.json) retain
binary and generated-suite hashes, exact compiler flags, Python, OS/libc,
Docker image/base identity and artifact hashes. [Compressed logs and reproduction
instructions](../evidence/csh-046/README.md) retain each assertion result.
Records were collected on 2026-09-26 UTC; collection timestamps are explicit
and are not presented as exact test-start times.

| Environment / command | Result |
| --- | --- |
| Native macOS 14.8.7 build 23J520, Darwin 23.6.0 arm64, Apple Clang 15.0.0, Python 3.12.2; `make -j4 test test-pty test-harness` | Pass. 1,420 public runtime cases (including 102 new syntax cases); 49 invocation probes plus two capability skips; 63 input, 71 lexer, 238 parser checks; all default API/fault suites; 13 job PTY and 27 runtime PTY cases; 64 harness self-tests. |
| Debian bookworm, Linux 6.4.16-linuxkit aarch64, GCC 12.2.0, glibc 2.36-9+deb12u14, Python 3.11.2; `docker run --rm --init cshell-test:csh-046 make -j4 test test-pty test-harness` | Pass, same runtime/input/lexer/parser/PTY/harness counts and the same two identity skips as native. Image built from this worktree with its own Linux compiler. |
| Same Docker image, `--user 0 python3 tests/invocation.py ./cshell` | 51 passed, zero failures/skips. Child setup verifies unequal real/effective UID or GID separately before exec; the tested shell accepts `-i`. |
| Native ASan/UBSan: `make -j4 test-input test-lexer test-parser test-alias test-syntax test-runtime-pty` with flags below | Pass: 63 input, 71 lexer, 238 parser checks, alias suites, 102 syntax cases, 49 invocation probes/two identity skips, 27 runtime PTY cases. No sanitizer diagnostics. |
| Docker ASan/UBSan, same focused targets at `-j4` | First run failed one existing input case (`file: empty`, five-second timeout); other 62 input checks, lexer 71, parser 238, alias suites, syntax 102 and invocation 49/two skips passed. No sanitizer diagnostic. Make did not start runtime PTY after the input failure. |
| Same instrumented Docker snapshot, targeted `make test-input`, then separate `make test-runtime-pty` | Input retry: 63 passed with unchanged five-second deadlines. Separate terminal run: 27 passed, zero failures/skips. The initial failed log remains attached; CPU contention from concurrent test containers is a plausible explanation, not a proven root cause. |

Normal flags: `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`, with
`-D_POSIX_C_SOURCE=200809L -Iinclude` and no extra linker libraries.
Sanitizer CFLAGS:
`-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer`;
LDFLAGS: `-fsanitize=address,undefined`;
`ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`.
The runtime descriptor-observer helper remains uninstrumented, per the existing
Makefile contract; cshell/input/parser and their API/fault binaries are
instrumented. Native libSystem identity is tied to the recorded macOS build
(the standalone dylib is not present outside the system shared cache).

The two ordinary-run identity skips require Linux root setresuid/setresgid;
CSH-046 owns the skip and the separate root run covers it. There are no PTY or
locale skips in the new C-locale syntax/descriptor probes. This record does not
claim native Linux outside Docker, non-C encodings, unrestricted recursive
size, or any unexecuted combination identified in the clause map. No reference
shell results are used as normative evidence. `git diff --check` and Python
warning-as-error compilation of the changed generators/probes pass.

### Integration validation (2026-09-26)

After integrating CSH-042/043, local macOS ASan/UBSan checks passed: 49
invocation probes (two Linux-root-only skips), 102 syntax cases, and 36 offset
cases. Hosted macOS run 36248557880 exposed allocator startup warnings on PTY
stderr because the new runner dropped CI's `MallocNanoZone=0`. The runner now
preserves this one setting, matching `smoke.py`; exact terminal assertions are
unchanged and report their actual bytes on failure. No diagnostic stripping is
performed.
