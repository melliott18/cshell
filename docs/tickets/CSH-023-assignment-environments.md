# CSH-023: Apply assignment prefixes by execution category

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-007
- Depends on: CSH-019, CSH-022
- Branch: feature/CSH-023-assignment-environments
- Issue: [#24](https://github.com/melliott18/cshell/issues/24)

## Goal

Connect shell storage to command dispatch so assignment values, exported
environments, and restoration follow the selected command category.

## Scope

- Apply assignment-only commands and prefixes on ordinary external commands.
- Define category-aware assignment handling for builtins and function consumers.
- Enforce readonly errors before invalid mutations reach command execution.
- Integrate environment snapshots and explicit state save/restore operations.
- Document the boundary consumed by CSH-009 functions and CSH-010 builtins.

## Acceptance criteria

- [x] Assignment-only commands persist values in shell state; ordinary external
  command prefixes reach the child environment without incorrectly persisting.
- [x] Unit/dispatch fixtures verify ordinary and special-builtin assignment
  categories, including specified persistence and temporary-state restoration.
- [x] Unexported shell values remain absent from external environments unless a
  command prefix supplies them; empty and overwritten values are covered.
- [x] Readonly assignment failures produce the applicable diagnostic/status and
  execution-context behavior without partial state corruption or unintended exec.
- [x] Save/restore and copied-state fixtures preserve values/attributes through
  success and failure, with documented handoffs for function and builtin work.

## Validation

Run native and Docker external environment-inspection fixtures and focused unit
tests for assignment categories, empty values, export attributes, readonly errors,
and nested save/restore. Use dispatch fixtures for command categories whose full
builtin/function implementation is pending; distinguish those from end-to-end
coverage. Run sanitizers on failure and restoration paths.

## Implementation notes/evidence

Use CSH-019's dispatch contract and CSH-022's storage APIs instead of adding a
second variable store. Expanded assignment values arrive through the CSH-008
adapter. Full function and special-builtin integration remains CSH-009/CSH-010;
their tests must preserve the command-category rules established at this boundary.


### Implemented contract

`csh_execute_resolved()` applies prepared prefixes by execution category and
provides a handler boundary for CSH-009/CSH-010. Assignment-only and special
builtin values persist; external, regular builtin, and function prefixes are
exported temporarily. Special prefixes preserve export attributes unless
allexport is enabled. Function prefixes use temporary lifetime as a documented
choice for unspecified behavior. Literal prefixes are also accepted by the
bounded AST adapter; general expansion remains CSH-008/CSH-026 work.

Selective variable saves preserve missing/unset/empty values and attributes
without rolling back unrelated handler mutations. Duplicate names apply in
order, and nested scopes restore without allocating. Readonly errors fail
before redirection/dispatch, return status 1, and request exit only in the active
noninteractive context. Allocation failures roll back incomplete assignment
batches. External PATH/environment preparation copies temporary state before
restoration and fork. No process-global environment mutation is used.

The [execution contract](../execution.md#assignment-categories-and-resolved-dispatch)
and [state contract](../shell-state.md#copying-checkpoints-and-restoration)
document ownership, ordering, rollback, and future consumer obligations.

### Validation evidence

Validated on 2026-09-23 in the separate worktree
`csh-023-assignment-environments`, based on `main` at `fd17641`.
Native: Darwin arm64, Apple Clang 15.0.0, Python 3.12.2.
Docker: Debian Bookworm Linux aarch64, GCC 12.2.0, Docker Engine 24.0.6.

- `make -j8 test test-pty test-harness`: passed all module suites, 74 execution
  behavior cases plus API/assignment/fault fixtures, four prototype pipe cases,
  the prototype PTY case, and 61 harness self-tests. The pre-existing generated
  legacy scanner signedness warning remains; replacement modules build cleanly.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-023`: passed the full test target,
  including the same external environment-inspection and assignment fixtures.
  An initial Docker Hub TLS handshake timeout was resolved by retrying the build.
- After `make clean`, `make -j8 test-state test-execute CC=clang` passed with
  `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`
  and `LDFLAGS='-fsanitize=address,undefined'`, with ASan/UBSan halt-on-error.
- The Docker image passed a clean `make -j8 test-state test-execute CC=gcc`
  using the same strict sanitizer flags, `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`,
  and `UBSAN_OPTIONS=halt_on_error=1`. No sanitizer or leak diagnostics appeared.
- Allocation sweeps cover selective-save construction, literal-prefix adaptation,
  persistent/temporary assignment batches, external environment preparation,
  redirection and fork failures. Selective restoration makes zero allocations
  with the next allocation armed to fail. Assertions remain active under NDEBUG.
- `git diff --check` passed. No diagrams changed.

Builtin/function fixtures use resolved handlers; they do not claim complete
builtin/function or public-runtime integration. The default `cshell` executable
still uses the prototype. This ticket remains `review` until integration.
