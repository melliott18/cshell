# Contributing to cshell

Development proceeds through the [implementation tickets](docs/tickets/README.md).
These Markdown files are the project backlog and implementation record. Their
`Issue` links connect to GitHub Issues. Keep both representations aligned; the
Markdown remains readable in a browser, editor, or terminal.

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
| `refactor` | Change code structure | `refactor/CSH-NNN-module-boundaries` |
| `docs` | Documentation changes | `docs/CSH-013-visual-roadmap` |
| `test` | Test coverage or test tooling | `test/CSH-017-test-harness-and-ci` |
| `build` | Build or CI changes | `build/CSH-NNN-toolchain-update` |
| `chore` | Project maintenance | `chore/CSH-001-project-foundation` |

Replace `NNN` with an allocated ticket number. Examples do not allocate IDs;
create the matching ticket before starting new work. This convention replaces
the `codex/` branch prefix for this repository.
It is a documented convention, not an installed Git hook or server-side rule.

## Ticket lifecycle

1. Choose an implementation ticket whose own dependencies are complete. For new work, copy the
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

Allowed statuses are `backlog`, `ready`, `in-progress`, `blocked`, `review`,
`done`, and `superseded`. `ready` means dependencies are complete and the ticket
is actionable.
`superseded` means the planned work was replaced, not implemented: retain the
historical scope, name its replacement owners, and close the GitHub issue as
`not planned`. Remove or replace incoming dependencies before superseding a
ticket; this status never satisfies a dependency as if the work were done.
For `blocked`, describe the actual blocker and what resolves it. Keep status in
the ticket itself; the index provides navigation and dependency order.

A large roadmap ticket is retained as a `Kind: milestone` when split. Its
`Children` list identifies implementation tickets, whose `Parent` fields point
back to it. Parent prerequisites are milestone completion gates, not additional
prerequisites silently inherited by every child. A child never depends on its own
parent. Close the milestone only when all children, its prerequisites, and the
original acceptance criteria are complete.

In GitHub, milestone tickets are parent issues and their children are native
sub-issues. This use of "milestone" describes the ticket's role; it does not
create a separate GitHub Milestones object. Keep both these relationships and
the Markdown child checklists synchronized.

See the [visual implementation plan](docs/implementation-plan.md) for the first
parallel tasks and shared-interface boundaries. A milestone is not a second
implementation branch; changes happen through its child tickets.

## Replacing the prototype

The legacy code is a starting reference, not a compatibility target. New modules
must use the documented replacement contracts without importing `legacy.h`,
wrapping the old dispatcher, or preserving prototype quirks. CSH-039 owns the
complete runtime cutover and deletion; its prerequisites do not include legacy
hardening. Safety regressions belong to the replacement module tickets. Create
a narrow containment ticket only for a demonstrated blocker while the prototype
is still used. See the [replacement strategy](docs/architecture.md#replacement-strategy).

## Build and validation

From the repository root:

```sh
make clean
make -j
make test
make test-pty
make test-expand
make test-execute
make test-runtime test-runtime-pty
make test-pipeline
make test-alias
make test-harness
```

The tests require Python 3.9 or newer. `make test` runs the replacement
input/invocation, lexer, parser/AST, shell-state, value-expansion, and execution API checks
and the selected behavioral fixtures; its default suite checks the prototype's
startup, explicit exit, and
simple external commands. `make test-input` checks only the replacement input
modules, without Flex or legacy dependencies. `make test-lexer` independently
builds and checks replacement tokens, fragments, and parser handoffs.
`make test-parser` builds independent parser/AST fixtures, including ordered
here-documents, source diagnostics, read boundaries, and allocation failures.
See [Parser and AST](docs/parser-and-ast.md) for the ownership contract.
`make test-harness` checks the runner's own assertions, resource limits, and
descendant cleanup, including deliberately failing cases and terminal-control
helpers. `make test-pty` checks the selected candidate on a controlling
pseudo-terminal; its default prototype fixture checks startup and explicit exit.
These checks do not establish shell correctness or POSIX compliance.

`make test-state` checks the replacement shell-state API, including controlled
allocation failures. It also needs no Flex or legacy dependencies. See
[Shell state](docs/shell-state.md) for its ownership and restoration contracts,
and [Testing](docs/testing.md#shell-state-api-and-sanitizer-checks)
for focused sanitizer and Docker commands.

`make test-expand` checks value expansion, arithmetic, the shared quote decoder,
and allocation failures without the legacy scanner or executor. It also runs
`make test-fields` for IFS splitting, pathname generation, restricted contexts,
and allocation/I/O/interruption cleanup. See
[Value expansion](docs/value-expansions.md) for the intermediate output contract.

`make test-execute` checks simple-command lookup, owned children, ordered
redirections, bootstrap builtins, and failure cleanup without legacy objects or
Flex. See [Simple-command execution](docs/execution.md) for the prepared-command
contract and the temporary literal adapter's limits. `make test-pipeline` adds
concurrent pipeline behavior, ordered stage results, builtin isolation, and
partial-launch cleanup. It is also included in `make test` and sanitizer CI.

`make test-alias` checks alias storage, direct builtin handlers, parser
substitution, and allocation failures without invoking the prototype. See
[Aliases](docs/aliases.md) for parsing boundaries and the deferred dispatcher work.

`make test-runtime` checks the internal replacement candidate through `-c`, script
files, and stdin. `make test-runtime-pty` checks prompts, EOF, and interactive
exit errors on controlling terminals. They also run through `make test` and
`make test-pty`, respectively, including Docker and CI. See
[Candidate runtime](docs/candidate-runtime.md) for the supported subset and
documented status/exit decisions.

Keep prototype expectations in a `prototype` suite. Add replacement shell or
module expectations in a separate `replacement` or `module` suite and select both
the executable and suite explicitly. For example, once a module has a build
target and fixtures:

```sh
make test TEST_TARGET=build/module-test TEST_BINARY=./build/module-test TEST_SUITE=tests/fixtures/module.json
```

Use `TEST_TARGET=` for an executable that is already built. Fixture authors must
assert stdout, stderr, and exit status for pipe cases, or exact combined terminal
output and exit status for PTY cases. Include relevant filesystem effects, and
explain any platform restriction with `skip_reason`. Prompt stripping is an
explicit per-case allowance reserved for prototype pipe cases.

Select a terminal candidate and suite independently with `PTY_TEST_TARGET`,
`PTY_TEST_BINARY`, `PTY_TEST_SUITE`, and optional `PTY_TEST_CASE`:

```sh
make test-pty PTY_TEST_TARGET= PTY_TEST_BINARY=/absolute/path/to/candidate PTY_TEST_SUITE=tests/fixtures/candidate-pty.json
```

These example paths must be replaced with the actual candidate and suite.
Terminal fixtures use `transport: "pty"` and ordered `steps`; consult the
[PTY fixture contract](docs/testing.md#terminal-fixtures) before adding signal or
foreground-process-group assertions. Keep helper capability tests separate from
shell behavior evidence.

Put generated replacement or module executables under `build/` and give them a
Make target. Keep `tests/` for source fixtures and helper scripts. Docker excludes
`build/` and the host `cshell` executable, then rebuilds the selected target with
its Linux toolchain.

For a Linux build and the same tests using Docker's toolchain:

```sh
make docker-test
make docker-test-pty
```

See [Testing](docs/testing.md) for the fixture schema, runner limits, image
details, direct Docker commands, and troubleshooting. CI runs native Linux and
macOS checks alongside Docker; a Linux container cannot validate Darwin behavior.
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
- docs/implementation-plan.md diagrams implementation dependencies and parallel work.
- docs/posix.md records the conformance target and evidence policy.
- Each ticket owns its scope, status, acceptance criteria, and validation record.
- AGENTS.md points agents to the same documents used by people; global agent
  behavior rules remain in the applicable global AGENTS.md.

Separate implemented behavior from planned behavior. Update code references when
moving modules, and never label a feature compliant solely because one example
works.

Use fenced Mermaid blocks for small engineering diagrams. GitHub renders them
visually; nearby prose or tables must preserve the essential meaning for readers
without Mermaid support. Render and inspect changed diagrams before review.
