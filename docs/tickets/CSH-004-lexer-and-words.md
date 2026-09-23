# CSH-004: Preserve shell tokens and quoting

- Status: backlog
- Type: feat
- Depends on: CSH-003
- Branch: Assigned when work starts

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

- [ ] Adjacent quoted and unquoted fragments form one word and preserve empties.
- [ ] Operators are recognized by grammar rules without requiring spaces.
- [ ] Quoted operators and comment markers remain word content.
- [ ] Escaping, nested substitutions, and incomplete quotes retain their context.
- [ ] Tokens carry sufficient provenance for actionable syntax diagnostics.
- [ ] Lexer storage has documented ownership and is released on failure.
- [ ] The legacy lexer is removed from the active path after the new interface
  is integrated; temporary adapters are identified explicitly.

## Validation

Use lexer-level fixtures for token kinds, word fragments, and source positions,
plus behavioral cases through the shell. Cover long input, empty quotes, adjacent
fragments, newline continuations, nested constructs, and EOF in an open quote.
Compare behavior only where POSIX specifies the result.

## Implementation notes/evidence

Use the POSIX.1-2024 token recognition and quoting sections as the contract.
Removing quotes from raw strings at this stage would lose expansion semantics.
