# CSH-081 residual terminal evidence

This is a bounded implementation increment for CSH-081, **not completion of its
full-page acceptance criterion**. It adds 115 strict residual cases in five
paths, repairs reproduced provider failures, and expands isolated Linux sessions
to 21 cases in five paths. The [current section map](../../host-terminal-contracts.md#csh-081-residual-implementation)
identifies both tested contracts and remaining software partitions.

The user confirmed no disposable physical serial hardware and no privileged
disposable macOS VM. `U-040/stty-physical-terminal` remains individually open with
its exact hardware requirement, and positive Darwin sessions remain unqualified.
Neither absence is used to excuse the other open software work.

## Completed validation

| Environment | CSH-077 PTY/data assertions | New residual assertions | Harness | Registered sessions | Existing host profile |
| --- | --- | --- | --- | --- | --- |
| Native macOS, ordinary | 665 + 90 passed | 575 passed | 9 passed | Not supplied | 1,162 passed, zero gaps; ten ownership regressions passed |
| Native macOS, ASan/UBSan | 665 + 90 passed | 575 passed | 9 passed | Not supplied | Focused changed subsets only |
| Docker Debian, ordinary | 665 + 90 passed | 575 passed | 9 passed | 105 passed | 1,162 passed, zero gaps; ten ownership regressions passed |
| Docker Debian, ASan/UBSan | 665 + 90 passed | 575 passed | 9 passed | 105 passed | Focused changed subsets only |

Normal and sanitized records are separate. Every declared case is strict, with
no skips or gap waivers. Session records confirm private mount removal and
fixture-directory removal; terminal records confirm fixture removal. Capture
regressions include timeout/descendant cleanup, output limits and late output,
synchronized signals, and a negative offset test in all five paths.

Raw JSON retains platform, package/compiler identity, PATH, provider path/hash,
source-file hashes, environment, expected results, actual bytes/statuses, termios,
permissions, bounds and cleanup. Signal cases record the selected target after
confirmed sender alerts. Session runs clear supplementary groups and verify all
real/effective/saved nobody/tty IDs before dispatch; wrong-group cases explicitly
use nobody's primary group instead. Only owned terminals and private login
records are touched.

`source-comparison.json` compares all passing records with the delivered source.
All executable and build inputs match. Earlier records differ in the session
runner only by the final group-ID metadata correction and stricter sanitizer
rejection; the fresh `csh081-sessions-metadata-{normal,sanitized}.json.gz` records
match every current source file and each pass all 105 assertions. PTY/harness
runner bytes are unchanged. Some earlier records also differ in
`tools/host-profile/README.md`, written after their snapshots. Differences are
listed per file rather than hidden. Lossless gzip artifacts are hashed in
`artifacts.json`; earlier CSH-077/CSH-064 evidence was not changed.

### Final session evidence audit

The first session records incorrectly labeled wrong-group rows with tty's GID 5,
although the verified credential-drop call actually used nobody's primary GID
65534. This affected report metadata, not the exercised credentials. The final
runner records the actual requested/verified GID. It also explicitly rejects
sanitizer diagnostics in every case, including expected permission failures.
Fresh ordinary and sanitized runs both pass 105 assertions; their raw rows have
GID 65534 for all five wrong-group paths. `session-audit.json` additionally scans
the earlier complete captures and confirms they contained no sanitizer
diagnostics, while preserving their erroneous GID fields as historical data.
The second owned container's removal is in `metadata-container-cleanup.json`.
The `python` field in `environment.json` identifies the host evidence collector;
container/provider identity is given separately by the exact image and packages.

## Reproduction

Ordinary build and integration:

```sh
make -j4 test-host-profile
```

This includes ownership, baseline terminal/data, the new residual subset and
nine harness tests. The separately selectable target is
`make test-host-terminal-residuals`; `HOST_TERMINAL_FLAGS='--case NAME'` is only a
diagnostic filter, not a full-subset pass.

Sanitized changed subsets:

```sh
ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
MallocNanoZone=0 make -B -j4 test-host-terminal-profile \
  test-host-terminal-residuals test-host-terminal-effects test-host-terminal-harness \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Registered Linux sessions (ordinary and sanitized builds separately):

```sh
unshare --mount --propagation private --fork \
  python3 tests/host_registered_sessions.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-registered-sessions.json
```

The sanitized invocation also sets the ASAN_OPTIONS/UBSAN_OPTIONS shown above.
The terminal workflow runs the new residual target in both builds and preserves
JSON on failures as well as successes. These recorded results are local native
and Docker results, not claims about hosted CI.

`environment.json` identifies the exact pre-existing Debian qualification image
used for its installed compiler, libc, locales and ncurses dependencies. Current
sources were copied into a fresh `/csh081` inside an owned disposable container;
all executables were rebuilt there as its unprivileged cshell user. No host
binary was reused. Root was used only to establish the private mount namespace
and fixture credentials. The container supplied SYS_ADMIN and unconfined
seccomp for mount isolation, but did not need SYS_PTRACE. The read-only source
mount and container/image identities are recorded; removal is in
`container-cleanup.json`.

## Failed attempts and repairs

- `native-initial.json.gz` / `native-initial.log.gz`: 330 passes and 40 failures.
  Actual provider defects were stty -nl leaving INLCR/IGNCR, tabs -1 setting a
  stop beyond the last column, and ignored output errors in stty/tabs/tput.
  Two oracle assumptions were corrected independently against the normative
  text/environment: unset/null TERM has an unspecified default (not a required
  usage error), and ioctl terminal width takes precedence over the narrow
  terminfo model. The final narrow fixture explicitly sets width 17.
- `native-repair-attempt.*`: an incorrect fixed `/usr/bin/stty` provider path on
  Darwin caused 190 stty failures, plus five retained tabs interval failures.
  The path is now `/bin/stty` on both platforms. An intermediate 40-stop fixture
  guess was rejected; the independent width-41 oracle remains all positions
  0–40. The standalone provider repairs the extra position 41 rather than
  weakening the oracle.
- `csh081-build.log.gz` / `csh081-native-repair2.log.gz`: the first standalone tabs
  build collided with ncurses' `set_tab` macro. Capability variables were renamed;
  ordinary and strict -Werror sanitizer builds subsequently passed.
- `native-tty-output-failure.json.gz` / `csh081-native-final.log.gz`: 570 residual
  passes and five failures revealed Darwin tty's silent output failure with
  nonterminal stdin. The new tty provider checks output in both input states.
- `linux-sessions-initial.json.gz`: nine passes before signal-target discovery
  failed closed. Cross-user `/proc/PID/exe` requires ptrace privileges unavailable
  in the container. Target selection now checks owned process group, argv[0]
  and kernel command name without adding those privileges.
- `linux-sessions-second.json.gz`: 91 passes and four fixture failures. A
  root-owned mode-0620 sender prevented shell input redirection, so the utility
  was never reached in four paths. The fixture now grants mode 0660, permitting
  group reads/writes while retaining the intended non-owner chmod denial.
- Other `csh081-*.log.gz` files preserve intermediate passing runs. A filename
  containing “final” is not itself proof of success; the table above uses only
  `native-normal-*`, `native-sanitized-*`, `linux-normal-*` and
  `linux-sanitized-*` JSON and the corresponding qualified/sanitized logs.

The selected stty report relay and tput clear emitter now check actual writes,
not just descriptor access flags. No translated-catalog, physical terminal,
full-signal or complete resource/error-partition claim follows from these passes.
