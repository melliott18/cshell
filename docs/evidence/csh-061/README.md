# CSH-061 host environment residual evidence

CSH-061 adds 108 controlled Linux cases (324 string/file/stdin assertions).
Each access/default ACL, named-user/supplementary-group, read/write/execute
combination has grant, unrelated-identity denial and mask denial cases. Each
checks test, bracket and an independent actual operation. Writes assert exact
retained bytes; execution uses a private copy of the helper. Parent/default and
child/access numeric ACLs, stat metadata and actual credentials are retained.
Defaults are inherited at creation without a subsequent child chmod.

## Results

| Scope | Result |
| --- | --- |
| Native macOS 14.8.7 arm64, UID 501, `/dev/disk0` stat only | 1168 passes, no failures/gaps |
| Debian 12 Docker arm64, UID 10001, disposable block node | 1168 passes, no failures/gaps |
| Docker root, controlled identities and extended ACL matrix | 1525 passes, no failures/gaps |
| Docker root, explicit BusyBox fancy echo | 1144 passes, no failures/gaps |
| Native focused ASan/UBSan helper and printf allocation executable | 1168 passes, no failures/gaps/diagnostics |
| Docker focused ASan/UBSan helper and printf allocation executable, controlled identities | 1525 passes, no failures/gaps/diagnostics |
| Native, Docker GNU and Docker BusyBox profile PATH integration | Each: 3341 runtime, 30 jobs PTY, 32 runtime PTY, one job-notification and one terminal-fault case pass |
| Native and Docker harness self-tests | 75 pass each |
| Separate strict unequal-ID ACL reproducer | **1519 passes, 6 failures, zero gaps; runner exit 1, make exit 2** |

The unchanged shell runtime and production printf are not newly instrumented;
the changed C helper and existing allocation executable are. The additional
libc diagnostic branch is also run under ASan/UBSan. Native Linux and hosted CI
execution are not claimed. The temporary Docker container uses only private
files/nodes and owned children. No real block-device contents are opened.

## Unequal-ID investigation

[`acl-diagnosis.json`](acl-diagnosis.json) records the actual test binary's dynamic
imports/linkage, coreutils `9.1-1`, libc6 `2.36-9+deb12u14`, and the SHA-256 of
`/lib/aarch64-linux-gnu/libc.so.6`. Full qualification records retain selected
test/bracket executable hashes, package inventory, libc version and helper hash.

For the same mode-000, root-owned, named-user read ACL as CSH-060:

| Real/effective UID and GID; supplementary groups empty | euidaccess(R_OK) | faccessat(AT_EACCESS, R_OK) | actual open(O_RDONLY) |
| --- | --- | --- | --- |
| 10001 / 10001 | 0 | 0 | success |
| 10002 / 10001 | -1 | 0 | success |
| 10001 / 10002 | -1 | -1 | denied |

The diagnostic is an observation, not a passing ACL-grant requirement. The
strict profile still expects **status 0** for both utility grants; its six
failures remain failures. Actual cat reads also require the authored private
bytes, independently of all permission predicates.

[Coreutils 9.1 test](https://github.com/coreutils/coreutils/blob/v9.1/src/test.c)
calls `euidaccess` for these predicates. The recorded binary imports that libc
symbol. [glibc 2.36's implementation](https://github.com/bminor/glibc/blob/glibc-2.36/sysdeps/posix/euidaccess.c)
delegates equal IDs to access, but uses stat mode bits for unequal IDs and
explicitly lacks ACL support on that path. Together, source, binary linkage and
the direct probe explain the observed failure. No vendor source or selected
utility was replaced to hide it. Utility/libc vendors retain implementation
ownership; [CSH-062 / #116](../../tickets/CSH-062-host-contract-controlled-platforms.md)
owns requalification with changed binaries and further controlled environments.

## Residuals and limits

Every qualification record retains the 27 existing sourced residual conditions
plus a separate Darwin ACL row. Ordinary native/non-root Docker runs retain 29
limitations, controlled root retains 30, and ordinary root BusyBox retains 31.
Missing controlled root, missing locales, effective-root mode-bit denial and
absent supplied block nodes remain distinct conditional rows. All carry source,
actual environment, reason and next owner; utility rows also carry executable
identity. No limitation is counted as a pass or known-gap allowance.

Darwin lacks a supplied privileged identity fixture in this session. Its
ordered allow/deny entries and inheritance remain explicitly unqualified.
Linux tests cover one named user or supplementary group, equal IDs, and the
container filesystem. Unequal-ID supplementary groups and other filesystems
remain unqualified. All other individually sourced locale/catalog, printf
libc/stack/format, echo policy/exact exec threshold, utility filesystem/resource/
interruption and physical-terminal conditions remain owned by CSH-062.
System queries, actual credentials, fixture bounds and unmet requirements stay
separate. Parent utility families remain open and the CSH-012 gate stays closed.

## Reproduction

Use [CSH-060's commands](../csh-060/README.md), substituting image tag
`cshell-test:csh-061` and disposable node name `/tmp/csh061-block`. Commands run:

```sh
make -j4 test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
make test-harness
docker build -t cshell-test:csh-061 .
```

Inside the disposable root Docker container, run non-root first:

```sh
mknod /tmp/csh061-block b 7 255
runuser -u cshell -- make -j4 test-host-profile HOST_PROFILE_FLAGS='--block-device /tmp/csh061-block'
make test-host-profile HOST_PROFILE_FLAGS=--controlled-identities
make test-host-profile HOST_PROFILE_FLAGS='--controlled-identities --unequal-acl'
```

Save `build/tests/host-profile-results.json` after **each** run, including the
strict failing one. BusyBox and profile integration use the CSH-060 commands.
Native sanitizers use its focused compilation/run commands. Docker sanitizers
use the same two focused compile commands, then:

```sh
python3 tests/host_utilities.py ./cshell build/sanitized/helper \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" --strict-gaps --boundaries \
  --controlled-identities --printf-faults build/sanitized/printf-faults \
  --sanitizer --record build/sanitized/results.json
```

Copy [`probe.py`](probe.py) into the container and run from `/work` as root.
Its optional first argument selects an alternate helper. It creates only a
private temporary ACL file and removes it. Unequal-ID exec strips the sanitizer
environment settings, so the initial instrumented diagnostic re-exec encountered
LeakSanitizer's credential/ptrace limitation (retained in
`acl-diagnosis-sanitizer-env-failure.json`, not counted as a pass). Build the
same Linux leak-scan exclusion into this diagnostic only:

```sh
cc -D_POSIX_C_SOURCE=200809L -Iinclude -std=c99 -Wall -Wextra -Wpedantic \
  -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer \
  tests/host_utility_helper.c /tmp/sanitizer-options.c -o build/sanitized/probe-helper
python3 /tmp/probe.py build/sanitized/probe-helper
```

Copy [`sanitizer-options.c`](sanitizer-options.c) to `/tmp` first. All three
credential combinations then complete with no ASan/UBSan diagnostics, recorded
in `acl-diagnosis-sanitizer.json`; ordinary profile instrumentation is unchanged.

Both identity records have source digest
`e854cd09f896458d7b9ff6a645609a2cb9101d21ebc747ce3f3fe00288e4a444`.
The source is base `8ffb99e` plus the CSH-061 working tree. The shared CSH-056
identity collector records compiler, source and executable identities; the
source digest includes Makefile, Dockerfile, src, include, tests and tools,
excluding Python caches. The final source differs from compiled helper source
only by a two-line comment clarification; no executable statements changed.
Subsequent ticket/evidence documentation is outside the digest. Compressed
qualification and log artifacts are hashed in [`artifacts.json`](artifacts.json).
