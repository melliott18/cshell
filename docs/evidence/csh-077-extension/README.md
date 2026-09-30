# CSH-077 controlled PTY and session extension

These records extend, without replacing, the [original evidence](../csh-077/README.md).
The user supplied no disposable physical hardware and requested qualification of
available PTYs and sessions. No physical serial/terminal device was opened or
configured. `U-040/stty-physical-terminal` stays open under CSH-081.

## Completed strict subsets

| Environment | Ordinary PTY assertions | ASan/UBSan PTY assertions | Registered sessions |
| --- | --- | --- | --- |
| Native macOS 14.8.7 arm64 | 640 original + 90 effects; zero failures | 640 + 90; zero failures | Unavailable: Linux mount namespace required |
| Hosted Ubuntu 24.04, kernel 6.17, glibc 2.39 | 640 + 90; zero failures | 640 + 90; zero failures | 20 selected vendor assertions; zero failures |

Six capture/cleanup harness tests pass in each normal/sanitized focused run.
The final native ordinary run also passes ten ownership regressions. The 90
new assertions comprise eighteen cases across direct execution, command string,
script file, shell stdin and explicit exec. They verify eleven real-byte stty
transformations, four mesg descriptor-priority scenarios and three who private
record/terminal-selection scenarios. The [section map](../../host-terminal-contracts.md#controlled-data-and-session-extension)
defines their exact boundaries.

The Linux session run covers delivery, denial and who am i/I in all five modes.
It used a new private mount namespace, private mount propagation and tmpfs /run,
with only two owned PTYs and private native-format login records. Each child
cleared supplementary groups and dropped real/effective/saved credentials to
nobody/tty; it verified those identities before exec. The record confirms mount
removal and temporary-directory removal. Captures retain selected greeting,
message and footer bytes; these are vendor behavior witnesses.

Two observed obligations remain **unqualified**: `write/POSIX-EOT` (vendor emits
EOF instead of EOT) and `write/two-sender-alerts` (missing sender alerts). Both are
retained in the raw session JSON and assigned to CSH-081. `--strict-eot` is an
optional failing vendor audit; this evidence does not claim an invocation of
that option. Selected vendor passes are not full write/POSIX passes. Hardware,
untested combinations, locale/signal/I/O partitions and all remaining full-page
contracts remain open.

## Reproduction and identities

Run ordinary native checks from the worktree:

```sh
make -B -j2 test-host-terminal-profile test-host-terminal-effects \
  test-host-terminal-harness test-host-inventory
```

Sanitizer builds use:

```sh
ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
MallocNanoZone=0 make -B -j2 test-host-terminal-profile \
  test-host-terminal-effects test-host-terminal-harness \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The first native sanitizer rebuild is in `csh-077-extended-asan.log.gz`; the final
native sanitizer invocation reused that instrumented build (without `-B`) after
Python-only fixture edits. Its binary hashes match the first sanitizer records.
The final ordinary run rebuilt all targets and restored ordinary binaries.

Linux sessions additionally require:

```sh
sudo unshare --mount --propagation private --fork \
  python3 tests/host_registered_sessions.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-registered-sessions.json
```

The [focused workflow run](https://github.com/melliott18/cshell/actions/runs/36656716717)
at `cccd71f6aa083f2176cfbd9db819fdfcc95a25d9` supplies the Ubuntu results.
`linux-normal-*` came from its preserved ordinary records; `linux-asan-*` came
from its post-rebuild records. Sessions ran only against the ordinary build.
`linux-hosted-job.log.gz` retains build commands and exit results;
`linux-hosted-run.json.gz` retains job metadata. Hosted macOS was still queued at
the recorded snapshot; no hosted macOS success is claimed.

The [general CI run](https://github.com/melliott18/cshell/actions/runs/36656716818)
at the same source passed its Ubuntu and Docker jobs; its macOS job was queued.
`general-hosted-run.json.gz` preserves that snapshot. These are separate from the
local Docker daemon, which continued returning HTTP 500; it was not restarted.

Every raw report includes provider paths/hashes, package/environment identity,
actual byte captures, fixture cleanup, and per-file build/test source hashes.
Final native sanitizer and hosted Linux source digests match
`2550bd8017c8851b298f992d7a936ee6bd3c19ff709c5927e6465e9e81e215f1`.
The final native ordinary report additionally includes descriptive extension
metadata in `tests/host_contracts.json`; executable and fixture sources are
unchanged. Gzip files are lossless; `artifacts.json` hashes each retained file.

## Earlier attempts and limitations

- `csh-077-effects-first.log.gz` and `csh-077-extended-native.log.gz` retain the
  first passing effects and combined ordinary runs. `native-asan-*` and
  `csh-077-extended-asan.log.gz` retain the earlier passing sanitizer rebuild.
- `csh-077-hosted-macos.log.gz` retains the earlier general macOS CI failure
  (run 36630264396, job 109617417716): ten mesg fd2 output mismatches in the
  sanitizer phase. That job did not retain the unexpected bytes. Targeted
  sanitized local reproduction passed ten cases both before and after preserving
  ASAN_OPTIONS/UBSAN_OPTIONS/MallocNanoZone in the child environment; the two
  `csh-077-mesg-sanitizer*` records retain this. No cause is assigned to the
  historical failure and hosted macOS revalidation remains pending.
- `csh-077-native-session-unavailable.*` records a refused native macOS session
  attempt: zero passes, one setup failure. It is unavailable capability, not a
  passing or skipped Linux profile.
- The original evidence's broader Darwin job-terminal fault timeout and residual
  UE child, and local Docker artifact/cleanup limitations, remain unresolved.
  They were not rerun or erased by these focused passing runs.

CSH-077 remains review; CSH-081 owns the remaining utility contracts. No complete
terminal/session, stock-host or full-system POSIX qualification is claimed.
