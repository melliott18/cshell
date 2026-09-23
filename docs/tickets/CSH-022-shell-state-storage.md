# CSH-022: Define shell variable and parameter storage

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-007
- Depends on: CSH-016
- Branch: feat/CSH-022-shell-state-storage
- Issue: [#23](https://github.com/melliott18/cshell/issues/23)

## Goal

Provide an owned shell-state model that the parser, executor, expansion engine,
and builtins can use without relying on the process environment as their store.

## Scope

- Import environment values into a variable store with unset/empty distinctions.
- Model export/readonly attributes and snapshot environment vectors for children.
- Store invocation operands, positional parameters, and special-parameter state.
- Define APIs for last status, background identifier, process ID, and options.
- Add copying/restoration primitives with explicit allocation and mutation rules.

## Acceptance criteria

- [x] Unit fixtures distinguish unset and empty values through create, replace,
  lookup, and unset operations, with no ownership or allocation leaks.
- [x] Environment snapshots include only exported variables, preserve empty
  values, and remain valid independently of later mutations to the variable store.
- [x] Readonly mutation/unset attempts return defined errors without altering
  stored values or attributes; invalid inputs and allocation failures are tested.
- [x] Invocation mapping preserves `$0` and positional arguments, and documented
  APIs expose `$?`, `$#`, `$!`, `$$`, and option state to future consumers.
- [x] Copied states and save/restore operations preserve ownership and isolation,
  with sanitizer-backed unit tests that do not require the new executor.

## Validation

Run focused C unit tests natively and in Docker, including environment import,
empty values, attribute transitions, parameter replacement, snapshot lifetime,
copy isolation, and controlled allocation failures. Use ASan/UBSan for ownership
checks. End-to-end expansion and assignment behavior is validated in later work.

## Implementation notes/evidence

This ticket can run alongside lexer/parser work after CSH-016 supplies invocation
data. Export stable interfaces for CSH-019 and CSH-023 before integrating either.
Represent status/background fields now; their producers are integrated by the
invocation and executor tickets. Function call semantics remain CSH-009 work.


### Implemented contract

`include/cshell/state.h` and `src/state.c` provide opaque, owned shell state.
The variable store distinguishes missing names, attributed-but-unset variables,
and set empty values. Valid environment names are copied and exported; invalid
entries are ignored and duplicate valid names use the last entry. Assignments
preserve attributes, readonly assignments/unsets fail atomically, and exported
snapshots own their NULL-terminated vectors independently of later mutations.

Invocation operands are copied without retaining or consuming input sources.
The API exposes positional replacement, status, background ID, original shell
PID, invocation mode, and option storage. Clones preserve all fields and retain
the original PID even when made after a fork. Full-state checkpoints restore
without allocation and consume the saved object, including when later mutations
added readonly attributes. Every fallible mutation stages its allocations before
publishing changes.

The [shell-state contract](../shell-state.md) documents ownership, error values,
input validation, borrowing lifetimes, option masks, and checkpoint limitations.
CSH-019 and CSH-023 can consume these interfaces independently of the prototype.
CSH-023 still owns category-aware assignments and selective restoration around
builtins; full-state checkpoints restore all variables and metadata. Special
startup variable initialization, expansion, option effects, function semantics,
and default-executable integration remain with their existing tickets.

### Validation evidence (2026-09-23)

Native environment: macOS/Darwin arm64, Apple Clang 15.0.0, GNU Make 3.81,
Python 3.12.2. Docker environment: Linux aarch64, Debian Bookworm, GCC 12.2.0,
GNU Make 4.3, Python 3.11.2, glibc 2.36, Docker Engine 24.0.6; tests ran as
unprivileged UID 10001.

- `make -j8`, `make test`, and `make test-harness`: both state fixture suites,
  all 63 input/invocation checks, four prototype fixtures, and 23 harness
  self-tests passed. The existing generated legacy scanner retains its macOS
  signedness warning; replacement modules compile warning-free.
- After `make clean`, `make test-state CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'`
  passed with `ASAN_OPTIONS=halt_on_error=1` and `UBSAN_OPTIONS=halt_on_error=1`.
  Checks remain active with `-DNDEBUG`.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-022` passed both state suites,
  63 input checks, and four prototype fixtures. Source hashes in the image
  match the validated host state implementation and C fixtures.
- The Docker image passed a clean `make test-state CC=gcc` with the same strict
  sanitizer flags, `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`, and
  `UBSAN_OPTIONS=halt_on_error=1`, followed by all 23 harness self-tests.
  No sanitizer or leak diagnostics appeared on either platform.
- A temporary source-only snapshot containing state/input/invocation modules,
  their headers, Makefile, and state fixtures passed `make test-state LEX=false`
  with `-Werror`. No legacy headers, sources, scanner, or executor were present.
- `tests/state_fixture.c` checks import/ownership, unset/empty distinctions,
  attribute transitions, readonly failures, independent snapshots, actual
  invocation mappings, aliased parameter replacement, scalar validation,
  copied PID preservation after fork, clone isolation, and nested checkpoints.
- `tests/state_faults.c` fails each allocation in turn for construction/import,
  variable creation/replacement, attributed declarations, parameter replacement
  and clearing, snapshots, cloning, and saving. Every failure checks state
  preservation and allocation counts; restore succeeds with the next allocation
  armed and makes zero allocation calls. Production objects contain no hooks.
- `make test` includes state checks through bounded module suites in the existing
  runner; CI runs them on native Linux/macOS and Docker. Native CI also has a
  focused state ASan/UBSan step. Hosted results are recorded by the pull request.
- Independent source review found no ownership or rollback defects. Local
  Markdown file links and `git diff --check` passed; diagrams are unchanged.

These results establish the CSH-022 storage API, not end-to-end shell behavior
or general POSIX conformance. The ticket remains in review until integration.


Hosted CI for implementation commit `c35b80f` passed all three branch jobs and
all three PR jobs: native Ubuntu/GCC, native macOS/Clang, and Docker Linux.
[PR run](https://github.com/melliott18/cshell/actions/runs/35920676755) and
[branch run](https://github.com/melliott18/cshell/actions/runs/35920657825).
The first PR macOS attempt hit an existing descendant-cleanup EPERM failure;
its retry passed. [CSH-040](CSH-040-macos-harness-cleanup.md) records the evidence
and follow-up regression work. CSH-022 does not modify that harness code.
