# CSH-050: Close jobs, signal and trap evidence gaps

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-036, CSH-039
- Branch: test/CSH-050-jobs-signals-evidence
- Issue: [#82](https://github.com/melliott18/cshell/issues/82)

## Goal

Separate base and conditional portions, map exact runtime/PTY/API cases to each obligation, resolve or retain concrete CSH-044/045 defects, and reproduce foreground/background startup, terminal restoration, notifications, trap timing/inheritance and wait/status cases. Record capability skips with reasons and owners and never count intermittent failure as a pass.

## Explicit current limitation

The retained job/signal/trap witnesses do not form complete requirement-family evidence. CSH-044/045 are integrated; their regressions are retained. The clause map and residual obligations are now explicit in [jobs/signals evidence](../jobs-signals-evidence.md) and [CSH-053](CSH-053-signal-contract-gaps.md). Base signal/asynchronous-list/wait semantics remain applicable even while the UP utility profile is unselected; implemented job-control extensions need their supported behavior and terminal capability conditions recorded separately.

This is an open evidence limitation found by the
[CSH-037 independent review](../audit-review.md), not a declaration that every
listed behavior is absent or defective. Existing passing witnesses retain
their original scope. This ticket must not be closed by relabeling a broad
requirement family from a small sample.

## Scope

| Requirement | Obligation to review and map to exact assertions |
| --- | --- |
| [EXEC-009](../posix-matrix.md#exec-009) | Launch asynchronous lists without waiting; track IDs/status, stdin redirection and required interactive messages. |
| [JOB-001](../posix-matrix.md#job-001) | Initialize process/foreground groups according to controlling-terminal and foreground/background startup state. |
| [JOB-002](../posix-matrix.md#job-002) | Group foreground/background pipelines and lists; hand off and regain the terminal, retaining stopped jobs and terminal settings. |
| [JOB-003](../posix-matrix.md#job-003) | Track job numbers/known PIDs and issue stopped/completed notifications at monitor/notify-dependent times. |
| [SIG-001](../posix-matrix.md#sig-001) | Apply interactive shell signal dispositions and asynchronous-list SIGINT/SIGQUIT inheritance. |
| [SIG-002](../posix-matrix.md#sig-002) | Defer trapped signals during foreground commands; interrupt wait with status above 128 before dispatching the trap. |
| [SIG-003](../posix-matrix.md#sig-003) | Reset/retain signal and trap state as required across subshells, functions, substitutions, exec and exit. |
| [U-008](../posix-utilities.md#u-008) | `exit`: current environment termination, 0–255 statuses, applicable signal-derived statuses, omitted operand, EXIT trap behavior. |
| [U-015](../posix-utilities.md#u-015) | `trap`: set/reset/ignore/list, Issue 8 `-p` and reinput, EXIT, saved status, signal inheritance/subshell listing; XSI numeric signals under O-021. Invalid conditions warn and return non-zero without becoming special-builtin errors. Exclude undefined SIGKILL/SIGSTOP installations from pass/fail oracles. |
| [U-026](../posix-utilities.md#u-026) | `kill`: `-s`, `-l`, default TERM, PID/process-group/job operands, signal-name/status mapping and diagnostics. Supply/record external host kill as well; alternate forms under O-021. |
| [U-032](../posix-utilities.md#u-032) | `wait`: all/selected known children, last-operand status, unknown PID 127, status retention and consumed IDs; interrupts/traps and enabled job-control operands. |

Relevant documented choices: D-007, JOB-001/JOB-002/JOB-003 applicability, U-015/U-026 conditional XSI portions. Review the
[choice register](../posix-matrix.md#open-implementation-choices) and the
source links in each row; separate required, conditional, unspecified and
implementation-defined portions before selecting an oracle.

## Existing witnesses to reconcile

- [tests/jobs_cases.py](../../tests/jobs_cases.py)
- [tests/jobs_fixture.c](../../tests/jobs_fixture.c)
- [tests/trap_cases.py](../../tests/trap_cases.py)
- [tests/traps.py](../../tests/traps.py)
- [tests/runtime_cases.py](../../tests/runtime_cases.py)

These are starting points for inspection, not claims that the complete rows
already pass. Reuse exact case names and assertions where they are sufficient;
add or split fixtures only for a concrete coverage gap.

## Acceptance criteria

- [x] Every requirement above has a clause/condition map naming the reviewed
  normative source, selected policies, implementation, exact fixture assertions
  and any narrower unresolved defect or limitation.
- [ ] Remaining applicable runtime cases pass on supported native macOS and
  Linux/Docker configurations; required PTY/capability or locale skips name
  the reason, scope and follow-up owner.
- [x] Results record the source/suite revision, binary identity, compiler,
  flags, OS/libc/architecture and exact status/output/state assertions.
- [x] Matrix rows and reverse ownership links reflect only the verified scope;
  broad rows are split where necessary and the CSH-012 compliance gate remains
  closed while any applicable requirements are unmet.

## Validation

Run the applicable focused suites above and the integration paths documented in
[Testing](../testing.md), including `make test test-pty test-harness`, Docker
and ASan/UBSan checks where the changed paths require them. Record exact case
names and results following the [evidence rules](../posix-evidence.md).
Reference-shell comparisons are separate observations, never normative oracles.

## Implementation notes/evidence

Allocated by the CSH-037 follow-up audit at baseline `58ca5c3`. The explicit
limitation and complete row list above replace reliance on already-completed
implementation tickets as owners of remaining verification work.


### Implemented audit scope

The [eleven-family clause map](../jobs-signals-evidence.md) names normative
sources, policies, implementation entry points, exact assertions and residual
clauses. Parent requirements remain implemented subsets. CSH-053 owns two
confirmed shell defects (interactive TERM and lowercase `kill -s`) plus the
narrower unverified obligations. CSH-052 owns the reproduced external kill
status-mapping failure. None is counted as a pass or as inapplicable.

This change fixes three concrete trap gaps: `-p` now emits default actions,
listings include signals ignored at entry, and unsigned-first-operand reset
handles `trap 0`. New evidence covers nested foreground/background startup,
notification timing with both notify settings, launch PID messages, numeric
wait ordering/consumption, background stdin, both asynchronous interrupt
ignores, dot/exec trap inheritance and external kill provisioning.

Before/after probes reconstructed the baseline runtime with the original
`src/traps.c` from `b692aa5` and otherwise identical normal objects:

| Script (`-c`) | Before | After |
| --- | --- | --- |
| `trap -p USR1 EXIT` | Empty stdout/stderr, status 0 | `trap -- '-' USR1\ntrap -- '-' EXIT\n`, empty stderr, status 0 |
| `trap ':' EXIT; trap 0; trap -p EXIT` | `trap -- ':' EXIT\n`; stderr `cshell: trap: missing condition\n`, final status 0 | `trap -- '-' EXIT\n`, empty stderr, status 0 |

### Validation record

Source and suite revision: `7810e2adf4066ace2f0b1d42ac6387389b0cf8e5`, based on
`b692aa5`; only documentation was dirty during the final runs. Tests and helpers
are from that commit. UTC date: 2026-09-26 (runs began around 05:00 UTC; final focused checks after 06:00 UTC).
No scanner generator/runtime is used. Resolved normal binary:
`/Users/mitchell/.codex/worktrees/csh-050-jobs-signals-evidence/cshell/cshell`.
The sanitizer source copy is the same revision at `build/asan`, with binary
`build/asan/cshell`. Docker runs at `/work`, with binary `/work/cshell`.

Native: macOS 14.8.7, build 23J520; Darwin 23.6.0
`xnu-10063.141.1.712.16~1/RELEASE_ARM64_T6000`, arm64; Apple Clang 15.0.0
(`clang-1500.3.9.4`); Python 3.12.2. System libraries are identified by the
macOS/Darwin build. Normal flags: `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`,
CPPFLAGS `-D_POSIX_C_SOURCE=200809L -Iinclude`; no additional link flags/libraries.

Docker: engine 24.0.6; final image
`sha256:d722bb64b088016fd8c3b38c87e5a7993229a2f4724ee9fa94a258093e16dbdf`,
`debian:bookworm-slim`, Debian 12 arm64; Linux 6.4.16-linuxkit aarch64;
GCC 12.2.0 (`12.2.0-14+deb12u1`), glibc `2.36-9+deb12u14`, Python 3.11.2;
procps `2:4.0.2-3`. Native Linux outside Docker is **not-run** on this Mac;
CSH-053/CI owns that additional environment, not a capability exclusion.

Sanitizer flags on both hosts:
`-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer`, link
`-fsanitize=address,undefined`. The make invocations supply
`ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`, plus
`MallocNanoZone=0` on macOS. The runtime harness intentionally supplies its
controlled environment (see the clause map), so ASAN/UBSAN runtime defaults
apply to those subprocesses; API runners inherit the supplied sanitizer options. The native caller has
LANG/LC_ALL/LC_CTYPE `C.UTF-8`, TERM `dumb`, no TZ; the complete inherited
variable-name list and relevant values are in `build/evidence/native-identity.json`.

SHA-256 identities:

| Binary | SHA-256 |
| --- | --- |
| Native normal cshell | `1e3540b4d9acea1c5d4018c37609431854336b102764834a3038ab33c17226f2` |
| Native sanitizer cshell | `4b73d6292c1e37821c9aa22e3962175a2c6b2b42e414ed4e8651bf635607b34a` |
| Native jobs API fixture | `e01f59b48e878221c1a420fc048af87335784835cba5d8ef8d792f97e346c0ca` |
| Native jobs PTY helper | `af8f6b962d2128fb28850295693774bbcde0f38da59901efe01577df057eb7ad` |
| Native fault fixture | `0df7a54f746e479538bfa3ac414792f28b124232b824fb4434fd785b9bcd9279` |
| Docker normal cshell | `48238e4a586ffeff7d39e45dc406b7bdeafb9b74f8db60bb7a64708794fd8674` |
| Docker sanitizer cshell | `70e0c8d6a8bcb6c69f0a18008585563a292586b15a6cfc6fc5f77b9af3c8d61a` |
| Native `/bin/kill` (OS build above) | `2cb72601038b0d001f6a584a86edcbd98489cedc64ce61f27c3cf75c499c6d31` |
| Docker `/bin/kill` (procps-ng 4.0.2) | `51e5efe55fbb617951e3e00626dd1a1c1435fe4f8c9b7c180e080f156ceb14c0` |

Reproduction commands from the worktree:

```sh
make test && make test-pty && make test-harness
make docker-test docker-test-pty DOCKER_IMAGE=cshell-test:csh-050
docker run --rm --init cshell-test:csh-050 make test-harness
# In a separate source copy, retain the normal binary for identity comparison:
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
  make test test-pty \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

| Run | Result |
| --- | --- |
| Native focused `make -j4 test-jobs test-jobs-pty test-traps` | PASS: 148 jobs runtime cases; 15 job PTY cases; one terminal fault case; five entry-ignore cases; API ownership/fault/watchdog checks |
| Native initial `make -j4 test test-pty test-harness` | PASS before narrowing the external kill case from status 143 to signal 15; runtime 1354, runtime PTY 27, jobs 148, jobs PTY 15, harness 64 |
| Native final source, serial `make test && make test-pty && make test-harness` | PASS: same counts, zero failures/skips, plus all module, fault and portability targets; harness 64 in 31.596s |
| Native final sanitizer, serial `make -C build/asan test` then `test-pty` | PASS: runtime 1354, runtime PTY 27, jobs 148, jobs PTY 15, terminal faults 1, all module/fault/portability checks; zero failures/skips or sanitizer findings |
| Docker focused sanitizer from the preserved build image | PASS: 117 trap runtime cases, five inherited-ignore cases, 15 job PTY cases, one terminal fault case; zero failures/skips or sanitizer findings. Binary hash unchanged |
| Docker final harness `docker run --rm --init cshell-test:csh-050 make test-harness` | PASS: all 64 self-tests in 8.610s; the earlier failed run remains recorded below |
| Docker final normal `make docker-test docker-test-pty DOCKER_IMAGE=cshell-test:csh-050` | PASS: runtime 1354, runtime PTY 27, jobs 148, jobs PTY 15, terminal faults 1; all normal module/fault/portability targets; zero skips |

The broad Docker sanitizer run was stopped with container status 143 after
passing the jobs/API/watchdog, entry-ignore, control, input, parser, lexer,
state, expansion and other module checks and reaching the runtime suite. It
was making progress but had become unusually slow. This is **incomplete**, not
a full sanitizer pass. Its already-built filesystem was preserved as
`sha256:4ea6e4558e2629b3c9a4c01d4db7dc6b31db5a27a27c5bba7e3779b5aeabb79c`
(`cshell-test:csh-050-asan`) for focused changed-path validation. No compiler
flags or assertions were relaxed. A first focused invocation incorrectly used
`--case 'traps:'`, but the runner requires an exact name; it exited 2 before
running tests. The corrected invocation selects all `traps:` cases into a
separate JSON suite, then runs `test-traps test-jobs-pty`. Exact focused command (completed around
06:04 UTC):

```sh
docker run --rm --init -e ASAN_OPTIONS=halt_on_error=1 \
  -e UBSAN_OPTIONS=halt_on_error=1 cshell-test:csh-050-asan sh -c '
python3 -c '\''import json; from pathlib import Path; s=json.loads(Path("build/tests/runtime.json").read_text()); s["cases"]=[c for c in s["cases"] if c["name"].startswith("traps:")]; Path("build/tests/traps-focused.json").write_text(json.dumps(s))'\'' &&
python3 tests/smoke.py ./cshell --suite build/tests/traps-focused.json &&
make test-traps test-jobs-pty && sha256sum cshell'
```

Failed observations are retained separately:

- First Docker run used external `/bin/kill -l 143`: all three invocation modes
  **failed** (stdout empty; stderr `/bin/kill: unknown signal name 143\n`; status
  0). Direct signal-number mapping (`-l 15`) is a narrower later passing case,
  not a fix for status mapping. CSH-052 owns the failure. macOS returns `TERM\n`.
- Final-source native parallel run, concurrent with full native sanitizer and
  Docker work, **failed** `Ctrl-Z jobs bg fg Ctrl-C` only at cleanup: `/bin/ps
  -axo pid=,stat=` timed out at 0.99965 seconds. The concurrent sanitizer run
  similarly **failed** `nested background startup and restoration` at 0.99924
  seconds. There was no transcript/foreground mismatch in either failure.
  CSH-053 retains this load/transport boundary; serial passes do not erase it.
- The first Docker harness run **failed** two self-tests:
  `test_snapshot_failure_reports_teardown_error_and_reaps_leader` did not reach
  process setup, and `test_terminal_control_characters_deliver_interrupt_quit_and_eof`
  exceeded the five-second fixture bound. Sanitizer execution chained after
  that harness was **not-run**; it was subsequently launched separately.
  CSH-053 owns these transport failures with the CSH-033/040 fixtures.
- Isolated probes on both hosts **failed** interactive untrapped TERM (process
  status -15, no output) and lowercase `kill -s term` (status 1 with invalid-signal
  diagnostic). CSH-053 records sources and reproducers.

Logs and identity JSON are retained locally in this worktree's ignored
`build/evidence/` (also `/tmp/csh050-*.log`). The serial native log begins after
the first control-flow output chunk; the full command exited 0. The source,
exact fixture assertions and summarized results above are the durable record.
The full platform acceptance box remains open while the recorded harness/load
failures and residual requirement defects are unresolved; this audit is ready
for review, not an assertion of complete jobs/signal conformance.
