# CSH-048: Close shell state and builtin integration evidence gaps

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: `test/CSH-048-state-builtin-evidence`
- Issue: [#80](https://github.com/melliott18/cshell/issues/80)

## Goal

Map and reproduce existing tests by utility option/operand/status/environment clause, explicitly document selected unspecified or implementation-defined policies, test uncovered startup and cross-environment combinations, and retain profile exclusions only for source-conditional portions. Associate every row with exact assertions and native/Docker run records.

## Explicit current limitation

The [clause/condition map](../state-builtin-evidence.md) now links all 24 families to exact assertions, implementation and selected policies. Startup IFS/PPID/PWD, times formatting and ulimit resource descriptions are corrected. Residual permissions, allocation/I/O errors, locale, prompt, signal and option combinations remain explicitly identified in that map; those limitations prevent whole-family verification. ENV-005 now separates source-conditional UP/XSI variable processing from applicable base consumers.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [ENV-001](../posix-matrix.md#env-001) | Import valid environment names with export attributes; preserve unset/empty, readonly and export state. |
| [ENV-003](../posix-matrix.md#env-003) | Initialize IFS, PPID and PWD correctly; consume HOME, PATH and locale variables with specified precedence. |
| [ENV-005](../posix-matrix.md#env-005) | Track ENV startup, LINENO, PS1/PS2/PS4, history/editor/mail variables and NLSPATH requirements. |
| [ENV-006](../posix-matrix.md#env-006) | Preserve or isolate cwd, descriptors, umask, limits, traps, variables, functions, aliases, options and known child IDs by context. |
| [U-001](../posix-utilities.md#u-001) | Special-builtin assignment persistence, lookup precedence, interactive/non-interactive error consequences, output redirection; apply utility syntax exceptions individually and `command` suppression under U-020. |
| [U-002](../posix-utilities.md#u-002) | `:` performs argument expansion/redirections, ignores arguments, and succeeds; no option parsing. |
| [U-005](../posix-utilities.md#u-005) | `.`: readable-file PATH search, parse/execute in current environment, syntax/read errors, result status and `return` integration. Extra positional operands are an extension, not a baseline requirement. |
| [U-006](../posix-utilities.md#u-006) | `eval`: join arguments with spaces, parse and execute in current environment; no/empty argument success and nested errors. |
| [U-007](../posix-utilities.md#u-007) | `exec`: process replacement, environment/descriptor inheritance, permanent redirections without a command, lookup and failure statuses. |
| [U-009](../posix-utilities.md#u-009) | `export`: attributes, assignments, `-p` reinput-safe listing including unset names, declaration-utility expansion, readonly/error behavior. |
| [U-010](../posix-utilities.md#u-010) | `readonly`: attribute/assignment protection, `-p` reinput-safe listing, declaration-utility expansion, errors and inherited environments. |
| [U-011](../posix-utilities.md#u-011) | `return [n]`: function/dot control transfer, default and explicit status, trap context; function parameter restoration. |
| [U-012](../posix-utilities.md#u-012) | `set`: variable listing with quoting and locale order, positional replacement, `--` and zero arguments; option families are O-001–O-018. |
| [U-013](../posix-utilities.md#u-013) | `shift [n]`: default/zero/count shifts; invalid or excessive counts may exit a non-interactive shell, otherwise require warning and non-zero status. |
| [U-014](../posix-utilities.md#u-014) | `times`: shell and child user/system accumulated times, required POSIX-locale format and success/error status. |
| [U-016](../posix-utilities.md#u-016) | `unset`: `-v` variables, `-f` functions, readonly errors, absent-name success and environment removal. |
| [U-019](../posix-utilities.md#u-019) | `cd`: HOME/CDPATH/OLDPWD, `-L`/`-P` and Issue 8 `-e`, path canonicalization, PWD/OLDPWD updates, output and failures. CSH-029 documents HOME choice; permitted PWD/OLDPWD variations need explicit expectations. |
| [U-020](../posix-utilities.md#u-020) | `command`: function suppression, special-builtin property suppression, `-p`, `-v`/`-V`, statuses; declaration-utility assignment context and alias interaction. |
| [U-023](../posix-utilities.md#u-023) | `getopts`: OPTIND/OPTARG, positional/explicit parameters, missing/unknown options, leading-colon diagnostics, end-of-options status 1 versus processing errors >1, reset with OPTIND=1. |
| [U-024](../posix-utilities.md#u-024) | `hash`: remember/report utility paths, `-r`, exclude functions/builtins from output, PATH invalidation and lookup errors. Do not assert unspecified listing format. |
| [U-027](../posix-utilities.md#u-027) | `read`: `-r`, Issue 8 `-d`, logical lines, IFS field distribution, EOF partial assignment/status 1, assignment errors >1, current environment and continuation prompt. |
| [U-029](../posix-utilities.md#u-029) | `ulimit`: `-H`/`-S`, `-a`, resources `-c`/`-d`/`-f`/`-n`/`-s`/`-v`, defaults, units, unlimited, inherited limits and errors. Test limit mutations in disposable child shells; isolate unspecified repeated options. |
| [U-030](../posix-utilities.md#u-030) | `umask`: octal/symbolic changes, no-operand output and `-S`, file creation effects and subshell isolation; default output style is unspecified but must be reusable; do not assume numeric formatting. |
| [U-033](../posix-utilities.md#u-033) | `pwd`: absolute directory output, `-L`/`-P`, logical PWD validation and errors; unlike cd it is not an intrinsic utility. |

Relevant documented choices: D-006, D-007 (pipeline environment only), U-019 (HOME), ENV-005 (profile classification). Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/state_fixture.c](../../tests/state_fixture.c)
- [tests/builtin_fixture.c](../../tests/builtin_fixture.c)
- [tests/builtins.py](../../tests/builtins.py)
- [tests/evaluation_cases.py](../../tests/evaluation_cases.py)
- [tests/assignment_fixture.c](../../tests/assignment_fixture.c)
- [tests/option_cases.py](../../tests/option_cases.py)

These are starting points for inspection, not claims that the complete rows
already pass. Reuse exact case names and assertions where they are sufficient;
add or split fixtures only for a concrete coverage gap.

## Acceptance criteria

- [ ] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [ ] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [ ] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [ ] Matrix rows and reverse ownership links reflect only the verified scope;
  broad rows are split where necessary and the CSH-012 compliance gate remains
  closed while any applicable requirements are unmet.

## Validation

Run the applicable focused suites above and the integration paths documented in
[Testing](../testing.md), including `make test test-pty test-harness`, Docker
and ASan/UBSan checks where the changed paths require them. Record exact case
names and results following the [evidence rules](../posix-evidence.md).
Reference-shell comparisons are separate observations, never normative oracles.

## Implementation notes/evidence

Allocated by the CSH-037 follow-up audit at baseline `58ca5c3`. The explicit
limitation and complete row list above replace reliance on already-completed
implementation tickets as owners of remaining verification work.
