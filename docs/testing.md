# Testing cshell

## Coverage and suite selection

`tests/smoke.py` is a bounded fixture runner for a selected executable. The default
`tests/fixtures/prototype.json` suite checks the current prototype's startup,
explicit exit, external command execution, successive commands, and filesystem
effects from external commands. It sends `exit` because EOF handling is incomplete
and explicitly allows the prototype's
`Shell> ` prompt on non-interactive stdout.

Each suite declares one of four kinds:

| Kind | Purpose |
| --- | --- |
| `prototype` | Current legacy behavior; individual cases may request prompt stripping. |
| `replacement` | Strict behavior expected from a replacement shell executable. |
| `module` | Behavior of a separately selected module test executable. |
| `self` | Runner self-fixtures, including deliberate failures. |

Suite kind does not choose or build an executable. Always select the intended
candidate and suite together. Replacement and module tests do not inherit
prototype allowances. Passing the prototype suite does not establish quoting,
pipelines, redirections, signal behavior, or POSIX compliance. Future script-file
and `-c` cases can use fixture arguments without requiring these modes from the
current shell.

## Native tests

Install the build dependencies from the [README](../README.md) and Python 3.9 or
newer:

```sh
make test
make test-harness
```

`make test` builds `TEST_TARGET` and runs the selected behavioral suite.
`make test-harness` runs Python unit tests against helper executables and
self-fixtures. Some helpers intentionally produce wrong output, nonzero statuses,
filesystem mismatches, hangs, descendants, or excessive output; the unit tests
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
| `TEST_TARGET` | `cshell` | Target to build before running; set empty for an already built executable. |
| `TEST_BINARY` | `./cshell` | Candidate executable. |
| `TEST_SUITE` | `tests/fixtures/prototype.json` | JSON fixture suite. |
| `TEST_TIMEOUT` | `5` | Maximum wall-clock seconds per case. |
| `TEST_OUTPUT_LIMIT` | `65536` | Maximum combined stdout and stderr bytes per case. |
| `TEST_CASE` | Empty | Run only the named case. |
| `PYTHON` | `python3` | Host Python command. |

For a separately built replacement or module, use its own suite:

```sh
make test TEST_TARGET= TEST_BINARY=/absolute/path/to/candidate TEST_SUITE=tests/fixtures/candidate.json
```

For a module with a Make target, set `TEST_TARGET` to that target instead. These
candidate paths and fixture filenames are examples to replace with real ones.
Do not use the default prototype suite as evidence for replacement behavior.
Generated candidate and module executables belong under `build/` with their own
Make targets. Keep `tests/` for source fixtures and helper scripts, not generated
native executables. Docker excludes `build/` and the host `cshell` executable, then
rebuilds the selected target from source for Linux.

Direct invocation gives the same controls:

```sh
python3 tests/smoke.py ./cshell --suite tests/fixtures/prototype.json --timeout 5 --output-limit 65536
python3 tests/smoke.py ./cshell --suite tests/fixtures/prototype.json --case exit
```

Cases report `PASS`, `FAIL`, or `SKIP`. Failures include the case name and relevant
differences, status, timeout, or output-limit details. Invalid suites and unknown
case names also return a nonzero status. A suite with all selected cases skipped
fails with `no cases ran on this platform`. Make and Docker preserve failures.

## Authoring fixtures

A suite is a UTF-8 JSON object with `version: 1`, a descriptive `name`, a `kind`,
and a nonempty `cases` array. Unique, nonempty case names identify cases for
diagnostics and `--case` selection. Unknown fields are rejected to catch typos.
Each case requires `name`, `stdin`, and `expect`; `expect` requires exact `stdout`,
`stderr`, and integer `status`. The default comparison is strict, including
whitespace and trailing newlines. Strings are compared as UTF-8 bytes.

This example is a strict replacement-shell fixture. It can be saved under
`tests/fixtures/example.json` and exercised with `/bin/sh` to check the fixture
itself; it is not an expectation for the current prototype:

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
| `args` | Array of arguments passed directly after the executable; no host shell expansion. |
| `env` | String-to-string overrides for the isolated environment; `HOME` and `TMPDIR` are reserved. |
| `setup` | Relative path-to-text mapping of files created before execution. |
| `expect.files` | Relative paths asserted as a file with exact `content`, a directory, or absent. |
| `platforms` | Allowed platform names, `linux` and/or `darwin`; requires a nonempty `skip_reason`. |
| `skip_reason` | Explanation shown when the current platform is excluded. |
| `timeout` | Per-case wall-clock limit, capped by the command-line limit. |
| `output_limit` | Per-case combined stdout/stderr byte limit, capped by the command-line limit. |
| `strip_prompt` | Allowed only in a `prototype` case; `true` removes the known `Shell> ` stdout text before comparison. |

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
use platform skips to hide ordinary failures. Keep prototype prompt allowances
visible in fixtures, and remove each allowance when its behavior is replaced.

## Isolation and limits

Every case runs in a fresh temporary working directory with fresh `HOME` and
`TMPDIR` directories. The environment begins with the platform's default `PATH`
and `LC_ALL=C`, `LANG=C`; the invoking user's environment is not inherited.
Explicit fixture `env` values are then applied, except `HOME` and `TMPDIR` cannot
be overridden. Suite files are limited to 1 MiB.

The runner streams both output channels and stops the case when their combined
byte limit is exceeded. The default wall-clock limit is five seconds and the
default output limit is 65,536 bytes. Per-case values may lower these limits but
cannot raise the selected command-line ceilings. Each candidate starts in a new
process group. Cleanup kills that group after success or failure, including
descendants left behind by a candidate that exits early.

The candidate also receives POSIX resource limits: CPU time is limited to at most
the effective timeout rounded up plus one second, each file is limited to the larger
of 1 MiB or the output limit, open file descriptors are limited to 64, and core
dumps are disabled. Any lower inherited limits remain in force. These limits
complement the wall-clock and streaming-output checks; there is no portable
process-count or address-space cap.

This harness is not a security sandbox. Executables can access files outside the
temporary directory, and descendants that deliberately leave their process group
are outside the supported cleanup contract. Use trusted test programs and fixture
inputs. Docker adds a reproducible Linux environment, but does not replace native
platform testing.

## Docker tests

Install Docker with a running Linux container engine. A local C compiler, Flex,
or Python installation is not needed for the Docker path.

From the repository root:

```sh
make docker-test
```

This builds the test image from the current source files and runs the selected
suite inside it. `TEST_TARGET`, `TEST_BINARY`, `TEST_SUITE`, `TEST_TIMEOUT`,
`TEST_OUTPUT_LIMIT`, and `TEST_CASE` select the same tests as the native target.
The build target is compiled using the container's Linux toolchain. Candidate
executables and suites must exist inside the image; host absolute paths are not
mounted, and custom fixture suites must be under `tests/` to be copied in.

The image uses Debian Bookworm, GCC, GNU Make, Flex, and Python 3. Source is copied
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
```

For a clean refresh of the toolchain, use `docker build --pull --no-cache --tag
cshell-test:local .`, then run the image. If Docker cannot connect to the daemon,
start Docker Desktop or the configured engine and check `docker info`. Build and
test failures propagate through `make docker-test` as a nonzero exit status.

## Continuous integration

[`.github/workflows/tests.yml`](../.github/workflows/tests.yml) builds and runs the
default prototype suite and the harness self-tests on Ubuntu 24.04 with GCC and
macOS 15 with Clang. A separate Ubuntu job builds and runs the Docker Linux path
and runs the same harness self-tests in the image. Failing builds, fixtures, or
self-tests fail their jobs.

Hosted CI results establish only the checks actually run for that revision.
Keep native macOS validation alongside Docker: Linux containers do not validate
Darwin-specific terminal, signal, or library behavior.

## Growing the suite

- [CSH-002](tickets/CSH-002-legacy-safety.md) tracks regression cases for memory,
  process, descriptor, and EOF defects, including sanitizer runs.
- [CSH-003](tickets/CSH-003-invocation-and-test-harness.md) tracks shell invocation
  and behavioral coverage; its children extend strict replacement expectations.
- [CSH-011](tickets/CSH-011-signals-and-job-control.md) adds pseudo-terminal tests.
- [CSH-012](tickets/CSH-012-conformance-and-portability.md) audits coverage and
  supported environments, including compiler/libc versions.

Add a fixture when a behavior is implemented and record which executable and
suite supplied the evidence. Do not turn a passing harness self-test or a
prototype allowance into a language-conformance claim.
