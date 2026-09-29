# CSH-065: Recover from interactive main-parser syntax errors

- Status: ready
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-039
- Branch: Assigned when work starts
- Issue: [#134](https://github.com/melliott18/cshell/issues/134)

## Goal

Keep an interactive shell usable after a shell-language syntax error at the main input boundary.

## Scope

- POSIX.1-2024 XCU §2.8.1; SH-008, GRAM-005 and EXEC-015.
- `src/main.c` currently breaks for every parser error; nested `eval` recovery is a different path.
- Preserve source-read failures, EOF, allocation failures and noninteractive exit semantics; do not discard already completed commands or execute malformed trees.

## Acceptance criteria

- [ ] A malformed complete command emits a diagnostic, sets a nonzero status and returns to a usable interactive command boundary.
- [ ] String, script, forced-interactive stdin and controlling-terminal regressions assert following-command effects, streams/status and prompt recovery; noninteractive controls still exit.
- [ ] Recovery preserves aliases, parser/input ownership and pending here-document boundaries without loops, leaks or unintended side effects.
- [ ] Integrate the regressions into the default suite and update the invocation map.

## Validation

Run the retained review probe below, then the default runtime, parser, PTY and sanitizer checks. Its four recovery cases currently fail with status 2; the three noninteractive and three interactive-eval controls pass. Keep five-second bounds and strict expected success after recovery.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.
