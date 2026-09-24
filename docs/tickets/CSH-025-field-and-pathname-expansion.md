# CSH-025: Complete field splitting and pathname expansion

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-024
- Branch: feature/CSH-025-field-pathname-expansion
- Issue: [#26](https://github.com/melliott18/cshell/issues/26)

## Goal

Turn intermediate expanded words into correctly separated argument fields and
filename matches without losing quoted empty values.

## Scope

- Apply field splitting using the active `IFS` and retained quote provenance.
- Implement pathname pattern matching and expansion, including no-match behavior
  and leading-dot rules, followed by final quote removal.
- Respect expansion contexts that suppress splitting or pathname expansion;
  expose field ownership and error results to CSH-026 integration.

## Acceptance criteria

- [x] Unset, empty, whitespace-only, and mixed whitespace/non-whitespace `IFS`
  fixtures produce the expected fields, including required empty fields.
- [x] Quoted metacharacters and empty quoted words survive the proper stages
  without becoming unintended patterns or disappearing.
- [x] Controlled filename fixtures cover matches, no matches, leading dots,
  bracket patterns, and multiple directory components in a stable locale.
- [x] Assignment and other restricted contexts omit the prohibited expansion
  stages, with distinct tests for each supported context.
- [x] Allocations are released on pattern, expansion, and interrupted error paths.

## Validation

Use an argument-inspection fixture and temporary directory trees with whitespace,
metacharacters, and dotfiles. Run module cases under sanitizers and record field
counts as well as bytes; compare only standard-defined reference-shell behavior.

## Implementation notes/evidence

CSH-026 owns cross-feature execution checks,
including command substitutions and here-documents. Completion of this child does
not close [CSH-008](CSH-008-word-expansion.md).

### Implemented contract

`csh_expand_fields()` consumes the borrowed CSH-024 intermediate fields and
returns independent, counted, NULL-terminated argument strings. Argument
context applies active IFS splitting, pathname generation, and final quote
removal; `noglob` suppresses pathname generation alone. Assignment context
returns scalar value bytes, and pattern context returns matcher-ready protected
patterns. Both restricted contexts omit splitting and pathname generation.
The existing prototype executable is unchanged; CSH-026 owns execution,
substitution, redirection, and here-document integration.

`src/fields.c` retains explicit empty values at their original positions and
splits only eligible spans, including multibyte IFS boundaries. `src/pathname.c`
walks directory components iteratively with one open stream, protects quoted
pattern characters, sorts matches in the caller's locale, and preserves
unmatched patterns. Hidden names, bracket expressions, literal metacharacters,
repeated separators, trailing slashes, and symlinks have controlled fixtures.
Errors and cooperative interruption release all output and open directories
without mutating the borrowed input or state. The final stage does not reverse
side effects from an earlier successful value-stage call; CSH-026 can checkpoint
across both calls when it needs whole-word atomicity.

[Value expansion](../value-expansions.md#final-fields-and-pathname-generation)
documents ownership, locale and unspecified choices, filesystem error policy,
component limits, and the Issue 8 quoted-empty behavior that differs from older
reference shells. The implementation follows the
[Issue 8 expansion and pattern requirements](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_05).
`make test-fields` is part of `make test-expand`, so native, Docker, and existing
sanitizer CI exercise the new stage.

### Validation evidence (2026-09-23)

Environment: macOS/Darwin arm64, Apple Clang 15.0.0, GNU Make 3.81; Docker
Engine 24.0.6, Linux aarch64, Debian Bookworm/GCC 12.2.0, unprivileged UID 10001.

- Native `make -j8`, `make test test-pty test-harness`, and the complete Docker
  module/behavioral suite passed (`make docker-test DOCKER_IMAGE=cshell-test:csh-025`).
  Native and Docker PTY checks and all 61 harness self-tests passed. The
  unchanged generated prototype scanner
  retains its existing macOS signedness warning.
- Clean `make test-expand CC=clang` passed with
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`,
  `LDFLAGS='-fsanitize=address,undefined'`, `ASAN_OPTIONS=halt_on_error=1`,
  and `UBSAN_OPTIONS=halt_on_error=1`. The Linux GCC run uses the same flags
  and additionally `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`. Both include
  final-field fixtures and exhaustive failure sweeps; no sanitizer diagnostics
  appeared.
- `make test-fields` passes 110 checks, including 85 selected `/bin/sh`
  comparisons. Quoted class-name, collating, and equivalence cases use direct
  expectations where host reference shells differ.
- Argument inspection checks field counts and NUL-delimited bytes in controlled
  temporary trees, repeats finalization to check borrowed-input preservation,
  and destroys input/state before inspecting independently owned results.
  Standard-defined cases are compared with `/bin/sh`; Issue 8 quoted-empty and
  documented unspecified choices use explicit expected results instead.
- Fault-only objects fail every allocation and each directory/stat operation
  with `EIO`, `EINTR`, and `ENOMEM`, and cancel at successive callback points.
  They assert no live tracked allocations or directory streams, cleared output,
  and unchanged input/state. Swallowed `EACCES`/`ENOENT` directory-read failures
  discard that directory's partial matches while preserving other directories.
- Independent review added regressions for expansion-produced pattern escapes,
  escaped path separators, quoted pattern boundaries, malformed bracket
  fallback, quoted bracket subexpressions, and partial-directory read failures. A 240-case randomized IFS
  comparison found only the documented older-shell quoted-empty differences.
- Changed Markdown links and `git diff --check` passed; diagrams are unchanged.

The ticket remained at `review` until integration. These module checks do not
claim complete shell or POSIX conformance and do not close CSH-008.

Integrated into `main` through [pull request #56](https://github.com/melliott18/cshell/pull/56)
on 2026-09-23. Implementation commit: `8e34da6`; merge commit: `bae2036`.
GitHub closed issue #26 when the pull request merged. CSH-026 retains the
remaining CSH-008 milestone work.
