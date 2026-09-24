# CSH-039: Switch cshell to the replacement runtime and delete the legacy code

- Status: review
- Type: refactor
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-018, CSH-020
- Branch: refactor/CSH-039-legacy-retirement
- Issue: [#41](https://github.com/melliott18/cshell/issues/41)

## Goal

Make the replacement runtime the only `cshell` implementation and remove every
legacy runtime/build dependency without waiting for the remaining POSIX features.

## Scope

- Wire the production entry point and default native/Docker builds to the new
  input, lexer, parser, state, and executor modules validated by CSH-018/020.
- Delete `src/legacy/`, `include/cshell/legacy.h`, the old input/dispatch loop,
  legacy object/scanner rules, compatibility adapters, and fallback switches.
- Remove temporary candidate executables/drivers and prototype-only test
  allowances; unit-test drivers remain where they test replacement module APIs.
- Remove tools/packages needed only by the deleted scanner from build, Docker,
  and CI instructions. Flex may remain only if the new lexer independently uses
  it with documented rationale, not because the prototype used it.
- Update current architecture, supported behavior, and build documentation.
  Preserve historical tickets and Git history as records of previous work.

## Acceptance criteria

- [x] Clean-checkout `make`, `make test`, and `make docker-test` build/run only
  the replacement `cshell`; no environment setting or alternate public mode
  selects legacy execution.
- [x] Command strings, script files, and stdin support the declared bootstrap
  subset: literal simple commands, external lookup/statuses, bootstrap `cd` and
  `exit`, ordered redirections, and concurrent pipelines. Empty input, EOF,
  failures, and non-interactive output follow CSH-018/020 evidence.
- [x] Unsupported constructs/expansions fail with a diagnostic before that
  construct has side effects; no fallback, silent reinterpretation, or promise
  of compatibility with legacy extensions is used to pass the suite.
- [x] The legacy directory/header and build dependencies are deleted, no
  replacement module imports them, and linked objects/symbols contain no legacy
  runtime. Review confirms the old dispatcher was not copied into renamed files.
- [x] Temporary migration drivers, fallback flags, and prototype prompt/output
  allowances are gone. Any remaining temporary literal-word adapter is new code
  owned by CSH-008, explicitly bounded, and unable to call legacy code.
- [x] Native and Docker regression/sanitizer results cover input ownership,
  child failure, descriptor restoration, high-volume pipelines, and cleanup.
  Current documentation describes the replacement and remaining POSIX gaps.

## Validation

Run clean native and Docker builds/tests; record platform and compiler versions.
Exercise the bootstrap subset through all invocation modes with exact output,
status, filesystem, and timeout assertions. Run relevant ASan/UBSan cases and
controlled failure fixtures from CSH-004/016/019/020. Inspect build commands,
dependency files, linked objects/symbols, and source references for legacy use;
inspect the diff to distinguish actual replacement from renamed/copied code.
Historical documentation references are permitted, executable legacy paths are
not. Verify the default build succeeds without the deleted sources and that no
cached generated scanner or object hides a dependency.

## Implementation notes/evidence

CSH-018 validates invocation/status using the replacement candidate; CSH-020
provides pipeline coverage. This cutover does not wait for CSH-021 lists/groups,
full expansion, compounds, or job control. Coordinate build/entry-point changes
with CSH-021 if it runs concurrently. CSH-006 cannot complete until this ticket
is done; CSH-037 later checks that legacy paths or expired adapters did not return.

### Implementation

`src/main.c` now contains the CSH-018 complete-command runtime with CSH-021's
persistent execution context, replacing the prototype loop. `cshell` links main,
input/invocation, lexer/parser/AST, alias storage, quote, state, builtin, executor,
and redirection objects. The legacy source directory/header, scanner rules,
Flex dependency, `src/candidate.c`, and alternate executable target are deleted.
The CSH-008-owned literal adapter is unchanged and cannot call legacy code.

Default pipe and terminal suites now run the public executable, once per target.
Focused runtime targets remain convenient selectors for that same executable;
module API drivers and harness self-test helpers remain independent test tools.
Prototype suites and `strip_prompt` are rejected by the harness schema, and
exact output comparison has no normalization path. New public-runtime cases
exercise an 8 MiB four-stage pipeline, continuation after a failed pipeline
child, and a later stage's unsupported expansion with no first-stage file effect,
all through strings, scripts, and stdin. The terminal exit case retains a
foreground ownership assertion.

Native and Docker sanitizer CI now run the full `test` and `test-pty` suites,
including input ownership/fault and execution-context tests. Current usage,
architecture, test defaults, module integration status, and POSIX limitations
are updated. Historical ticket records and the matrix's explicitly historical
smoke evidence remain available.

### Validation evidence (2026-09-24 UTC)

- Native macOS arm64 / Darwin 23.6.0, Apple Clang 15.0.0, Python 3.12.2:
  clean worktree `make clean && make -j4`, followed by
  `make -j4 test test-pty test-harness`, passed the module suites, runtime suites,
  and **62 harness self-tests**. After adding the cutover pipeline cases,
  `make test-runtime test-runtime-pty` passed **279 pipe cases** and **9 PTY
  cases**, while `make test-context` passed **60 behavior cases** plus API/fault
  checks, with no failures or skips. The final clean build also passed with
  `LEX=false`, and the README command-string example printed `hello world`.
- Debian Bookworm Linux aarch64, GCC 12.2.0, Python 3.11.2, Docker 24.0.6:
  `make docker-test DOCKER_IMAGE=cshell-test:csh-039-integration` passed all
  module suites and **279 runtime cases**, including **60 context behavior cases**
  plus API/fault checks. `docker run --rm --init
  cshell-test:csh-039-integration make test-pty test-harness` passed **9 terminal
  cases** and **62 harness self-tests**.
  The source-only Docker build contains neither `flex` nor `lex`.
- Native ASan/UBSan: after `make clean`, ran
  `ASAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 UBSAN_OPTIONS=halt_on_error=1
  make -j4 test test-pty CC=clang` with
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
  -fsanitize=address,undefined -fno-omit-frame-pointer'` and
  `LDFLAGS='-fsanitize=address,undefined'`. All module suites, **279 runtime
  cases**, **60 context behavior cases** plus API/fault checks, and **9 PTY
  cases** passed without sanitizer findings.
- Docker ASan/UBSan: `docker run --rm --init -e ASAN_OPTIONS=halt_on_error=1
  -e UBSAN_OPTIONS=halt_on_error=1 cshell-test:csh-039-integration sh -c "make clean &&
  make -j2 test test-pty CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow
  -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'
  LDFLAGS='-fsanitize=address,undefined'"` passed all module suites, **279 runtime
  cases**, **60 context behavior cases** plus API/fault checks, and **9 PTY
  cases**, without sanitizer findings or skips. These
  include **63 input**, **61 lexer**, **223 parser**, **110 final-field**,
  **73 execution**, and **55 pipeline** behavior checks plus API/fault sweeps.
- Source and build audit: `cc -D_POSIX_C_SOURCE=200809L -Iinclude -MM` for every
  production source and `nm cshell` contain no legacy or generated-scanner
  dependencies/symbols. Clean builds contain neither `build/legacy` nor
  `build/cshell-candidate`. The new main body matches the prior replacement
  candidate after integrating CSH-021's persistent context entry point; it is
  not the deleted prototype dispatcher. `git diff --check` and changed-document
  local-link checks passed.

The original checkout remains unchanged. Hosted CI is configured for native
Linux/macOS and Docker; its run results are separate from the local evidence
above. Remaining POSIX gaps are unchanged and documented in the runtime guide.
