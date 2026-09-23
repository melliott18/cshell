# cshell

A Unix shell written in C, being developed toward POSIX.1-2024 shell language
and `sh` behavior. **cshell is currently an early prototype, not a POSIX-compliant
shell.** The executable is named `cshell`; this project implements the Bourne-style
POSIX language, not the C shell (`csh`) language.

## Build and run

Requirements: a C99 compiler, GNU Make, and Flex. The build does not require
`libfl`.

```sh
make -j
./cshell
```

Enter `exit` to quit. EOF handling, quoting, pipelines, and redirections still
have known defects; see the [implementation tickets](docs/tickets/README.md).
The replacement [input and invocation APIs](docs/input-and-invocation.md)
support script files, `-c`, and stdin in API fixtures. The default `cshell`
executable still uses the prototype input loop; script-file and `-c` arguments
remain unavailable until runtime integration.

```sh
make clean     # Remove the executable and generated build files
make CC=clang  # Select a compiler
```

## Test

```sh
make test          # Input API and selected behavioral fixtures; Python 3.9+
make test-input    # Replacement input/invocation API checks only
make test-pty      # Controlling-terminal startup and explicit-exit fixture
make test-harness  # Test the runner's failure detection and cleanup
make docker-test   # Build and run the selected fixtures in a Linux container
make docker-test-pty # Build and run the selected terminal fixtures in Linux
```

`make test` includes independent input/invocation API checks. Its default
behavioral suite records the current prototype's stdin behavior and explicit
prompt allowance. Replacement shell and module tests select their executable and
fixture suite separately; passing prototype tests does not establish replacement
behavior or POSIX compliance.

`make test-pty` independently selects a candidate and terminal suite with
`PTY_TEST_TARGET`, `PTY_TEST_BINARY`, and `PTY_TEST_SUITE`. Its default fixture
checks startup and explicit exit on a controlling pseudo-terminal. Harness
self-tests exercise terminal signals and foreground ownership with helper
programs; they do not claim that cshell implements signals or job control.

The Docker path requires Docker with a running Linux engine and uses its own
compiler, Flex, and Python. Native Linux, native macOS, and Docker checks also run
in CI. See [Testing](docs/testing.md) for fixture authoring, executable selection,
resource limits, direct Docker commands, and troubleshooting.

## Where to start

| Task | Read |
| --- | --- |
| Find the next implementation ticket | [Ticket index](docs/tickets/README.md) |
| See dependencies and parallel work | [Visual implementation plan](docs/implementation-plan.md) |
| Create a branch or contribute a change | [Contributing](CONTRIBUTING.md) |
| Run native or Docker tests | [Testing](docs/testing.md) |
| Understand the code and planned modules | [Architecture](docs/architecture.md) |
| Use replacement input and invocation APIs | [Input and invocation](docs/input-and-invocation.md) |
| Check the POSIX target and known gaps | [POSIX tracking](docs/posix.md) |
| Browse all project documentation | [Documentation index](docs/README.md) |
| Find project context as an agent | [Agent entry point](AGENTS.md) |

## Repository layout

```text
include/cshell/   Internal module interfaces
src/main.c       Program entry point and current input loop
src/input.c      Replacement physical-line input sources
src/invocation.c Replacement invocation and operand mapping
src/legacy/      Transitional lexer and executor
docs/            Architecture, POSIX tracking, and implementation tickets
tests/           Input API fixtures, pipe/PTY behavioral runner, and self-tests
build/           Generated scanner and object files (ignored by Git)
```

The original code is a starting point for understanding the problem. Its APIs,
implementation choices, and behavior do not constrain the replacement. New
modules follow the POSIX specification and explicit ownership contracts; they
must not depend on the legacy interface.

[CSH-039](docs/tickets/CSH-039-legacy-retirement.md) will switch `cshell` to the
replacement runtime and delete the legacy sources, headers, build rules, and
compatibility paths. That cutover follows the input, lexer, parser, command, and
pipeline work; it does not wait for every POSIX feature. Git history and
historical tickets remain as records. See [Architecture](docs/architecture.md)
for the removal criteria and [Implementation plan](docs/implementation-plan.md)
for the revised sequence.

Originally authored by Mitchell Elliott.
