# CSH-042: Complete locale-sensitive shell behavior

- Status: backlog
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-037
- Branch: Assigned when work starts
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
