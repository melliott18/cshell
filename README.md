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
make test         # Native smoke checks; requires Python 3
make docker-test  # Build and run the checks in a Linux container
```

The Docker path requires Docker with a running Linux engine and uses its own
compiler, Flex, and Python. See [Testing](docs/testing.md) for direct Docker
commands, coverage limits, and troubleshooting.

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
tests/           Bounded smoke checks
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
