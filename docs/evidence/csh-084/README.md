# CSH-084 private residual environments

Collected on 2026-10-08 in a separate worktree at dependency commit
`1ecae53480204bfb26251d35f621c0635698c62b` (CSH-080, still unmerged).
This adds 26 cases / 104 assertions across 16 utilities. No entire utility page,
U-034/U-040 family, privileged environment or full POSIX profile is qualified.

## Results

| Command / profile | Native macOS 14.8.7 arm64, UID 501 | Docker Debian 12 arm64, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Accounting, 10 inventory and 24 filesystem harness tests pass | Same checks pass |
| `make test-host-profile`: host integration | 1162 pass, 0 fail, 0 gaps | 1162 pass, 0 fail, 0 gaps |
| Same command: filesystem assertions | 914 pass, 0 fail | 930 pass, 0 fail |
| Same command: pathname allocation assertions | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 842 pass, **52 fail** | 874 pass, **32 fail** |
| Stock `--extended-only --provider-audit` | 152 pass, **16 fail** | 176 pass, **8 fail** |

The inventory/allocation checks run as prerequisites of the selected profile.
Stock audits return nonzero and are retained separately; they are not passes.
All filesystem and allocation records report successful cleanup, including stock
failures. Linux has additional virtual-device ENOSPC witnesses; different
absolute temporary path lengths change allocation call counts. Neither is
actual filesystem-capacity evidence. This is local native/Docker validation,
not hosted-CI completion. No C provider or runtime source changed, so no new
sanitizer claim is made; CSH-080's sanitizer evidence remains historical.

## Oracles and provider scope

The [case source](../../../tests/host_filesystem_residual_cases.py) and
[section map](../../../tests/host_filesystem_contracts.json) name every assertion.
Fourteen permission cases cover thirteen utilities. Python creates a private
search-denied directory and independently verifies EACCES before dispatch under
the same unprivileged identity. Each record retains IDs, groups and probe errno.
The fixture restores search permission before checking unchanged file/link
contents, absent destinations, link counts or timestamps, then cleans the tree.
No account, privileged mount or developer data is touched.

Four `file -m` cases use independent databases and samples for string matching,
continuation, hexadecimal offset and escaped spaces. Expected messages come
from the authored rules, not a reference utility or the installed magic database.
Four readlink cases preserve three non-UTF-8 target bytes in C/UTF-8 with and
without newline. Four basename/dirname cases require a positive status and
diagnostic after independently armed EBADF/EPIPE; signal death cannot pass.

The sixteen [normative page hashes](normative-sources.json) match the inherited
Issue-8 sources. Only the listed clauses/assertions are qualified. The selected
profile uses unchanged providers. Both stock readlink implementations omit the
required diagnostic for the denied prefix, adding four failures each. The
existing selected local readlink already handles this case; no allowance or
output/status adapter was added.

## Setup, failure and timeout verification

The 24 filesystem harness tests include rejection of root and ineffective
permission bits, failures while creating magic samples and byte links, corruption
of protected effects, altered output, and timeouts for each new environment.
All timeout helpers must report their PID and disappear; leftover processes or
fixtures fail the tests. The new deadline is two seconds. Python helpers use
`-S` to avoid unrelated site initialization. Development runs with a half-second
startup deadline failed before obtaining a PID; the original one-second helper
also failed without `-S`. These were harness startup failures, not utility
contract failures, and were corrected before the retained full validation.
Synthetic setup exceptions are harness tests, not real ENOSPC/EIO evidence.

## Reproduction and integrity

```sh
# Darwin needs gtest, g[, gfind and gdd on the provisioning PATH.
make -j4 cshell host-profile
make test-host-profile test-host-filesystem-provider-audit test-host-filesystem-residual
# Preserve these nonzero stock audits independently:
make test-host-filesystem-audit
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json

docker build -t cshell-test:csh-084 .
docker run --rm cshell-test:csh-084 make test-host-profile \
  test-host-filesystem-provider-audit test-host-filesystem-residual
```

Native provisioning used `PATH="$PWD/build/native-findutils/bin:$PATH"` with the
unchanged CSH-080 GNU find binary copied into the ignored build directory.
[Build provenance](provider-provenance.json), separate native/Linux manifests,
compiler commands and compressed logs are retained. Reports include full
argv/environment, actual output/status/effects, source hashes and binary hashes.
All final reports share source-input SHA-256
`30dd1b8fd78d3deb8e41fb9e5d597ba94be3cb790b5a414c42b9e707df69fff7`.
`SHA256SUMS` covers the evidence artifacts.

[CSH-085](../../tickets/CSH-085-filesystem-isolated-contracts.md) owns the
individual remaining contracts and all four original conditions. Its
[ledger](../../../tests/host_filesystem_residuals.json) keeps explicit required
environments and reasons, including the five utilities with no new witnesses.
ACLs, privileged ownership, quotas, cross-device/mount boundaries, real capacity
exhaustion, EIO, libc internals and remaining locale/format contracts stay open.
Historical CSH-064 reasons and CSH-072/CSH-080 records are unchanged. The shared
registry reserves CSH-085 to issue #181; the identity check passes with only the
two pre-existing historical shared-branch warnings.
