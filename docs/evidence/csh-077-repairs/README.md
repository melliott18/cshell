# CSH-077 remaining-issue repairs

This pass implements the user's request to proceed with remaining issues while
identifying external environment/manual-test needs. It preserves the
[original](../csh-077/README.md) and [extension](../csh-077-extension/README.md)
evidence. Implementation commit: `ae9a815fbbde0d6a07e7a0cf079fe479f3cee965`.

## Changes and strict boundary

- The opt-in profile builds a portable FreeBSD-derived write provider. The
  licensed original source, upstream commit/hash and adapted hash are retained
  here; [provenance and local changes](../../../tools/host-profile/README.md#standalone-write-provenance)
  explain the removal of FreeBSD-specific APIs, permission checks, conversion
  policy and async-signal-safe interrupt handling. It is never installed with
  elevated privileges or over a system provider.
- Selected write now emits the required greeting structure, exactly two sender
  alerts, preserved printable/space/bell input and EOT on EOF/SIGINT. Linux
  assertions cover full and partial EOF, erase/kill, selected control characters,
  implicit terminal selection, denied/missing recipients and who am i/I through
  five dispatch modes, plus synchronized direct/exec SIGINT (47 assertions).
  EOT/alerts are strict requirements with no gap allowance.
- Four new tput cases cover missing operations/continuation and attached/repeated
  -T. A ncurses capability query distinguishes an absent clear operation from a
  vendor error; no vendor failure status is waived. Linux builds require
  libncurses-dev, now supplied by Docker/CI. The mesg no-terminal case requires
  both error status and diagnostic; the adapter supplies the missing diagnostic.
- The principal terminal suite grows from 640 to 665 assertions. Together with
  90 data-effect assertions there are 755 PTY assertions. A readiness-triggered
  signal regression increases the capture harness from six to seven tests.

This closes `write/POSIX-EOT` and `write/two-sender-alerts` **only for the repaired
selected Linux subset**. Historical stock vendors are unchanged. Positive native
macOS registered sessions, other signal paths, locale/multibyte/IEXTEN matrices,
additional credentials, resource/I/O failures and remaining whole-page/default
requirements stay with CSH-081. No physical hardware was supplied or tested.

## Completed validation

| Environment/build | PTY assertions | Harness tests | Sessions | Existing integration |
| --- | --- | --- | --- | --- |
| Native macOS ordinary | 755 passed | 7 passed | Positive sessions unavailable | 1,162 host assertions; 3,950 runtime witnesses; runtime PTY and ten ownership regressions passed |
| Native macOS ASan/UBSan | 755 passed | 7 passed | Not run | Focused changed subsets |
| Docker Debian ordinary | 755 passed | 7 passed | 47 passed | 1,162 host assertions; runtime PTY and ten ownership regressions passed |
| Docker Debian ASan/UBSan | 755 passed | 7 passed | 47 passed | Focused changed subsets |

Each declared assertion is strict. Both Linux session records have an empty
unqualified-condition list for EOT/alerts and successful mount/directory cleanup.
This does not waive the remaining full-page contracts. Normal and sanitizer raw
JSON, build/test logs and immutable per-file source/provider hashes are separate.

## Reproduction

Ordinary profile, harness, ownership and existing integration:

```sh
make -B -j2 test-host-profile test-runtime-pty
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime
```

Sanitized terminal subsets:

```sh
ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
MallocNanoZone=0 make -B -j2 test-host-terminal-profile \
  test-host-terminal-effects test-host-terminal-harness \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Linux sessions, against each ordinary/sanitized build:

```sh
unshare --mount --propagation private --fork \
  python3 tests/host_registered_sessions.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-registered-sessions.json
```

The Docker image was built using `--build-arg TEST_TARGET=host-profile`.
A disposable root container supplied `--cap-add SYS_ADMIN --security-opt
seccomp=unconfined`; ordinary checks/builds ran as its cshell user via runuser,
then root invoked the mount-namespace session fixture. Both session runs clear
supplementary groups and verify real/effective/saved nobody/tty credentials
before dispatch. Only owned PTYs and the namespace's private /run login database
are used. The JSON records successful mount and fixture removal. Artifacts were
copied out and the owned test containers were removed; image identity and final
container exit state are retained. The host Docker daemon was not restarted.

## Attempts retained

- `csh-077-followup-tput-before.*`: four added tput cases reproduced 20 failures
  across the five paths. Expectations were preserved by the final repair.
- Initial native full-profile run: five mesg diagnostic mismatches came from a
  fixture key typo (expected stderr remained empty). The fixture was corrected
  to explicitly require a diagnostic; the native provider already emitted one.
- `csh-077-followup-linux-initial-profile.json.gz`: fifteen strict failures on
  Debian. Ten exposed a second missing-clear vendor status (2 instead of the
  macOS status 1); five exposed mesg's silent no-terminal error. The final tput
  implementation queries the capability before executing, avoiding ambiguous
  status normalization. The mesg adapter emits the required diagnostic.
- Preliminary standalone compilation exposed Darwin feature-macro/header
  differences (S_IWRITE, O_NOFOLLOW and signal declarations), corrected with
  S_IWGRP, signal.h and explicit platform feature macros. The initial compiler
  output is in the conversation, not a retained build log.
- Earlier passing native/sessions iterations remain distinct from final files.
  A filtered 55-case tput pass is diagnostic evidence, not a full-profile pass.
- `csh-077-latest-macos-failure.log.gz` retains the prior general-CI signal test
  timeout: a 16-iteration exit-status batch produced correct output through 14
  then reached its five-second limit. Other paths and a second general macOS
  job passed. This is not identified as a terminal regression; its cause and
  robustness remain outside the selected repairs. The earlier focused macOS
  workflow subsequently passed at c5769df.

The first new hosted Ubuntu job at
[run 36674557318](https://github.com/melliott18/cshell/actions/runs/36674557318)
passed ordinary 755 PTY/47 session assertions, then its sanitized build rejected
an ignored best-effort diagnostic write result under fortified libc and -Werror.
`csh-077-repairs-hosted-linux-failure.log.gz` retains this failure. Commit
`a51f0987a633f540367eed7468d8a78e2dae65e8` explicitly consumes that byte count;
failed EOT output still exits 1. The corrected native ordinary binary is
byte-identical to the one in the full passing native record. All other build/test
source files are unchanged from the completed full runs. Fortified local compile
and session rechecks, and the new hosted snapshot, are retained separately.

Hosted macOS in the initial repair run was still queued. The earlier focused
macOS workflow passed at c5769df. Historical Darwin job-terminal fault/UE cleanup
remains unresolved; focused passes do not retroactively resolve it.

The [environment matrix](../../host-terminal-contracts.md#remaining-environment-requirements)
separates additional automated fixtures from external capabilities. Physical
serial validation needs supplied hardware and manual connection/identification.
Real display effects need a specified observable terminal/emulator. Privileged
Darwin sessions need a disposable macOS VM. Most other residual work needs
software fixtures and can use the already available environments.

## Corrected hosted result and artifact integrity

The corrected [Ubuntu job](https://github.com/melliott18/cshell/actions/runs/36674970874)
passes all 755 PTY assertions, seven harness tests and 47 registered-session
assertions in both ordinary and ASan/UBSan builds. Hosted macOS remained queued
in the final snapshot. `hosted-linux-normal-*` and `hosted-linux-asan-*` retain
separate raw results. The final sanitized source identity matches every current
build/test source byte, verified in `source-comparison.json`.

An additional disposable Debian run explicitly enabled `_FORTIFY_SOURCE=3` and
-Werror with ASan/UBSan for the corrected standalone write; all 47 sessions
passed. This additional run used an ordinary shell with a sanitized write, and
is labeled separately from the fully sanitized Docker and hosted runs. Its
container used --rm; the current write source was mounted read-only and only a
private evidence directory was writable from the host. Mount cleanup passed.

`artifacts.json` hashes every retained artifact except itself. Gzip contents are
lossless. Source/provider hashes and actual captures live in each raw record;
no earlier evidence was modified. CSH-077 remains review and CSH-081 remains the
open owner of full-page and external-capability requirements.

## Recovery of original stopped Docker fixtures

With the Docker API available again, both original CSH-077 containers
`csh077-verified` and `csh077-validation` were confirmed stopped with exit 0.
Their final terminal/profile JSON was recovered separately as `recovered-*`
artifacts, and both containers were removed successfully. This resolves the
original retrieval/removal limitation without altering its historical evidence.
Those old records are baseline evidence, not validation of the later repairs.

The earlier Darwin fault-helper PID 42555 still has the exact owned worktree
command and UE state, parent 1, after its prior SIGKILL attempt. The new read-only
process snapshot is retained. No second fault fixture or machine restart was
attempted. Clearing the kernel-blocked process may require host recovery/reboot;
this is separate from the passing normal and sanitizer terminal subsets.
