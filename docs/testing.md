# Testing cshell

## Portability audit probes

`make test-portability` runs [`tests/portability.py`](../tests/portability.py)
against the public `cshell` executable. `make test` includes it, so the native,
Docker, and sanitizer CI jobs run the same probes from a clean checkout. It uses
the shared bounded runner for exact streams/status, per-case directories, process
group cleanup, wall/CPU/file/output limits, and all three invocation modes where
applicable.

The probes assert C versus installed UTF-8 locale pathname matching, locale
precedence (including after an LC_CTYPE assignment), UTF-8 IFS splitting, generated
arithmetic and quote nesting through depth 32, and a 256 KiB input line in file
and stdin modes. A sparse file larger than 2 GiB tests pathname expansion and a
one-byte append past that offset; the append case raises only the runner's file
size limit. Its disk use remains sparse. An unavailable UTF-8 locale is reported
as a scoped skip; C-locale, generated, and sparse-file cases still run. The
[CSH-037 record](tickets/CSH-037-portability-audit.md) identifies the tested
platforms and remaining requirements. Pathname matching does not establish the
separate rule for initial lexical interpretation; CSH-042/047 retain that gap.

## Runtime integration

`make test-runtime` checks `cshell` across `-c`, script-file, and
stdin modes using shared fixtures. `make test-runtime-pty` checks interactive
exit errors, child statuses, EOF, primary/continuation prompts, and here-documents
on a controlling terminal. The build uses only replacement modules and needs
no Flex. See [Runtime behavior](candidate-runtime.md) for the exact subset,
status/exit policy, and deferred interactive features.

The source cases in `tests/runtime_cases.py` generate
`build/tests/runtime.json` and `build/tests/runtime-pty.json`. They use the same
`tests/smoke.py` runner, per-case directories, process/session cleanup, timeout,
and output limits as other suites. Every case asserts exact output and status;
relevant cases also check file effects or their absence. No runtime case
strips prompts. The compiled `execute_helper` provides exact output, completion,
and signal behavior without relying on additional shell features.

```sh
make test-runtime test-runtime-pty
make docker-test DOCKER_IMAGE=cshell-test:csh-039
make docker-test-pty DOCKER_IMAGE=cshell-test:csh-039
# Select a generated case with the existing runner:
python3 tests/smoke.py ./cshell --suite build/tests/runtime.json --case 'unknown command (stdin)'
```

The pipe cases join `make test`; the terminal cases join `make test-pty`.
Consequently both run through existing native and Docker CI entry points.
Native and Docker sanitizer CI include both runtime suites. For focused sanitizer work,
use a separate checkout or clean build:

```sh
make clean
MallocNanoZone=0 ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 make test-runtime test-runtime-pty CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
```

`MallocNanoZone=0` prevents the macOS allocator from writing a compatibility
notice into the PTY output before the sanitizer-instrumented shell starts.

## Coverage and suite selection

CSH-016 adds independent replacement-input API fixtures alongside the behavioral
suites. `make test-input` builds only `src/input.c`, `src/invocation.c`, and their
fixtures; it needs no legacy header, scanner, executor, or Flex. These fixtures
do not execute shell commands. They cover source bytes and positions, owned
invocation operands, explicit EOF, diagnostics/status data, descriptor ownership
and read boundaries, and terminal/prompt selection. The Python runner uses
five-second subprocess timeouts, including for its pseudo-terminal cases.

The fault fixture compiles separate module objects with test-only allocator and
read wrappers. It fails each allocation in turn across all constructors,
invocation modes, and line-buffer growth; it checks retained-allocation counts
and descriptor cleanup after every run. It injects read errors before, within,
and after physical lines, checks that partial lines never escape, and verifies
EINTR retries. Production objects contain no fault-injection hooks.

CSH-004 adds independent lexer fixtures through `make test-lexer`. They compile
only `src/lexer.c` and the lexer/input type headers, with no scanner, input
implementation, or executor. [`tests/lexer.py`](../tests/lexer.py) checks token
kinds, physical source spans, quote/escape fragments, and identical results from
whole-input, physical-line, and one-byte feeds. The C fixture checks owned-token
lifetimes, incomplete contexts, grammar-selected command-substitution endings,
and raw here-document collection. Its tiny command recognizer is a test adapter,
not the CSH-005 parser. `tests/lexer_faults.c` injects each lexer allocation failure
and verifies sticky errors, cleared outputs, and zero live allocations after
cleanup. The Python driver bounds subprocess time and captured output.

CSH-005 adds parser/AST fixtures through `make test-parser`, linking only the
replacement input, lexer, quote, AST, and parser modules. Structural checks cover
precedence, groups, assignments, descriptor adjacency, ordered redirections,
command substitutions, and here-document collection. Error checks distinguish
invalid syntax, incomplete final input, and clean EOF. Separate wrapped objects
inject allocation failures across the entire parsing stack. The parser does
not execute any fixture command. CSH-027 extends these checks to `if`/`elif`,
`for`, `while`, `until`, `case` (including `;&`), and function definitions,
including reserved-word contexts, nested here-documents and substitutions,
source spans, attached redirections, and incomplete/malformed productions.

CSH-030 adds `make test-alias`, linking alias storage/handlers and the replacement
parser stack. Bounded module fixtures exercise builtin output/status, quoting,
recursive substitution, token eligibility, complete-command read boundaries,
nested substitutions, and here-documents. Storage allocation failures check
atomicity; `make test-parser` also sweeps failures through alias injection and
parser cleanup. These fixtures do not execute alias-expanded shell scripts;
CSH-031 owns dispatcher integration.

For focused sanitizer validation:

```sh
make clean
make test-lexer test-parser test-alias CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
```

CSH-022 adds independent shell-state fixtures. `make test-state` builds the
state module, input/invocation modules, and its C fixtures, without Flex or the
executor. The normal fixture covers environment import, unset versus empty
values, attributes, parameter replacement, snapshot lifetimes, copying, and
checkpoint restoration.
The fault fixture compiles a separate state object with test-only allocator
wrappers and checks failed allocations for leaks and unchanged state. Both
executables use module suites through the existing bounded smoke runner.

CSH-019 adds replacement simple-command execution and redirection checks through
`make test-execute`. Its fixtures link the replacement parser, AST, state, and
execution modules without legacy objects or Flex. They exercise AST execution
and the prepared-command API; successful module checks do not
extend the public executable's supported syntax. See
[Simple-command execution](execution.md) for the supported subset and ownership
contracts.

`tests/smoke.py` is a bounded fixture runner for a selected executable. The
default `build/tests/runtime.json` suite checks the public `cshell` across
command strings, script files, and stdin with exact stdout, stderr, status, and
filesystem assertions. `build/tests/runtime-pty.json` checks prompts, EOF, exit
errors, and continuation on a controlling terminal. Both suites are generated
from `tests/runtime_cases.py` using the current platform's helper and errno text.

CSH-033 supplies the controlling pseudo-terminal (PTY) transport. Harness
self-tests use helper programs for signals, stop/continue, foreground transfers,
and cleanup; these are separate from the CSH-034 shell job-control suites.

Each suite declares one of three kinds:

| Kind | Purpose |
| --- | --- |
| `replacement` | Strict behavior expected from the shell executable. |
| `module` | Behavior of a separately selected module test executable. |
| `self` | Runner self-fixtures, including deliberate failures. |

Suite kind does not choose or build an executable. Select the intended executable
and matching suite together. All output comparisons are exact; prototype suites
and prompt stripping are no longer accepted.

## Native tests

Install the build dependencies from the [README](../README.md) and Python 3.9 or
newer:

```sh
make test
make test-pty
make test-harness
```

`make test` builds `TEST_TARGET`, runs the input, lexer, parser, state,
value-expansion, and execution API checks,
and runs the selected behavioral suite.
`make test-pty` builds `PTY_TEST_TARGET` and runs its independently selected
terminal suite. It does not run the input, lexer, parser, state,
value-expansion, or execution API tests. Keeping separate selection variables
means choosing
a module for `make test` does not silently run that module against shell
terminal expectations.
`make test-harness` runs Python unit tests against helper executables and
self-fixtures. Some helpers intentionally produce wrong output, nonzero statuses,
filesystem mismatches, hangs, descendants in multiple terminal process groups,
or excessive output; the unit tests
pass only when the runner detects and handles those conditions correctly.
Self-fixtures are separate from passing shell behavior expectations.

To see a deliberate failure directly, run:

```sh
python3 tests/smoke.py tests/helpers/candidate.py --suite tests/fixtures/self/failing.json --case 'mismatched stdout'
```

This command must exit nonzero and show the differing stdout values. It is an
expected runner demonstration, not a failing shell regression.

The same runner is used by native tests, Docker, and CI. Test selection is explicit:

| Make variable | Default | Meaning |
| --- | --- | --- |
| `TEST_TARGET` | `cshell` | Behavioral candidate target to build; set empty for an already built executable. Input, lexer, parser, state, value-expansion, and execution API fixtures still build and run. |
| `TEST_BINARY` | `./cshell` | Candidate executable. |
| `TEST_SUITE` | `build/tests/runtime.json` | JSON fixture suite. |
| `TEST_TIMEOUT` | `5` | Maximum wall-clock seconds per case. |
| `TEST_OUTPUT_LIMIT` | `65536` | Maximum combined stdout/stderr or PTY output bytes per case. |
| `TEST_CASE` | Empty | Run only the named case. |
| `PTY_TEST_TARGET` | `cshell` | Target built by `test-pty`; set empty for an already built executable. |
| `PTY_TEST_BINARY` | `./cshell` | Candidate selected by `test-pty`. |
| `PTY_TEST_SUITE` | `build/tests/runtime-pty.json` | Suite selected by `test-pty`. |
| `PTY_TEST_CASE` | Empty | Run only the named case in the PTY suite. |
| `PYTHON` | `python3` | Host Python command. |

For a separately built replacement or module, use its own suite:

```sh
make test TEST_TARGET= TEST_BINARY=/absolute/path/to/candidate TEST_SUITE=tests/fixtures/candidate.json
make test-pty PTY_TEST_TARGET= PTY_TEST_BINARY=/absolute/path/to/candidate PTY_TEST_SUITE=tests/fixtures/candidate-pty.json
```

For a module with a Make target, set `TEST_TARGET` to that target instead. These
candidate paths and fixture filenames are examples to replace with real ones.
Generated candidate and module executables belong under `build/` with their own
Make targets. Keep `tests/` for source fixtures and helper scripts, not generated
native executables. Docker excludes `build/` and the host `cshell` executable, then
rebuilds the selected target from source for Linux.

After `make test-runtime test-runtime-pty` generates the suites, direct invocation
gives the same controls:

```sh
python3 tests/smoke.py ./cshell --suite build/tests/runtime.json --timeout 5 --output-limit 65536
python3 tests/smoke.py ./cshell --suite build/tests/runtime.json --case 'exit initially (stdin)'
python3 tests/smoke.py ./cshell --suite build/tests/runtime-pty.json
```

Cases report `PASS`, `FAIL`, or `SKIP`. Failures include the case name and relevant
differences, status, timeout, or output-limit details. Invalid suites and unknown
case names also return a nonzero status. A suite with all selected cases skipped
fails with `no cases ran on this platform`. PTY allocation or controlling-terminal
capabilities that are genuinely unavailable produce a scoped `SKIP` with the
reason; assertion failures, timeouts, unexpected setup errors, and cleanup
failures remain failures. Make and Docker preserve failures.

## Input API and sanitizer checks

For the replacement input layer alone, including sanitizer validation:

```sh
make clean
make test-input
make clean
make test-input CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
```

The full production runtime can also be checked with `make test test-pty` using
these sanitizer flags. Allocation counters work on both macOS and Linux;
Linux ASan also checks leaks. See the [input contract](input-and-invocation.md)
and [ticket evidence](tickets/CSH-016-input-and-invocation.md).

## Parser/AST API and sanitizer checks

```sh
make clean
make test-parser
make clean
make test-parser CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
```

The parser fixtures preserve ownership assertions under `-DNDEBUG`. Allocation
counters cover failed construction, partially built trees, queued here-documents,
nested command substitutions, compound branches/pattern vectors, and function
bodies. Direct AST checks also cover overflow ownership and iterative destruction
of deep compound trees. See [Parser and AST](parser-and-ast.md), the
[initial parser evidence](tickets/CSH-005-parser-and-ast.md), and
[compound syntax evidence](tickets/CSH-027-compound-syntax.md).

For the focused Linux suite:

```sh
make docker-build TEST_TARGET=test-parser DOCKER_IMAGE=cshell-test:csh-005
docker run --rm --init cshell-test:csh-005 make test-parser
```

## Shell-state API and sanitizer checks

For the replacement state module and controlled allocation failures:

```sh
make clean
make test-state
make clean
make test-state CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
```

The normal executable is built from `tests/state_fixture.c`; the
allocation-fault executable is built from `tests/state_faults.c`. The fault
wrappers are used only for the separate test object. The target verifies storage
independently of command execution, including readonly failures and restoring
saved state after later mutations. Allocation counters complement ASan/UBSan;
Linux ASan also checks leaks. See the [state contract](shell-state.md) and
[ticket evidence](tickets/CSH-022-shell-state-storage.md).

To build and run only the focused target in Docker:

```sh
make docker-build TEST_TARGET=test-state
docker run --rm --init cshell-test:local make test-state
```

The image build runs the selected target using the Linux toolchain, and the
second command runs it again in the built image. When setting a custom
`DOCKER_IMAGE` on the build command, use the same image name for `docker run`.

## Authoring fixtures

A suite is a UTF-8 JSON object with `version: 1`, a descriptive `name`, a `kind`,
and a nonempty `cases` array. Unique, nonempty case names identify cases for
diagnostics and `--case` selection. Unknown fields are rejected to catch typos.
Every case requires `name` and `expect`. A pipe case has an optional
`transport: "pipe"` (the default), requires `stdin`, and expects exact `stdout`,
`stderr`, and integer `status`. PTY cases use the terminal contract below instead.
The default comparison is strict, including
whitespace and trailing newlines. Strings are compared as UTF-8 bytes.

This example is a strict replacement-shell fixture. It can be saved under
`tests/fixtures/example.json` and exercised with `/bin/sh` to check the fixture
itself; check the runtime subset before selecting it as a cshell expectation:

```json
{
  "version": 1,
  "name": "file-copy-example",
  "kind": "replacement",
  "cases": [
    {
      "name": "copy and report",
      "stdin": "cat seed.txt > result.txt\nmkdir output\nprintf 'fixture-ok\\n'\nexit 0\n",
      "setup": {"seed.txt": "seed contents\n"},
      "expect": {
        "stdout": "fixture-ok\n",
        "stderr": "",
        "status": 0,
        "files": {
          "result.txt": {"type": "file", "content": "seed contents\n"},
          "output": {"type": "directory"},
          "unwanted.txt": {"type": "absent"}
        }
      }
    }
  ]
}
```

```sh
make test TEST_TARGET= TEST_BINARY=/bin/sh TEST_SUITE=tests/fixtures/example.json
```

Optional case fields:

| Field | Meaning |
| --- | --- |
| `transport` | `pipe` (default) or `pty`; selects the case's input and output contract. |
| `args` | Array of arguments passed directly after the executable; no host shell expansion. |
| `env` | String-to-string overrides for the isolated environment; `HOME` and `TMPDIR` are reserved. |
| `setup` | Relative path-to-text mapping of files created before execution. |
| `expect.files` | Relative paths asserted as a file with exact `content`, a directory, or absent. |
| `platforms` | Allowed platform names, `linux` and/or `darwin`; requires a nonempty `skip_reason`. |
| `skip_reason` | Explanation shown when the current platform is excluded. |
| `timeout` | Per-case wall-clock limit, capped by the command-line limit. |
| `output_limit` | Per-case combined stdout/stderr or PTY byte limit, capped by the command-line limit. |

Use relative paths within the case directory for setup and filesystem assertions;
absolute paths, `..` traversal, and the reserved `.home` and `.tmp` trees are
invalid. Filesystem assertions do not follow symlinks. A symlink does not satisfy
a regular-file or directory assertion, and a
dangling symlink does not count as absent. Only declared paths are asserted; add
an `absent` expectation when unwanted output matters. File-content comparisons
are bounded, including when an output file is unexpectedly large.

Restrict platforms only for behavior that actually differs or is unavailable,
and explain why. For example, `"platforms": ["linux"], "skip_reason": "Requires a
Linux-specific helper"` runs on Linux and reports a reasoned skip on macOS. Do not
use platform skips to hide ordinary failures. Unexpected prompts fail exact
output comparison.

### Terminal fixtures

A PTY case requires `transport: "pty"` and a `steps` array instead of
`stdin`. The candidate starts as the leader of a new session with the PTY slave
as its controlling terminal and all three standard descriptors attached to it.
The terminal starts at 24 rows by 80 columns, with canonical input and terminal
signal processing enabled (`ICANON`, `ISIG`), echo disabled, and output
postprocessing disabled (`OPOST`). This prevents echoed input and newline
expansion from obscuring candidate output. A candidate can subsequently change
its terminal settings.

The terminal combines stdout and stderr into a single byte stream. Final
`expect` requires exact `output` and integer `status`, with optional `files`
using the same filesystem assertion contract as pipe cases. There is no prompt
stripping or output normalization for PTY cases.
An empty `steps` array simply captures output and waits for the candidate to exit.

The current startup fixture is:

```json
{
  "name": "terminal exit status",
  "transport": "pty",
  "steps": [
    {"expect": "$ "},
    {"foreground": "leader"},
    {"send": "exit 23\n"}
  ],
  "expect": {"output": "$ ", "status": 23}
}
```

Each step contains exactly one action:

| Action | Meaning |
| --- | --- |
| `{"expect": "text"}` | Wait for literal UTF-8 text after the previous match, then advance the match cursor past it. This is not a regular expression and does not discard captured output. |
| `{"send": "text\n"}` | Write UTF-8 bytes to the terminal master; canonical input normally requires a newline before the candidate can read a line. |
| `{"control": "C"}` | Send Ctrl-C. `{"control": "Z"}`, `{"control": "D"}`, and `{"control": "\\"}` send Ctrl-Z, Ctrl-D, and Ctrl-\ respectively. Terminal settings determine their effect. |
| `{"signal": "CONT"}` | Signal the terminal's current foreground process group. Supported names are `CONT`, `INT`, `TERM`, `HUP`, `KILL`, and `TSTP`, without a `SIG` prefix. |
| `{"foreground": "leader"}` | Assert that the candidate leader's process group is foreground, using the terminal's `tcgetpgrp` value. `other` asserts that a different group owns the foreground. |

Use an output wait as a handshake before sending the next action or checking
foreground ownership. All steps and process completion share one case timeout;
an `expect` does not restart it. Final output comparison still includes bytes
before, between, and after step matches, so unexpected output cannot be hidden by
a successful intermediate wait. An output limit applies throughout interaction.
Keep Ctrl-C/Ctrl-Z and foreground/background shell expectations in the tickets
that implement those shell features; current runtime fixtures cover prompts,
EOF, exit errors, and command status behavior.

## Isolation and limits

Every case runs in a fresh temporary working directory with fresh `HOME` and
`TMPDIR` directories. The environment begins with the platform's default `PATH`
and `LC_ALL=C`, `LANG=C`; the invoking user's environment is not inherited.
Explicit fixture `env` values are then applied, except `HOME` and `TMPDIR` cannot
be overridden. Suite files are limited to 1 MiB.

The runner streams both output channels and stops the case when their combined
byte limit is exceeded; PTY cases apply the same bound to their combined terminal
stream. The default wall-clock limit is five seconds and the
default output limit is 65,536 bytes. Per-case values may lower these limits but
cannot raise the selected command-line ceilings. Each candidate starts in a new
process group. Pipe cleanup kills that group after success or failure, including
descendants left behind by a candidate that exits early. PTY cleanup covers all
process groups still in the candidate's session, including stopped foreground
jobs, background groups, and descendants left after the leader exits. Terminal
descriptors are closed on success and failure. Final pipe and PTY cleanup have
their own one-second budgets separate from the case's overall timeout; inability
to reap the leader within that bound fails the case instead of hanging the
runner. PTY cleanup also verifies that no live session members remain.

PTY session discovery uses `/proc` on Linux and `/bin/ps` plus process-session
queries on macOS. Both transports share the group-kill check: macOS can return
`EPERM` when a group contains only zombies, so that error is accepted only after
a fresh, bounded session snapshot proves there are no live members of the target
group. The pipe post-exit check allows up to one second for this snapshot. Other
permission errors, a live group, or a failed snapshot remain failures, including
after an otherwise successful exit. The macOS snapshot facilities must therefore
also be available when pipe cleanup encounters `EPERM`. See
[CSH-040](tickets/CSH-040-macos-harness-cleanup.md) for deterministic regression
evidence.

The candidate also receives POSIX resource limits: CPU time is limited to at most
the effective timeout rounded up plus one second, each file is limited to the larger
of 1 MiB or the output limit, open file descriptors are limited to 64, and core
dumps are disabled. Any lower inherited limits remain in force. These limits
complement the wall-clock and streaming-output checks; there is no portable
process-count or address-space cap.

This harness is not a security sandbox. Executables can access files outside the
temporary directory. Pipe descendants that deliberately leave their process
group, and PTY descendants that create a new session with `setsid`, are outside
the supported cleanup contract. Use trusted test programs and fixture inputs.
Docker adds a reproducible Linux environment, but does not replace native
platform testing.

## Docker tests

Install Docker with a running Linux container engine. A local C compiler
or Python installation is not needed for the Docker path.

From the repository root:

```sh
make docker-test
make docker-test-pty
```

This builds the test image from the current source files and runs the input,
lexer, parser, state, and value-expansion API checks and selected behavioral
suite inside it. `TEST_TARGET`,
`TEST_BINARY`, `TEST_SUITE`, `TEST_TIMEOUT`,
`TEST_OUTPUT_LIMIT`, and `TEST_CASE` select the same tests as the native target.
The build target is compiled using the container's Linux toolchain. Candidate
executables and suites must exist inside the image; host absolute paths are not
mounted, and custom fixture suites must be under `tests/` to be copied in.
`docker-test-pty` separately builds `PTY_TEST_TARGET` and runs the terminal suite,
forwarding `PTY_TEST_BINARY`, `PTY_TEST_SUITE`, and `PTY_TEST_CASE` along with the
shared timeout and output limit.

The harness allocates its own controlling PTY inside the container: the
`docker run -t` option is unnecessary. Linux requires an accessible `/dev/ptmx` and a usable
`devpts` mount at `/dev/pts`, as provided by the normal Docker environment. If
container restrictions prevent PTY allocation or acquiring a controlling
terminal, the affected PTY cases report capability-specific skips. This does not
skip unrelated pipe, input, lexer, parser, state, or value-expansion API tests,
and an entirely skipped selected suite still fails. Investigate container device/mount restrictions
instead of adding platform skips for ordinary test failures.

The image uses Debian Bookworm, GCC, GNU Make, and Python 3. Source is copied
into the image, so a host executable or host object files cannot affect the Linux
build. Uncommitted source edits are included. Tests run as a non-root user, and
the container is removed on exit.

Docker uses the engine's default platform (typically Linux arm64 on Apple Silicon,
Linux amd64 on Intel/AMD). The initial image build needs network access to fetch
the base image and Debian packages. The image is a development/test environment
rather than a release package; its release tag is fixed, while security updates
can change the resolved image and packages.

Additional commands:

```sh
make docker-build  # Build the image without running tests
make docker-shell  # Open /bin/sh in the built image for investigation
make docker-test DOCKER_IMAGE=cshell-test:experiment
docker run --rm --init cshell-test:local make test-harness
docker run --rm --init cshell-test:local make test-pty
```

The default image name is `cshell-test:local`; `DOCKER` overrides the Docker
command. The helpers use a source snapshot in the image, without mounting the
working directory. Run `make docker-test` again after edits to rebuild affected
layers. Changes made inside `make docker-shell` disappear when the container
exits.

Equivalent default Docker commands, which do not require host Make:

```sh
docker build --tag cshell-test:local .
docker run --rm --init cshell-test:local
docker run --rm --init cshell-test:local make test-pty
```

For a clean refresh of the toolchain, use `docker build --pull --no-cache --tag
cshell-test:local .`, then run the image. If Docker cannot connect to the daemon,
start Docker Desktop or the configured engine and check `docker info`. Build and
test failures propagate through `make docker-test` as a nonzero exit status.

## Continuous integration

[`.github/workflows/tests.yml`](../.github/workflows/tests.yml) builds and runs the
module API and controlled failure checks, default runtime pipe and PTY suites,
and harness self-tests on Ubuntu 24.04 with GCC and macOS 15 with Clang. Both native
jobs also run the full module and runtime suites under ASan/UBSan, including
input ownership and pipeline failures. A separate Ubuntu job builds and runs the
Docker Linux path, harness self-tests, and full ASan/UBSan suites in the image.
Failing builds, fixtures, or self-tests fail their jobs.

Hosted CI results establish only the checks actually run for that revision.
Keep native macOS validation alongside Docker: Linux containers do not validate
Darwin-specific terminal, signal, or library behavior.

## Conformance fixture planning

Before adding a behavioral case, find its stable requirement ID in the
[requirements matrix](posix-matrix.md) or [utility and option map](posix-utilities.md).
Follow the [evidence conventions](posix-evidence.md) for specification-derived
expectations, environment capture, allowed alternatives and reference comparisons.
The [smoke evidence map](posix-evidence.md#existing-smoke-evidence) records the
observations from its pinned prototype baseline; planned fixture IDs are not
passing tests. That historical suite was removed by CSH-039. Current runtime
and module API checks have their own linked ticket evidence.
CSH-017 and CSH-033 own behavioral harness formats and adapters. Planned shell
fixtures must select a runtime that supports their invocation modes.

## Growing the suite

- [CSH-016](tickets/CSH-016-input-and-invocation.md) and
  [CSH-004](tickets/CSH-004-lexer-and-words.md) cover replacement input/EOF and
  allocation safety; [CSH-019](tickets/CSH-019-simple-command-redirections.md)
  and [CSH-020](tickets/CSH-020-pipeline-lifecycle.md) cover child/descriptor
  failures and high-volume pipelines. The superseded legacy repair tickets
  remain defect history, not required implementation work.
- [CSH-003](tickets/CSH-003-invocation-and-test-harness.md) tracks shell invocation
  and behavioral coverage; its children extend strict replacement expectations.
- [CSH-033](tickets/CSH-033-pty-test-harness.md) provides the PTY transport and
  helper-based terminal tests. [CSH-034](tickets/CSH-034-job-control.md)
  and [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) add shell job-control
  and signal expectations under [CSH-011](tickets/CSH-011-signals-and-job-control.md).
- [CSH-012](tickets/CSH-012-conformance-and-portability.md) audits coverage and
  supported environments, including compiler/libc versions.

CSH-018 supplied strict runtime fixtures.
[CSH-039](tickets/CSH-039-legacy-retirement.md) makes those fixtures the native
and Docker defaults against `cshell`, removes prototype allowances and the
temporary runtime driver, and validates clean builds without legacy objects.

Add a fixture when a behavior is implemented and record which executable and
suite supplied the evidence. Do not turn a passing harness self-test or a
module check into a language-conformance claim.

## Execution API and sanitizer checks

`make test-execute` builds a replacement execution driver and focused API
fixtures. The driver parses complete commands, invokes the AST execution API, and
honors `exit_requested`; it is test infrastructure rather than the replacement
shell runtime. The checks cover command lookup and failure statuses, ordered
redirections, here-document delivery, parent builtin effects and descriptor
restoration, assignment environments, unsupported constructs, and owned-child waiting.
`tests/assignment_fixture.c` exercises resolved regular/special-builtin and function
handlers, nested temporary prefixes, unrelated state retention, copied states,
readonly errors in interactive/noninteractive contexts, and persistent versus
temporary assignment behavior on failure. These are dispatch contracts; the full
CSH-028 supplies function invocation; additional builtin implementations remain
separate work.

```sh
make test-execute
make clean
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 make test-execute CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
make docker-build TEST_TARGET=test-execute DOCKER_IMAGE=cshell-test:csh-019
docker run --rm --init cshell-test:csh-019 make test-execute
```

`make test` includes these checks on native and Docker paths. The test driver
links no legacy objects and needs no Flex. Parent API checks verify restoration
of descriptor flags and initially closed descriptors, including failure after
an earlier redirection succeeded. Prepared here-document checks cover embedded
NUL bytes. An unrelated child verifies that execution waits only for its own
child. The Python runner also checks large and multiple ordered here-documents,
exported environment snapshots, executable-format fallback, and rejection before
side effects.

`tests/execute_faults.c` compiles separate execution/redirection/state objects with
test-only wrappers. Assignment sweeps fail each allocation during selective saves,
batch application, and external environment preparation, checking atomic rollback
and cleanup. State fault fixtures also verify allocation-free selective restoration. It sweeps adapter, parent-dispatch, and external-launch allocation failures,
injects open, duplication, saved-descriptor, temporary-file, and fork failures,
and verifies interrupted waits retry the owned positive PID. Native CI includes
the focused execution target in its AddressSanitizer/UndefinedBehaviorSanitizer
matrix. Fixture assertions remain enabled with `-DNDEBUG`. See
[Simple-command execution](execution.md) for the bounded syntax and prepared-input
contracts.

## Pipeline API and sanitizer checks

`make test-pipeline` uses `build/tests/execute_fixture` with `tests/pipeline.py`,
plus `build/tests/pipeline_fixture` for ownership/status assertions and
`build/tests/execute_faults --pipeline` for deterministic failures. All candidates
link replacement modules only. The runner enforces process-group cleanup,
10-second behavior deadlines, 25-second API/fault deadlines, bounded output,
and a 64-descriptor resource limit. These checks join `make test`, Docker, and
native sanitizer CI without switching the default shell executable.

Coverage includes a 48-stage pipeline, an 8 MiB stream through four stages,
early consumer exit, missing/unexecutable commands, executable-format fallback,
ordered redirection overriding pipes, here-documents, closed stdin/stdout/stderr,
private-fd closure in every stage, default status/negation, and `cd`/`exit`
isolation. Unsupported later stages must reject the whole construct before
creating a file or launching a child.

The API fixture checks repeated execution, raw signal/exit statuses, categories,
last-status updates, and an unrelated exited child left for its owner. Fault
wrappers sweep preparation allocations and every pipe/fork/fcntl setup boundary,
including failure after long-lived stages launch. Each owned PID is verified
reaped and descriptor/allocation counts return to baseline. Child connection,
redirection open/duplication/save, here-document, and allocation failures are
injected at every stage; wait interruption and errors exercise retry/cancellation.

```sh
make test-execute test-pipeline
make clean
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 make test-execute test-pipeline CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
make docker-test DOCKER_IMAGE=cshell-test:csh-020
```

The external descriptor-observer helper remains uninstrumented for the same
macOS sanitizer-startup reason as the simple-command checks. Executor, state,
parser, API fixtures, and fault objects remain instrumented. See
[Pipeline lifecycle](execution.md#pipeline-lifecycle-and-stage-results) for the
synchronous ownership contract and the boundaries reserved for options/job control.

## Value-expansion API and sanitizer checks

`make test-expand` builds independent expansion, arithmetic, and quote-decoder
fixtures and runs the value suites plus `make test-fields`. These check structured fields and
span provenance, state effects, lazy operands, explicit deferred substitutions,
integer boundaries, and allocation failures. `test-fields` adds counted, byte-exact
argument inspection, controlled temporary filename trees, context restrictions,
selected reference-shell comparisons, and allocation/I/O/interruption sweeps.
These fixtures do not claim command-capture or runtime integration behavior.

```sh
make test-expand
make clean
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 make test-expand CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -DNDEBUG -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
make docker-test DOCKER_IMAGE=cshell-test:csh-025
```

`make test` includes these suites on native and Docker paths. Native CI also
runs expansion/state sanitizer checks. Fault-only objects instrument expansion
and quote allocations together, arithmetic/state allocations together, and
field/pathname allocations and directory I/O together;
production objects contain no allocator hooks. All fixture checks stay active
with `-DNDEBUG`. The shared decoder's standalone target is
`build/tests/quote_fixture`, allowing parser reuse without linking the expansion
engine. See [Value expansion](value-expansions.md) for supported contexts,
locale/unspecified choices, ownership, and remaining integration requirements.


`make test-fields` builds `build/tests/fields_fixture` and
`build/tests/fields_faults` independently of the runtime entry point. `tests/fields.py`
creates temporary directory trees with whitespace, wildcard characters, dotfiles,
and symlinks, fixes the C locale for filename assertions, and inspects counts and
bytes. Selected UTF-8 API cases run when a UTF-8 locale is available. The fault
fixture fails each instrumented allocation and filesystem operation and
interrupts at successive callback points, including while a directory is open.
It checks cleared output, unchanged borrowed input/state, and zero outstanding
tracked allocations/streams. The same sanitizer command above includes these
checks; use `test-fields` alone for a focused run.

## State builtin checks

`make test-builtins` runs `tests/builtin_fixture.c` (state/status tables and prepared
special assignments) and `tests/builtins.py` (24 replacement execution cases).
It is included in `make test` and `make docker-test`. For sanitizer validation,
clean first and run `make test-builtins test-execute test-state` with the Clang
AddressSanitizer/UndefinedBehaviorSanitizer flags documented above.


## List, group, and background execution checks

`make test-context` runs `tests/contexts.py` against the public `cshell`,
`context_fixture` for owned PID/state/descriptor assertions, and
`execute_faults --context` for deterministic allocation, pipe, fork and wait
failures. It is included in `make test`, Docker tests and native sanitizer CI.

The behavioral suite covers list precedence/statuses, short-circuiting, state
and cwd isolation, nested redirection lifetimes, group pipeline stages carrying
8 MiB, background stdin overrides, and private descriptor exclusions. FIFO
rendezvous keep the shell alive until background output has been observed.
The API fixture uses pipe gates rather than timing assumptions to prove
asynchronous return, compares the helper's actual PID with the published
background identifier (including pipeline final stages), checks unrelated-child
ownership, and verifies reaping without changing shell status. Fault injection
checks EINTR retry, retained ownership after failed reaping, and partial-launch
cleanup for foreground and background group pipelines.

```sh
make test-context
make clean
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 make test-context CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'
make docker-test
```

These checks target the public executable after the CSH-039 cutover. They
establish list and process-context behavior. The CSH-026 suites below add
expansion integration, and CSH-034 adds job-control coverage. Full POSIX
verification remains separate work.

## Job-control checks

`make test-jobs` exercises runtime job ownership, retained statuses, idle
SIGCHLD reaping, interrupted waits, rapid pipeline exits, and controlled launch
failures. It also runs job builtins through command strings, files, and stdin.
The jobs API fixture gives each phase and each of its 150 rapid-exit pipelines
a five-second progress watchdog, with a 60-second outer runner bound. Timeout
diagnostics name the active phase. A deliberately stalled pipeline checks the
watchdog and descendant cleanup. This separates cumulative sanitizer/fork cost
from a stalled operation without reducing the iteration count.
`make test-jobs-pty` drives actual cshell jobs using the CSH-033 transport:
foreground signals, stopped pipelines, bg/fg, background terminal reads,
selectors, monitor changes, descriptor collisions, and saved terminal settings.
One case repeats 32 complete stop/bg/fg/Ctrl-C cycles with exact prompt and
foreground-group assertions under the existing five-second case bound.
A second PTY fixture injects process-group, terminal-transfer, mode-restoration,
and wait errors and checks the recovered shell group and resource ownership.

Both targets are included in the default native, Docker, and sanitizer paths.
The job helper has no sanitizer instrumentation so its terminal/descriptor
observations measure the launched process rather than sanitizer startup.
See [Job control](job-control.md) and [Traps and signals](traps-and-signals.md)
for the combined behavior. Harness timeouts bound all interactive scenarios; no job-control
claim follows from a helper-only test.

`make test-prompt` compiles only the main module with fault hooks that interrupt
and shorten prompt writes. Its exact primary/continuation transcript proves
that prompt output retries EINTR and partial writes before waiting for input.
It runs through `make test`, including the default Docker and sanitizer paths.
See [CSH-044](tickets/CSH-044-intermittent-bg-prompt.md) and
[CSH-045](tickets/CSH-045-jobs-fixture-timeout.md) for the failing observations
and fixes.

## Trap and signal checks

`tests/trap_cases.py` contributes cross-mode cases to `make test-runtime` and
`make test`. They cover EXIT and signal actions, listing/reinput, ignored and
reset dispositions, invalid conditions, function/eval/subshell/substitution
environments, foreground deferral, and interrupted wait status. The runtime
PTY suite adds idle and continuation Ctrl-C recovery, trapped INT, and hangup.
`make test-pty` and `make docker-test-pty` include these cases alongside the
existing job and terminal ownership checks. The strict runner terminates the
case's process session after a failure or timeout.

## Integrated substitutions and here-documents

CSH-026 adds `tests/substitution_cases.py` to the generated runtime suites.
`make test-runtime test-runtime-pty` checks exact output, diagnostics, status and
files across command strings, script files, stdin and terminal recovery. Cases
include nested dollar/backquote substitutions, captures up to 1 MiB (larger than
pipe capacity), an expanded 512 KiB here-document, trailing-newline removal,
IFS/globbing, scalar assignments/redirections, declaration operands, shared
parameter-pattern encoding, state/cwd isolation and failure timing.

`make test-substitution` runs `tests/substitution_fixture.c` and the execution
fault binary through a bounded Python runner in temporary directories. It checks
unrelated child ownership, repeated captures, all initially closed standard-fd
combinations, word rollback, API-supplied nounset/noglob/interactive options,
parent descriptor counts, and injected allocation/pipe/fcntl/fork/read/wait
failures. Capture failures drain or close output and reap the owned child.
The option flags exercise state APIs; CSH-032 adds runtime `set -u`/`set -f`
and other option parsing/effects through `make test-options`.

Both suites are in `make test`, so the normal native, Docker and sanitizer CI
paths cover them. For a focused sanitizer run:

```sh
make clean
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 make -j2 \
  test-substitution test-runtime test-runtime-pty test-expand test-pipeline \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The runtime harness's file-size limit is at least 1 MiB; generated here-document
fixtures stay below it because the redirection implementation uses an unlinked
temporary file. The 1 MiB substitution cases inspect the captured length instead
of passing the entire value as an external argument or printing it to the
bounded output file.

## Control-flow and function execution

`make test-control` runs control-flow fixtures in command-string, script-file,
and stdin modes, plus allocation-failure sweeps through function calls, retained
definitions, loops, case, and nested redirects. It is included in `make test`,
Docker tests, and sanitizer CI. See [Control flow and functions](control-flow.md)
for observable behavior and ownership checks.

## Evaluation and utility builtin checks

`make test-evaluation` selects CSH-031 cross-mode and interactive invocation
fixtures. `make test` includes them in the full runtime suite. `make test-control`
also sweeps allocation failures in nested eval/dot, read, getopts and hash, with
parameter, descriptor and allocation restoration assertions. The terminal suite
adds read continuation prompts, eval error recovery and `command` foreground
interruption. See [Evaluation builtins](evaluation-builtins.md) for supported
behavior, explicit host dependencies and profile boundaries.

## Shell options

`make test-options` checks invocation and runtime option behavior with explicit
stdout/stderr/status/filesystem expectations in all three input modes.
`make test-runtime-pty` adds interactive EOF, monitor defaults and overrides,
nounset recovery and noexec. These suites are included in `make test` and
`make test-pty`, including Docker and sanitizer runs. See
[Shell options](shell-options.md) for the requirement mapping and permitted
choices; fixture sources are `tests/option_cases.py` and `tests/runtime_cases.py`.

## CSH-050 jobs and signal evidence

The [clause map](jobs-signals-evidence.md) identifies exact runtime, PTY and API
assertions and residual requirements. `make test-jobs` also invokes `/bin/kill`;
the Docker image installs Debian `procps` explicitly. Native hosts must supply
that external executable. Its signal-number listing and TERM delivery are
tested separately from the builtin. Debian procps 4.0.2 fails the separate
`/bin/kill -l 143` audit probe; [CSH-052](tickets/CSH-052-host-utility-evidence.md)
owns that host gap. It is not counted as a passing status-mapping assertion.
