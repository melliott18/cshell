# CSH-050 integrated jobs, signals and trap evidence

Source/test revision: `bf7723f`, based on `b1b6b15`; collected 2026-09-28.
The original CSH-050 implementation was already merged in PR #91. This follow-up
repairs focused validation coverage and reconciles the integrated follow-ups;
it changes no production C code or expected shell behavior.

`make test-traps` previously omitted the original `tests/trap_cases.py` cases,
which were only exercised by the full runtime suite. It now includes
`test-trap-runtime`: 207 unchanged runtime cases, comprising 114 trap cases
and 93 exit/signal-status cases. `selected-cases.json` records their exact names
and generated-suite hash. A structural comparison verified that each selected
case equals its counterpart in the full generated runtime suite, with unique
names. The invalid numeric exit cases remain project-policy observations.

`make test-jobs-signals` combines jobs/API/fault/retention, trap/exit runtime,
signal contracts/edges, interposed and public waits, notification/terminal
fault checks, and both jobs and runtime PTY suites. Each uses the existing
bounded runner; no retries, assertions, deadlines or capability rules change.

## Fresh results

| Retained log | Command and result |
| --- | --- |
| `native-focused.log.gz` | `make test-jobs-signals`: exit 0. 207 selected runtime cases, 148 jobs cases, 2,464 signal edges, 361 signal contracts, 20 inherited-ignore cases, six interposed waits, both 30-case PTY suites, one fault PTY case, lifecycle APIs and ownership/fault/watchdog checks pass. No focused skips. |
| `native-full.log.gz` | `make test test-pty test-harness`: exit 0. All 3,113 runtime cases, selected focused cases, module/fault checks, both 30-case PTY suites and 73 harness self-tests pass. Existing stock-host gaps and capability skips are listed below. |
| `docker-full.log.gz` | `make test-jobs-signals test test-harness` in the retained image: exit 0. All 3,113 runtime cases, 207 selected cases, 148 jobs cases, 2,495 signal edges, 361 signal contracts, both 30-case PTY suites, lifecycle/API/fault checks and 73 harness self-tests pass. No jobs/signal skips; unrelated gaps/skips below. |
| `native-sanitizer.log.gz` | `make test-trap-runtime` in a separate instrumented source copy: exit 0; 207 passed, zero failures/skips and no sanitizer diagnostics. |
| `docker-sanitizer.log.gz` | `make clean` then `make test-trap-runtime` with ASan/UBSan in a fresh container: exit 0; 207 passed, zero failures/skips and no sanitizer diagnostics. |

The new source-selection/build wiring is exercised with ASan/UBSan. Full fresh
sanitizer validation of the unchanged production implementation is **not-run**
in this follow-up; the broader prior runs remain in CSH-054/057/058's records.
Native Linux outside Docker is also **not-run** at this revision locally; CI
owns that additional platform check. Neither limitation is a capability waiver.

## Identity and reproduction

The normal and sanitizer builds on both hosts share source digest
`0ba6c898d3d8a63df8039450ce16ba1162a6455191f7207aad944bc7d953fd9c`.
The identity JSON files retain the full source manifest (Makefile, Dockerfile,
src, include and tests, excluding Python caches), source revision and dirty
state, binary/helper/generated-suite hashes, UTC collection time, compiler,
flags, platform/system-library versions and relevant environment. Only evidence
and documentation changed after `bf7723f`. Identity collection reuses
[CSH-058's collector](../csh-058/identity.py); the native normal identity also
hashes every built helper executable. Generated helper paths differ by platform.

Native: macOS 14.8.7, Darwin 23.6.0 arm64, Apple Clang 15.0.0, Python 3.12.2.
Docker: Debian 12 arm64, Linux 6.4.16-linuxkit aarch64, GCC 12.2.0,
glibc 2.36, Python 3.11.2, Docker engine 24.0.6. Exact image/engine metadata
is retained in `docker-image.json` and `docker-engine.json`.
Normal flags are `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`, with
`-D_POSIX_C_SOURCE=200809L -Iinclude` and no extra link libraries/flags.

```sh
make -j4
make test-jobs-signals
make test test-pty test-harness

docker build -t cshell-test:csh-050-integration .
docker run --rm --init cshell-test:csh-050-integration \
  make test-jobs-signals test test-harness

# In a separate clean source/build copy:
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
make test-trap-runtime \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The retained Docker invocation also mounts Dockerfile and the identity collector
read-only and writes its identity after testing; these do not affect assertions.
The normal suite uses the C locale, PATH=os.defpath, temporary HOME/TMPDIR, no
TZ override, umask 077, five-second case deadlines and 65,536-byte smoke output
bounds. Terminal cases retain the CSH-033 controlling session, canonical ISIG,
no echo and exact LF transcript, with bounded descendant cleanup. Specialized
API/edge/watchdog bounds remain as documented in the linked follow-up maps.
The smoke runner retains MallocNanoZone but does not forward ASAN_OPTIONS or
UBSAN_OPTIONS: sanitizer defaults apply inside its shell subprocesses even
when the outer make invocation supplies those variables. The Docker sanitizer
caller sets `ASAN_OPTIONS=halt_on_error=1:detect_leaks=0` and
`UBSAN_OPTIONS=halt_on_error=1`; these likewise do not override the controlled
smoke subprocess environment.

## Residual failures, skips and ownership

- CSH-057's hosted `repeated background resumes preserve prompt and terminal`
  failure (status 1 instead of 130) remains applicable to baseline `b1b6b15`.
  [PR #112](https://github.com/melliott18/cshell/pull/112) proposes its correction;
  it is **not included** in this source revision. Fresh passes do not erase the
  retained failure. CSH-050's platform acceptance remains unchecked until that
  correction and integration evidence resolve it.
- CSH-054 and CSH-058 are integrated. The [current clause map](../../jobs-signals-evidence.md)
  links their exact assertions, replacing stale descriptions of inheritance,
  delivery, public waits, listing failures and group/permission evidence as
  future work. Permission tests prove the interposed EPERM handling contract,
  not enforcement across actual host credentials.
- Native full validation retains 12 stock-host timestamp comparison gaps;
  Docker retains nine stock-host printf/kill gaps. CSH-052 owns those observations;
  CSH-056's opt-in qualified profile addresses the selected gaps, with wider
  capability boundaries under CSH-059/060. Stock external kill's failed status
  mapping is not converted into a pass by builtin or qualified-profile results.
- Both normal full runs skip two unequal UID/GID probes: CSH-046 requires Linux
  root setresuid/setresgid; this Docker run uses the image's unprivileged user.
- CSH-053 skips Shift-JIS, Big5 and GBK pathname/locale groups on both hosts;
  macOS also cannot represent the GB18030 raw pathname probe. CSH-042 retains
  the unavailable translated ENOENT diagnostic on macOS. Exact reasons are in
  the full logs. None is a new jobs/signal allowance.
- Earlier CSH-050/054/057/058 failed or incomplete loaded runs remain retained
  at their original records under their existing owners. No reference-shell
  comparison supplies an oracle here. Full UP/XSI remains unselected, parent
  families remain implemented subsets, and the CSH-012 gate stays closed.
