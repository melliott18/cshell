# CSH-062 supplied host platform evidence

CSH-062 adds 108 controlled ACL cases (324 string/file/stdin assertions), covering
multiple named users, first/second supplementary groups, named-user precedence,
unrelated groups and masks. Each exercises read/write/execute on access and
inherited ACLs. Predicates and actual operations have independent expectations;
writes assert retained bytes and execution uses a private helper copy. Existing
CSH-061 cases remain. No shell runtime or production utility source changed.

## Results

| Scope | Result |
| --- | --- |
| Native macOS 14.8.7 arm64, UID 501, no supplied block node | 1162 passes, zero failures/gaps; missing block remains separate |
| Native with `/dev/disk0`, stat only | 1168 passes, zero failures/gaps |
| Debian 13 arm64 non-root, private stat-only block node | 1168 passes, zero failures/gaps |
| Docker root, overlay, equal-ID ACL combinations | 1849 passes, zero failures/gaps |
| Docker root, disposable ext4 volume, equal-ID combinations | 1849 passes, zero failures/gaps |
| Docker strict unequal-ID scope on overlay and ext4 | Each: **1735 passes, 114 failures, zero gaps; runner exit 1** |
| Docker tmpfs, controlled ACL setup | **1183 passes, 666 setup failures, zero gaps; runner exit 1** |
| Docker BusyBox fancy echo | 1144 passes, zero failures/gaps |
| Native focused ASan/UBSan helper and printf allocation executable | 1168 passes, zero failures/gaps/diagnostics |
| Docker focused ASan/UBSan, equal-ID combinations | 1849 passes, zero failures/gaps/diagnostics |
| Docker focused ASan/UBSan, strict unequal-ID combinations | **1735 passes, 114 grant failures**, zero gaps/sanitizer diagnostics |
| Native, Docker GNU, Docker BusyBox, and ext4-volume profile integration | Each: 3905 runtime, 30 jobs PTY, 32 runtime PTY, one job-notification and one terminal-fault case pass |
| Native and Docker harness self-tests | 80 pass each |

The new `--fixture-root` controls both private fixtures and filesystem queries.
Linux records identify actual mounts: overlay `/tmp`, ext4 `/fixtures` backed by
a newly created Docker volume, and executable tmpfs `/fixtures`. The volume's
backing device is only mount metadata; it is never opened. No real accounts,
protected mounts, unrelated processes or real disk contents are modified.
Native Linux, privileged Darwin, physical hardware and hosted CI are not claimed.

## Updated vendor diagnosis

The updated image uses coreutils **9.7-3**, libc6 **2.41-12+deb13u4** and Debian 13.
[`acl-diagnosis.json`](acl-diagnosis.json) retains exact binary linkage/imports,
helper and libc hashes; qualification records include selected test/bracket
hashes and the full package inventory. The imported symbol remains `euidaccess`.

For the private root-owned named-user read ACL, the direct helper observes:

| Real/effective UID and GID; no supplementary groups | euidaccess | faccessat AT_EACCESS | actual open |
| --- | --- | --- | --- |
| 10001 / 10001 | 0 | 0 | success |
| 10002 / 10001 | -1 | 0 | success |
| 10001 / 10002 | -1 | -1 | denied |

[Coreutils 9.7 test](https://github.com/coreutils/coreutils/blob/v9.7/src/test.c)
still calls euidaccess for permission predicates.
[glibc 2.41 euidaccess](https://github.com/bminor/glibc/blob/glibc-2.41/sysdeps/posix/euidaccess.c)
still uses mode bits on the unequal-ID path and lacks ACL support there.
These sources, the binary import and direct probes support the same diagnosis
as CSH-061. Utility/libc vendors retain implementation ownership.

The 114 failures consist of the six original read grants plus 108 new predicate
grants: three granting credential scenarios, three permissions, two inheritance
states, two utilities and three invocation modes. Actual operations and denial
controls pass. Every rejected grant still expects status 0; there are no known-gap
allowances. Instrumented strict results reproduce the same failures.
Unequal-ID exec strips sanitizer environment settings, so that helper links
[CSH-061's diagnostic defaults](../csh-061/sanitizer-options.c), preserving the
Linux leak-scan exclusion and halt-on-error behavior. All direct instrumented
probes also complete without sanitizer diagnostics.

## Unsupported and retained conditions

This Docker kernel's tmpfs returns `Operation not supported` from setfacl.
The runner now saves each failed setup with phase, command, status, diagnostic,
original success/denial expectation, source and owner. All 666 failures are setup
failures; none is evidence of a utility predicate or operation. Temporary
fixtures are cleaned up. The earlier aborted tmpfs logs are retained as
`tmpfs-initial-*.log.gz`; their stale copied JSON files are excluded from evidence.
No tmpfs ACL or complete tmpfs profile qualification is claimed.

All 28 stable residual rows remain individually sourced and owned by
[CSH-063 / #122](../../tickets/CSH-063-host-platform-residual-qualification.md).
Native/no-block retains 30 limitations; native/block and non-root Docker retain
29; controlled root retains 30; ordinary root BusyBox retains 31. Missing root,
locales, root mode-bit denial and supplied block nodes remain separate conditional
rows, with executable identities. Privileged Darwin remains an explicit absent
environment. Locale/catalog, printf libc/stack/full-format, echo policy/exact
threshold, per-utility resource/filesystem/interruption and physical-terminal
conditions are not promoted by bounded witnesses. Queries, measured credentials,
fixture limits and unmet requirements remain separate. Parent utilities remain
open and CSH-012 stays closed.

## Reproduction

From the repository root, native validation:

```sh
make -j4 test-host-profile
make test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
make test-harness
```

Only supply an existing block node for stat-only checks; omitting it retains the
missing witness. Save the qualification JSON after each run, before the next
Make target replaces it. Focused sanitizer compile/run commands are unchanged
from [CSH-060](../csh-060/README.md).

Build the updated disposable image and container:

```sh
docker build --build-arg BASE_IMAGE=debian:trixie-slim -t cshell-test:csh-062 .
docker run -d --init --user 0 --name csh062-validation \
  --tmpfs /fixtures:rw,exec,size=128m,mode=1777 cshell-test:csh-062 sleep 7200
docker exec csh062-validation sh -c '
  mknod /tmp/csh062-block b 7 255
  runuser -u cshell -- make -j4 test-host-profile HOST_PROFILE_FLAGS="--block-device /tmp/csh062-block"
  make test-host-profile HOST_PROFILE_FLAGS=--controlled-identities'
```

Inside the container, use a separate `--record` for each strict/unsupported run:

```sh
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path "/work/build/host-profile/bin:$(getconf PATH)" --strict-gaps --boundaries \
  --printf-faults build/tests/host_printf_faults --controlled-identities \
  --unequal-acl --record build/tests/unequal.json
# This exits 1; preserve the record and its failures.
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path "/work/build/host-profile/bin:$(getconf PATH)" --strict-gaps --boundaries \
  --printf-faults build/tests/host_printf_faults --controlled-identities \
  --fixture-root /fixtures --record build/tests/tmpfs.json
# This kernel exits 1 with setup failures, not predicate results.
```

For ext4, start another container using a fresh Docker volume instead of tmpfs:

```sh
docker run -d --init --user 0 --name csh062-volume-validation \
  --mount type=volume,source=csh062-disposable-fixtures,target=/fixtures \
  cshell-test:csh-062 sleep 7200
docker exec csh062-volume-validation make -j4 test-host-profile \
  HOST_PROFILE_FLAGS='--controlled-identities --fixture-root /fixtures'
```

Inspect the recorded mount type before making a filesystem claim: a different
Docker installation may use a different backing filesystem. Repeat the strict
command with `--fixture-root /fixtures`. Integration uses
`TMPDIR=/fixtures CSH_TEST_PATH="/work/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty`.
GNU/BusyBox integrations and focused Docker sanitizer compile/run commands are
in [CSH-060](../csh-060/README.md). Link `sanitizer-options.c` into a separate
`unequal-helper` for strict sanitizer runs; use that helper and `--unequal-acl`.
Copy [probe.py](probe.py) into the container and run from `/work`; its optional
argument selects the instrumented helper.

After exporting records, remove only the two task-owned containers and the
newly created volume. Compressed results/logs and identity files are hashed in
[`artifacts.json`](artifacts.json). Source identity includes all tests/tools,
Makefile and Dockerfile; evidence and ticket documentation are outside the digest.

All three source identity records have SHA-256
`01d7b6e58496421f0d714bfc0df73625c4d497fddd212cf76a0a5ea47cced9fe`.
The source is base `faf2e95` plus the CSH-062 working tree. Docker validation
started from image `sha256:74422d54a491ddfb391bbdee50d22ed4367d57dc17c8e255631c0057abcba91c`;
the final Python harness, residual ownership and profile documentation were
copied into the disposable containers before final qualification runs.
The final source digest matches native, overlay and volume runs. Compiler
identities and normal flags are in the identity records; focused sanitizer flags
are `-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer`. Runtime/PTY integrations
preceded the setup-error retention change; their executable and fixture sources
are unchanged. Only host-profile runs use that changed harness.
