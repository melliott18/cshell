# CSH-081 continuation evidence

This is a bounded continuation of the [first increment](../csh-081/README.md).
CSH-081 remains in-progress. No result here establishes complete utility-page
or full-system POSIX conformance. The [current section map](../../host-terminal-contracts.md#csh-081-residual-implementation)
retains untested software partitions and unavailable environments individually.

## Behavior and independent oracles

- `tput init/reset` on a real read-only PTY previously returned success without a
  diagnostic in all five invocation paths. `init-errors-before.json.gz` retains
  all 10 failures, alongside 25 passing existing output-error cases. The provider
  now emits checked terminfo strings for every operand. Initialization emits
  is1/is2/is3; reset emits rs1/rs2/rs3 with per-phase initialization fallback.
  Missing operations remain successful no-ops. Ordered literal strings,
  control/eight-bit bytes, empty operations, unknown types, unset/null defaults,
  unchanged kernel terminal modes and real output failures have strict oracles.
  Initialization programs/files and vendor margin/tab/termios extensions are not
  part of this documented implementation-defined policy. Real display effects
  are not inferred from emitted bytes.
- The `stty -a` oracle compares base flag polarity, character size, speed,
  nine control values, MIN/TIME and window size with independent termios/ioctl
  state, both before and after changed flag/control preconditions. A synthetic
  report regression rejects wrong flags, controls, speeds, sizes and conflicting
  polarities. It does not call stty to construct expected values. Unequal-speed,
  additional representation/locale partitions and physical behavior remain open.
- `who -u` uses explicitly private records with authored timestamps/PIDs and
  controlled PTY access times: current, two hours plus 30 seconds, and 25 hours.
  The two-hour precondition stays away from minute boundaries. Exact selected
  Darwin/GNU idle strings and record PIDs are checked. Read-only-PTY output must
  fail with a diagnostic. Database race/corruption/read-error partitions and
  non-C LC_TIME formats are not qualified here.
- Linux registered sessions add default HUP/QUIT/PIPE termination after observed
  sender alerts. Both actual registered usernames and terminal ownership differ
  in the added access/denial cases. No account is created or changed: existing
  nobody/daemon identities are used only in the disposable container, with the
  sender's real/effective/saved IDs and empty supplementary groups verified.
- Two real output faults close the owned recipient PTY master only after its
  complete greeting and both sender alerts have been independently captured.
  Subsequent message data and EOF/EOT separately require status 1, a diagnostic,
  and no delivered message/EOT bytes. Captures record the synchronized hangup.
  The master descriptor is replaced with /dev/null so caller cleanup retains
  ownership of its descriptor number. No unrelated terminal is closed.

The residual subset is 137 cases × five modes = 685 assertions. Together with
665 original terminal and 90 data-effect assertions, there are 1,440 strict
terminal/data assertions. Linux registered sessions have 28 × five = 140.
Modes are direct provider execution, command string, script file, shell stdin,
and explicit exec. Ordinary failures, sanitizer diagnostics, timeouts, setup
failures, unused-input consumption and cleanup failures fail closed.

## Validation

| Environment/build | Result |
| --- | --- |
| Native macOS ordinary | 1,440 terminal/data assertions; 10 harness tests; 10 ownership regressions; 1,162 host assertions; 3,950 runtime assertions; 33 runtime PTY cases; all pass, zero gaps/skips |
| Docker Debian ordinary | Same counts and results; additionally all 140 private registered-session assertions pass |
| Docker Debian ASan/UBSan, `-Werror` | All 1,440 terminal/data assertions, 10 harness tests and 140 private registered-session assertions pass |
| Native macOS ASan/UBSan, `-Werror` | All 1,440 terminal/data assertions and 10 harness tests pass |

The source identity for the all final ordinary and sanitized runs is
`5507eb3605623107472bb3c3a1b6fd49ac1febab1383d9f9df89cd634530093d`.
Records retain the complete file/hash map, exact provider and binary hashes,
OS/compiler/package information, command, environment, raw byte streams and
termios observations. Each run also verifies source stability and fixture
removal. Source identity covers Makefile, Dockerfile, src, include, tests and
tools; explanatory docs/evidence are outside that digest.

Ordinary validation used:

```sh
make -B -j4 cshell host-profile build/tests/host_session_records
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" \
  make -j4 test-host-profile test-runtime test-runtime-pty
```

Sanitized validation used:

```sh
ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 \
UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
make -B -j4 test-host-terminal-profile test-host-terminal-effects \
  test-host-terminal-residuals test-host-terminal-harness \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

On Linux only, root entered a fresh private mount namespace inside the owned
container for each normal/sanitized registered-session run:

```sh
unshare --mount --propagation private --fork \
  python3 tests/host_registered_sessions.py ./cshell \
  --path /csh081/build/host-profile/bin:/usr/bin:/bin --record RECORD.json
```

The sanitized session command also supplied the ASAN_OPTIONS/UBSAN_OPTIONS
shown above. The runner verifies private mount propagation, creates a private
`/run`, removes that mount afterward and confines delivery to owned PTYs. The
container used SYS_ADMIN with seccomp unconfined, not privileged mode; its source
mount was read-only and Linux builds ran in a separate copied tree as `cshell`.
Container/image identity and removal are retained in the adjacent JSON files.
The owned container was removed after its records were collected.

## Record guide and limitations

`native-normal-*`, `linux-normal-*`, `native-sanitized-*` and `linux-sanitized-*` contain final raw
captures/manifests. Full ordinary build/test logs retain runtime, harness and
inventory results as well as terminal totals. `init-errors-before` preserves the
reproduced vendor delegation defect. `tput-after`, `reports-before` and
`who-before` are focused native diagnostics during development; the latter two
passed without provider repairs. `linux-residual-first` and
`linux-sessions-first` are passing earlier Linux runs before the final source
snapshot and hangup cases. `native-normal-tests.log.gz` retains an intermediate
ordinary pass; the final ordinary records supersede it. Old evidence directories
are unchanged. Gzip files decompress to their original byte contents.

The macOS SDK's older `tigetstr(char *)` declaration initially produced const
qualification warnings. String-literal pointer declarations were adjusted for
that API; the final `-Werror` builds verify both platforms without suppression.

`artifacts.json` hashes every neighboring file except itself. Raw failures are
not normalized or overwritten. Physical serial behavior retains the exact open
identifier `U-040/stty-physical-terminal`; no disposable hardware was supplied.
Privileged positive Darwin sessions remain unqualified because no disposable
macOS VM was supplied. Those unavailable environments do not excuse remaining
software partitions in the section map, including additional locales, resource
boundaries, signal inheritance and database/input/output error timing.
