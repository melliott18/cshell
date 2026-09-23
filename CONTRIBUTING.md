# Contributing to cshell

Development proceeds through the [implementation tickets](docs/tickets/README.md).
These Markdown files are the project backlog and implementation record. They can
be reviewed in a browser, editor, or terminal without a separate tracking service.

## Branch names

Use this project convention:

```text
<type>/CSH-<number>-<short-description>
```

Use uppercase ticket IDs, at least three digits, and a lowercase description
separated by hyphens. Every implementation branch identifies its ticket.

| Type | Use | Example |
| --- | --- | --- |
| `feat` | New shell behavior | `feat/CSH-004-quote-aware-lexer` |
| `fix` | Correct existing behavior | `fix/CSH-002-runtime-safety` |
| `refactor` | Change code structure | `refactor/CSH-016-executor-cleanup` |
| `docs` | Documentation changes | `docs/CSH-013-developer-guide` |
| `test` | Test coverage or test tooling | `test/CSH-014-parser-cases` |
| `build` | Build or CI changes | `build/CSH-015-linux-ci` |
| `chore` | Project maintenance | `chore/CSH-001-project-foundation` |

Examples do not allocate ticket IDs; create the matching ticket before starting
new work. This convention replaces the `codex/` branch prefix for this repository.
It is a documented convention, not an installed Git hook or server-side rule.

## Ticket lifecycle

1. Choose a ticket whose dependencies are complete. For new work, copy the
   [template](docs/tickets/TEMPLATE.md), allocate the next unused ID, and add it to
   the index. Define observable acceptance criteria before implementation.
2. Create the ticket branch from the agreed integration branch (`main` initially).
   Record its name in the ticket and set the status to `in-progress`.
3. Implement the ticket's scope. Update affected documentation with the code.
   Record newly discovered work in linked follow-up tickets.
4. Run the ticket's validation. Record commands, results, environment, and any
   gaps in the ticket. Set the status to `review` when the result is ready.
5. Open a pull request identifying the ticket, behavior change, and validation.
   Mark the ticket `done` when acceptance criteria are met and the change is
   integrated into `main`.

Allowed statuses are `backlog`, `ready`, `in-progress`, `blocked`, `review`, and
`done`. `ready` means dependencies are complete and the ticket is actionable.
For `blocked`, describe the actual blocker and what resolves it. Keep status in
the ticket itself; the index provides navigation and dependency order.

A large roadmap ticket may be split into smaller tickets before implementation.
Retain the original ID as a parent, link the children, and define when the parent
is complete. Dependencies on a parent are satisfied only when its required
children are complete.

## Build and validation

From the repository root:

```sh
make clean
make -j
make test
```

The tests require Python 3 and check startup, explicit exit, and simple external
commands. They do not establish shell correctness or POSIX compliance. CSH-003
extends this smoke runner into a broader behavioral harness.

For a Linux build and the same tests using Docker's toolchain:

```sh
make docker-test
```

See [Testing](docs/testing.md) for coverage limits, image details, direct Docker
commands, and troubleshooting. Keep native platform checks alongside Docker.
See each ticket for the validation required by its changes.

The Makefile accepts compiler, preprocessor, compiler flag, linker flag, library,
and scanner overrides through `CC`, `CPPFLAGS`, `CFLAGS`, `LDFLAGS`, `LDLIBS`,
and `LEX`. For a diagnostic build with Clang or GCC:

```sh
make clean
make CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
```

## Documentation

Keep documentation in ordinary Markdown with relative links so it works both
locally and in a Git repository browser. Use descriptive filenames and headings.
Use paths, ticket IDs, and concrete commands when describing implementation work.

- README.md is the user and contributor entry point.
- docs/README.md indexes the documentation.
- docs/architecture.md describes current and planned module boundaries.
- docs/testing.md documents native and Docker test entry points and coverage.
- docs/posix.md records the conformance target and evidence policy.
- Each ticket owns its scope, status, acceptance criteria, and validation record.
- AGENTS.md points agents to the same documents used by people; global agent
  behavior rules remain in the applicable global AGENTS.md.

Separate implemented behavior from planned behavior. Update code references when
moving modules, and never label a feature compliant solely because one example
works.
