# CSH-001: Establish the cshell project foundation

- Status: done
- Type: chore
- Kind: implementation
- Parent: None
- Depends on: None
- Branch: chore/CSH-001-project-foundation
- Issue: [#2](https://github.com/melliott18/cshell/issues/2)

## Goal

Make the project build and run as `cshell`, with an explicit migration layout and
a documented ticket and branch workflow.

## Scope

- Rename the executable and its usage documentation to `cshell`.
- Separate the entry point, legacy execution, and legacy lexer into `src/main.c`,
  `src/legacy/execute.c`, and `src/legacy/lexer.l`, with declarations in
  `include/cshell/legacy.h`.
- Make generated files build artifacts and remove the unconditional dependency
  on the Flex runtime library when the scanner can provide its own EOF handling.
- Establish documentation navigation, module boundaries, an initial POSIX coverage map,
  and the initial ticket backlog.
- Provide a source-only Docker Linux build/test environment, a bounded smoke
  runner, and matching native/Docker Make targets.

## Acceptance criteria

- [x] A clean build produces `./cshell` using the documented toolchain.
- [x] `make clean` removes generated build artifacts and the executable.
- [x] Build rules express header and lexer dependencies and allow tool overrides.
- [x] Source files expose intentional interfaces instead of including `.c` files.
- [x] README links to architecture, workflow, requirements, and ticket documents.
- [x] Workflow uses a documented branch convention without the `codex/` prefix.
- [x] Documentation identifies the current implementation as incomplete.
- [x] `make test` and `make docker-test` run the same bounded smoke checks;
  Docker compiles in Linux and runs the tests as a non-root user.

## Validation

Run a clean build, a second incremental build, and the documented smoke check.
Verify that `make clean` removes artifacts and that documentation links resolve.
Record the platform and toolchain; do not imply validation on untested systems.

## Implementation notes/evidence

Validated on macOS / Darwin arm64 with Apple Clang 15.0.0, Apple Flex 2.6.4,
and GNU Make 3.81:

- `make clean`: removed `build/` and `cshell`; their absence was checked.
- `make -j8`: built `cshell` without `libfl`.
- A second `make -j8`: reported no work required.
- `printf 'exit\n' | ./cshell`: exited with status 0.
- `/bin/echo foundation` followed by `exit` on stdin: printed `foundation`,
  exited with status 0, and produced no stderr. Both runtime checks used a
  five-second subprocess timeout. Non-interactive prompt output remains a
  known limitation for CSH-003.
- `make -n -B CC=clang LEX=flex CPPFLAGS=-DCSHELL_OVERRIDE_CHECK CFLAGS=-O0 LDFLAGS=-g LDLIBS=-lm`:
  confirmed tool and flag overrides in generated commands.
- Initial documentation validation checked 21 Markdown files, all 52 relative links,
  all 12 ticket metadata records, and the dependency graph for missing IDs and
  cycles.

The generated scanner emits one signedness warning with this Apple Flex version;
handwritten C compiled without warnings. Full behavioral/sanitizer coverage is
not claimed by this ticket. Docker/Linux smoke evidence is recorded below.

The source extraction also resets `argc` for each command, changes the scanner's
newline return to an integer, and removes the unreachable series helper. It does
not enable semicolon execution. Safety and language correctness work continues
in CSH-002 and later tickets.

The Docker follow-up extends this foundation on the same branch. `make test`
passed all three smoke cases natively, and `make docker-test` built and passed
them on Linux arm64 using Docker Desktop 4.25.2 / Engine 24.0.6 and Debian
Bookworm. The image builds from an allowlisted source context as user `cshell`
(UID 10001); it does not copy host binaries or mount the working directory.
The container reported GCC 12.2.0, GNU Make 4.3, Flex 2.6.4, Python 3.11.2, and
glibc 2.36. Deliberately failing and hanging fixtures verified that the runner
returns failure and enforces its timeout. No claim of amd64 testing is made.
See [Testing](../testing.md) for reproducible commands and coverage limits.

Integrated into `main` through [pull request #1](https://github.com/melliott18/cshell/pull/1)
on 2026-09-23. Implementation commit: `12b7014`; merge commit: `844787a`.
The clean native build, native/Docker smoke suites, and documentation checks
passed before merging.
