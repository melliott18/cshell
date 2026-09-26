# CSH-053: Preserve syntax-valued bytes inside multibyte source characters

- Status: ready
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-004
- Branch: Assigned when work starts
- Issue: [#86](https://github.com/melliott18/cshell/issues/86)

## Goal

Make lexical processing respect startup character boundaries in encodings where
multibyte characters can contain bytes with ASCII shell syntax values. This is
a concrete remaining defect found by [CSH-042](CSH-042-locale-semantics.md),
separate from the working C/POSIX and UTF-8 syntax paths.

## Reproduction

On native macOS 14.8.7, Apple libc, installed `ja_JP.SJIS`, run cshell with
`LC_ALL=ja_JP.SJIS` and the command bytes
`70 72 69 6e 74 66 20 27 25 73 5c 6e 27 20 83 5c 0a`
(`printf '%s\\n' ` followed by the Shift-JIS character ソ and newline).
Expected stdout is `83 5c 0a`; current stdout is `83 0a`, status 0, empty stderr.
The lexer mistakes the character's second byte for a backslash and consumes
the following newline. Quoting/expansion paths also need boundary review.
macOS `/bin/sh` and `/bin/bash` 3.2.57 produce `83 5c 0a`; these are reference
observations, not the source of the character-preservation requirement.

## Scope

- Preserve a startup LC_CTYPE decoding context through lexer/parser lifetime,
  eval, dot input, subshells, and command substitutions.
- Do not let later LC_CTYPE assignments change that lexical context; continue
  using current categories for expansion and builtins.
- Audit quote removal, escaped input in `read`, and pattern encoding for
  constituent bytes which equal syntax bytes.
- Add byte-preserving fixtures with explicit skips when the required encoding
  is unavailable. Trace ENV-004, LEX-002/004 and EXP-010 obligations.

## Acceptance criteria

- [ ] The reproduction preserves the complete character.
- [ ] Startup lexical state remains fixed after locale assignments in parent
  and subshell parsing; newly invoked shells use their new startup state.
- [ ] Native macOS/Linux and sanitizer results identify tested encodings and
  unavailable-locale skips without treating reference output as an oracle.

## Validation

Run the new raw-byte witnesses and `make test-portability test test-pty`, plus
the documented sanitizer configuration. CSH-042 does not claim support for all
encodings merely because the host lists their locales.
