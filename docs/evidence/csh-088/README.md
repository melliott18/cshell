# CSH-088 measured metadata and timestamp evidence

Collected 2026-10-12 on a separate worktree based on CSH-087 published commit
`dd133268f075d0610873ae030e700719a96180d5`. CSH-087 is implemented but unmerged;
integration remains gated on that dependency. This change adds 16 cases / 64
assertions and retains explicit open dispositions for unsupplied environments.
No complete utility is qualified.

## Results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64 container, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Inventory + 10 inventory and 44 filesystem harness tests pass | Same checks pass |
| `make test-host-profile`: integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1197 pass, 0 fail | 1213 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-isolated` | 112 pass, 0 fail | 112 pass, 0 fail |
| `make test-host-filesystem-interactive` | 39 pass, 0 fail | 39 pass, 0 fail |
| `make test-host-filesystem-decisions` | 68 pass, 0 fail | 68 pass, 0 fail |
| `make test-host-filesystem-metadata` | 64 pass, 0 fail | 64 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 1104 pass, **73 fail** | 1153 pass, **36 fail** |
| Stock `--extended-only --provider-audit` | 152 pass, **16 fail** | 176 pass, **8 fail** |

Selected commands exit zero; stock Make audits exit 2 and direct stock audits
exit 1. Stock failing assertion IDs and modes are identical to CSH-087 on each
platform. Every filesystem record reports successful fixture cleanup. Native
selected-PATH `make test-runtime test-pty` also passes; this change makes no new
Linux runtime/PTY, hosted CI or sanitizer qualification claim.

All final reports share build/test source-input SHA-256
`c2bba899e0e8d3006626e3eba8197d0b548888b15be8040d3676d2a0d98cb256`.
Provider manifests, executable hashes and cp configure/build logs retain exact
provenance. Selected provider sources, patches, build options and allowances
are unchanged. Native provisioning uses the same gfind binary as CSH-087,
copied into ignored `build/native-findutils/bin` and prepended to provisioning
PATH. The native build was retried with that PATH after a provisioning attempt
correctly rejected unavailable gfind; that setup attempt is not qualification.

## Independent oracles

The Issue-8 [ls](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html)
OPTIONS/STDOUT and [find](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html)
OPERANDS define the exercised fields, ordering and timestamp comparisons.
`normative-sources.json` records directly retrieved page hashes; the web reader
returned HTTP 403, while direct HTTPS retrieval supplied the normative pages.

Each case creates a private directory. `lstat` before exec supplies type, mode,
link count, numeric owner/group, size and timestamps for numeric `ls -dn`
listings of a regular file, a hard link, directory, FIFO and symlink. The
hard-link identity/count is independently verified. C-locale UTC output must
contain the authored January 2, 2000 date and exact operand/link target. Column
padding and known alternate-access marker spellings are accepted; ACL semantics
are not claimed. Every other field and the complete single-line record are
checked. No provider output generates its own expected values.

Four authored regular files have deliberately different size, mtime and atime
orders, including primary-key ties. Six cases check descending size/mtime/atime
ordering, C-locale secondary names and reversal. `utime(ns)` followed by exact
`lstat` readback establishes every timestamp before invocation. Five find cases
compare modification times one nanosecond before, equal to and one nanosecond
after a reference, and require -H/-L to follow a reference symlink whose own
timestamp would give the opposite result. Unsupported timestamp resolution is
a setup failure, never a skip or allowance. This tests authored timestamps,
not live-clock age predicates or timestamp-range boundaries.

Every case runs by direct provider exec and through cshell command string,
script file and stdin. Measurements and actual post-exec metadata are retained.
Measured objects must remain unchanged, except for symlink access times that
may change when readlink is used. Stdout, stderr, status, capture errors,
setup errors and cleanup are recorded separately.

## Harness and ownership checks

Four new harness tests reject corrupted listing fields, extra/missing lines,
incorrect ordering/status/stderr, modified fixtures, rounded timestamps and
partial setup failure. A deliberately stalled provider must time out, disappear
and leave no private fixture in all four execution modes. These tests verify
failure detection, not utility conformance.

The current section map and residual ledger retain every old assertion ID.
[CSH-089](../../tickets/CSH-089-filesystem-environment-residuals.md) owns each
remaining utility contract, required environment, reason and all four retained
CSH-064 conditions. Utility/libc/platform vendors retain implementation
ownership. Non-C collation, arbitrary graphs, mount/depth limits, privileged
identities, ACLs, quotas, real filesystem exhaustion and libc-internal faults
remain unqualified. Prior evidence is unchanged; inherited call-site ENOMEM,
kernel EFBIG/EPIPE and virtual-device ENOSPC retain their distinct scope.

The shared ticket registry lacked pre-existing CSH-087/#185 and CSH-088/#187.
The allocator initially assigned the new follow-up #189 the colliding CSH-087
ID. A history-preserving fast-forward correction reconciled the existing
bindings and assigned #189 CSH-089. `ticket-registry-reconciliation.json`
records the commits. Live identity validation passes with 89 reservations and
two pre-existing historical shared-branch warnings.

## Reproduction and artifacts

```sh
# Native: gtest, g[, gfind and gdd must be available on provisioning PATH.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive \
  test-host-filesystem-decisions test-host-filesystem-metadata
make test-host-filesystem-audit # expected nonzero stock result
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty

docker build -t cshell-test:csh-088 .
docker run --rm cshell-test:csh-088 make test-host-inventory test-host-profile \
  test-host-filesystem-allocation test-host-filesystem-provider-audit \
  test-host-filesystem-residual test-host-filesystem-isolated \
  test-host-filesystem-interactive test-host-filesystem-decisions \
  test-host-filesystem-metadata
```

The selected Linux and stock audit containers used the same image and UID
10001. They were retained for report export, then removed. Compressed JSON
retains arguments, environment, provider identities, expectations, actual
outputs/effects, measurements and cleanup. Logs retain commands and results.
`SHA256SUMS` covers all retained artifacts other than this narrative.
