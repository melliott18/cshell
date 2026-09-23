# CSH-025: Complete field splitting and pathname expansion

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-008
- Depends on: CSH-024
- Branch: Assigned when work starts
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

- [ ] Unset, empty, whitespace-only, and mixed whitespace/non-whitespace `IFS`
  fixtures produce the expected fields, including required empty fields.
- [ ] Quoted metacharacters and empty quoted words survive the proper stages
  without becoming unintended patterns or disappearing.
- [ ] Controlled filename fixtures cover matches, no matches, leading dots,
  bracket patterns, and multiple directory components in a stable locale.
- [ ] Assignment and other restricted contexts omit the prohibited expansion
  stages, with distinct tests for each supported context.
- [ ] Allocations are released on pattern, expansion, and interrupted error paths.

## Validation

Use an argument-inspection fixture and temporary directory trees with whitespace,
metacharacters, and dotfiles. Run module cases under sanitizers and record field
counts as well as bytes; compare only standard-defined reference-shell behavior.

## Implementation notes/evidence

Record commands and results here. CSH-026 owns cross-feature execution checks,
including command substitutions and here-documents. Completion of this child does
not close [CSH-008](CSH-008-word-expansion.md).
