# CSH-020: Execute pipelines with explicit child and descriptor ownership

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-019
- Branch: feature/CSH-020-pipeline-lifecycle
- Issue: [#21](https://github.com/melliott18/cshell/issues/21)

## Goal

Compose simple execution into arbitrary-length concurrent pipelines that finish
without pipe deadlocks, leaked descriptors, or lost child statuses.

## Scope

- Create and connect pipeline stages through the CSH-019 execution interface.
- Record child ownership and each stage's status without waiting too early.
- Close unused pipe ends in parent and children, including partial setup failure.
- Implement default pipeline status and negation; reserve `pipefail` for CSH-010.
- Define the stage-status interface that later option and job-control work uses.

## Acceptance criteria

- [x] Three-or-more-stage and high-volume pipelines run concurrently, deliver
  expected output, and terminate under bounded regression timeouts.
- [x] Every unused descriptor is closed and owned child is reaped; an unrelated
  child fixture keeps its status available to its own owner.
- [x] Default final-stage status and pipeline negation match specified behavior,
  including a failed earlier stage and a failed final stage.
- [x] Injected pipe/fork/redirection failures after some stages have launched
  unwind the partial pipeline without hangs or leaked children/descriptors.
- [x] Pipeline builtin state follows the documented execution-environment choice,
  and stage status/ownership APIs are documented for CSH-010 and CSH-011.

## Validation

Run native and Docker pipeline fixtures against the replacement runtime with
large-output, early-consumer-exit,
missing-command, builtin-stage, and status/negation fixtures. Run bounded resource
failure fixtures at each stage boundary and check ownership with deterministic
hooks or available platform facilities. Use sanitizer builds for cleanup paths.
Record the candidate target used before CSH-039 switches `make test` and
`make docker-test` to the replacement executable by default.

## Implementation notes/evidence

Pipe capacity must not determine whether a test succeeds: launch the necessary
stages before blocking on completion. Retain all stage statuses even though the
default result uses the final stage. Interactive process groups and terminal
ownership remain CSH-011 work; this ticket defines their child-lifecycle boundary.


### Implemented contract

`execute.c` composes the existing prepared-command, lookup, builtin, and
redirection interfaces into concurrent foreground pipelines. The literal AST
path prepares every simple stage before launch and rejects unsupported later
stages without side effects. Multi-stage builtins execute in children; singleton
commands retain the current execution environment.

A rolling pipe pair bounds parent descriptor usage independently of stage count.
Private pipes are CLOEXEC, moved off closed standard descriptors, and closed in
children before ordered redirections. All stages launch before any wait.
Partial parent setup failure closes every remaining pipe, kills all unreaped
owned children, and reaps each by positive PID. Child setup/exec failures are
ordinary stage statuses. The default result is the final stage's status with
logical negation for `!`, while every stage's original status remains available.

`csh_execute_pipeline()` accepts prepared commands;
`csh_execute_pipeline_ast()` adapts one foreground simple-command pipeline;
`csh_execute_ast()` exposes the summary. The owned result vector records PID,
command category, completion/reaping flags, raw wait status, and shell status.
See [Pipeline lifecycle and stage results](../execution.md#pipeline-lifecycle-and-stage-results)
for cleanup requirements and CSH-010/CSH-011 integration boundaries. Process
groups, job control, pipefail, compound stages, and the default-runtime switch
remain with their existing tickets.


### Validation evidence (2026-09-23)

- Native macOS arm64 / Apple Clang 15: `make -j4 test test-pty test-harness`
  passed all replacement suites, four prototype pipe cases, one prototype PTY
  case, and all 61 harness self-tests. The existing generated legacy scanner
  retains its signedness warning; replacement handwritten sources are clean.
- Final focused `make test-execute test-pipeline` checks passed **68 existing
  simple-command cases** and **54 pipeline behavior cases**, plus API/fault
  checks. The former unsupported-pipeline case moved from rejection coverage to
  the new pipeline suite. Candidates are `build/tests/execute_fixture`,
  `build/tests/pipeline_fixture`, and `build/tests/execute_faults --pipeline`;
  this is replacement module evidence before CSH-039's default-runtime cutover.
- Pipeline fixtures include 48 stages under a 64-fd limit, an 8 MiB stream,
  early consumer exit, statuses/negation, signal status, builtin isolation,
  redirection precedence, and all seven combinations of closed standard fds.
  Repeated API runs retain all stage statuses and leave an unrelated exited
  child available to its owner.
- Fault checks sweep pipeline/adapter/launch allocations; all four pipe and five
  fork boundaries in a five-stage pipeline; all eight pipe-flag and eight
  low-fd relocation boundaries; every wait boundary; and connection, open,
  duplication, saved-fd, temporary-file, and child-allocation failures at every
  stage. Partial-launch fixtures use 30-second sleepers under a 25-second
  fixture deadline and verify every launched PID is already reaped, every
  acquired parent descriptor is released, and live tracked allocations are zero.
- A source-only snapshot without `src/legacy`, `src/main.c`, or
  `include/cshell/legacy.h` passed `make -j4 test-execute test-pipeline CC=clang
  LEX=false` with `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror
  -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`,
  `LDFLAGS='-fsanitize=address,undefined'`, and both sanitizers set to
  `halt_on_error=1`. An initial sanitizer-discovered fixture array lifetime bug
  was corrected; the final run passed with no diagnostics.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-020` passed all replacement
  suites, including the final 54 pipeline cases and ownership/fault checks,
  plus the four prototype cases under Debian Linux/GCC.
- A clean Linux/GCC `make -j2 test-execute test-pipeline LEX=false` in that image
  passed with the same strict sanitizer flags, `-DNDEBUG`,
  `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`, and
  `UBSAN_OPTIONS=halt_on_error=1`, without sanitizer/leak diagnostics.
- `make test-pipeline` is included in `make test`, Docker, and the native CI
  ASan/UBSan command. The descriptor-observer helper remains uninstrumented for
  the previously documented macOS sanitizer startup behavior; executor,
  parser/state, API fixtures, and fault objects remain instrumented.

Integrated assignment environments and state builtins before merge. The combined
pipeline suite passed 55 behavior cases, including exported prefix assignments
for external stages and isolation of state-builtin mutations between stages and
the parent. Full native, harness, and strict ASan/UBSan suites passed locally.

Integrated into `main` through [pull request #60](https://github.com/melliott18/cshell/pull/60)
on 2026-09-23. Implementation commit: `cfe2219`; sanitizer descriptor fix:
`927b81d`; cross-feature integration commit: `24e8616`; merge commit: `ba3aeb9`.
GitHub closed issue #21 when the pull request merged. Both hosted workflows
passed Ubuntu/GCC, macOS/Clang, and Docker Linux.
