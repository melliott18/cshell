# CSH-102 string-magic bytes and offset boundaries

Implemented on 2026-10-26 in a separate worktree based on CSH-101 commit `b71283d`.
Integration remains gated on that open dependency.

## Scope and independent oracle

Issue 8 [file](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html)
EXTENDED DESCRIPTION defines byte offsets, string comparisons, required escape
spellings and failure on insufficient bytes. STDOUT, STDERR and EXIT STATUS
supply exact channels and status for these authored messages. The retrieved
source hash is in `normative-sources.json`; the web reader returned 403 and direct
HTTPS retrieval succeeded.

`tests/host_filesystem_magic_strings.py` supplies 91 cases, run through direct
exec and cshell string/file/stdin dispatch: 364 assertions per platform.
Fifteen literal encoded/decoded pairs cover ordinary strings, escaped spaces
and backslashes, seven control escapes, one/two/three-digit octal sequences,
an octal escape followed by a fourth digit, embedded NUL and byte 255. Each
has exact-EOF, trailing-data, mismatched, truncated and at-EOF variants.
Four equivalent offset spellings (decimal, octal, lower/uppercase hexadecimal)
have exact, one-byte-early, one-byte-late and past-EOF samples.

The magic spellings and literal sample bytes are authored separately; no escape
decoder, provider result or default classifier supplies the expected output.
A successful top-level literal rule makes continuation failure observable without
using unspecified default classification. Readback must verify both files before
execution. Exact output, empty stderr, zero status and unchanged input contents
are required. The reused setup also records native byte order/byte-short widths;
these numeric facts are incidental, not a string-matching oracle.

Four additional harness tests check authored byte/boundary distinctions, reject
wrong output/status and modified inputs, reject corrupt setup before execution,
and verify failed-exec and timeout cleanup in all four modes. No new provider,
wrapper, syscall injection, privileged credentials or filesystem exhaustion is
introduced. The selected `file` executable remains the inventoried host binary.

## Reproduction

```sh
# Native PATH must contain gtest, g[, gfind and gdd.
make -j4 cshell host-profile
python3 docs/evidence/csh-102/validate.py native
python3 docs/evidence/csh-102/supplement.py native

docker build -f docs/evidence/csh-102/Dockerfile.linux -t cshell-test:csh-102 .
docker create --init --name cshell-csh102-validation cshell-test:csh-102 \
  sh -c 'python3 docs/evidence/csh-102/validate.py linux && python3 docs/evidence/csh-102/supplement.py linux'
docker start -a cshell-csh102-validation
docker cp cshell-csh102-validation:/work/build/csh102-validation ./build/csh102-linux-results
docker cp cshell-csh102-validation:/work/build/csh102-supplement ./build/csh102-linux-supplement
docker rm cshell-csh102-validation

# Copy retained records here, then check both current and historical expectations.
python3 docs/evidence/csh-102/verify.py
```

The Linux image reuses the CSH-101 provider build and unprivileged UID 10001;
no host volume or protected mount is exposed. Native providers are built from
pinned sources here; GNU find is copied unchanged from the CSH-101 local provider
and separately hashed. Manifests and build logs identify the actual providers.

`validate.py` runs every ticket-required selected target plus the new target,
then distinct stock full/provider audits. Expected command statuses are 0, 2
and 1. `supplement.py` checks runtime, runtime PTY and harness behavior under the
selected PATH. `verify.py` requires every previous authored expectation unchanged
(except measured per-run inode identities), exactly 364 added passing assertions,
all retained stock failure IDs/modes unchanged, clean fixture teardown and matching
provider/build/test identities across reports. `SHA256SUMS` covers retained files
except this narrative and itself. No hosted-CI or sanitizer result is claimed.

## Remaining ownership

[CSH-103](../../tickets/CSH-103-filesystem-environment-residuals.md)
([#217](https://github.com/melliott18/cshell/issues/217)) owns all 21 individual
utility residuals and four original U-040 conditions. Additional numeric types,
unsigned ranges, multi-database precedence, default classification, arbitrary
encodings/locales and resource failure environments remain unqualified. Utility,
libc and platform vendors retain implementation ownership. The explicit open
alternative is used for all unsupplied environments; U-034/U-040 remain partial
and no whole utility is qualified.

## Development and environment setup

The first native provider provisioning stopped because GNU find was absent from
the inherited PATH. After copying the previously qualified CSH-101 GNU find
into this worktree's local provider directory and adding that directory plus
`/usr/local/bin` to PATH, provisioning succeeded. The build log preserves both
attempts; `native-find-provenance.json` records the exact copied executable.
The first harness run overlapped editing the clause map and failed its missing-ID
accounting check; the completed map is tested by the final validation run.
An initial native smoke probe using `/bin/sh` passed 364 assertions, but is kept
only as development evidence; final qualification uses this worktree's cshell.
The first Linux run was stopped to synchronize the updated provider README used
in the build/test source digest, then restarted. No completed result is claimed
for that interrupted run. The Linux supplemental script was copied into the
container after image creation; the checked-in Dockerfile includes it on rebuild.

## Final results

Native macOS 14.8.7 arm64 UID 501 and Debian 12 arm64 Docker UID 10001
pass all required selected targets with zero allowances: 3863 and 3903 full
filesystem assertions, respectively, including 364 new assertions per platform.
Both general host profiles pass 1162 assertions with zero gaps. Both platforms
pass all 10 ownership and 108 filesystem harness tests, 3950 runtime cases,
33 terminal cases and the 93-test harness suite (one Darwin-only test skipped
on Linux). Stock full/provider failures remain exactly 137/16 on native macOS
and 42/8 on Linux; they are retained failures, never allowances.

The retained verifier passes: every previous expected value and stock failure
is preserved, setup/readback/cleanup records are complete, provider hashes agree
with manifests, and both platforms match the current build/test source digest
`bb4248770c4ab8813fffbf211b436107cd30d4d301e2850183a7b004d399e186`. Historical evidence is unchanged.

| Target/report | macOS pass/fail | Linux pass/fail |
| --- | --- | --- |
| host-filesystem-allocation | 240 / 0 | 200 / 0 |
| host-filesystem-audit | 3706 / 137 | 3837 / 42 |
| host-filesystem-calendar | 160 / 0 | 160 / 0 |
| host-filesystem-creation | 104 / 0 | 104 / 0 |
| host-filesystem-cwd-logical | 48 / 0 | 48 / 0 |
| host-filesystem-cwd | 32 / 0 | 32 / 0 |
| host-filesystem-datetime | 256 / 0 | 256 / 0 |
| host-filesystem-day-rules | 512 / 0 | 512 / 0 |
| host-filesystem-decisions | 68 / 0 | 68 / 0 |
| host-filesystem-interactive | 39 / 0 | 39 / 0 |
| host-filesystem-isolated | 112 / 0 | 112 / 0 |
| host-filesystem-magic-strings | 364 / 0 | 364 / 0 |
| host-filesystem-magic | 184 / 0 | 184 / 0 |
| host-filesystem-metadata | 64 / 0 | 64 / 0 |
| host-filesystem-output | 32 / 0 | 56 / 0 |
| host-filesystem-path-limits | 32 / 0 | 32 / 0 |
| host-filesystem-profile | 3863 / 0 | 3903 / 0 |
| host-filesystem-provider-audit | 168 / 0 | 184 / 0 |
| host-filesystem-recursive | 30 / 0 | 30 / 0 |
| host-filesystem-reference | 112 / 0 | 112 / 0 |
| host-filesystem-residual | 104 / 0 | 104 / 0 |
| host-filesystem-stock-provider-audit | 152 / 16 | 176 / 8 |
| host-filesystem-timezone | 416 / 0 | 416 / 0 |
| host-filesystem-transition-times | 384 / 0 | 384 / 0 |
| host-profile-results | 1162 / 0 | 1162 / 0 |
