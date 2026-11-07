# CSH-085 private filesystem contracts

Collected on 2026-10-09 in a separate worktree, based on CSH-084 commit
`5f30e232b5cb35b289939784e32350413811fa1b` (implemented, still unmerged).
The change supplies 28 cases / 112 assertions across three utilities, using the
ticket's explicit-disposition alternative for every unsupplied environment.
No entire utility page or complete POSIX profile is qualified.

## Final results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Accounting, 10 inventory + 31 filesystem harness tests pass | Same checks pass |
| `make test-host-profile`: host integration | 1162 pass, 0 failures/gaps | 1162 pass, 0 failures/gaps |
| Same command: filesystem assertions | 1026 pass, 0 fail | 1042 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-isolated` | 112 pass, 0 fail | 112 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 954 pass, **52 fail** | 982 pass, **36 fail** |
| Stock `--extended-only --provider-audit` | 152 pass, **16 fail** | 176 pass, **8 fail** |

Selected commands exit zero; stock Make audits exit 2 and direct stock audits
exit 1. Every filesystem record reports successful cleanup. Linux selected-PATH
`make test-runtime test-pty` also passes (see runtime log); the additional four
Linux stock failures are the retained GNU du default-unit defect. All final
reports share source-input SHA-256
`85c71862563ebdc6e0845363c7f832118eb8e8a491630006b0d86ffc360aa402`.

## Independent oracles

Seven `du` cases use private regular files, directories, an operand symlink,
a nested symlink and a hard-link pair. Pre-execution `lstat` records retain
actual device/inode identities and 512-byte allocated-block counts. Fixed
formulas for this authored graph produce recursive totals and `-k` rounding;
no selected or reference utility generates expected output. Post-execution
measurements must match the original graph. Unspecified output order is allowed;
wrong totals, duplicate, missing or extra paths fail. This is allocated-block
accounting on the reported filesystem, not measurement of unique physical
shared extents or a mounted disposable volume.

Sixteen `file -m` assertions pair matching and nonmatching byte samples for
equality, less/greater comparisons, hexadecimal/octal masks, set/missing bits
and native short equality. Authored continuation messages provide exact positive
and negative output. Neither the host magic database nor another `file` process
supplies an oracle.

Five `touch` cases use exact nanosecond metadata for period/comma fractions,
T/space separators, UTC/fixed-offset local time and access/modification isolation.
The parent independently proves the .002-second target and .125-second baseline
representable using `utime(ns)` and `stat` before execution. Rounding, unsupported
precision, changed untouched timestamps and setup errors cannot pass.

All cases run through direct exec and cshell string/file/stdin modes under an
unprivileged fixture identity. The [section map](../../../tests/host_filesystem_contracts.json)
and [case source](../../../tests/host_filesystem_isolated.py) bound every claim.
The three normative utility page hashes match the inherited Issue-8 sources.

## Selected Linux du configuration and retained failure

Unconfigured GNU coreutils 9.1 `du` reports 1024-byte units. The initial Linux
selected run failed the required default-512 assertion in all four modes
(**1038 pass, 4 fail**). Its original report and manifest remain retained here.
The oracle and expected values are unchanged.

Linux now selects the standalone [du launcher](../../../tools/host-profile/du.c),
which sets `POSIXLY_CORRECT=1` and immediately execs `/usr/bin/du` with the
original argument vector. GNU implements all traversal, formatting, option and
status behavior. There is no output/status translation. This is GNU's documented
configuration: [coreutils 9.1 block-size documentation](https://github.com/coreutils/coreutils/blob/v9.1/doc/coreutils.texi).
Explicit block-size overrides remain GNU behavior; the tested default has none.
The invoking shell's environment is unchanged. The manifest records launcher
and backend hashes and the exact configuration; stock audits still dispatch
unconfigured system du and retain its four failures. macOS retains system du.

## Setup, failure and cleanup

The filesystem harness has 31 tests, including seven new regressions for
incorrect/missing/duplicate accounting records, hard-link double counting,
partial graph setup, unrepresentable timestamps, lost subsecond precision,
paired magic expectations, and timeouts for all three environments. Timeout
helpers report their PID and must disappear; fixture removal is checked.
Synthetic setup errors are harness checks, not kernel ENOSPC/EIO evidence.
An initial timestamp mock incorrectly intercepted fixture creation itself;
limiting it to nanosecond-setting calls repaired that regression test.

All current filesystem result records require successful cleanup, including
stock failure records. The only created trees and files are private fixtures.
No credentials, privileged mounts, host-volume filling or external data are
used. Existing call-site allocation injection and Linux virtual-device ENOSPC
remain distinct from libc-internal failure and actual filesystem exhaustion.

## Reproduction

```sh
# Darwin provisioning PATH needs gtest, g[, gfind and gdd.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated
make test-host-filesystem-audit # expected nonzero stock failures
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json

docker build -t cshell-test:csh-085 .
docker run --rm cshell-test:csh-085 make test-host-profile \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated
# In that Linux image, after provisioning the profile:
CSH_TEST_PATH='/work/build/host-profile/bin:/bin:/usr/bin' make test-runtime test-pty
```

Native provisioning copies the unchanged CSH-084 gfind binary into the ignored
`build/native-findutils/bin` directory and prepends that directory to PATH.
The existing CSH-080 provenance identifies its upstream build. Source-input
hashes, actual argv/environment/output/status/effects, providers, packages and
platforms are retained in the compressed reports; build commands are in logs.
`SHA256SUMS` covers the evidence artifacts. Validation is local native macOS and
Docker/Linux, not a hosted-CI or complete sanitizer qualification claim.

[CSH-086](../../tickets/CSH-086-filesystem-unsupplied-contracts.md) owns all
remaining utility contracts and the four immutable original condition IDs.
The current [ledger](../../../tests/host_filesystem_residuals.json) gives every
required environment, open reason and vendor owner. Privileged ownership,
ACLs, quotas, mount/cross-device boundaries, actual ENOSPC/EIO, libc internals,
shared extents and remaining locales/formats are still open. CSH-072/080/084
historical evidence has not been rewritten.
