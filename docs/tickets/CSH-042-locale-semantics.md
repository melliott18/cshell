# CSH-042: Complete locale-sensitive shell behavior

- Status: review
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-037
- Branch: `fix/CSH-042-locale-semantics`
- Issue: [#73](https://github.com/melliott18/cshell/issues/73)

## Goal

Close the locale behavior left open by the CSH-037 startup-locale fix before
advancing [ENV-004](../posix-matrix.md#env-004) or related pattern rows to verified.

## Scope

- Exercise initial `LC_CTYPE`, `LC_COLLATE`, `LC_MESSAGES`, `LANG`, and `LC_ALL`
  precedence on supported macOS and Linux locales. Include invalid or unavailable
  locale names with an explicit decision based on the standard.
- Check locale-sensitive parameter removal, `case`, pathname matching, bracket
  classes, collation, multibyte IFS, and diagnostic language where catalogs are
  available. Keep locale-dependent or unspecified results out of exact oracles.
- Preserve the rule that a change to `LC_CTYPE` after shell startup does not
  change lexical processing in the current invocation or its subshells.

## Acceptance criteria

- [x] Supported locale behavior and catalog limitations are documented and
  linked to the affected matrix rows.
- [x] Native macOS and Linux fixtures cover applicable locale precedence and
  pattern cases, with concrete skip reasons for unavailable locales/catalogs.
- [x] Each discovered mismatch is fixed with a regression or linked to a
  narrower defect ticket; diagnostics retain their specified stderr/status rules.

## Validation

Run `make test-portability test test-pty` on both supported systems and the
sanitizer configuration in [Testing](../testing.md). Record the installed locale
names, library versions, exact fixture results, and reference observations
separately from specification-derived expectations.

## Implementation notes/evidence

[CSH-037](CSH-037-portability-audit.md) initializes the runtime locale and
adds selected C/UTF-8 probes. Those cases establish only their assertions.

## Implementation and validation record (2026-09-26)

Started from `main` at `b692aa517d7ce26750f28b7855ed844c4793d758` in a
separate worktree. [Locale behavior](../locales.md) documents category precedence,
invalid-name policy, libc catalog limitations, exact fixture families and their
matrix links. Runtime state now refreshes libc on locale assignment/unset and
scope restoration; `read` consumes whole multibyte IFS characters. Assignment-only redirection
clones reselect the parent locale before subsequent command expansion, including
the redirection-failure path (two additional three-mode regressions).

A clean build of the starting revision fails the new string-mode regressions:

- `locale runtime CTYPE assignment and unset`: `2/3/2` lengths instead of `1/3/1`.
- `locale UTF-8 read IFS whole characters`: splits the shared leading byte of
  `è`/`é`, producing broken fields rather than `è`, `a`, empty, `b`.
- `locale runtime collation and temporary scope restoration`: retains C order
  after LC_COLLATE assignment instead of the host's en_US order.

The updated runtime passes all three in each input mode. An additional concrete
Shift-JIS lexer mismatch has its own reproduction, acceptance criteria and owner:
[CSH-053 / #86](CSH-053-multibyte-lexical-boundaries.md). CSH-042 does not advance
ENV-004 or the related broad matrix families to verified.

### Validation evidence

The final runtime/test revision is `7bf7025abbe4e69d2111769a9873f2e5373f634f`.
Later evidence-only edits do not change the executable or fixtures. Normal
build flags are `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`, with
`_POSIX_C_SOURCE=200809L`. Sanitizer flags are
`-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer`, matching linker flags,
`ASAN_OPTIONS=halt_on_error=1`, `UBSAN_OPTIONS=halt_on_error=1`, and on macOS
`MallocNanoZone=0`.

| Environment | Commands and results |
| --- | --- |
| Native macOS 14.8.7 (23J520), Darwin arm64, Apple Clang 15.0.0 (`clang-1500.3.9.4`), Python 3.12.2, SDK libSystem 1345.120.2 | Full `make -j2 test test-pty` and the same full ASan/UBSan run passed at the initial implementation revision: all module/fault checks, 1,318 runtime, 13 job PTY and 27 runtime PTY cases. Final normal `make test-portability test-execute` passed: 162 portability cases plus 61 execution behaviors/API/fault checks. Final sanitizer `make -j2 test-portability test-execute test-substitution test-context` passed all checks, including the additional redirection-clone regressions. One locale capability group is skipped: installed candidate locales have no translated libc ENOENT message. |
| Docker Desktop 24.0.6, Linux 6.4.16-linuxkit aarch64, Debian 12.15, GCC 12.2.0, glibc 2.36 (`2.36-9+deb12u14`), Python 3.11.2 | `make docker-build DOCKER_IMAGE=cshell-test:csh042` and in-image `make -j2 test test-pty` passed all normal tests. After the final clone fix, in-image `make test-portability test-execute` passed 174 portability cases and all execution checks with zero skips, including French diagnostic precedence/assignment. |
| Hosted native Ubuntu 24.04.5, image `20260920.314.1`, GCC 13.3.0 (`13.3.0-6ubuntu2~24.04.1`), glibc `2.39-0ubuntu8.9` from the pinned runner SBOM, Python 3.11 from setup-python | [Run 36220246008](https://github.com/melliott18/cshell/actions/runs/36220246008), job `108344013572`, passed normal `make test`, `make test-pty`, 64 harness self-tests and full ASan/UBSan `make -j2 test test-pty` on the final runtime revision. Each configuration passed 162 portability, 1,318 runtime, 13 job PTY, 27 runtime PTY, and all module/fault cases. One diagnostic-catalog capability skip; the runner exposes no translated ENOENT catalog. The run records the exact runner image and its linked software manifest. |
| Hosted Docker Linux | The same run's job `108344013736` passed normal and full ASan/UBSan tests: 174 portability cases, 1,318 runtime, 13 job PTY, 27 runtime PTY, all module/fault checks, and 64 harness self-tests. Zero locale skips; the image explicitly retains the French libc catalog. |

Installed/probed locale names were recorded separately from oracles. Native
macOS candidates are C, en_US.UTF-8, fr_FR.UTF-8, de_DE.UTF-8, sv_SE.UTF-8;
C.UTF-8 is unavailable. Local Debian lists C, C.utf8, POSIX, en_US.utf8 and
fr_FR.utf8; libc accepts the `.UTF-8` spellings used by the tests. Hosted Ubuntu
probes C, C.UTF-8, en_US.UTF-8 and fr_FR.UTF-8. Native Shift-JIS was additionally
probed only to reproduce CSH-053, not counted as a passing supported encoding.

An earlier **local Docker sanitizer run failed** on nine 5-second portability
timeouts and a 10-second context-fixture timeout, without an ASan/UBSan report.
Other sanitizer work was concurrently using the local Docker engine. A direct
sanitized reproduction of the first C-locale case passed within the unchanged
five-second bound. The final revision passed the complete hosted Linux sanitizer
suite with unchanged bounds. A redundant local sequential rerun was stopped
after those hosted checks passed; it is not counted as a pass. Resource contention
is a possible explanation for the local timeouts, not a proven root cause.

Hosted macOS 15.7.9 (24G830), arm64 image `20260907.0337.1`, also passed
all stages in [run 36220246008](https://github.com/melliott18/cshell/actions/runs/36220246008),
job `108344013720`, completed 2026-09-26 05:23:40 UTC. Normal and full sanitizer
runs each passed 162 portability, 1,318 runtime, 13 job PTY, 27 runtime PTY and
all module/fault checks; 64 harness self-tests passed. C.UTF-8 is available on
this newer macOS runner, along with the named locales above. The only capability
skip is the untranslated libc ENOENT catalog. All three jobs passed on the final
runtime revision without relaxed fixture timeouts or assertions.

Ubuntu package versions above come from the
[pinned image SBOM](https://github.com/actions/runner-images/releases/tag/ubuntu24%2F20260920.314);
the job installed only build-essential without upgrading libc or GCC. Local
Docker's final normal image is
`sha256:0c766fd7c8ee0aed321818e27ac8532f84a5fbfddaec87d6f270c676c76432eb`.
[PR #87](https://github.com/melliott18/cshell/pull/87) is ready for review.
CSH-042 remains `review` until integrated; CSH-053 remains open.

### Reference observations (not test oracles)

macOS `/bin/sh` and `/bin/bash` 3.2.57 both return length 1 after changing
LC_CTYPE from C to en_US.UTF-8 for `v=é`. Both preserve `83 5c 0a` in the
Shift-JIS reproduction; cshell currently emits `83 0a`. These comparisons only
corroborate the source-derived obligations. Collation and translated-error
fixtures use the installed libc data explicitly; invalid-locale cases assert
cshell's documented policy where POSIX leaves the result unspecified.
