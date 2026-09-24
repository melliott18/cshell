# CSH-019: Execute simple commands with ordered redirections

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-005, CSH-022
- Branch: feature/CSH-019-simple-command-redirections
- Issue: [#20](https://github.com/melliott18/cshell/issues/20)

## Goal

Create the AST execution entry point and an explicit expanded-command contract,
with correct lookup, child ownership, and redirection restoration.

## Scope

- Execute simple-command AST nodes through a temporary literal-word adapter.
- Define owned expanded argv, assignment, and redirection inputs for CSH-008.
- Centralize lookup, exec/wait, status conversion, and executable-format fallback.
- Apply ordered file, descriptor, and here-document input redirections.
- Support builtin dispatch in the parent with saved/restored descriptors.
- Supply bootstrap `cd` and `exit` handlers needed to retire the prototype;
  CSH-018 completes exit/status rules and CSH-029 completes state-builtin coverage.
- Build against replacement input/AST/state interfaces only, without copying
  the legacy scanner or operator dispatcher into renamed modules.

## Acceptance criteria

- [x] Lookup tests distinguish command-not-found status 127 from applicable
  found-but-unexecutable status 126 and cover executable-format fallback.
- [x] `2>&1 >file` and `>file 2>&1`, descriptor closure, and here-document input
  have distinct specified effects tested through AST/API or supported syntax.
- [x] Parent builtin redirections restore descriptors on success and failure;
  failed external execution cannot return into the parent's input loop.
- [x] Child ownership is explicit: waits target owned children, and fork/open/
  duplication failures release every acquired descriptor and command allocation.
- [x] Unsupported syntax or expansions are rejected before that construct
  has side effects; the literal-word adapter never delegates to legacy code
  and is replaced by CSH-008 expansion integration.
- [x] Bootstrap `cd` changes the parent directory once without external-command
  fallthrough, and the execution test driver links no legacy objects or symbols.
- [x] Adapter/dispatch interfaces document ownership and execution categories,
  with focused tests that permit later expansion and assignment integration.

## Validation

Run native and Docker fixtures for lookup, fallback, redirection order, closed
descriptors, here-document delivery, and builtin descriptor restoration. Exercise
failures through controlled hooks or resource limits and run focused sanitizer
checks. Use AST/API fixtures where syntax or expansion is deliberately pending.

## Implementation notes/evidence

CSH-022 supplies the state storage contract without waiting for the CSH-007
milestone. CSH-023 adds assignment lifetime rules to this dispatch boundary.
Here-document collection belongs to the front end and expansion to CSH-008;
this ticket delivers the prepared input and owns its descriptor lifecycle.


### Implemented contract

`execute.h`/`execute.c` define the owned prepared-command boundary and a temporary
literal AST adapter. The adapter accepts a simple command or the parser's
singleton foreground wrapper, removes literal quotes/escapes, and rejects
assignments, active expansion, and unsupported compound syntax before dispatch.
Prepared assignments reserve the CSH-023 boundary and currently fail before
redirection. See [Simple-command execution](../execution.md) for ownership,
execution categories, supported operands, and explicit bootstrap limitations.

External execution searches the state's PATH, snapshots exported variables,
forks one owned child, and uses `waitpid(child, ...)` with EINTR retry. Missing
commands produce 127; applicable execution failures produce 126. ENOEXEC invokes
host `/bin/sh` with the resolved path and arguments. Dash-leading paths are
normalized so they cannot become interpreter options. A present script with a
missing interpreter produces 126 as an explicit project choice. Signal status
is `128 + signal_number`. Every child failure terminates with `_exit`.

`redirect.h`/`redirect.c` apply source-ordered files, descriptor duplication and
closure, and prepared here-document bytes. Parent dispatch snapshots each
target's open/closed state and descriptor flags, avoids every source/target fd
when allocating private backups, and restores after both success and failure.
Here-documents use immediately unlinked temporary files, including binary and
large input. Restoration does not undo file creation/truncation or shared
file offsets. Bootstrap `cd` changes the parent directory without fallthrough;
`exit` returns a caller-owned exit request after restoration.

The behavioral specification references are POSIX.1-2024
[redirection](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07),
[exit status](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_02),
and [simple commands](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01).
General expansion, assignment lifetime, pipelines, noclobber options, full builtin
semantics, and default-executable integration remain with their existing owners.

### Validation evidence (2026-09-23)

- Native macOS arm64 / Apple Clang 15: `make -j4 test test-pty test-harness`
  passed all replacement module suites, four prototype pipe fixtures, one PTY
  fixture, and all 61 harness self-tests. The existing generated legacy scanner
  retained its signedness warning; handwritten replacement sources were clean.
- Final `make test-execute` passed **69 behavioral cases** plus direct API and
  fault checks. Cases assert lookup/fallback, exported state environments,
  redirection order, closures, binary/large/multiple here-documents, parent
  restoration, unsupported-construct rejection, and a separately owned exited
  child left available to its owner.
- Controlled faults sweep adapter, parent-dispatch, and external-launch
  allocations, and inject open, saved-descriptor duplication, dup2, temporary
  file, fork, and interrupted-wait failures. Cleanup checks count live
  allocations/descriptors and assert original descriptor flags and closures.
- A separate source-only snapshot, with `src/legacy`, `src/main.c`, and
  `include/cshell/legacy.h` absent, passed `make -j4 test-execute CC=clang
  LEX=false` using `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror
  -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'` and
  `LDFLAGS='-fsanitize=address,undefined'`, with both sanitizers set to
  `halt_on_error=1`. All 69 cases and API/fault checks passed without diagnostics.
  `nm build/tests/execute_fixture` also shows no legacy or scanner symbols.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-019` passed the final 69 execution
  cases, API/fault checks, existing replacement suites, and four prototype cases
  under Debian Linux/GCC. The image also passed `make test-pty test-harness`
  (one PTY fixture and all 61 harness self-tests).
- A clean Linux/GCC `make -j2 test-execute LEX=false` build with the same
  ASan/UBSan flags plus `-DNDEBUG` passed all 69 cases and API/fault checks with
  `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1` and
  `UBSAN_OPTIONS=halt_on_error=1`; no sanitizer/leak diagnostics appeared.
- `make test-execute` joins `make test`, Docker, and native CI; CI's strict
  ASan/UBSan run now includes it. These are replacement module checks, not a
  default-runtime cutover or a complete POSIX conformance claim.
- The external descriptor-observer helper is intentionally built without
  sanitizer runtime linkage. On macOS 15, AddressSanitizer can reopen an
  intentionally closed standard descriptor before the helper reaches `main`,
  masking the post-`exec` state being tested. Executor, parser, state, and
  fault-injection objects remain instrumented in sanitizer runs.

Integrated into `main` through [pull request #54](https://github.com/melliott18/cshell/pull/54)
on 2026-09-23. Implementation commit: `5d427b9`; sanitizer-fixture commits:
`eff0bae` and `130d030`; integration commit after CSH-025, CSH-027, and CSH-030:
`dc36799`; merge commit: `9026c0e`. GitHub closed issue #20 when the pull request
merged. Both hosted workflows passed Ubuntu/GCC, macOS/Clang, and Docker Linux.
