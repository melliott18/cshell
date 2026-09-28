# CSH-060 controlled host environment evidence

The [condition map](../../host-contract-profile.md#csh-060-controlled-environments)
and [profile instructions](../../../tools/host-profile/README.md) define these
bounded claims. Remaining conditions belong to
[CSH-061 / #110](../../tickets/CSH-061-host-environment-residuals.md). Utility
families remain open and the CSH-012 gate remains closed.

## Results

| Run | Result |
| --- | --- |
| macOS 14.8.7 arm64, UID 501, supplied `/dev/disk0` (stat only) | 1168 passes; no failures/gaps |
| Debian 12 Docker arm64, UID 10001, disposable block node | 1168 passes; no failures/gaps |
| Docker root, controlled equal-ID ACLs, unequal owner/group IDs, private nodes | 1201 passes; no failures/gaps |
| Docker root, explicit BusyBox fancy echo alternative | 1144 passes; no failures/gaps |
| Native focused ASan/UBSan helper and printf allocation executable | 1168 passes; no sanitizer diagnostics/failures/gaps |
| Docker focused ASan/UBSan helper, allocation executable and profile printf, controlled root | 1201 passes; no sanitizer diagnostics/failures/gaps |
| Native and Docker profile PATH integration | Each: 3113 runtime cases; 17 job PTY, 1 prompt PTY and 30 runtime PTY cases pass |
| Docker BusyBox profile PATH integration | Same runtime and PTY counts pass |
| Native and Docker harness self-tests | 74 pass on each host |
| Separate strict unequal-ID ACL reproducer, Docker root | **1195 passes, 6 failures, zero gaps; exit 1** |

There are 51 new ordinary cases (153 invocation assertions) where both added
locales exist. The controlled root scope adds 19 cases (57 assertions), but
omits ordinary non-root denial and the separately supplied block node; both
omissions remain explicit limitations. Native/non-root Docker retain 28
limitations, controlled root retains 29, and ordinary root BusyBox retains 30.
Each includes the 27 stable residual rows, source, actual environment, selected
executable identity, reason and next owner. No limitation is a pass.

Both identity records have source SHA-256
`397d9e274301f2c4263874e150453ddff46891a0756f1180b782fbf570b3016c`.
The revision is base `b1b6b15` plus the CSH-060 working tree; the digest covers
Makefile, Dockerfile, src, include, tests and tools (including the profile README),
excluding Python caches. Subsequent evidence/ticket documentation is outside
that digest. Compiler identities are Apple clang 15 and Debian GCC 12.2;
Docker records coreutils 9.1, BusyBox 1.35.0 and glibc 2.36. Every qualification
JSON contains actual selected executable, helper and allocation-executable hashes.
Shell runtime and production printf sources are unchanged.

The integration log includes an earlier passing profile run before six ACL
read controls were added and rm file assertions were made independent of test.
The final qualification JSON and `docker-final.log.gz` supersede those profile
counts. Runtime/PTY binaries and behavior were unchanged. Native's final harness
log supersedes the earlier 73-test run with the new 74th regression test.
No native Linux or hosted CI execution is claimed; CI jobs are configured.

## Unequal-ID ACL finding

A root-owned mode-000 private file receives the numeric ACL
`user:10001:r--,mask::r--`. With real UID/GID 10002, effective UID/GID 10001 and
no supplementary groups, an actual `cat` read returns the authored `private\n`
bytes, but GNU test and bracket `-r` each return 1. The grant expectation remains
status 0. The six failures are the two predicates in string/file/stdin modes.
Reverse-identity denial and actual read denial pass. Equal-ID ACL grant/denial,
and unequal owner/group mode-bit predicates, also pass.

`docker-unequal-acl.json.gz` retains each exact invocation, numeric ACL, stat
metadata, actual credentials, expectation and result. `--unequal-acl` is a
strict reproducer, not a known-gap allowance; the harness regression ensures
these rejected grants stay failures. CSH-061 owns this known unmet combined
condition and the broader remaining ACL requirements. A passing narrower
profile must not be interpreted as qualifying unequal-ID ACLs.

## Queries, limits and independent expectations

German numeric formatting is authored as `1,50`. GB18030 data is constructed
with Python's codec (one two-byte and one four-byte character); printf preserves
the bytes and sed replaces two characters with `xx`. The 27 format expectations
are authored literals. Test-only allocation interposition checks both local
strdup/realloc ENOMEM paths and successful controls without changing production
source or injecting errors into libc.

Exec probes construct single and aggregate oversized operand vectors with only
`LC_ALL=C` (9 bytes including NUL) in the environment. Each requires E2BIG before
the utility starts and records its actual child ARG_MAX, operand count and bytes.
The operand-string byte total excludes argv[0] and pointer-table overhead. No
exact last-successful threshold or utility capacity is claimed. Queries are
1048576 ARG_MAX natively and 2097152 in Docker; allocation is independently
bounded by rejecting queries above 16 MiB. The record is private fixture data.

Cat/sed file-limit cases lower only the child RLIMIT_FSIZE to 1024 bytes and
ignore SIGXFSZ, require nonzero diagnostic status and exactly 1024 retained
bytes. This is a controlled resource error, not disk exhaustion. rm requires
status 0, a prompt, and independently read file presence/absence for explicit
no/yes input. All ordinary parent/child/filesystem queries and harness bounds
remain recorded separately. Devices are stat'ed, never opened; all created
files/nodes and signalled children belong to the fixture.

## Reproduction

Native normal profile, integrations and harness:

```sh
make -j4 test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
make test-harness
```

Omit the block option if no suitable node exists; the missing witness is retained
as a separate limitation. Native sanitizer checks compiled only the changed
helper and test-only allocation executable with
`-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer`:

```sh
mkdir -p build/sanitized
cc -D_POSIX_C_SOURCE=200809L -Iinclude -std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer tests/host_utility_helper.c -o build/sanitized/helper
cc -D_POSIX_C_SOURCE=200809L -Iinclude -std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer tests/host_printf_faults.c -o build/sanitized/printf-faults
MallocNanoZone=0 python3 tests/host_utilities.py ./cshell build/sanitized/helper \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" --strict-gaps --boundaries \
  --block-device /dev/disk0 --printf-faults build/sanitized/printf-faults \
  --sanitizer --record build/sanitized/results.json
```

Docker supplies acl, German, French and GB18030 locales. Build and run both
identity scopes (non-root first so generated files remain writable):

```sh
docker build -t cshell-test:csh-060 .
docker run --rm --init --user 0 cshell-test:csh-060 sh -c '
  mknod /tmp/csh060-block b 7 255 &&
  runuser -u cshell -- make -j4 test-host-profile HOST_PROFILE_FLAGS="--block-device /tmp/csh060-block" &&
  make test-host-profile HOST_PROFILE_FLAGS="--controlled-identities"'
```

Add `--unequal-acl` to the controlled flags for the strict known-failure
reproducer. Save `build/tests/host-profile-results.json` even when make exits
nonzero; each subsequent profile run replaces that file.

For the alternate policy, after `make host-profile`, run inside Docker:

```sh
mkdir -p build/busybox-echo
ln -s /bin/busybox build/busybox-echo/echo
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path "/work/build/busybox-echo:/work/build/host-profile/bin:$(getconf PATH)" \
  --strict-gaps --boundaries --printf-faults build/tests/host_printf_faults \
  --echo-policy busybox-fancy --record build/tests/host-busybox-results.json
CSH_TEST_PATH="/work/build/busybox-echo:/work/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
```

The GNU profile integration uses the same command without the BusyBox prefix.
Run `make test-harness` on both hosts. Focused Docker sanitizers start a fresh
image container, retaining its ordinary shell and instrumenting the newly built
helper/allocation/profile printf executables:

```sh
docker run --rm --init --user 0 cshell-test:csh-060 make -j4 test-host-profile \
  HOST_PROFILE_FLAGS=--controlled-identities \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The runner sets halt-on-error ASan/UBSan in each case, retaining the existing
Linux leak-scan exclusion. Compressed records/logs are hashed in `artifacts.json`.
The [shared identity collector](../csh-056/identity.py) records source/compiler
identity; in Docker mount its script and Dockerfile and supply EVIDENCE_REVISION
because the image excludes Git. No production vendor source patch was needed.
