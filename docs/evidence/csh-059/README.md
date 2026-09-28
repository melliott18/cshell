# CSH-059 host capability evidence

The [condition map](../../host-contract-profile.md) and
[profile instructions](../../../tools/host-profile/README.md) define this bounded
qualification. All four identity files have source SHA-256
`160a9a2ac001c9a51da53027d2d04dcfaa4569edf0cc36c4eb63a7cadcbc2251`.
The source revision field identifies the base `a26053c` plus the CSH-059 working
tree; the digest identifies tested Makefile, Dockerfile, src, include, tests and
tools contents, excluding Python caches. Subsequent changes are evidence/docs
outside that digest. No cshell runtime sources changed.

## Results

| Run | Result |
| --- | --- |
| macOS 14.8.7 arm64, strict profile with `/dev/disk0` | 1015 passes, zero failures/gaps |
| Debian 12 Docker arm64, UID 10001, disposable block node | 1015 passes, zero failures/gaps |
| Native ASan/UBSan profile, shell/helper/printf instrumented | 1015 passes, zero failures/gaps or sanitizer diagnostics |
| Docker ASan/UBSan profile, shell/helper/printf instrumented | 1015 passes, zero failures/gaps or sanitizer diagnostics; existing Linux leak-scan exclusion retained |
| Native and Docker profile PATH runtime/PTY reruns | Each: 3113 runtime, 17 job PTY, 1 prompt PTY and 30 runtime PTY passes |
| Native and Docker `make test-harness` | Each: 73 self-tests pass |
| Native stock host | 784 passes, 12 existing timestamp gaps, zero new failures |
| Docker stock host | 787 passes, 9 existing printf/kill gaps, zero new failures |

There are 32 new ordinary cases, each run in string/file/stdin modes (96 new
assertions). Each dedicated profile run retains 27 residual capability
limitations with source, environment, selected executable and next owner
[CSH-060](../../tickets/CSH-060-extended-host-environments.md). Zero assertion
gaps does not make those limitations passes or certify a whole utility page.
The CSH-012 gate remains closed.

The actual native compiler is Apple clang 15; Docker uses GCC 12.2 and glibc
2.36. Result inventories record every selected path, resolved path and binary
SHA-256, and Docker package ownership/versions. The native GNU test/bracket
selection remains Homebrew coreutils 9.3; Docker uses coreutils 9.1, BusyBox
1.35.0 and ed 1.19. Native real/effective UID is 501, Docker is 10001. Both
supply French numeric/messages and en_US.UTF-8. Block nodes are checked using
stat only and never opened. No native Linux or hosted CI result is claimed.

## Limits observed

| Query | Native | Docker |
| --- | ---: | ---: |
| Parent ARG_MAX | 1048576 | 2097152 |
| Parent OPEN_MAX | 1048575 | 1024 |
| Parent LINE_MAX | 2048 | 2048 |
| Fixture filesystem NAME_MAX | 255 | 255 |
| Fixture filesystem PATH_MAX | 1024 | 4096 |
| Fixture filesystem PIPE_BUF | 512 | 4096 |

Both child probes observe soft and hard limits of zero core bytes, six CPU
seconds, 1048576 file bytes and 64 open descriptors. Child OPEN_MAX is 64;
ARG_MAX matches its parent. The outer harness separately enforces five seconds
wall time and 65536 combined output bytes. JSON records the ephemeral query
path on the temporary-fixture filesystem, not the repository filesystem.
These values are system ceilings/harness protections, not utility maxima.
Finite sizes in individual cases remain successful witnesses only. The local
printf `%b` adapter separately rejects literal width/precision above `INT_MAX`.

## printf investigation

`printf-investigation.json` compares the unmodified base vendor/adapter compiled
under `build/upstream-printf` with the corrected profile. Before CSH-059,
`printf '[%5.3b]' 'a\000bZ'` emitted `[    a]` with success. Its `%b` branch
computed the decoded length, then discarded that length by using libc `%s`.
After the local patch the expected bytes are `[  a`, NUL, `b]`. Plain `%b` and
`\c` likewise preserve bytes past NUL. The source retains its BSD license and
pinned provenance; the local modification is declared in the profile README.

All-byte format octals and `%b`, binary precision/padding, numbered recycling,
`\c`, UTF-8 byte precision, finite formats/conversion counts/allocations and the
upstream star-width extension are checked. This investigation does not qualify
every format combination, malformed extension, locale or allocation failure.
No new known-gap signature masks a failed binary regression.

## Reproduction

Normal native checks:

```sh
make -j4 test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty test-harness
make test-host-utilities
```

Omit the block-node option where no suitable node exists; omission is recorded
as its own capability limitation. Ordinary root/absent-locale limitations are
also distinct. No evidence is inferred from a missing witness.

Docker checks (the image provides unprivileged user `cshell`):

```sh
docker build -t cshell-test:csh-059 .
docker run --rm --init --user 0 cshell-test:csh-059 sh -c '
  mknod /tmp/csh059-block b 7 255 &&
  exec runuser -u cshell -- sh -c '\''
    make -j4 test-host-profile HOST_PROFILE_FLAGS="--block-device /tmp/csh059-block" &&
    CSH_TEST_PATH="/work/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty test-harness &&
    make test-host-utilities'\'''
```

For Docker sanitizers use the same disposable-node/runuser setup, `make clean`,
then `make -j4 test-host-profile` with the same HOST_PROFILE_FLAGS and:

```sh
CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'
LDFLAGS='-fsanitize=address,undefined'
```

Native sanitizer binaries were built separately to preserve the ordinary
profile. Compile `src/*.c` into `build/sanitized/cshell` with the same flags,
`-D_POSIX_C_SOURCE=200809L -Iinclude`; compile `tests/host_utility_helper.c` into
`build/sanitized/helper` and `tools/host-profile/printf.c` into
`build/sanitized/printf`. Provision `build/sanitized/profile/bin`, replace only
its printf symlink with the sanitizer executable, then run:

```sh
MallocNanoZone=0 python3 tests/host_utilities.py build/sanitized/cshell \
  build/sanitized/helper --path "$PWD/build/sanitized/profile/bin:$(getconf PATH)" \
  --strict-gaps --boundaries --block-device /dev/disk0 --sanitizer \
  --record build/sanitized/results.json
```

## Artifact interpretation

Compressed JSON records contain exact scripts, expectations, outputs/statuses,
fixture files, identities, capabilities, limitations and queries. Compressed logs
retain command output; `artifacts.json` hashes the retained machine records.
The shared [identity collector](../csh-056/identity.py) reproduces source and
compiler records. Supply `EVIDENCE_REVISION` in Docker because its image has no
git executable; mount the Dockerfile for the source digest.

The first Docker log ends in an **evidence collector** error (git absent), after
all qualification/integration/harness/stock tests passed. The subsequent
Docker sanitizer log includes the rebuilt ordinary profile/identity followed
by passing sanitizer qualification; all final identity JSON files are valid
and have the same source digest. No test failure was relaxed or skipped.
