# CSH-064 external host prerequisites

CSH-064 supplies a **new disposable Linux user namespace**, keeping root mapped
to root while mapping inner IDs 1..65535 to outer IDs 20001..85535. Fixture
UID/GIDs 10001..10005 therefore refer to outer IDs 30001..30005. The namespace
allows setgroups. This uses only private files and process credentials; it does
not create or modify real accounts. No additional ACL filesystem, privileged
Darwin environment or physical terminal was supplied.

The second new capability is a focused independent filesystem probe for the
previously supplied `fakeowner` bind profile. The existing overlay is its control.
The [prerequisite inventory](prerequisites.json) records these capabilities and
a concrete requirement for every residual before further qualification work.

No shell, utility or helper C changed. The Python harness records user/mount
namespace links, UID/GID maps and setgroups policy; validates numeric metadata
for **all** controlled ACL fixtures; and rejects malformed/duplicate metadata
as setup failures. Exact source/executable hashes, independent actual operations,
strict grant/denial expectations and separate failure phases are retained.

## Results

| Scope | Result |
| --- | --- |
| Native macOS 14.8.7 arm64, UID 501, no block supplied | 1162 passes, zero failures/gaps |
| Debian sid overlay, ordinary controlled IDs | 2281 passes, zero failures/gaps |
| Same vendor, strict unequal-ID profile | **2077 passes, 204 predicate failures, exit 1** |
| New mapped namespace, controlled IDs | **2269 passes, 12 setup failures, exit 1** |
| New mapped namespace, strict unequal IDs | **2065 passes, 204 predicate + 12 setup failures, exit 1** |
| Supplied tmpfs | **1183 passes, 1098 ACL setup failures, exit 1** |
| Supplied fakeowner bind | **1162 passes, 1110 setup + 9 assertion failures, exit 1** |
| Focused overlay probe | 8 passes |
| Focused fakeowner probe | **3 passes, 5 failures, exit 1** |
| Native, ordinary Linux, mapped namespace runtime integration | Each: 3905 passes |
| Same three scopes, terminal integration | Each: 30 jobs PTY, 32 runtime PTY, notification and terminal-fault checks pass |
| Same three scopes, harness self-tests | Each: 86 passes |

All qualification records have zero gap allowances. The mapped namespace is
**not a passing complete host profile**: all twelve private character/block
`mknod` assertions fail setup with EPERM. Its ACL assertions and independent
read/write/execute controls pass with equal IDs. Ordinary Linux, namespace and
macOS runtime/PTY checks use their selected profile PATH. No sanitizer run is
claimed or required for this Python/documentation-only change.

The normal profile was rerun after an initial development invocation overlapped
a binary rebuild. Only the completed final invocation and its exit status are
retained. No aborted run or stale JSON is qualification evidence.

## Strict vendor failures

Coreutils 9.10-1 and libc6 2.43-6, including exact test, bracket and libc hashes,
are unchanged from CSH-063. This is a **credential-namespace recheck**, not a new
vendor release claim. [Direct probes and imports](acl-diagnosis.json) retain the
same distinction: with real UID 10002 and effective UID 10001, euidaccess rejects
the named-user read grant while faccessat AT_EACCESS and actual open succeed.
Equal-ID controls succeed, and the reverse identity denies access.

Both ordinary and mapped strict profiles retain **132 rejected grants and 72
false grants**. The 204 predicate failures are distinct from namespace device
setup failures; corresponding actual operations pass. No failure is changed to
an allowance. Utility/libc vendors retain implementation ownership.

## Independent fakeowner diagnosis

[Overlay control](overlay-probe.json) and [fakeowner experiment](bind-probe.json)
use `tests/host_platform_probe.py`, the same selected test/bracket/chmod binaries
and the same Python executable. Each records hashes, actual mount, source and
measured child credentials/capabilities.

On fakeowner, binding an AF_UNIX socket succeeds, but Python stat reports
**EINVAL**. Test and bracket each return status 1 for `-S`. Listening, connecting
and transferring one byte succeeds. This identifies a metadata failure below
the utility predicate; it does not establish every socket operation or explain
the filesystem implementation's internal cause.

For chmod, both fixtures begin as owner 10001, group 10002, mode 0400. Owner
10001 succeeds and changes mode to 0600 on both filesystems. Non-owner 10002,
with matching real/effective IDs, empty supplementary groups and zero effective
capabilities, is denied on overlay by both external chmod and direct
`os.chmod`. On fakeowner, **both succeed and change mode to 0600**. Parent and
child metadata agree. This reproduces the permission failure without cshell or
the external chmod implementation being necessary for it.

The full bind qualification independently retains its original six socket
predicate failures, three cross-user chmod failures, 1098 ACL setup failures and
twelve private-node setup failures. Tmpfs retains its own 1098 unsupported ACL
setup failures. No failing filesystem is qualified by its passing cases.

## Residuals and ownership

All thirty stable conditions in `tests/host_capability_limits.py` are individually
retained, including separate fakeowner socket and chmod rows. Every qualification
JSON includes actual environment and selected executable identities, source,
reason, CSH-064 as qualification owner and selected utility/libc/platform vendors
as implementation owners. Each run has 32 limitation rows: two conditional
missing-capability rows remain separate from the stable conditions.

The [prerequisite inventory](prerequisites.json) names the capability required
for each future recheck. No new vendor, privileged Darwin, physical hardware or
additional ACL-capable filesystem is claimed. Locale/catalog, printf libc/stack/
format, echo policy/threshold, per-utility filesystem/resource/interruption and
other unqualified conditions remain explicit. Missing root/controlled fixtures,
locales and explicit stat-only block witnesses are not inferred from unrelated
passing cases. Namespace private-node failures remain failures, not limitations.

Queries, measured credentials, fixture bounds and unmet requirements occupy
separate fields. No parent utility family is promoted and CSH-012 stays closed.

## Reproduction

Native:

```sh
make -j4 test-host-profile
# Save build/tests/host-profile-results.json before another host-profile run.
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty test-harness
```

The retained container starts from the existing CSH-063 sid image, whose image
ID and exact mount configuration are in [container.json](container.json).
Current Makefile, Dockerfile, src, include, tests and tools were copied into
`/work` and compiled there. The image has the selected unchanged vendor packages.
A fresh source build is also possible with `docker build --build-arg
BASE_IMAGE=debian:sid-slim -t cshell-test:csh-064 .`; changed vendor identities
require a new qualification record.

Start a disposable root container with a private bind directory and tmpfs:

```sh
mkdir -p build/csh064-bind
docker run -d --init --user 0 --name csh064-validation \
  --mount "type=bind,source=$PWD/build/csh064-bind,target=/bind-fixtures" \
  --tmpfs /tmpfs-fixtures:rw,exec,size=128m,mode=1777 cshell-test:csh-064 sleep 14400
```

No privileged container, added capabilities, protected mount or real disk I/O
is used. Inside the disposable container, build before starting qualification:

```sh
make -j4 cshell host-profile build/tests/host_utility_helper build/tests/host_printf_faults
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path /work/build/host-profile/bin:/bin:/usr/bin --strict-gaps --boundaries \
  --printf-faults build/tests/host_printf_faults --controlled-identities \
  --record /tmp/normal.json
```

Repeat independently with `--unequal-acl`, `--fixture-root /tmpfs-fixtures` and
`--fixture-root /bind-fixtures`, saving each to a different record. Never accept
a record from a prior invocation when the current invocation aborts. For the
new namespace, prefix the normal and strict commands separately with:

```sh
unshare --user --map-users=0:0:1 --map-users=1:20001:65535 \
  --map-groups=0:0:1 --map-groups=1:20001:65535 --setgroups=allow
```

Use the same prefix before `sh -c 'CSH_TEST_PATH=/work/build/host-profile/bin:/bin:/usr/bin
make test-runtime test-pty test-harness'` for namespace integration. Run that
integration without the prefix for ordinary Linux. Full failed profiles return
1; the evidence audit verifies retained failure counts without changing them.

Run the focused probe independently on `/tmp` and `/bind-fixtures`:

```sh
python3 tests/host_platform_probe.py --fixture-root /bind-fixtures \
  --path /work/build/host-profile/bin:/bin:/usr/bin --record /tmp/bind-probe.json
```

Run `docs/evidence/csh-063/probe.py` from `/work` for direct ACL/libc diagnosis.
Its unchanged script and helper are identified in prior evidence and the current
source inventory. Run `identity.py` from the repository root in each environment.
Export records before removing only this task's container and empty bind directory.

## Artifact identity and audit

The source base is `07ee1cb` plus this worktree. Every qualification and focused
probe has final source SHA-256
`fe524b6a90519e622a00f21f792e201bdaa3f7de7ed9323200479a9ff2be1319`.
The inventory includes build files, src, include, tests and tools; evidence/docs
are outside it. Identity JSON records compiler, Python, OS and build flags.
Compressed records preserve every case, expectation, actual bytes/status/files,
source/executable identity, resource query, namespace/mount and limitation.
Integration logs and command exit statuses are retained separately.

`artifacts.json` hashes the retained artifacts. From the repository root:

```sh
python3 docs/evidence/csh-064/audit.py
```

The audit verifies source identity, residual provenance, exact failure-phase
counts, rejected/false grants, namespace maps and the independent bind diagnosis.
It does not turn known failures into passing profiles.
