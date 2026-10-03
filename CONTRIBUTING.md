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
   [template](docs/tickets/TEMPLATE.md), [reserve its ID](#reserve-a-ticket-number)
   in the shared ledger, and add it to the index. Define observable acceptance criteria before implementation.
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

## Runtime boundaries

The replacement is the only runtime. New modules must use the documented
ownership contracts without restoring the deleted legacy dispatcher or its
interfaces. CSH-026 connects context-sensitive expansion to execution. Unsupported
constructs must fail before their side effects.
See the [replacement strategy](docs/architecture.md#replacement-strategy).

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
and the selected behavioral fixtures; its default suite checks `cshell` through
command strings, script files, and stdin. `make test-input` checks only the replacement input
modules, without Flex or legacy dependencies. `make test-lexer` independently
builds and checks replacement tokens, fragments, and parser handoffs.
`make test-parser` builds independent parser/AST fixtures, including ordered
here-documents, source diagnostics, read boundaries, and allocation failures.
See [Parser and AST](docs/parser-and-ast.md) for the ownership contract.
`make test-harness` checks the runner's own assertions, resource limits, and
descendant cleanup, including deliberately failing cases and terminal-control
helpers. `make test-pty` checks the selected candidate on a controlling
pseudo-terminal; its default suite checks prompts, EOF, and exit/error behavior.
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
contract and context-sensitive AST preparation. `make test-pipeline` adds
concurrent pipeline behavior, ordered stage results, builtin isolation, and
partial-launch cleanup. It is also included in `make test` and sanitizer CI.

`make test-alias` checks alias storage, direct builtin handlers, parser
substitution, and allocation failures independently of the runtime. See
[Aliases](docs/aliases.md) for parsing boundaries and the deferred dispatcher work.

`make test-runtime` checks `cshell` through `-c`, script
files, and stdin. `make test-runtime-pty` checks prompts, EOF, and interactive
exit errors on controlling terminals. They also run through `make test` and
`make test-pty`, respectively, including Docker and CI. See
[Runtime behavior](docs/candidate-runtime.md) for the supported subset and
documented status/exit decisions.

Use strict `replacement` suites for shell behavior and `module` suites for API
fixtures. Select the executable and matching suite together. For example, once a module has a build
target and fixtures:

```sh
make test TEST_TARGET=build/module-test TEST_BINARY=./build/module-test TEST_SUITE=tests/fixtures/module.json
```

Use `TEST_TARGET=` for an executable that is already built. Fixture authors must
assert stdout, stderr, and exit status for pipe cases, or exact combined terminal
output and exit status for PTY cases. Include relevant filesystem effects, and
explain any platform restriction with `skip_reason`. Output comparisons are exact; prompt stripping is not supported.

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

The Makefile accepts compiler, preprocessor, compiler flag, linker flag, and library
overrides through `CC`, `CPPFLAGS`, `CFLAGS`, `LDFLAGS`, `LDLIBS`. For a diagnostic build with Clang or GCC:

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

## Reserve a ticket number

CSH numbers remain sequential and are distinct from GitHub issue numbers.
**Never choose the next number by scanning a worktree, the ticket index, or
GitHub titles.** Concurrent branches can see different snapshots. The shared
reservation ledger is `allocations.json` on the data branch
[`chore/CSH-001-ticket-registry`](https://github.com/melliott18/cshell/tree/chore/CSH-001-ticket-registry).
It maps each CSH ID to exactly one GitHub issue, including closed issues.
`docs/tickets/allocations.json` is an offline snapshot, not the allocator.

For a new ticket:

1. Prepare its scope, acceptance criteria and validation using the ticket
   template, leaving `CSH-NNN` and the Issue placeholder intact.
2. Create **one unnumbered GitHub issue**, with the intended descriptive title
   and that body. Record its issue number immediately.
3. Run `python3 tools/tickets.py reserve --issue ISSUE_NUMBER`. This atomically
   reserves a CSH ID in the shared ledger, updates the issue title/body
   placeholder, and refreshes the local allocation snapshot. Use the returned
   ID for the ticket filename, heading, index, dependencies and branch.
4. Run `make test-tickets` and `python3 tools/tickets.py check --live` before
   publishing the implementation PR. Commit the refreshed snapshot with the
   ticket document. Existing allocated tickets must reuse their reservation.

Two allocators may propose the same next ID, but only one fast-forward push
can advance the shared ref from the same parent. The loser fetches the new tip
and retries. No force push is used. A retry for the **same issue number** returns
its existing reservation. If GitHub publication, the network, or the local file
write fails after reservation, rerun the same command for the same issue.
Do not create a second issue or reuse the reserved ID. If the registry cannot
be read or written, stop allocation; there is no local fallback.

The registry branch contains only allocation data and has separate history;
it is not an implementation branch or a branch to merge into `main`. Never
force-push, reset, delete, or repurpose it. Reservations are append-only.
The live branch requires linear history and blocks force pushes and deletion,
including for administrators. These protections preserve history; the allocator
and review enforce append-only contents.
Renumbering an already reserved ticket is an exceptional coordinated migration
of GitHub identity, registry binding, Markdown filename/heading/index and current
references. Preserve historical evidence as historical evidence. Do not recycle
an allocated ID through ordinary tooling.

`tools/tickets.py check --live` checks the shared bindings against GitHub and
local documents. It rejects duplicate issue IDs, conflicting reservations,
filename/heading/title/link mismatches and incorrect index links. Its `--ref`
option audits additional fetched branches without checking them out. A local
snapshot may omit reservations made after it was copied, but cannot contradict
a shared binding. Unnumbered drafts do not constitute allocations. Explicitly
closed duplicate issues with non-CSH titles do not allocate an additional ID.

The **Ticket integrity** CI workflow runs these checks on pushes and PRs, with
read-only credentials. It does not allocate tickets from CI and does not execute
code from issue bodies. Once this workflow is merged, maintainers can make its
`Ticket integrity` check required in the existing branch rules. It is not yet a
required merge check merely because the workflow exists in a PR.

When a ticket is integrated, update its Markdown and GitHub body `Status` fields
alongside closing the issue. Closed issue bodies with an old status are reported
as lifecycle warnings, separately from naming errors. Completed historical
tickets may share a branch named for another ticket; the checker reports these
as warnings, while an active ticket with the wrong branch ID fails. An active PR may correctly
say `review` while its older `main` snapshot still says `ready`; do not downgrade
active work to match an older snapshot.
