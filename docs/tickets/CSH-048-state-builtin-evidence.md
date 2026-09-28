# CSH-048: Close shell state and builtin integration evidence gaps

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: `test/CSH-048-state-builtin-evidence`
- Issue: [#80](https://github.com/melliott18/cshell/issues/80)

## Goal

Map and reproduce existing tests by utility option/operand/status/environment clause, explicitly document selected unspecified or implementation-defined policies, test uncovered startup and cross-environment combinations, and retain profile exclusions only for source-conditional portions. Associate every row with exact assertions and native/Docker run records.

## Explicit current limitation

The [clause/condition map](../state-builtin-evidence.md) links all 24 families to exact assertions, implementation and selected policies. The 2026-09-28 continuation closes the named startup-allocation, directory/permission, listing/error, read-assignment, prompt and resource-unit partitions. Broader expansion, signal, option and host conditions retain CSH-047/054/051/060 ownership, and no row is promoted to whole-family verification. ENV-005 separates source-conditional UP/XSI processing from the applicable base prompt/trace consumers.

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

- [x] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [x] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [x] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [x] Matrix rows and reverse ownership links reflect only the verified scope;
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

### Initial audit scope (2026-09-26)

The [24-family clause map](../state-builtin-evidence.md) reconciles existing
state/builtin/assignment APIs and public runtime cases, adds 144 exact cross-mode
cases and 36 predicate observations, and records selected unspecified choices
separately from normative assertions. All new checks run through `make test`;
`make test-state-builtins` selects them directly.

The runtime now resets IFS, PPID and OPTIND, initializes PWD from a validated
logical path or physical cwd, and handles initialization allocation failure.
Raw storage import remains unchanged. `times` emits the POSIX-locale `%f`
precision and `ulimit -a` includes resource descriptions and units. The map
retains narrower untested permission/I/O/allocation/locale/option conditions;
those are not silently closed by this audit. CSH-012 remains closed to a
conformance claim. At the end of this initial audit, the second acceptance criterion remained open
for those residual conditions and the recorded validation failures. The
continuation below adds their concrete runtime partitions and fresh run records. The Linux LSan directory-output leak found during
validation is fixed, with the original failed run retained.

### Validation record

Source/tests: `ae993de53f2efcfd179e93ec3c632aa6b524b755`, based on `daa1be1`.
The first committed source manifest matches on native and Docker:
`fed0e528cbc7d9bdfae5fec911325bc9d06d8dc83b17a7e1177fe1ec67a75ce1`.
The first normal runs preceded two fixture-only refinements described in
[the artifact README](../evidence/csh-048/README.md); generated runtime scripts
and compiled C source were unchanged. Full earlier and final manifests are
retained in `validation.json`. Final code is
`1e08f41397ee978eda090d0338ea1ef2c5849009`, which replaces directory `dprintf`
calls with checked writes after Linux LSan exposed a closed-stdout allocation
leak. Corrected runs identify that revision separately, with source digest
`9d0b53965645842c7cba4bf9ecff0e424a3d8694453e3082b56ad1ca1680fc65`. All runs occurred on 2026-09-26; collection
UTC timestamps and exact executable hashes are in that record.

- Native: macOS 14.8.7 build 23J520, Darwin 23.6.0 arm64, runtime libSystem
  1345.120.2, Apple Clang 15.0.0, Python 3.12.2.
- Docker: Debian 12 bookworm, LinuxKit 6.4.16 aarch64, glibc 2.36
  (`2.36-9+deb12u14`), GCC 12.2.0 (`12.2.0-14+deb12u1`), Python 3.11.2;
  Docker Engine 24.0.6. Exact normal/base/sanitizer image IDs are retained.
- Normal flags: `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`,
  `-D_POSIX_C_SOURCE=200809L -Iinclude`, no additional linker libraries.
- Sanitizer flags: `-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
  -fsanitize=address,undefined -fno-omit-frame-pointer`, link
  `-fsanitize=address,undefined`; ASAN_OPTIONS/UBSAN_OPTIONS=`halt_on_error=1`,
  native MallocNanoZone=0. Helper executables omit instrumentation so process
  observations are not altered by sanitizer startup.

| Command / configuration | Result and precise limit |
| --- | --- |
| Native `make -j4 test test-pty test-harness` | All 1,600 runtime cases and module/API checks pass; harness 64/64. Job PTY 15/15 and fault PTY 1/1 pass. Runtime PTY 26 pass, 1 fails during cleanup: `traps: hangup signals background job`, `/bin/ps` exceeded the cleanup helper's one-second deadline. This initial run remains a failure. |
| Native serial `make test-state-builtins test-pty` | New exact cases 144/144 and observations 36/36; job PTY 15/15, fault PTY 1/1 and runtime PTY 27/27 pass with unchanged limits. |
| Docker `make -j4 test test-pty test-harness` | Pass: runtime 1,600/1,600; job PTY 15/15, fault PTY 1/1, runtime PTY 27/27; harness 64/64; module/API checks pass. |
| Docker `make test-state-builtins` on final fixtures | Pass: exact cases 144/144, observations 36/36. |
| Native ASan/UBSan `make -j2 test-state-builtins test-builtins test-state test-execute test-evaluation` | Pass: 144 exact cases, 36 observations, 304 evaluation cases; builtin API and 24 literal-executor cases, state/allocator fixtures, and 61 execution behavior cases plus API/fault checks. No sanitizer report. |
| Docker ASan/UBSan first serial focused run | Fail: observations 33 pass, 3 exceed five seconds after producing expected output (`times format and accumulated children (file)`, `ulimit query d (string)`, `ulimit default and inherited units (file)`). Subsequent targets not run after make stops. No ASan/UBSan diagnostic; timing failure is retained. |
| Docker ASan/UBSan retry before directory-output correction | Observations 36/36 pass. Exact cases 141 pass, 3 fail: `pwd output failure continues` in every mode. LSan reports an 8192-byte glibc allocation from `dprintf` on closed stdout. Corrected in `1e08f41`; no suppression or leak-detection disablement is used. |
| Final native and Docker normal `make test-state-builtins test-builtins` | Pass after directory-output correction: exact cases 144/144, observations 36/36, builtin API and 24 literal-executor cases. |
| Final native ASan/UBSan `make -j2 test-state-builtins test-builtins` | Pass after directory-output correction: 144 exact cases, 36 observations, builtin API and 24 literal-executor cases; no sanitizer report. |
| Final Docker ASan/UBSan serial focused targets | Pass after correction: 144 exact cases, 36 observations, 304 evaluation cases, builtin API and 24 literal-executor cases, state/allocator fixtures, and 61 execution behavior cases plus API/fault checks. No sanitizer report; leak detection remains enabled. |

The normal invocation suite skips two unequal-ID probes on non-root hosts
(CSH-046); that separate capability is not claimed by this ticket. Native
portability skips translated libc diagnostics because installed candidate
locales have no translation (CSH-042); Docker exercises them. Source-owned
UP/XSI exclusions are detailed under ENV-005, not inferred from these skips.
Logs preserve names and failure details; a retry never changes the outcome of
the original run.

### Continuation implementation (2026-09-28)

Implemented on the separate `test/CSH-048-state-builtin-evidence` worktree,
starting at `b1b6b15`. Source commits `47aae4e`, `7d50b61` and `4144945` add 228 exact
cross-mode cases (372 total), 102 public-entry edge/fault checks, and two PTY
cases. The 36 predicate observations are retained. New checks also run through
`make test`; `make test-state-edges` selects the edge/fault partitions.

The added evidence exposed and fixes:

- `read` discarded a trailing non-whitespace separator from the last variable
  and prevalidated later readonly operands before assigning earlier ones.
  Issue 8 requires the unsplit remainder and ordered assignments; later operands
  remain unchanged after failure under the selected permitted policy.
- Here-document continuation prompts ignored PS2. They now use its current
  literal value under the selected base profile; read's -r suppression and
  literal PS2 are asserted on a controlling terminal.
- Listing/utility output used dprintf on closed descriptors, and times/umask/
  ulimit output errors could lack diagnostics. Checked writes handle EINTR,
  short writes and zero/error writes, with fatal/suppressed/interactive checks.
- cd's rollback descriptor incorrectly required read permission on cwd. Search
  handles allow leaving searchable but unreadable directories. Logical paths
  beyond PATH_MAX now use relative syscall operands or component-wise directory
  handles, preserving full PWD and resolving logical parents/symlinks before
  changing cwd; nonexistent components before /.. still fail.

The [expanded map](../state-builtin-evidence.md#additional-runtime-partitions-2026-09-28)
reconciles existing CSH-055 dot-read failures and allocation/context witnesses,
adds exact error/attribute/locale/limit assertions, and distinguishes required
behavior from malformed-environment and invalid-syntax policies. It does not
claim the full cross-product of arbitrary programs or kernel resource
implementation behavior. CSH-012 remains closed to a conformance claim.

### Continuation validation

See [complete logs, identities, source hashes and reproduction commands](../evidence/csh-048/completion/README.md).
Source/test manifests distinguish the initial continuation (`47aae4e`) from
the final lookup-output correction (`4144945`), which includes the intermediate
long-path correction (`7d50b61`); documentation was added afterward.
The earlier 2026-09-26 failures above remain failures, and the three development
fixture mistakes in the new dot permission probe are also retained explicitly.

Final results are recorded in `completion/runs.json` alongside immutable binary
and image identities. Native and Docker normal runs each exercise the full
3,341-case runtime suite, module/API/fault tests, 30 job PTY cases, one job fault
PTY case, 32 runtime PTY cases and 73 harness self-tests. CSH-048's focused
partitions comprise 372 exact cases, 36 predicate observations and 102 edge/fault
checks. Permission and non-C locale checks have no skips on these non-root hosts.

The final normal and focused sanitizer builds share source/test digest
`cf5caf1ffa9f0989ff974b2bad237b7d863e4b74935e91348a5b6a3ee19c9698`.
The final native/Docker ASan+UBSan focused runs pass `test-state-builtins`,
`test-builtins`, `test-execute` and `test-evaluation` with leak detection enabled and no sanitizer
report. Native uses Apple Clang 15.0.0 / libSystem 1345.120.2 on macOS 14.8.7 arm64;
Docker uses GCC 12.2.0 / glibc 2.36 on Debian 12 aarch64. Complete flags, executable
hashes and preceding broader sanitizer results are in the linked identities and
run manifest. Non-UTF-8 pathname/locale skips remain CSH-053, catalog availability
CSH-042, and non-root unequal-ID skips CSH-046; none applies to the 102 state edge
checks. All ticket acceptance criteria are ready for review; integration into
main, rather than this branch, changes the ticket status to done.

An additional closed-stdout hash probe on `47aae4e` reproduced an 8,192-byte
glibc dprintf leak under Linux LSan. `4144945` extends checked writes and output
diagnostics to hash, command/type reports and executor diagnostics. Twelve new
cross-mode scenarios cover hash, -v/-V reports of builtins/functions/reserved
words/paths/aliases, and closed stderr. The original failed probe and its source
identity are retained separately from the passing regression suites.
