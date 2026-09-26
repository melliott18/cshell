# CSH-042: Complete locale-sensitive shell behavior

- Status: in-progress
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

- [ ] Supported locale behavior and catalog limitations are documented and
  linked to the affected matrix rows.
- [ ] Native macOS and Linux fixtures cover applicable locale precedence and
  pattern cases, with concrete skip reasons for unavailable locales/catalogs.
- [ ] Each discovered mismatch is fixed with a regression or linked to a
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
scope restoration; `read` consumes whole multibyte IFS characters.

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

### Validation in progress

- Native macOS 14.8.7 (23J520), Darwin arm64, Apple Clang 15.0.0
  (`clang-1500.3.9.4`), Python 3.12.2. Selected locales: C, en_US.UTF-8,
  fr_FR.UTF-8, de_DE.UTF-8, sv_SE.UTF-8; C.UTF-8 unavailable. The default
  `make -j2 test test-pty` passed all module checks, 1,318 runtime, 13 job PTY,
  27 runtime PTY and the initial 150 portability cases. The final focused
  `make test-portability` passes 156 cases, zero failures; one capability group
  is skipped because no candidate libc locale translates ENOENT.
- Docker Linux aarch64, Debian bookworm, GCC 12.2.0, glibc 2.36
  (`2.36-9+deb12u14`). Selected installed names: C, C.utf8, POSIX,
  en_US.utf8, fr_FR.utf8. The final image retains French libc catalogs and the
  focused portability suite passes 168 cases, zero failures/skips.
- Full ASan/UBSan runs and hosted native Linux validation are pending.

### Reference observations (not test oracles)

macOS `/bin/sh` and `/bin/bash` 3.2.57 both return length 1 after changing
LC_CTYPE from C to en_US.UTF-8 for `v=é`. Both preserve `83 5c 0a` in the
Shift-JIS reproduction; cshell currently emits `83 0a`. These comparisons only
corroborate the source-derived obligations. Collation and translated-error
fixtures use the installed libc data explicitly; invalid-locale cases assert
cshell's documented policy where POSIX leaves the result unspecified.
