# CSH-063 host-platform residual qualification

CSH-063 adds 144 controlled Linux ACL cases, each in string/file/stdin modes
(432 assertions). All read/write/execute predicates have independent actual
operations. The new partitions cover file-owner precedence, owning-group access,
matching-group denial without falling back to other, owner/other access outside
the mask, and default ACL creation with modes 0700 and 0777. Setup verifies the
numeric access ACL and ownership before attributing results to a utility.
Expectations follow the [Linux ACL access and creation rules](https://man7.org/linux/man-pages/man5/acl.5.html).
No production shell, utility, or C helper source changed.

## Results

| Scope | Result |
| --- | --- |
| Native macOS 14.8.7 arm64, UID 501, no block supplied | 1162 passes, zero failures/gaps |
| Native with `/dev/disk0`, stat only | 1168 passes, zero failures/gaps |
| Debian sid non-root, private stat-only block node | 1168 passes, zero failures/gaps |
| Debian 13 overlay, controlled equal-ID ACLs | 2281 passes, zero failures/gaps |
| Debian sid overlay, controlled equal-ID ACLs | 2281 passes, zero failures/gaps |
| Strict unequal-ID ACLs, Debian 13 and sid separately | Each: **2077 passes, 204 failures, zero gaps, exit 1** |
| Sid tmpfs, controlled setup | **1183 passes, 1098 setup failures, zero gaps, exit 1** |
| Sid host bind, `fakeowner` mount | **1162 passes, 1110 setup failures, 9 assertion failures, zero gaps, exit 1** |
| Sid focused ASan/UBSan, strict unequal IDs | **2077 passes, 204 predicate failures**, zero gaps or sanitizer diagnostics |
| Native, Debian 13, Debian sid runtime integration | Each: 3905 passes |
| Same three environments, terminal integration | Each: 30 jobs PTY, 32 runtime PTY, one notification and one terminal-fault case pass |
| Same three environments, harness self-tests | Each: 83 passes |

The three runtime/PTY integrations use each selected profile PATH. They preceded
only final residual-description/timeout-record metadata edits; runtime, helper,
fixture and assertion behavior are unchanged. Final host-profile records use the
same source digest on every environment. No native Linux, privileged Darwin,
physical terminal, complete bind/tmpfs profile or hosted CI qualification is claimed.

## Vendor change and strict failures

The baseline uses coreutils **9.7-3**, libc6 **2.41-12+deb13u4** (Debian 13).
The new vendor environment uses coreutils **9.10-1**, libc6 **2.43-6** (Debian sid).
`trixie-acl-diagnosis.json`, `sid-acl-diagnosis.json`, and the instrumented sid
record retain exact test/bracket/libc hashes, linkage/imports and direct probes.
The test/bracket binaries still import `euidaccess`; the
[coreutils 9.10 source](https://github.com/coreutils/coreutils/blob/v9.10/src/test.c)
calls it for permission predicates. On both hosts the private named-user read
probe reports:

| Real/effective UID and GID, empty supplementary groups | euidaccess | faccessat AT_EACCESS | actual open |
| --- | --- | --- | --- |
| 10001 / 10001 | success | success | success |
| 10002 / 10001 | denied | success | success |
| 10001 / 10002 | denied | denied | denied |

Each strict run retains 132 rejected grants and 72 false grants. The original
CSH-062 partitions account for 114 rejected grants. CSH-063 adds 18 rejected
creation-mode-0777 grants and 72 false grants in owning-group/named-group
no-fallback cases. All corresponding actual operations pass, including denial
controls and retained written bytes. Failures are utility predicates, never
setup failures or known-gap allowances. This supports continued utility/libc
vendor ownership; no utility implementation is patched by this ticket.

The instrumented helper and printf fault executable use ASan/UBSan. Unequal-ID
exec discards environment settings, so the helper links `sanitizer-options.c`
(the existing CSH-061 diagnostic defaults) to retain halt-on-error and Linux's
leak-scan exclusion. The direct instrumented probes also have no sanitizer
diagnostics. This is focused helper coverage, not a new full-shell sanitizer run.

## Unsupported filesystems and residual ownership

The tmpfs mount returns `Operation not supported` for ACL setup. All 1098 failed
assertions retain phase `setup`, command/status/diagnostic, original expectation,
source, owner and mount identity. No failed setup is counted as a utility result.
The fixture root is queried directly, independently of the source checkout.

The additional macOS-to-Linux bind mount identifies itself as `fakeowner`, not
an ordinary Linux filesystem. It retains 1098 ACL setup failures plus 12 private
node creation failures (`EPERM`). Nine separate assertions also fail: six
socket-type predicates return false, and three cross-user chmod operations
succeed and change mode despite the authored denial expectation. These are
retained platform-profile failures, not a diagnosis of a shell or standalone
utility bug. No ACL, private-device or complete bind-profile qualification is
claimed. The original success/denial expectations are unchanged.

All 28 stable conditions in `tests/host_capability_limits.py` remain individually
sourced and owned for qualification by [CSH-064 / #127](../../tickets/CSH-064-host-platform-external-prerequisites.md).
Each JSON row retains the actual environment and selected executable identity,
reason and separate implementation owner. Conditional missing root/controlled
fixtures, locale availability and stat-only block witnesses remain distinct:
native/no-block has 30 rows, native/block and sid/non-root have 29, and controlled
root has 30. Privileged Darwin remains an explicit absent environment; local
non-root macOS is not a substitute. Physical hardware, other locales/catalogs,
printf libc/stack/full-format, echo policies/exact thresholds and per-utility
resource/filesystem/interruption contracts remain unqualified.

System queries, actual credentials, private fixture bounds, limitations and
assertion verdicts remain separate fields. No parent utility family is promoted;
CSH-012 stays closed. Fixtures are private and processes are owned. Real accounts,
protected mounts and real disk contents are never modified or used as data.

## Reproduction

Native, from the repository root:

```sh
make -j4 test-host-profile
# Save build/tests/host-profile-results.json before another Make run overwrites it.
make test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
make test-harness
```

Supply a block path only when it exists and is appropriate for stat-only checks.
Omitting it retains a separate limitation. Build either tested vendor scope:

```sh
docker build --pull --build-arg BASE_IMAGE=debian:trixie-slim -t cshell-test:csh-063 .
docker build --pull --build-arg BASE_IMAGE=debian:sid-slim -t cshell-test:csh-063-sid .
docker run -d --init --user 0 --name csh063-sid-validation \
  --tmpfs /fixtures:rw,exec,size=128m,mode=1777 cshell-test:csh-063-sid sleep 7200
docker exec csh063-sid-validation make -j4 test-host-profile \
  HOST_PROFILE_FLAGS=--controlled-identities
```

Inside the disposable container, preserve every independent record:

```sh
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path "/work/build/host-profile/bin:$(getconf PATH)" --strict-gaps --boundaries \
  --printf-faults build/tests/host_printf_faults --controlled-identities \
  --unequal-acl --record /tmp/unequal.json
# Exit 1 is a failed strict profile, not a passing expectation.
# Repeat without --unequal-acl and with --fixture-root /fixtures for tmpfs.
mknod /tmp/csh063-block b 7 255
runuser -u cshell -- python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path "/work/build/host-profile/bin:$(getconf PATH)" --strict-gaps --boundaries \
  --printf-faults build/tests/host_printf_faults --block-device /tmp/csh063-block \
  --record /tmp/nonroot.json
CSH_TEST_PATH="/work/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
make test-harness
```

For the host bind experiment, create `build/csh063-disposable-fixtures` and start
a separate container with
`--mount type=bind,source="$PWD/build/csh063-disposable-fixtures",target=/fixtures`
in place of `--tmpfs`. Run the controlled profile with `--fixture-root /fixtures`.
The recorded mount, not the container image or directory name, identifies the
filesystem. Only this new disposable directory is exposed to the container.

For focused sanitizer validation inside the sid container, copy
`sanitizer-options.c` and `probe.py` from this evidence directory into `/work`:

```sh
cc -D_POSIX_C_SOURCE=200809L -Iinclude -std=c99 -Wall -Wextra -Wpedantic -Wshadow \
  -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer \
  tests/host_utility_helper.c sanitizer-options.c -o build/tests/host_utility_helper_sanitized
cc -D_POSIX_C_SOURCE=200809L -Iinclude -std=c99 -Wall -Wextra -Wpedantic -Wshadow \
  -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer \
  tests/host_printf_faults.c -o build/tests/host_printf_faults_sanitized
```

Repeat the strict command with the instrumented helper, instrumented
`--printf-faults` and `--sanitizer`; save to a different record. Run
`python3 probe.py build/tests/host_utility_helper_sanitized` for direct diagnosis.
Export results before removing only task-owned containers and the empty private
bind directory. No volume or device contents are read.

## Artifact identity

`source_identity` in each qualification JSON hashes Makefile, Dockerfile, src,
include, tests and tools (excluding Python caches). `*-identity.json` records
compiler/OS/Python identities and normal flags. The source base is `66f8900` plus
this working tree; evidence and ticket documentation are outside the digest.
The final source SHA-256 is
`b7f93888592686e2a92ee94462588b8b497d02c4032da52df4dff1075eda3832`.
`containers.json` records image/container/mount identities. Containers started
from the recorded images and received the final Python harness, profile README
and Dockerfile before final profile runs. A fresh final Docker build separately
verifies that the Dockerfile includes the complete source inventory.

Compressed records retain complete authored cases, invocation environments,
actual bytes/status/files, source hashes, executable hashes, package versions,
limits and residual rows. Normal, strict and unsupported runs are separate;
failed or aborted development runs are not used as qualification evidence.
`artifacts.json` hashes retained artifacts; `audit.py` validates source identity,
residual provenance, verdict totals and failure separation.
