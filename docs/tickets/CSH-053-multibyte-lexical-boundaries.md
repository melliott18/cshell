# CSH-053: Preserve syntax-valued bytes inside multibyte source characters

- Status: review
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-004
- Branch: `fix/CSH-053-multibyte-lexical-boundaries`
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

- [x] The reproduction preserves the complete character.
- [x] Startup lexical state remains fixed after locale assignments in parent
  and subshell parsing; newly invoked shells use their new startup state.
- [ ] Native macOS/Linux and sanitizer results identify tested encodings and
  unavailable-locale skips without treating reference output as an oracle.

## Validation

Run the new raw-byte witnesses and `make test-portability test test-pty`, plus
the documented sanitizer configuration. CSH-042 does not claim support for all
encodings merely because the host lists their locales.

## Implementation

`src/character.c` captures the startup locale once, before any input parsing.
Lexer lookahead, ordinary/escaped fragments, delimiter and backquote quote
removal, and dollar-single-quote source decoding preserve complete characters.
Eval, dot, alias and substitution parsers share the process-owned snapshot;
fork inherits it and an external invocation captures a new one. Pattern
encoding, IFS splitting and `read` use the current LC_CTYPE and preserve
constituent syntax bytes. Generated control escapes retain their current-locale
representability check.

The boundary contract covers ASCII-compatible stateless encodings. Invalid and
final incomplete source sequences use byte fallback; stateful encodings are
not claimed. See [locale behavior](../locales.md#raw-byte-lexical-witnesses-csh-053)
for ENV-004, LEX-002/004 and EXP-010 witness mappings and capability limits.
Linux CI and Docker now provision GB18030 so constituent-byte tests run there.

## Validation record

Base: `3d1000baf1da70590548f6bbcd12a1355fcb5dc4`. Native host: macOS 14.8.7,
arm64, Apple clang 15.0.0/Apple libc. Docker: Debian bookworm, Linux arm64,
GCC 12/glibc 2.36. Docker Linux is recorded separately from native Linux CI.

- `make -j4 test`: passed on native macOS; CSH-053 reports 2,044 checks,
  zero failures and four raw-pathname capability skips. Tested installed
  `ja_JP.SJIS`, `zh_TW.Big5`, `zh_CN.GBK`, `zh_CN.GB18030` in all three input
  modes. Each encoding's pathname group skips because the macOS filesystem
  rejects those non-UTF-8 names. The full portability run reports 2,206 passes
  and five capability groups skipped, including the existing message-catalog gap.
- `make test-pty`: passed on native macOS.
- `make -j4 test test-pty` in `cshell-test:csh-053`: passed on Docker Linux;
  CSH-053 reports 553 checks, zero failures and three unavailable encoding
  groups (Shift-JIS, Big5, GBK). GB18030 raw filenames and patterns pass.
  Full portability: 727 passes, three capability skips.
- `make test-lexer test-parser test-expand`: passed, including existing fault
  injection. The added API fixture checks every two-feed split of bare,
  escaped, single/double/dollar-single quoted and dollar-adjacent characters
  after switching the runtime locale to C.
- Full macOS and Docker ASan/UBSan runs are in progress. An initial parallel
  macOS run hit the existing five-second invocation fixture timeout; its
  isolated rerun uses `MallocNanoZone=0 ASAN_OPTIONS=halt_on_error=1
  UBSAN_OPTIONS=halt_on_error=1` and the documented sanitizer flags. Hosted
  native Linux/macOS CI validation is pending.

Expected raw bytes are derived from character-preservation and quote rules;
no reference shell output is used as the oracle. Startup-C invalid-byte
witnesses are explicitly implementation-policy checks. Existing broad POSIX
family and host-utility gaps are not promoted by this ticket.
