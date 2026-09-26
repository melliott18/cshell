# cshell

A Unix shell written in C, being developed toward POSIX.1-2024 shell language
and `sh` behavior. **cshell is currently a bootstrap implementation, not a POSIX-compliant
shell.** The executable is named `cshell`; this project implements the Bourne-style
POSIX language, not the C shell (`csh`) language.

The current target is the [base shell profile](docs/posix.md#selected-profile).
Native macOS and Linux and the documented Docker image are tested; this
repository has no installation target yet. Build locally and run `./cshell`.

## Build and run

Requirements: a C99 compiler and GNU Make. The handwritten lexer needs no
scanner generator or scanner runtime library.

```sh
make -j
./cshell
./cshell -c 'printf "%s\n" "hello world"'
./cshell script-file arg1 arg2
printf 'exit 23\n' | ./cshell
```

Enter `exit` or send EOF to quit. The [runtime](docs/candidate-runtime.md) supports
expanded simple commands, external lookup, state builtins including `cd` and
`exit`, lists, groups, ordered redirections, and concurrent pipelines through
command strings, script files, and stdin. Command substitutions and expanded
here-documents use the same parser and executor. Non-interactive execution prints
no prompt or banner. Background jobs and interactive
[job control](docs/job-control.md) are supported. [Control flow and functions](docs/control-flow.md) include conditionals,
loops, case selection, and explicit control transfer. [Evaluation, lookup, aliases, and stateful utilities](docs/evaluation-builtins.md)
are supported. [Shell options](docs/shell-options.md) include errexit, pipefail, nounset,
noclobber, noglob, tracing and noexec. [Traps and signal handling](docs/traps-and-signals.md)
provide the documented subset; [clause evidence](docs/jobs-signals-evidence.md)
records remaining gaps. Unsupported syntax is diagnosed before that
construct executes.
See [Runtime behavior](docs/candidate-runtime.md) for the exact subset and statuses.

```sh
make clean     # Remove the executable and generated build files
make CC=clang  # Select a compiler
```

## Test

```sh
make test          # Module API and selected behavioral fixtures; Python 3.9+
make test-syntax   # Clause-mapped invocation, descriptor, syntax and alias checks
make test-input    # Replacement input/invocation API checks only
make test-lexer    # Replacement lexer/token API checks only
make test-parser   # Replacement parser/AST API checks only
make test-alias    # Alias storage, handlers, and token/AST substitution
make test-expansion # Clause-mapped public-runtime expansion evidence
make test-expand   # Replacement value/field expansion, arithmetic, and quote APIs
make test-substitution # Integrated expansion, child ownership, and capture failures
make test-fields   # IFS splitting, pathname expansion, and cleanup checks
make test-options  # Invocation/set, option effects, and environment interactions
make test-host-utilities # Host integration, executable identities and known gaps
make test-evaluation # Evaluation, lookup, aliases, and remaining utilities
make test-builtins # Replacement state builtins and executor integration
make test-state-builtins # Clause-mapped runtime state and utility evidence
make test-state    # Replacement shell-state API checks only
make test-execution-evidence # Clause-mapped execution/redirection/control witnesses
make test-execute  # Replacement command, assignment, and redirection API checks
make test-pipeline # Concurrent pipeline, stage-status, and failure-cleanup checks
make test-control  # Conditionals, loops, case, functions, and failure cleanup
make test-context  # Lists, groups, background ownership, and cleanup checks
make test-jobs     # Job builtins, retained statuses, idle reaping, and failure checks
make test-traps    # Signal contracts, inherited ignores, and blocked-wait checks
make test-jobs-pty # Process groups, terminal signals, stop/resume, and restoration
make test-runtime  # Cross-mode invocation/status behavior
make test-redirection-offset # Sparse-file offset and resource-limit boundaries
make test-portability # Locale, large input, sparse files, bounded generated cases
make test-prompt   # Interrupted and partial primary/continuation prompt writes
make test-runtime-pty # Shell prompts, EOF, and exit errors on a terminal
make test-pty      # Shell terminal behavior, prompts, EOF, and exit errors
make test-harness  # Test the runner's failure detection and cleanup
make docker-test   # Build and run the selected fixtures in a Linux container
make docker-test-pty # Build and run the selected terminal fixtures in Linux
```

`make test` includes module API and controlled failure checks, plus strict
runtime fixtures against `./cshell` in all three input modes. `make test-pty`
runs the terminal suite. The focused `test-runtime` and `test-runtime-pty`
targets select the same public executable. Alternate executables and suites can
be selected with `TEST_*` and `PTY_TEST_*` variables. The job suite exercises terminal signals and foreground ownership through cshell;
harness self-tests separately validate the runner with helper programs.

The Docker path requires Docker with a running Linux engine and uses its own
compiler and Python. Native Linux, native macOS, and Docker checks also run
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
| Run the shell and understand its limits | [Runtime behavior](docs/candidate-runtime.md) |
| Use replacement tokens, words, and parser handoffs | [Lexer and words](docs/lexer-and-words.md) |
| Parse complete commands and inspect owned trees | [Parser and AST](docs/parser-and-ast.md) |
| Store aliases and substitute command words | [Aliases](docs/aliases.md) |
| Use owned shell variables and parameters | [Shell state](docs/shell-state.md) |
| Expand structured words with quote provenance | [Value expansion](docs/value-expansions.md) |
| Execute prepared commands and restore redirections | [Simple-command execution](docs/execution.md) |
| Execute loops, conditionals, and functions | [Control flow](docs/control-flow.md) |
| Use evaluation and utility builtins | [Evaluation builtins](docs/evaluation-builtins.md) |
| Use invocation and runtime options | [Shell options](docs/shell-options.md) |
| Use interactive jobs and job builtins | [Job control](docs/job-control.md) |
| Check the POSIX target and known gaps | [POSIX tracking](docs/posix.md) |
| Browse all project documentation | [Documentation index](docs/README.md) |
| Find project context as an agent | [Agent entry point](AGENTS.md) |

## Repository layout

```text
include/cshell/   Internal module interfaces
src/main.c       Invocation, complete-command loop, prompts, and final status
src/input.c      Replacement physical-line input sources
src/invocation.c Replacement invocation and operand mapping
src/lexer.c      Replacement tokens, word fragments, and parser handoffs
src/parser.c     Replacement complete-command parser and here-documents
src/ast.c        Owned syntax trees and cleanup
src/alias.c      Alias storage and alias/unalias handlers
src/state.c      Replacement variable, parameter, and state storage
src/expand.c     Replacement value expansion with quote provenance
src/fields.c     Final field splitting and quote removal
src/pathname.c   Component-wise filename generation
src/arithmetic.c Checked signed-long arithmetic evaluation
src/quote.c      Shared dollar-single-quote escape decoding
src/builtin.c    Replacement state builtin handlers
src/utility.c    Read, getopts, umask, times, and resource-limit handlers
src/prepare.c    Context-sensitive command preparation and lazy substitution handoff
src/execute.c    Execution contexts, assignment scopes, dispatch, capture, and pipelines
src/redirect.c   Ordered descriptor operations and restoration
src/jobs.c       Process groups, terminal ownership, job statuses, and builtins
src/traps.c      Trap actions, signal flags, dispositions, and listing
docs/            Architecture, POSIX tracking, and implementation tickets
tests/           Module fixtures, pipe/PTY behavioral runner, and self-tests
build/           Object files and generated test fixtures (ignored by Git)
```

[CSH-039](docs/tickets/CSH-039-legacy-retirement.md) makes the replacement runtime
the only `cshell` implementation. The legacy sources, scanner build rules,
internal candidate executable, and prototype test allowances are removed.
Historical tickets and Git history retain the previous implementation record.
CSH-026 replaces the bounded literal adapter with context-sensitive expansion.
CSH-041 adds arithmetic-first lexer replay for ambiguous `$((` input; new
modules follow POSIX requirements and explicit ownership contracts.

Originally authored by Mitchell Elliott.
