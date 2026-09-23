# CSH-030: Implement alias storage and token substitution

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-004, CSH-005
- Branch: Assigned when work starts
- Issue: [#31](https://github.com/melliott18/cshell/issues/31)

## Goal

Apply aliases at the specified token-reading stage while preserving parser
context, quoting, and bounded recursive substitution behavior.

## Scope

- Add alias storage, lookup, replacement, removal, and `alias`/`unalias` handlers
  behind interfaces suitable for later command-dispatch integration.
- Integrate substitution with token input, respecting command position, quoting,
  trailing blanks, and input/read timing.
- Track active alias expansion to prevent prohibited recursive re-expansion;
  release injected token/input resources on errors and end of input.

## Acceptance criteria

- [ ] Lexer/parser fixtures distinguish eligible command words from quoted words,
  ordinary arguments, and words made eligible by trailing-blank alias values.
- [ ] Direct and indirect self-reference terminate with the specified expansion
  behavior; valid chained replacements produce the expected token stream.
- [ ] Definitions and removals take effect at the required read/parse boundary,
  with fixtures covering multiple commands and multiline input.
- [ ] Alias handlers validate operands, report lookup failures, and preserve
  replacement text with tested output/status and memory ownership.

## Validation

Run token/AST fixtures and direct builtin-handler tests under sanitizers. Record
source requirements for parse timing and any unspecified cases; reserve executed
script checks for the CSH-031 dispatcher integration.

## Implementation notes/evidence

Record interface decisions and results here. This work may start before shell
state and full expansion are available; CSH-010 must later demonstrate alias
behavior in complete scripts before the builtin milestone can close.
