# CSH-049: Close execution, redirection and control-flow evidence gaps

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: test/CSH-049-execution-evidence
- Issue: [#81](https://github.com/melliott18/cshell/issues/81)

## Goal

Map existing exact fixtures and their implementation revisions; decompose ordering, descriptors, concurrency/status, lookup, loops/functions and error consequences. Document and test descriptor, assignment, pipeline and signal-status policies; integrate CSH-043 boundary evidence and CSH-042 relevant case findings without treating those fixes as complete family verification.

## Explicit current limitation

The [25-row clause map](../execution-evidence.md) now identifies exact assertions, policies and narrower gaps. [CSH-055](CSH-055-execution-contract-gaps.md) owns a confirmed prefix-PATH/builtin lookup defect and residual execution contracts. CSH-043’s completed offset evidence and CSH-042’s locale witnesses retain their bounded scope; CSH-053 owns non-UTF-8 lexical gaps. Full family verification remains open.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [SH-009](../posix-matrix.md#sh-009) | Do not fail pathname expansion because of file size; document redirection offset maximum. |
| [RED-001](../posix-matrix.md#red-001) | Apply redirections left to right, expand targets in context, use default descriptor numbers and restore parent descriptors. |
| [RED-002](../posix-matrix.md#red-002) | Open `<`, `>` and `>\|` with specified creation/truncation and noclobber handling. |
| [RED-003](../posix-matrix.md#red-003) | Append using `>>`, creating missing files without truncating existing data. |
| [RED-004](../posix-matrix.md#red-004) | Deliver here-documents with quoted/unquoted delimiters, tab stripping, expansion and evaluation timing. |
| [RED-005](../posix-matrix.md#red-005) | Duplicate/close input and output descriptors using `<&` and `>&`, including invalid-descriptor failures. |
| [RED-006](../posix-matrix.md#red-006) | Open read/write redirections with `<>`, creation and offset behavior. |
| [EXEC-001](../posix-matrix.md#exec-001) | Process simple-command expansion, redirection and assignment in the specified order and permitted alternatives. |
| [EXEC-002](../posix-matrix.md#exec-002) | Apply prefix assignment lifetime by no-name/external/special/function category; enforce readonly errors. |
| [EXEC-003](../posix-matrix.md#exec-003) | Handle assignment/redirection-only commands and last-substitution status without corrupting parent state. |
| [EXEC-004](../posix-matrix.md#exec-004) | Search commands with correct special-builtin/function/intrinsic/PATH precedence; execute pathname commands and format fallback. |
| [EXEC-005](../posix-matrix.md#exec-005) | Pass argv, environment and open descriptors to external commands; apply rules for initially closed standard descriptors. |
| [EXEC-006](../posix-matrix.md#exec-006) | Connect concurrent pipeline stages before command redirections and wait for required completion. |
| [EXEC-007](../posix-matrix.md#exec-007) | Compute pipeline status and `!` negation, including Issue 8 pipefail selection. |
| [EXEC-008](../posix-matrix.md#exec-008) | Execute sequential, AND and OR lists with short-circuiting, precedence and final status. |
| [EXEC-010](../posix-matrix.md#exec-010) | Execute brace groups in the current environment and parenthesized groups in subshell environments. |
| [EXEC-011](../posix-matrix.md#exec-011) | Execute for loops, including positional-parameter defaults, expansion timing and zero-iteration status. |
| [EXEC-012](../posix-matrix.md#exec-012) | Execute case matching, pattern expansion, no-match status, `;;` termination and `;&` fall-through. |
| [EXEC-013](../posix-matrix.md#exec-013) | Execute if/elif/else, while and until with condition-controlled evaluation and specified statuses. |
| [EXEC-014](../posix-matrix.md#exec-014) | Define/invoke functions with call-time redirections, argument restoration, status, scope and separate function/variable namespaces. |
| [EXEC-015](../posix-matrix.md#exec-015) | Apply interactive/non-interactive consequences for syntax, expansion, assignment, utility, redirection and read errors. |
| [EXEC-016](../posix-matrix.md#exec-016) | Retain zero/nonzero statuses; report 126/127 execution failures and documented signal-derived values above 128. |
| [U-003](../posix-utilities.md#u-003) | `break [n]`: default depth, nested/outermost loop transfer, same-environment enclosure, status; isolate non-lexical enclosure cases. |
| [U-004](../posix-utilities.md#u-004) | `continue [n]`: default depth, nested/outermost loop continuation, enclosure and status; isolate non-lexical enclosure cases. |
| [O-026](../posix-utilities.md#o-026) | Document shell redirection offset maximum and demonstrate representative boundary/error behavior on each supported system. CSH-019 chooses/documents the descriptor policy; CSH-037 records platform limits. |

Relevant documented choices: D-002, D-006, D-007. Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/execute.py](../../tests/execute.py)
- [tests/pipeline.py](../../tests/pipeline.py)
- [tests/contexts.py](../../tests/contexts.py)
- [tests/control_flow_cases.py](../../tests/control_flow_cases.py)
- [tests/runtime_cases.py](../../tests/runtime_cases.py)
- [tests/substitution_cases.py](../../tests/substitution_cases.py)
- [tests/portability.py](../../tests/portability.py)

These are starting points for inspection, not claims that the complete rows
already pass. Reuse exact case names and assertions where they are sufficient;
add or split fixtures only for a concrete coverage gap.

## Acceptance criteria

- [x] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [ ] Remaining applicable runtime cases pass on supported native macOS and
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


## Implemented audit scope

Added 66 three-mode execution scenarios (198 cases) and ten error-consequence
categories in three noninteractive plus two interactive modes (50 cases).
`make test-execution-evidence` selects all 248; they are also included in
`make test`, Docker and existing sanitizer CI. New helper operations distinguish
true O_APPEND behavior from an initial seek and check shared read/write offsets.
The shell runtime itself is unchanged.

The [clause map](../execution-evidence.md) links every scope row to normative
sources, implementation, exact old/new witnesses and remaining owners. It
separates descriptor/assignment/function/pipeline/signal policies from required
outcomes and integrates the existing 36 offset probes and locale case findings.
No entire family has been relabeled verified. CSH-012 remains closed.

The audit reproduced the prefix-PATH/builtin selection failure on native macOS
and Docker Linux. [CSH-055 / #92](https://github.com/melliott18/cshell/issues/92)
contains the diagnosis and remaining runtime obligations. The separate strict
`execution-known-gaps.json` reproducer asserts the required `custom-pwd\n`
output and **fails** on both hosts; it is not a passing regression or a default
suite case. This audit is ready for review with that limitation explicitly open.

## Validation record

Source/suite revision: `9f755dec9d7c8840f3e38e95011eceb64e55e662`, based on
`daa1be1`. Normal runs preceded the commit with identical source/test bytes;
subsequent edits affect documentation only. The Makefile/src/include/tests
fingerprint is `8b0645c281259c58b21d989cefb639d63ea20759df9f5a6570222e2a960c5124`.
No scanner generator/runtime is used. Records collected on 2026-09-26 UTC.

[Machine-readable identities](../evidence/csh-049/validation.json) record
source-file hashes, binary realpaths/hashes, generated suite hashes, compiler,
flags, Python, OS/libc, relevant inherited API-runner environment and Docker
image identity. [Compressed logs](../evidence/csh-049/README.md) preserve each
case result, including failed attempts. Collection timestamps are not asserted
to be exact run-start timestamps. Runtime fixture environments/assertions are
specified in the [map](../execution-evidence.md#fixture-identities-and-conditions).

| Environment / command | Result |
| --- | --- |
| macOS 14.8.7 build 23J520, Darwin 23.6.0 arm64, Apple Clang 15.0.0, Python 3.12.2; `make -j4 test` then `make test-pty` | PASS: 1,704 runtime cases, 210 control, 148 jobs, 36 offset, 162 portability, all module/API/fault targets; 15 jobs PTY, one terminal fault and 27 runtime PTY cases. Two Linux-root invocation skips and one untranslated-libc diagnostic capability skip; no new execution-case skips. |
| Same native build, first `make test-harness` | FAIL: one of 64 self-tests, `test_repeated_cleanup_after_parent_exit_accepts_verified_darwin_eperm`, timed out at its one-second bound and observed -9 instead of 0. Other 63 passed. The following isolated retry passed all 64 in 24.779s with unchanged limits; the failed log remains evidence. |
| Debian bookworm, Linux 6.4.16-linuxkit aarch64, GCC 12.2.0, glibc 2.36, Python 3.11.2; Docker `make -j4 test && make test-pty && make test-harness` | PASS: 1,704 runtime, all normal module/API/fault/offset/portability targets, 15 jobs PTY, one terminal fault, 27 runtime PTY and 64 harness self-tests (11.250s). Two Linux-root invocation skips in the unprivileged suite. |
| Same Docker image, `--user 0 python3 tests/invocation.py ./cshell` | PASS: all 51 invocation probes, including unequal real/effective uid and gid; zero skips. |
| Native ASan/UBSan focused command below | PASS: 248 execution, 210 control, 36 offset, 61 execution API behavior, 52 pipeline and 60 context behavior cases, plus their API/fault checks. No sanitizer findings or skips. |
| Docker ASan/UBSan focused command (`-j2`, same targets/flags) | Combined make FAIL: all 248 new execution cases passed; offset suite 33 passed/3 timed out. Remaining execution/pipeline/context/control API targets were not-run after make stopped scheduling. No sanitizer diagnostics. |
| Native and Docker `execution-known-gaps.json` | FAIL as recorded above: working-directory output instead of `custom-pwd\n`; status 0, stderr empty. Owned by CSH-055. |

Normal flags: `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`, CPPFLAGS
`-D_POSIX_C_SOURCE=200809L -Iinclude`, no extra link flags/libraries. System
libraries on macOS are identified by macOS/Darwin build (shared-cache libSystem).
Docker engine 24.0.6; normal image
`sha256:11f34d504c3a749522cda49ea27566759f961fffcca19583cec968e9d5807f71`,
from `debian:bookworm-slim`. The Docker identity record reconstructs generated
suite/helper hashes from the same immutable image because the completed normal
test container was removed; it does not claim those are a retained test process.

Normal binary SHA-256:

- Native: `54126453f5d15fffa203f922a58c7e39ea8e0519d29a9d383a8b700c358eea59`.
- Docker: `f2941e02ff522749f3146e10dbc7172ced88462a289f551fd8f9cb6759561069`.

Sanitizer reproduction in a separate source copy (native used `build/asan`):

```sh
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
make -j4 test-execution-evidence test-execute test-pipeline test-context \
  test-control test-redirection-offset \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The external descriptor-observer helper remains uninstrumented under the
existing Makefile contract; the shell and module/fault fixtures are instrumented.
The runtime harness passes only its controlled environment (and macOS allocator
setting), so its sanitizer subprocesses use default ASan/UBSan options. API
runners inherit the supplied halt options.

The untranslated libc diagnostic skip is CSH-042’s installed-catalog condition;
the two identity skips are CSH-046’s Linux-root condition, separately covered
above. No PTY or locale capability was substituted for applicable execution
evidence. Native Linux outside Docker remains not-run locally. The complete
platform acceptance box stays open while the recorded harness timeout and
CSH-055/other residual obligations remain unresolved.


Docker sanitizer failures were `positioned first rejected byte (string)`,
`(file)` and `(stdin)`: each exceeded the unchanged five-second bound and
observed status -9 instead of 23. All other offset cases and all new execution
cases passed. Host load averages were approximately 620/581/522 during the run,
with other sanitizer containers active. Contention is a possible explanation,
not a proven cause; the failed run is retained. The sanitizer container exited
2 and its binary/suite identities were copied before removal. CSH-049 retains
this platform-validation gap with the CSH-043 offset witnesses; native focused
sanitizer success does not erase it.

[PR #93](https://github.com/melliott18/cshell/pull/93) contains this audit.


### Hosted integration checks

[Run 36252848695, attempt 1](https://github.com/melliott18/cshell/actions/runs/36252848695/attempts/1)
tested `ed4eb175cec221c37ced130c29dfe1d6e26ce8d9`, whose implementation/test
bytes are unchanged from `9f755de`. Ubuntu 24.04/GCC and Docker Linux passed
all normal, terminal, harness and full ASan/UBSan stages, including all 1,704
runtime cases and all 36 offset cases in both normal and sanitizer builds.
These independent passes do not erase the local Docker timeout observations.
Native Linux is therefore exercised by CI, although not available locally.
Ubuntu runner image: `20260920.314.1`, Python 3.11.16.

Hosted macOS 15.7.9 arm64, image `20260907.0337.1`, Python 3.11.9 passed normal
runtime (1,704), PTY and all 64 harness tests, then **failed** the existing
sanitizer PTY case `repeated background resumes preserve prompt and terminal`:
expected 7,216 combined terminal bytes, captured 7,438. The logger truncates
the displayed byte prefixes, so this record does not infer the exact extra
message or root cause. Make stopped scheduling after `test-jobs-pty` failed;
its remaining full-sanitizer scope is incomplete. The archived log retains
all executed results. CSH-054 owns this job/terminal contract investigation.
The push run 36252831240 failed the existing sanitizer case `current previous
and ambiguous job operands`: expected 317 bytes, captured 432, including
`cshell: fg: cannot foreground job: %-` and a `Done(130)` notification. Its log
is retained separately as `hosted-push-macos.log.gz`; CSH-054 also owns this
observation. A failed-job retry was requested without changing code, fixture
expectations or limits.

Hosted logs are supplementary integration evidence: runner image/build commands
are recorded, but these CI jobs do not publish binary hashes. They do not
replace the detailed local binary identities or promote any broad matrix row.
