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
Script-file and `-c` invocation are planned, not currently supported.

```sh
make clean     # Remove the executable and generated build files
make CC=clang  # Select a compiler
```

## Test

```sh
make test          # Native prototype fixtures; requires Python 3.9+
make test-harness  # Test the runner's failure detection and cleanup
make docker-test   # Build and run the selected fixtures in a Linux container
```

The default suite records the current prototype's stdin behavior and its explicit
prompt allowance. Replacement shell and module tests select their executable and
fixture suite separately; passing prototype tests does not establish replacement
behavior or POSIX compliance.

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
| Check the POSIX target and known gaps | [POSIX tracking](docs/posix.md) |
| Browse all project documentation | [Documentation index](docs/README.md) |
| Find project context as an agent | [Agent entry point](AGENTS.md) |

## Repository layout

```text
include/cshell/   Internal module interfaces
src/main.c       Program entry point and current input loop
src/legacy/      Transitional lexer and executor
docs/            Architecture, POSIX tracking, and implementation tickets
tests/           Fixture runner, behavioral fixtures, and harness self-tests
build/           Generated scanner and object files (ignored by Git)
```

The current lexer and executor are isolated under `src/legacy/` so their
replacements can be delivered in bounded tickets. Future module responsibilities
and ownership rules are described in the architecture document.

Originally authored by Mitchell Elliott.
