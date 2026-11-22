# CSH-129: ed SIGINT response capture

Base: `d175f9f26f12775923d5f4350a1a187fb9f01f19` (`origin/main`).
The affected helper is byte-identical to CSH-127's helper. Production shell and
ed provider source are unchanged. This evidence qualifies the capture repair,
not the full ed page or other signal timing boundaries.

## Diagnosis and original evidence

[Original Linux language report](original-linux-language-initial.json.gz) and
[original command log](original-linux-initial-command-0.log.gz) are copied
byte-for-byte from CSH-127 commit `44cedbe`. They retain 1088 passes and the one
command-string `ed/signal-int` failure. That historical failure did not retain
saved-file contents or descriptor ordering; its exact schedule is unknown.

The selected provider's [command loop](../../../tools/host-profile/vendor/ed/main_loop.c)
flushes stdout before reading each next command and emits the required `?\n`
marker after SIGINT recovery. The signal driver sends `P`, `1p`, `w saved`, and
`q` together: ed may therefore finish and close its streams before the driver
reads the final `1p` response. The capture reader, rather than the provider's
recovery code, owns the reproduced failure.

The [ordering probe](../../../tests/ed_signal_order_probe.py) sends the unchanged
final editor commands, waits for the real selected ed to exit, then sorts the
ready descriptors with stderr first. It fabricates no provider bytes or status.
It records the helper result, read ordering, any stdout left unread by the old
helper, the saved and original files, and child/fixture cleanup.

- On Linux, [the old helper](linux-ordered-original.json) reads stderr EOF and
  raises before reading stdout. The probe then reads the pending `recovered\n`
  from the PTY. Status is zero, `saved` contains `recovered\n`, and `original`
  remains empty. This establishes a reproducible reader defect matching the
  original symptom; it does not reconstruct the historical event order.
- On macOS, [the old helper](native-ordered-original.json) also fails after
  stderr EOF, but closing the last slave descriptor has already discarded the
  final PTY bytes. [An intermediate EOF-only repair](native-ordered-eof-only.json)
  reaches stdout EOF without the final response. The saved file is correct and
  the editor exits zero in both runs. The
  [intermediate harness log](native-harness-eof-only.log.gz) retains that failure.
- The final helper keeps terminal input but captures stdout through a pipe.
  [macOS](native-ordered-fixed.json) and [Linux](linux-ordered-fixed.json) both
  read stderr EOF first, then the exact pending stdout response, and pass.
  Both pipes are drained independently so extra diagnostics or trailing output
  cannot escape the final exact assertions.

The [original helper](original-helper.py.gz) and
[intermediate EOF-only helper](eof-only-helper.py.gz) are retained with SHA-256
hashes in the native identity record for independent replay.

The unchanged SIGINT oracle requires stdout `recovered\n*?\n*recovered\n`, empty
stderr, normal exit, `saved` bytes `recovered\n`, and an unchanged empty original
operand. Every read/drain/write is bounded; combined stream bytes are capped at
65536 and the event trace at its first 512 entries. The seven-second outer
capture and inherited process group still bound descendants and remove fixtures.

## Validation

The focused records retain selected provider hashes, shell hash, credentials,
platform, source inputs, event traces and every fixture's removal flag:
[native](native-signal-int.json), [Linux](linux-signal-int.json).
Both pass direct, command-string and script-file execution. Linux runs as uid
10001 in Docker, not as root and not on a separate native Linux host.

The language harness includes the real-provider forced order, split markers,
EOF on either pipe, rejection of stale response bytes, protocol peers with
missing/trailing output, wrong files, signal death, flood and hang behavior,
and setup faults in terminal attributes, process spawn and capture setup.
The existing descendant/unrelated-child cleanup control remains in place.

The [Linux command manifest](linux-commands.json) records exit zero for
`make test-host-languages test-host-profile` and `make test-harness`; the old
helper probe's exit one is expected and separately retained. The actual
[validation driver](linux-validation.py) mounted this worktree read-only at
`/source`, copied the three current test files and original helper into the
fresh development image, then rebuilt and ran as its existing unprivileged
user. [Container identity](linux-container.json) and per-result source hashes
identify the executed state; no host binary was used in Linux.

| Linux check | Result |
| --- | --- |
| Language harness | 13 tests pass |
| Full language suite, standalone and profile | 1089 pass each |
| General selected host utilities | 1162 pass, no gaps |
| Filesystem profile | 12483 pass |
| Text boundary suite | 866 pass, 2 unavailable |
| General harness | 107 pass, 1 Darwin-only skip |

The text unavailability is the existing `cat/filesystem-enospc` boundary in two
modes: no explicit disposable filesystem of at most 2 MiB was supplied. These
are not CSH-129 passes or new allowances. Full Linux logs are
[build](linux-command-0.log.gz), [required targets](linux-command-4.log.gz), and
[general harness](linux-command-5.log.gz). Detailed records are
[language](linux-host-languages-results.json.gz),
[language in profile](linux-host-languages-profile-results.json.gz),
[host utilities](linux-host-profile-results.json.gz),
[filesystem](linux-host-filesystem-profile.json.gz), and
[text](linux-host-text-results.json.gz).

[Native required targets](native-required-targets.log.gz) also exit zero:

| Native macOS check | Result |
| --- | --- |
| Language harness | 13 tests pass |
| Full language suite, standalone and profile | 1089 pass each |
| General selected host utilities | 1162 pass, no gaps |
| Filesystem profile | 12443 pass |
| Text boundary suite | 866 pass, 2 unavailable |
| Additional general harness | 105 pass, 3 startup timeouts; see below |

The same two text ENOSPC cases are unavailable on macOS. Detailed records are
[language](native-host-languages-results.json.gz),
[language in profile](native-host-languages-profile-results.json.gz),
[host utilities](native-host-profile-results.json.gz),
[filesystem](native-host-filesystem-profile.json.gz), and
[text](native-host-text-results.json.gz). Final language records on both
platforms match the current helper, regression-test and probe SHA-256 hashes.
The earlier native focused record precedes comment-only helper cleanup; the
full language records include all three signal modes on the final source.

The final [native language harness](native-language-harness.log.gz) passes all
13 tests. All failure records remain separate from later results.

## Setup and additional observations

Native initial provisioning failed because `gfind` was absent from PATH:
[build](native-initial-build.log.gz), [target attempt](native-profile-missing-gfind.log.gz).
A focused invocation before provisioning finished selected system `/bin/ed`
and correctly failed its different signal transcript in all three modes:
[system-ed failure](native-signal-system-ed.json). This is not a selected-provider
pass. Provisioning was repaired by copying the existing CSH-128 private `gfind`
into `build/prerequisites` and prepending it to the provisioning PATH; no host
packages were installed. [Native identities](native-identities.json) retain its
hash and the actual shell/editor/helper/test hashes.

The broader [native general harness](native-general-harness.log.gz) has three
no-output startup timeouts out of 108 tests: case filtering, resource limits,
and cleanup after parent exit. These unchanged harness/helper files do not
exercise the edited language driver. A separate diagnostic run of those exact
three tests [passes](native-general-harness-isolated.log.gz); the initial
failures remain unresolved observations, not a successful full-suite result.
No deadline was increased and this isolated result does not replace the first.

[Ticket tests](tickets.log.gz) and [live registry validation](ticket-live.log.gz)
pass, with the existing historical shared-branch warnings for CSH-044/045.

## Reproduction

```sh
# Supply the existing GNU gfind, gdd, gexpr and gettext prerequisites on macOS.
make -j4 cshell host-profile build/tests/host_ed_faults
python3 tests/ed_signal_order_probe.py --ed build/host-ed --record build/tests/ed-order.json
python3 tests/host_languages.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --case ed/signal-int --record build/tests/ed-signal-int.json
make test-host-languages test-host-profile
make test-harness

# Replay the old driver without changing the checked-out implementation.
git show d175f9f:tests/host_language_helper.py > build/tests/old-ed-helper.py
python3 tests/ed_signal_order_probe.py --helper build/tests/old-ed-helper.py \
  --ed build/host-ed --record build/tests/ed-order-old.json # expected failure

# The repository development image runs as unprivileged cshell (uid 10001).
docker build --target development -t cshell-test:csh-129 .
docker run --init --rm cshell-test:csh-129 \
  sh -c 'make -j4 host-profile build/tests/host_ed_faults && make test-host-languages test-host-profile test-harness'
```
