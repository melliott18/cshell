# CSH-056 validation artifacts

The [condition map](../../host-contract-profile.md) and
[provisioning instructions](../../../tools/host-profile/README.md) define the
bounded profile. Final source is `8b4cfc4` (full revision in native identities).
All four final identities have source SHA-256
`1fd583be34dfd0f25acc2cf118b2e6d3de1223f5e4681d665346d0201808826a`,
covering Makefile, Dockerfile, src, include, tests and tools, excluding Python
caches. Later commits contain evidence/documentation only. Shell runtime source
is unchanged from baseline `3d1000b`.

## Results

| Environment / command | Outcome |
| --- | --- |
| Native macOS 14.8.7 arm64, `make -j4 test test-pty` | Status 0; 3,045 runtime cases, 30 runtime PTY and 15 job PTY cases pass; module/fault suites pass. Stock host retains 784 pass / 12 timestamp gaps. |
| Native, `make test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'` | 919 pass, zero failures/gaps; strict-gap mode. |
| Native, `CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty` | Status 0; 3,045 runtime, 30 runtime PTY, 15 job PTY cases pass. |
| Native, `make test-harness` | 70 self-tests pass. |
| Debian 12 Docker arm64, final profile with stat-only block node | 919 pass, zero failures/gaps; strict-gap mode. |
| Docker, `make -j4 test test-pty` then profile PATH `make test-runtime test-pty` | Both status 0; each has 3,045 runtime, 30 runtime PTY, 15 job PTY passes. Module/fault suites pass. Stock host has 787 pass / 9 gaps after ed provisioning. |
| Docker, `make test-harness` | 70 self-tests pass. |
| Native ASan/UBSan, final focused host profile | 919 pass, zero failures/gaps or sanitizer diagnostics. |
| Docker ASan/UBSan, final focused host profile | 919 pass, zero failures/gaps or sanitizer diagnostics. Linux leak scanning is explicitly disabled by the existing runner policy. |

The native compiler is Apple clang 15; Docker uses GCC 12.2 / glibc 2.36.
The native GNU test/bracket package is Homebrew coreutils 9.3 (x86_64, run through
the host's translation support); Linux coreutils is 9.1. Linux selects BusyBox
1.35.0 kill and ed 1.19. Each actual executable path, resolved path and SHA-256
is in its result inventory, alongside Linux package ownership/version output.
The standalone printf source version and both adapters are checked in, with
normal/sanitized executable hashes in their respective inventories.

No native Linux run is claimed here; Linux evidence is the named container.
Hosted native Ubuntu/macOS and Docker qualification are configured in CI.

## Reproduction

Normal native qualification:

```sh
make -j4 test test-pty
make test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
make test-harness
```

`/dev/disk0` is a stat-only witness and is never opened. Do not supply that
argument on a host without the device node. Omission emits an explicit
capability limitation, not a pass. Mode-bit denial runs as native UID 501 /
Docker UID 10001; result files record effective UID/GID and supplementary groups.

Docker's dedicated capability run creates only a disposable block special file
inside the container, without mounting or opening a device. Qualification and
all subsequent suites run as the unprivileged image user:

```sh
docker build -t cshell-test:csh-056-final .
docker run --rm --init --user 0 cshell-test:csh-056-final sh -c '
  mknod /tmp/csh056-block b 7 255 &&
  exec runuser -u cshell -- sh -c '\''
    make -j4 test-host-profile HOST_PROFILE_FLAGS="--block-device /tmp/csh056-block" &&
    make -j4 test test-pty &&
    CSH_TEST_PATH="/work/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty &&
    make test-harness'\'''
```

Final Docker sanitizer qualification uses the same block-node/runuser setup,
then `make clean` and `make -j4 test-host-profile` with the above
`HOST_PROFILE_FLAGS`, CFLAGS
`-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer`
and LDFLAGS `-fsanitize=address,undefined`.

Native sanitizer binaries are built separately under `build/sanitized` to keep
the ordinary executable available: compile `src/*.c` with the same CFLAGS,
`-D_POSIX_C_SOURCE=200809L -Iinclude`, and sanitizer linking; compile
`tests/host_utility_helper.c` and `tools/host-profile/printf.c` with sanitizer
flags. Provision `build/sanitized/profile/bin`, point its printf symlink at
`build/sanitized/printf`, then run:

```sh
MallocNanoZone=0 python3 tests/host_utilities.py build/sanitized/cshell \
  build/sanitized/helper --path "$PWD/build/sanitized/profile/bin:$(getconf PATH)" \
  --strict-gaps --boundaries --block-device /dev/disk0 --sanitizer \
  --record build/sanitized/results-final.json
```

## Record interpretation

Compressed JSON files contain every script, mode, expected alternative,
actual byte stream, status, environment and filesystem assertion. The records
also preserve French-locale availability, effective identities, queried host
limits, and any capability limitations. The five-second/output/child-resource
bounds remain unchanged. `identity.py` reproduces compiler, platform, libc,
flags, source fingerprint and binary identity; mount Dockerfile for container
identity collection because the image does not otherwise copy its recipe.

`investigation-*` logs intentionally retain failed development observations:
Apple echo's environment policy, stock macOS printf's lost write failure, and
an initial profile that unnecessarily shadowed pwd. The final assertions follow
the documented host policy, the standalone printf checks writes, and the final
profile symlinks only replacements. All affected final qualification/runtime
runs pass; these investigation logs are not final source evidence.

Stock hosts still fail their original strict reproducer. This is expected and
is not converted to a pass. The qualified profile resolves those five gaps;
[CSH-057](../../tickets/CSH-057-host-boundary-capabilities.md) retains each
remaining capability/limit. No broad utility family or CSH-012 compliance gate
is promoted.
