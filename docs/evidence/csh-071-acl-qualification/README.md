# CSH-071 predicate, ACL, credential and ownership qualification

The selected `test`/`[` adapter now asks the filesystem for r/w/x access using
`faccessat(..., AT_EACCESS)`, including defined negated primaries. This replaces
GNU's retained unequal-ID mode-bit approximation for these predicates. No system
binary or account database is changed. The full utility contracts and untested
namespace/filesystem/session conditions remain open in CSH-071.

## Qualified subsets

| Environment and scope | Strict result and record |
| --- | --- |
| Native macOS 14.8.7 arm64; current-user ACLs and ownership | [496 pass, zero failures](native-acl.json.gz). Includes named read/write/execute grants, mode-bit denial controls, explicit ACL denials, allow-before-deny and deny-before-allow, file inheritance, test/bracket/negation in direct/string/file/stdin modes. Actual operations are independent of predicates. |
| Same native scope, instrumented adapter | [496 pass, zero failures](native-asan.json.gz), ASan/UBSan with halt-on-error. Only the adapter is instrumented; cshell and system utilities are not claimed sanitized by this run. |
| Native selected permission profile | [980 pass, zero failures](native-permissions.json.gz). |
| Native existing host profile | [1,162 pass, zero failures/gaps](native-profile.json.gz). |
| Hosted Ubuntu 24.04 x86_64, Linux 6.17.0-1022-azure, glibc 2.39, ext4 | [2,260 pass, zero failures/gaps](ci-linux-unequal-acl-qualification.json.gz) in the strict existing `--controlled-identities --unequal-acl` profile. Real/effective UID and GID combinations, supplementary ACL groups, masks, precedence and inherited ACLs retain their independently authored grants/denials and actual r/w/x controls. |
| Same Linux host, focused controlled credentials/ownership | [22 pass, zero failures](ci-linux-controlled-qualification.json.gz): independently varied UIDs/GIDs, supplementary groups, and non-owner chmod/chown/chgrp denial with unchanged metadata. Saved-root access must be rejected after dropping credentials. |
| Same Linux host, ordinary ownership | [16 pass, zero failures](ci-linux-ordinary-qualification.json.gz): nonprivileged set-ID clearing, actual supplementary-group ownership change, and mode/ownership ctime updates. These also form 16 of the native focused assertions. |

The [CI snapshot](ci-run.json) links the successful Linux job at source
`c9546ef007bc10698c268f6847d931f01bbaab7b`. Its privileged Darwin job is still queued:
**no privileged Darwin result is claimed**. The native run is a current-owner
qualification, not a substitute for distinct real/effective Darwin identities.
The workflow is ready to exercise existing runner/daemon accounts, swapped IDs,
ACLs and loss of saved-root access when that runner is supplied.

Native [filesystem observations](native-filesystem.json) retain the fixture
device, `df` result and mount information. Linux reports retain ext4 mount
options, device, initial user/mount namespace, full UID/GID maps, package versions,
provider/backend hashes, source hashes and exact outputs. This run uses the
initial namespace; it does not close the original remapped-namespace or fakeowner
conditions. Earlier failed provider assertions remain unchanged under CSH-064.

## Controls and failure classification

Darwin executable fixtures contain a real native helper. Mode 0454 provides the
global execute bit required by Darwin's exec path, while the owner cannot use
the group execute bit; for root-owned controlled fixtures neither dropped subject
is in the owning group. Each permission includes an empty-ACL denial control, so
an unrelated mode grant cannot substitute for an ACL grant. No shell script is
used for unequal-ID execute controls because an interpreter could reset IDs.

Write-only grants verify the write's return count and the resulting file size;
verification does not try to read through a write-only ACL. The harness retains
actual ACL entry order, principal, rights and inheritance flag, and rejects
mismatched fixture metadata before asserting a provider result. All selected
fixture directories were removed. Five [harness regressions](harness.log.gz) pass,
including timeout PID disappearance and strict retention of an ACL-cleanup error.

Failed development evidence is retained separately:

- [Initial native oracles](native-acl-before-oracles.json.gz): 272 pass / 128 fail.
  Sixty-four failures came from trying to read back a write-only file; 64 from
  expecting Darwin to execute a file with no execute mode bits. Both were fixture
  defects, not permission-predicate vendor failures.
- [Native execute precondition](native-acl-before-exec.json.gz): 336 pass / 64 fail,
  after repairing write-effect observation but before fixing the executable mode.
- [First hosted ACL attempt](ci-inaccessible-unequal-acl.json.gz): 1,384 pass /
  876 fail. Dropped users could not execute provider/helper paths under the hosted
  checkout. The workflow now copies only repository source inputs (not `.git` or
  checkout credentials) into a traversable disposable `/tmp` tree, builds there,
  and removes it after upload. These failures are execution-environment failures,
  not newly inferred ACL grants or denials.

The final small harness follow-up adds a guard against ignored Darwin selection
flags and preserves cleanup errors in JSON. Its five native regressions pass;
the qualification records identify the exact earlier assertion snapshots. No
production adapter code changed after those passing native/CI runs.

## Reproduction

```sh
make -j2 cshell host-profile build/tests/host_utility_helper
python3 tests/host_permissions.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --qualification-only --darwin-acls --record build/native-acl.json
make test-host-profile
```

For Linux root in a disposable exec-accessible tree:

```sh
python3 tests/host_permissions.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --qualification-only --controlled-identities --record build/credentials.json
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --strict-gaps --boundaries --printf-faults build/tests/host_printf_faults \
  --controlled-identities --unequal-acl --record build/unequal-acl.json
```

The `Permission qualification` workflow supplies dependencies, exact commands,
separate ordinary/root runs, artifacts on failure and disposable-tree cleanup.
Local Docker still returns API errors; hosted Linux evidence is not relabeled as
a local Docker result. The earlier native process cleanup failure is historical
and unchanged; this follow-up does not claim to have reaped that unrelated PTY
fixture by passing permission tests.
