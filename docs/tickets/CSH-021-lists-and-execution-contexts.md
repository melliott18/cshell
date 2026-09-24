# CSH-021: Execute lists, groups, and background contexts

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-020
- Branch: feature/CSH-021-lists-and-execution-contexts
- Issue: [#22](https://github.com/melliott18/cshell/issues/22)

## Goal

Complete AST composition around pipelines with explicit current-shell, subshell,
and asynchronous execution contexts in the replacement runtime.

## Scope

- Execute sequential lists, AND/OR lists, groups, and asynchronous lists.
- Define context ownership for state, descriptors, children, and last status.
- Isolate subshell state and preserve current-shell mutations where required.
- Register background children and expose the last background identifier.
- Build on the new executor without a legacy fallback; CSH-039 independently
  owns the default-binary cutover and complete legacy deletion.

## Acceptance criteria

- [x] Sequential and AND/OR lists run only required commands, preserving specified
  precedence, short-circuiting, and final statuses in behavioral fixtures.
- [x] Brace-group mutations persist in the current shell, while parenthesized
  subshell mutations remain isolated; group redirections have correct lifetimes.
- [x] Asynchronous lists return without waiting for completion, publish the
  applicable background identifier, and eventually reap their owned children.
- [x] Nested contexts and failed redirections preserve parent state/descriptors;
  cleanup tests include background children and interrupted waits.
- [x] All list/group behavior uses the shared replacement executor; architecture
  docs describe context ownership and remaining limitations.

## Validation

Run native and Docker fixtures for nested groups, filesystem/state effects,
short-circuiting, list statuses, and asynchronous completion under timeouts.
Use helper synchronization instead of sleep-only assertions for background
behavior and child reaping. Run the retained regression suite and sanitizer
checks against the replacement runtime, recording whether CSH-039 has already
switched the default executable. Coordinate changes to build/entry-point files
with CSH-039 if these tickets proceed in parallel.

## Implementation notes/evidence

This ticket supplies execution contexts consumed by later compound commands and
functions; their syntax and full behavior remain CSH-009. Background execution
here does not establish interactive job control. Coordinate stored background
identifiers and status fields through the CSH-022 state interface.


### Implementation

`csh_execute_context_ast()` prepares an owned literal execution plan and
composes sequential/AND/OR lists, braces, subshells and asynchronous items through
the replacement command/pipeline engines. Group stages are supported in
pipelines. Brace state/cwd changes persist; forked contexts isolate them.
Redirection backups exclude operands throughout nested bodies, and restoration
covers failures and exit requests. Ordinary redirection errors participate in
short-circuiting; special-builtin error policy stays context-dependent.

A persistent execution context owns registered background PIDs independently of
shell-state snapshots. Asynchronous pipelines register every stage and publish
the final PID through CSH-022; simple external background commands exec directly
in their published process. Explicit polling/blocking reaping retries EINTR and
never consumes unrelated children or overwrites last status/background identity.
The candidate polls at execution boundaries and detaches unfinished jobs on
exit. Idle SIGCHLD wakeups, retained wait statuses, process-group cancellation,
and interactive job control remain CSH-011 work. General expansion, including
command spelling of `$!`, remains CSH-008 work. CSH-039 has **not** switched the
default executable; `cshell` remains the prototype.

### Validation evidence (2026-09-23)

Environment: native macOS arm64, Darwin 23.6.0, Apple Clang 15.0.0;
Linux/GCC through Docker Engine 24.0.6 using image `cshell-test:csh-021`.

- `make -j4 test test-pty test-harness`: passed the retained native suite,
  candidate terminal cases and all 61 harness self-tests.
- Final `make -j4 test-context test-runtime test-runtime-pty`: passed 60 context
  behavior cases plus API/fault checks, 270 cross-mode runtime cases, and nine
  candidate terminal cases.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-021`: passed the full Linux suite,
  including all 60 context cases, 73 simple execution cases, 55 pipeline cases,
  their API/fault checks and 270 cross-mode cases.
- `docker run --rm --init cshell-test:csh-021 make test-pty test-harness`: passed
  candidate/prototype terminal suites and all 61 Linux harness self-tests.
- Clean native ASan/UBSan build with `-Werror`, `-g -O1`,
  `-fsanitize=address,undefined`, and `-fno-omit-frame-pointer` passed
  `test-lexer test-parser test-alias test-state test-expand test-builtins
  test-execute test-pipeline test-context test-runtime test-runtime-pty`.
  `ASAN_OPTIONS=halt_on_error=1`, `UBSAN_OPTIONS=halt_on_error=1` and
  `MallocNanoZone=0` were set; no sanitizer findings.
- `git diff --check`: passed.

Background fixtures use pipe/FIFO synchronization, assert the actual helper PID
against the stored background PID (also for a pipeline's final stage), prove
return before gate release, verify unrelated children stay waitable, and confirm
owned PIDs are no longer waitable after reaping. Fault checks sweep preparation
and registry allocations, inject pipe/fork/wait failures in foreground and
background group pipelines, retry interrupted waits, and retain background
ownership across failed polling. Documentation describes the direct-child
cleanup boundary and limitations; these checks do not claim full POSIX support.

Integrated into `main` through [pull request #62](https://github.com/melliott18/cshell/pull/62)
on 2026-09-23. Implementation commit: `5f77874`; merge commit: `cbd3d67`.
Both hosted workflows passed Ubuntu/GCC, macOS/Clang, and Docker Linux after a
single macOS harness startup-timing retry. GitHub closed issue #22 when the pull
request merged.
