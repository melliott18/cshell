# Application containers and Pipeline

cshell is a command-line application. Its container accepts shell arguments,
script files, or stdin; it does not expose a network port or an HTTP health
endpoint. Container packaging does not establish POSIX conformance or release
qualification. See the [runtime contract](candidate-runtime.md) and
[open tickets](tickets/README.md).

## Image targets

| Target | Purpose | Default command |
| --- | --- | --- |
| `runtime` (default) | Debian runtime utilities, cshell, and Tini; no compiler, Python, or test sources | cshell reading stdin |
| `test` | Full application-owned test environment and Pipeline reports | `python3 tests/container_report.py --output /work/test-results` |
| `development` | Existing toolchain and fixtures for focused development | `make test` |

All targets use UID/GID 10001:10001 for execution. The build uses Linux source
compilation and does not copy the workstation's cshell executable. `BASE_IMAGE`
selects the Debian base for every stage (default `debian:bookworm-slim`); record
the resolved image IDs with run evidence. Debian package repositories are needed
at build time; test and runtime containers can run without a network. This is
not a reproducible, pinned dependency release or a vulnerability-scan result.

Existing `make docker-test`, `make docker-test-pty`, and `make docker-shell`
explicitly select `development`. A plain `docker build .` now selects `runtime`.
For older direct test commands, add `--target development` to the build.

## Run cshell

```sh
make docker-runtime

docker run --rm cshell:local -c 'printf "hello from cshell\n"'
printf 'printf "stdin works\n"\nexit 7\n' | docker run --rm -i cshell:local
docker run --rm -it cshell:local
```

Use `exit` or Ctrl-D to leave the interactive session. Ctrl-C interrupts a
foreground command; Ctrl-Z, `jobs`, `bg`, and `fg` exercise terminal job control.
The terminal interface has no command history or line editor.

To run a script from the current directory, mount it read-only and pass its path:

```sh
docker run --rm --network none --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=16m,mode=1777 \
  --cap-drop ALL --security-opt no-new-privileges \
  --mount "type=bind,src=$PWD,dst=/scripts,readonly" \
  cshell:local /scripts/example.sh arg1 arg2
```

Scripts must be readable by UID 10001; writable output mounts must allow that
UID. `/work` and `/home/cshell` are writable in the ordinary container layer;
with `--read-only`, use `/tmp` or an explicitly supplied writable output mount.
Tini runs as PID 1, reaps orphaned descendants, forwards signals to the command
process group, and preserves exit status. Do not override the entrypoint for
normal application runs. `docker stop` uses TERM: noninteractive jobs terminate
without needing the kill deadline. An interactive shell intentionally ignores
TERM under its shell-language policy; exit normally or send HUP to end that
session. A shell is not a service supervisor; use `exec program ...` for a
single long-running noninteractive workload. No automatic restart policy or
healthcheck is installed for this CLI application.

The runtime uses stock Debian utilities and `/bin/sh` for the existing ENOEXEC
fallback. It does not include the opt-in test host profile or promise all POSIX
utility contracts. Install any extra script dependencies in a derived image.

## Pipeline test contract

Build and run the application test command under the current Pipeline limits:

```sh
make docker-pipeline-build
docker run --name cshell-pipeline-test \
  --user 10001:10001 --network none --memory 1g --cpus 2 --pids-limit 256 \
  --cap-drop ALL --security-opt no-new-privileges \
  cshell-pipeline-test:local
docker cp cshell-pipeline-test:/work/test-results ./cshell-test-results
docker rm cshell-pipeline-test
```

Choose unused container and output names for every retained run. Collect reports
on failure too; never convert a failed process result to success because a report
exists. The `test` target needs a writable container filesystem to compile its
fixtures and hold reports. It includes its own init, so the platform need not
supply `--init`.

The command runs `make test`, `make test-pty`, then `make test-harness`, serially,
and stops at the first failed target. It preserves every existing assertion and
case deadline. `/work/test-results/junit.xml` contains **one aggregate testcase
per completed Make target**, not one per individual shell assertion. Detailed
counts, skips, host `GAP` observations, diagnostics, and compiler output remain
in `test.log`, `test-pty.log`, and `test-harness.log`. Known host gaps retain their
existing classifications; this gate is the development regression suite, not
full host-profile qualification. Setup failures produce a failed testcase when
the report directory is writable. An interrupted run can have partial or missing
reports and must fail at the process/platform gate.

Pipeline's platform-owned registration can use the following values after this
change is merged into the approved application branch:

```json
{
  "schema_version": 1,
  "name": "cshell",
  "repository": "https://github.com/melliott18/cshell.git",
  "approved_ref": "refs/heads/main",
  "platform": "linux/arm64",
  "dockerfile": "Dockerfile",
  "test_target": "test",
  "runtime_target": "runtime",
  "test_user": "10001:10001",
  "reports_directory": "/work/test-results",
  "junit_reports": ["junit.xml"]
}
```

This is an application-side handoff example. Registration belongs in Pipeline's
`config/applications/cshell.json`; this change does not register or deploy the
application. The initial local integration profile uses Linux ARM64. The
[hosted application-container checks](evidence/csh-082/hosted/README.md) also
pass on native AMD64; emulation and other architectures are not qualified here.

Once registered, run from Pipeline with a full approved-main commit and a fresh
output path (replace `FULL_COMMIT_SHA` with that 40-character SHA):

```sh
python3 -m tools.pipeline --app cshell --commit FULL_COMMIT_SHA \
  --output pipeline-runs/cshell-example --timeout 1800
```

Pipeline owns commit admission, report validation, and the decision to build the
runtime after successful tests. Its runtime build alone is not a runtime test.
Use `make docker-runtime-test` here to check the shipped image's invocation,
non-root identity, read-only operation, terminal interaction, exit codes, and
TERM handling. These checks run outside the container with Docker access; they
are not part of the network-isolated application test command.
