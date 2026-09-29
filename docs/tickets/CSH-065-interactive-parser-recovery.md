# CSH-065: Recover from interactive main-parser syntax errors

- Status: done
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-039
- Branch: `fix/CSH-065-interactive-parser-recovery`
- Issue: [#134](https://github.com/melliott18/cshell/issues/134)

## Goal

Keep an interactive shell usable after a shell-language syntax error at the main input boundary.

## Scope

- POSIX.1-2024 XCU §2.8.1; SH-008, GRAM-005 and EXEC-015.
- `src/main.c` currently breaks for every parser error; nested `eval` recovery is a different path.
- Preserve source-read failures, EOF, allocation failures and noninteractive exit semantics; do not discard already completed commands or execute malformed trees.

## Acceptance criteria

- [x] A malformed complete command emits a diagnostic, sets a nonzero status and returns to a usable interactive command boundary.
- [x] String, script, forced-interactive stdin and controlling-terminal regressions assert following-command effects, streams/status and prompt recovery; noninteractive controls still exit.
- [x] Recovery preserves aliases, parser/input ownership and pending here-document boundaries without loops, leaks or unintended side effects.
- [x] Integrate the regressions into the default suite and update the invocation map.

## Validation

Run the retained review probe below, then the default runtime, parser, PTY and sanitizer checks. Its four recovery cases currently fail with status 2; the three noninteractive and three interactive-eval controls pass. Keep five-second bounds and strict expected success after recovery.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.


## Implementation

The interactive main loop explicitly requests `csh_parser_recover()` after
reporting a syntax diagnostic and preserving its status. Default parser errors
remain sticky, so noninteractive and nested callers retain their prior policy.
Recovery replaces the lexer at the absolute physical input position, preserves
borrowed input/aliases/hooks, and consumes pending here-documents without
expansion before returning to a fresh command boundary. Recovery snapshots own
only delimiters and buffered body bytes; failed ASTs are always destroyed.
Arithmetic replay clears speculative snapshots before retrying.

`tests/parser_recovery_cases.py` supplies 42 forced-interactive string/file/stdin
cases and one controlling-PTY case. Three noninteractive controls in
`tests/syntax_cases.py`, four recovery allocation sweeps and explicit parser
read-boundary tests, plus two public recovery read-failure cases, cover the
negative boundaries. The generators are dependencies of the default runtime,
syntax and PTY suites. The [invocation map](../invocation-syntax-evidence.md#interactive-parser-recovery)
records exact coverage for SH-008, GRAM-005 and EXEC-015.


## Validation record (2026-09-29)

Code revision: `81d2f0b31b1336b25c587b85c1979bed1e1f654a`.
[Commands, environments, retained probe and hashes](../evidence/csh-065/README.md).

- macOS arm64 / Apple Clang 15: `make -j4 test`, `make -j4 test-runtime test-pty`,
  and focused parser/execution-contract checks passed.
- Linux aarch64 / Debian GCC 12.2: `make docker-test docker-test-pty` passed.
- macOS ASan/UBSan: parser, default runtime, PTY and execution-contract targets
  passed. Linux ASan/UBSan/LSan: parser/AST checks and 46 focused recovery/control
  cases passed. Slow Linux full sanitizer grids were stopped and are not claimed
  as complete; see the evidence record for exact scope.
- Default runtime: 3,950 cases; parser: 239 checks; default runtime PTY: 33 cases;
  execution contracts: 53 checks, with zero failures in the completed runs.
- Retained review probe: all four recovery cases and six associated controls
  pass. Overall 19 pass and six fail; the six depth-128/129 failures remain with
  CSH-066. The historical review evidence is unchanged.

Ready for review; integration into `main` is still required before `done`.
