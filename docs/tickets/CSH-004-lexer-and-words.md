# CSH-004: Preserve shell tokens and quoting

- Status: ready
- Type: feat
- Kind: implementation
- Parent: None
- Depends on: CSH-016, CSH-017
- Branch: Assigned when work starts
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

- [ ] Adjacent quoted and unquoted fragments form one word and preserve empties.
- [ ] Operators are recognized by grammar rules without requiring spaces.
- [ ] Quoted operators and comment markers remain word content.
- [ ] Escaping, nested substitutions, and incomplete quotes retain their context.
- [ ] Tokens carry sufficient provenance for actionable syntax diagnostics.
- [ ] Lexer storage has documented ownership and is released on failure.
- [ ] Lexer fixtures build and run without the legacy scanner or header; the
  word/token API does not expose the prototype argument-array contract.
- [ ] Long tokens, many words, repeated scans, and allocation failures have
  bounded, sanitizer-checked cleanup without truncation or stale token reuse.
- [ ] Runtime integration is assigned to CSH-018 and complete legacy deletion
  to CSH-039; no adapter to the old executor is needed to complete this ticket.

## Validation

Use lexer-level fixtures for token kinds, word fragments, and source positions,
with runtime behavioral cases delivered by CSH-018. Cover long input, empty quotes, adjacent
fragments, newline continuations, nested constructs, and EOF in an open quote.
Compare behavior only where POSIX specifies the result.

## Implementation notes/evidence

Use the POSIX.1-2024 token recognition and quoting sections as the contract.
Removing quotes from raw strings at this stage would lose expansion semantics.
