# CSH-080 filesystem qualification

Collected on 2026-10-06 from a separate worktree based on CSH-072 commit
`96b1a669c0d619912bd7d1a700ddd3875c7e5583`. This adds 60 ordinary cases and
call-site allocation failures; **no full utility page is qualified**.
Every individual remaining contract and all four original retained conditions
have an explicit environment, reason and next owner in the
[CSH-084 ledger](../../../tests/host_filesystem_residuals.json).

## Results

| Command/profile | Native macOS 14.8.7 arm64 | Docker Debian 12 arm64 |
| --- | --- | --- |
| `make test-host-inventory` | Accounting plus 10 inventory and 17 filesystem harness tests pass | Same checks pass in the profile log |
| `make test-host-profile`: host integration | 1162 pass, 0 fail, 0 gaps | 1162 pass, 0 fail, 0 gaps |
| Same command: filesystem assertions | 810 pass, 0 fail | 826 pass, 0 fail |
| Same command: pathname allocation assertions | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` (selected PATH) | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-audit` (stock PATH, expected nonzero) | 742 pass, **48 fail** | 774 pass, **28 fail** |
| Stock `--extended-only --provider-audit` (expected nonzero) | 152 pass, **16 fail** | 176 pass, **8 fail** |
| ASan/UBSan pathname allocation assertions | 240 pass, 0 fail | Not run separately |

Every filesystem/injection fixture records successful cleanup, including stock
failures. Full stock audits exclude the separate provider-audit-only assertions;
these are retained in their own stock run. The selected profile includes both.
Native/Linux counts differ by Linux `/dev/full` cases and the number of allocation
calls needed to walk the absolute private temporary pathname. Both platforms
exercise every reached call in all six allocation scenarios and four modes.
The instrumented binary is test-only; production providers are not instrumented.
This is local macOS plus Docker evidence, not a hosted-CI completion claim.

The ordinary cases exercise direct exec and public cshell string/file/stdin
invocation, with exact authored bytes/status and independent Python filesystem
effects. GNU dd statistics require exact whole/partial counts and bytes; its
variable transfer-rate text uses a bounded format predicate. Stock Apple dd's
permitted odd-swab informational line is checked explicitly, not classified as
a defect. No new gap allowances or status/output adapters are used.

## Provider defect and selection

Apple `/bin/dd` counts short input padded by `conv=sync` as a whole input block,
contrary to the STDERR definition based on the bytes returned by `read()`.
The block+sync witness also emits an unexpected truncated-record count. The
original strict assertions remain in the stock audit. macOS now selects GNU
`gdd` from the existing coreutils prerequisite; this native run used coreutils
9.3. Linux keeps its stock GNU dd. Filesystem capacity, EIO, interrupt recovery
and other dd contracts remain individually open.

[Provider provenance](provider-provenance.json) includes the installed coreutils
receipt, gdd version/hash, the reused GNU find 4.10.0 build provenance, and Docker
image identity. GNU find was copied into this worktree's ignored build directory
and passed the complete selected profile again. Local readlink/realpath and
pinned pax are rebuilt from the unchanged CSH-072 sources; their identities are
in the separate [native](native-manifest.json) and [Linux](linux-manifest.json)
manifests. No system executable was replaced.

The [normative source index](normative-sources.json) records re-read Issue-8
pages. All 16 hashes match the inherited section map. XSI-shaded dd character-set
conversions are outside the selected base profile. Numeric timezone offsets in
touch -d are optional extensions; UTC and required local-time forms are tested.

## Allocation scope and harness checks

`host_paths_faults.c` includes the unchanged local provider with malloc, strdup,
getcwd and realpath call-site failure controls. A successful control measures
reached calls. Every index is then failed, followed by a non-triggering sentinel.
The checked marker must show the requested index and a reached failure, so an
exec/setup failure cannot satisfy a positive-error expectation. Error-path
allocations after the failure are allowed within the successful path's bounded
count. libc-internal allocation behavior and real kernel ENOMEM are not claimed.
All records retain the actual marker, argv/environment, status, diagnostics,
source hash and cleanup. The harness tests also reject missing/unarmed/malformed
markers, padded-input count errors, unavailable UTF-8 setup and timeout leaks.

## Reproduction

```sh
make -j4 cshell host-profile
make test-host-inventory
make test-host-profile
make test-host-filesystem-provider-audit
# Preserve these nonzero stock results separately:
make test-host-filesystem-audit
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json

# Test-only native sanitizer build, then restore the ordinary binary:
make -B build/tests/host_paths_faults \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
python3 tests/host_filesystem_allocation.py ./cshell build/tests/host_paths_faults \
  --sanitizer --record build/tests/host-filesystem-allocation-sanitized.json
make -B build/tests/host_paths_faults

# Fresh Linux toolchain and non-root fixtures:
docker build -t cshell-test:csh-080 .
docker run --rm cshell-test:csh-080 make test-host-profile
```

Native provisioning requires gtest, g[, gfind and gdd on the provisioning PATH.
This run used `PATH="$PWD/build/native-findutils/bin:$PATH"` for the locally
copied GNU find. Linux is the Dockerfile's UID 10001; no privileged container or
mount was used. The exact Docker build and validation logs are retained.

## Artifact integrity and development failures

All final machine reports share source-input SHA-256
`6f8c09f34217b6b8cff602346d6cd12e31a755b92234bbb16b958c9f276ba395`.
`native-host-*.json.gz` and `linux-host-*.json.gz` are full reports; matching logs
and provider manifests are retained. `SHA256SUMS` covers every evidence artifact.
CSH-072 evidence files and original condition IDs/reasons are unchanged.

`development-initial-ordinary.json.gz` retains the first 224 pass/16 fail run:
eight sync count failures reproduced the Apple defect; four odd-swab failures
were an overly narrow diagnostic oracle, and four touch failures requested an
optional numeric-offset extension. The final suite models the allowed diagnostic
and tests the required local-time form. These development results are not a
conformance claim. `development-initial-allocation.log.gz` preserves four overly
strict call-count failures: absolute-link cleanup performs another allocation
after a failure. The final marker oracle proves injection while permitting that
bounded control flow. No provider behavior was changed to satisfy those tests.

Ticket identities were checked against the atomically reserved CSH-084 / issue
#178 mapping. The two pre-existing historical shared-branch warnings remain.

## 2026-10-08 follow-up

[Hosted verification](hosted-1ecae53/README.md) now retains all eight successful
checks for implementation 1ecae53, including both broad native and Docker runs.
[Marker-reader hardening](marker-validation/README.md) records the subsequent
bounded-reader correction, ten invalid-marker subcases, and passing native/Linux
profiles. Each record is tied to its actual source version; stock failures and
CSH-084 dispositions remain unchanged.
