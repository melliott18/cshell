# CSH-071 reproduced failure resolutions

These are bounded corrections, not closure of all eight utility contracts.
Earlier records in CSH-064 and both earlier CSH-071 directories are immutable.
The records below identify the successive source/provider snapshots actually run.

| Scope | Result |
| --- | --- |
| Native selected chmod, original-X and traversal | [124 pass](native-chmod.json.gz), including original mode before setting/clearing execute, recursive changes, directory search removal, symlink policy and continued processing after a missing operand. |
| Same selected chmod with ASan/UBSan | [124 pass](native-chmod-asan.json.gz). The adapter is instrumented; system libc is not. |
| Linux non-root selected chmod | [124 pass](linux-chmod.json.gz), using the recorded libbsd package. |
| Linux newgrp selected sessions | [24 pass](linux-newgrp.json.gz): default/named/existing numeric/changed groups and unknown nonnumeric group errors, in direct/string/file/stdin modes. Non-root fallback preserves UID/GID/groups and ignores poisoned SHELL when choosing the shell. |
| Linux newgrp adapter ASan/UBSan | [24 pass](linux-newgrp-asan.json.gz). The vendor backend and spawned shell are not claimed instrumented. |
| Linux controlled permission/profile integration | [1,072 permission assertions](linux-permissions.json.gz) and [2,281 host assertions](linux-profile.json.gz) pass, zero gaps. |
| Original remapped user namespace, ordinary mknod setup | [2,269 pass, 12 setup failures](mapped-qualification.json.gz). All remaining failures are private device creation rejected with EPERM; ACL and credential assertions pass. |
| Same mapping with parent-supplied stat-only device nodes | [2,281 pass](mapped-nodes-qualification.json.gz), and [2,281 pass after the provider changes](mapped-final-qualification.json.gz), zero failures/gaps. |
| Native broader permission profile | [979 pass, 1 failure](native-permissions.json.gz): chgrp named-group string invocation timed out and missed the one-second leader-reap deadline. This is a failed run, not a passing profile. |
| Runtime integration | [Native](native-runtime.log.gz): 3,950 pass. [Linux runtime/PTY](linux-runtime-pty.log.gz): 4,015 summarized assertions pass. |
| Harness/inventory | [Six permission harness tests and 11 inventory tests](harness.log.gz); [19 host evidence tests](host-harness.log.gz) pass. |

The [latest Linux CI job](https://github.com/melliott18/cshell/actions/runs/36664020249/job/109724720134)
is recorded by the [CI snapshot](ci-run.json). Its artifacts independently pass
124 chmod, 24 newgrp, 22 controlled credentials, 16 ordinary ownership and
2,260 strict unequal-ID ACL/profile assertions. The snapshot supplies the exact
job URL and commit; macOS is still queued. `ci-linux-*.json.gz` retains all five
reports. Docker container `cshell-csh071-followup` was removed after exporting
the local records; a scoped container listing then returned no matching entry.

The selected chmod executable uses BSD `setmode`/`getmode` and kernel chmod,
with physical traversal and postorder directory changes. It never replaces the
system executable. The original GNU original-X failure remains a stock-provider
failure. Newgrp remains a non-set-ID dispatch adapter over an inventoried system
backend; known-group authorization and password handling are still delegated.
Unknown numeric IDs and known-group authorization failures are not claimed fixed
by the unknown-name fallback. The broader authentication/session contract stays open.

## Darwin credential measurement

The hosted macOS run completed after the previous evidence snapshot. Its
ordinary scope passed 496 assertions; the controlled scope had
[240 credential-check failures](darwin-account-groups-failure.json.gz).
Every failure reported `credential setup differs from requested IDs` because
the harness compared CPython's account group list with the requested process
groups. No predicate mismatch is inferred from that failed validation.

Modern macOS builds of [Python document that os.getgroups is not affected by
setgroups](https://docs.python.org/3/library/os.html#os.getgroups). The child now
reads the unextended libc getgroups symbol and records account membership
separately. Expected UID/GID and supplementary-group checks are not weakened;
loss of saved-root access is still mandatory. The fix is pushed, but its hosted
Darwin job is queued at this evidence snapshot. Privileged Darwin remains open.

## Reproduction and supplied capabilities

Native commands:

```sh
make host-profile
python3 tests/host_permissions.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --vendor-residuals --case-prefix chmod/ --record build/chmod.json
make test-host-profile
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime
```

Linux uses a task-owned disposable Debian container built from the Dockerfile,
with `--init --user 0 --cap-add SYS_ADMIN --security-opt seccomp=unconfined`.
Install `uidmap` and `libbsd-dev` there. util-linux 2.38.1 uses the old comma
ordering below. Add `root:20001:65535` to that container's `/etc/subuid` and
`/etc/subgid`; this is disposable subordinate-ID configuration, not a host
account change. Create `/tmp/csh071-nodes/block` (block 7:255) and `character`
(character 1:3), both mode 0600, in the parent namespace. Never open these nodes.

```sh
unshare --user --map-root-user --map-users=20001,1,65535 \
  --map-groups=20001,1,65535 --setgroups=allow \
  python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path /work/build/host-profile/bin:/bin:/usr/bin \
  --strict-gaps --boundaries --printf-faults build/tests/host_printf_faults \
  --controlled-identities --unequal-acl --device-fixtures /tmp/csh071-nodes \
  --record /tmp/mapped.json
python3 tests/host_permissions.py ./cshell \
  --path /work/build/host-profile/bin:/bin:/usr/bin \
  --session-controls --case-prefix newgrp/ --record /tmp/newgrp.json
```

The recorded namespace maps are exactly `0 0 1` and `1 20001 65535` for both
UIDs and GIDs, with setgroups allowed. The filesystem is the recorded Docker
overlay. Supplied nodes are type-checked and their path/device/inode is retained;
only predicates stat them. This does not claim the child namespace can mknod.

## Remaining environment and manual work

- Hosted macOS supplies the disposable privileged ACL environment; wait for and
  investigate the corrected measurement run before claiming qualification.
- Linux namespaces, ordinary filesystems, locales, signal/error cases and PTY
  fixtures can run automatically in the existing disposable container/CI setup.
- Password, login-database and supplementary-group boundary fixtures require
  controlled disposable accounts/session services. They can be automated with a
  PTY; real user passwords and manual keyboard entry are not prerequisites.
- Fakeowner socket-stat and non-owner-chmod failures require a changed filesystem
  implementation. A normal Docker volume is an alternative qualified filesystem,
  not proof that the original fakeowner behavior was repaired.
- Docker is responsive again and this follow-up exports evidence before removing
  its own container. That does not retroactively prove the earlier teardown.
- Native PID 53936 remains in UE under PID 1. Host recovery, potentially a reboot,
  may be needed; none was attempted because it would disrupt other work. The
  separate worktree is retained. The one fresh native timeout is retained above.

Run `python3 docs/evidence/csh-071-resolutions/verify.py` to audit these verdicts.
