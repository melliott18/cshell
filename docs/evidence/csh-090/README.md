# CSH-090 total pathname boundary evidence

Collected 2026-10-14 in a separate worktree based on published CSH-089 commit
`9b66eb7bd867536ef7f8d1a7c7e8d108337eef48`. CSH-089 remains unmerged;
integration is gated on that dependency. Eight cases add 32 assertions, without
changing selected providers or qualifying a complete utility.

## Independent oracles

Issue 8 [pathchk](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pathchk.html)
DESCRIPTION and OPTIONS require total-path and portable-limit diagnostics;
STDOUT, STDERR and EXIT STATUS define output channels and the status class.
The [limits definitions](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/limits.h.html)
include the terminating NUL in PATH_MAX and give the portable minimum as 256.
`normative-sources.json` records retrieved source hashes. The web reader returned
HTTP 403; direct HTTPS retrieval succeeded. The pathchk hash matches the retained
section map.

Each private fixture contains only two short target directories. Repeated `./`
components create operands of limit-1, limit and limit+1 bytes, excluding NUL;
therefore only the first fits the selected limit. Every component is at most
two bytes. The host limit comes from `pathconf`; the portable limit is authored
from the standard. Neither is inferred from the selected utility's output.

Before execution, unnormalized `stat` calls relative to an owned directory fd
prove resolution to the intended inode, ENAMETOOLONG at the host boundary, or
ENOENT for an allowed missing operand. Passing these operands through pathlib
would remove `./` and invalidate the oracle, so the probe passes raw strings.
Indeterminate, implausibly large or unexpectedly behaving filesystem limits
are setup failures. No deep tree, allocation fault, mount, quota, capacity
exhaustion or change to kernel limits is involved.

The continuation cases place a valid missing operand between two invalid
operands. Each invocation checks empty stdout, one C-locale length diagnostic
naming each complete invalid operand, zero or positive-error status, retained
directories, absent missing targets and successful cleanup. Known diagnostic
dialects require either a length-error phrase or the exact GNU numeric limit
and length; a permission diagnostic cannot satisfy the oracle. All four modes
(direct, cshell command string, script file and stdin) are mandatory.

Five harness regressions reject corrupted output/status/effects/diagnostics,
indeterminate or wrong kernel boundaries, and incomplete setup. They preserve
the reusable case specifications and verify timeout cleanup in all four modes.
A development Linux repeat exposed an immediate-reaping assertion: after the
watchdog killed a non-optimizing `/bin/sh` and its child, the child could still
be visible briefly before container init reaped it. The test now requires PID
disappearance, including zombies, within a separate two-second bound. It still
fails if reaping never occurs. The failed run is retained in
`development-linux-inventory-reap-race.log.gz`; it is not passing evidence.
The final complete validation follows that correction on both platforms.

## Results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64 container, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Inventory + 10 ownership + 54 harness tests pass | Same checks pass |
| `make test-host-profile`: host integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1259 pass, 0 fail | 1275 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-isolated` | 112 pass, 0 fail | 112 pass, 0 fail |
| `make test-host-filesystem-interactive` | 39 pass, 0 fail | 39 pass, 0 fail |
| `make test-host-filesystem-decisions` | 68 pass, 0 fail | 68 pass, 0 fail |
| `make test-host-filesystem-metadata` | 64 pass, 0 fail | 64 pass, 0 fail |
| `make test-host-filesystem-recursive` | 30 pass, 0 fail | 30 pass, 0 fail |
| `make test-host-filesystem-path-limits` | 32 pass, 0 fail | 32 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 1166 pass, 73 fail | 1209 pass, 42 fail |
| Stock `--extended-only --provider-audit` | 152 pass, 16 fail | 176 pass, 8 fail |

Selected commands require zero allowances. Stock Make audits exit 2; direct
stock provider audits exit 1. `stock-failure-comparison.json` compares each
failure ID and mode with CSH-089. Original stock failures remain failures,
including the unpatched GNU rm missing-parent-prompt timeouts. No historical
evidence files were edited.

## Provenance and reproduction

All final JSON reports record actual build/test input SHA-256
`894cbe4fc629381c0bf1cc157848e8b64770f5005494b35d46f9117cbe3c4699`.
Native and Linux records have identical source identities. All filesystem
cases record successful cleanup; native PATH_MAX is 1024 and Linux is 4096.

The native gfind executable was copied from the ignored CSH-089
`build/native-findutils/bin/gfind` into this worktree's ignored build directory;
its exact executable hash is in the selected manifest. All other provisioning
uses the documented dependencies. No host executable was overwritten.
`native-provider-build.log.gz`, provider manifests and coreutils build/configure
logs retain the selected source, patches, build options and executable identities.

`docker-image.json` identifies the Debian Linux image. Final test inputs were
copied into the disposable container before final validation;
`container-source-sync.json` records their actual hashes. The container used
`--init` and the image's unprivileged UID 10001, and was removed after export.
No new privileged, sanitizer or hosted-CI qualification is claimed.

```sh
# Native provisioning PATH must contain gtest, g[, gfind and gdd.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive \
  test-host-filesystem-decisions test-host-filesystem-metadata \
  test-host-filesystem-recursive test-host-filesystem-path-limits
make test-host-filesystem-audit # required separate nonzero stock result
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json

docker build -t cshell-test:csh-090 .
docker run --rm --init cshell-test:csh-090 make test-host-inventory \
  test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive \
  test-host-filesystem-decisions test-host-filesystem-metadata \
  test-host-filesystem-recursive test-host-filesystem-path-limits
```

Compressed JSON records retain expected and actual output, status, effects,
setup errors, cleanup, credentials, providers and source identities. Command
records retain exact argv and exit status; `SHA256SUMS` covers every retained
artifact other than this narrative. The shared allocator reserved CSH-091/#193;
live ticket identity validation passes with two historical shared-branch warnings.

## Remaining ownership

Every unsupplied environment and all four original retained conditions remain
open under [CSH-091](../../tickets/CSH-091-filesystem-environment-residuals.md)
([#193](https://github.com/melliott18/cshell/issues/193)). Utility/libc/platform
vendors retain implementation ownership. This uses CSH-090's explicit-disposition
acceptance alternative. Alternate filesystems, arbitrary trees, non-C repertoires,
ACLs, mounts, quotas, real capacity exhaustion and libc-internal allocation
faults remain unqualified. Kernel ENAMETOOLONG here does not close another
utility's PATH_MAX contract or any of the four retained conditions.
