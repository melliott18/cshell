# CSH-100 Julian and numbered daylight-saving rule evidence

Collected 2026-10-24 in a separate worktree based on CSH-099 commit `dab7620`.
Integration remains gated on that unmerged dependency.

## Scope and independent oracle

Issue 8 [touch](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html)
OPTIONS and ENVIRONMENT VARIABLES define local -d/-t interpretation and timestamp
field selection. [XBD chapter 8](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html#tag_08)
defines Julian `Jn` dates excluding leap day, zero-based `n` dates including it,
the default 02:00 transition time and the default one-hour daylight offset.
`normative-sources.json` retains direct HTTPS page hashes; the web reader returned 403.

`tests/host_filesystem_day_rules.py` supplies 128 cases, each run by direct exec
and cshell string/file/stdin dispatch: 512 assertions per platform. Sixteen
unique local times have both -d and -t spellings and default, access-only,
modification-only and explicit-both field selections.

The zones are `JST0JDT,J60,J300` and `NST0NDT,59,299`. Both begin daylight time
on March 1 in 2023. In leap year 2024, the Julian rule still starts March 1,
while day 59 is February 29. Similarly J300 remains October 27; numeric day 299
is October 26 in 2024. Unique times before/after the authored transitions,
February 29 under J60 and March 1 under day 59 distinguish the two policies.
Before fallback the sample precedes the repeated hour. No result is asserted
for a skipped or repeated local time. Omitted transition times and daylight
offsets exercise the standard's defaults.

UTC fields are authored separately from local input strings. Integer Gregorian
subtraction supplies Epoch nanoseconds. Literal Epoch seconds in the harness
regression check the day-count, offset and date-rollover expectations. No
provider result, timezone database, mktime, date-string parser, current clock
or floating-point timestamp supplies the oracle.

The existing CSH-098 setup probes exact expected timestamps on the target inode,
then restores distinct fractional baseline fields and reads them back. Failed
or rounded setup fails before execution. Post-exec metadata is captured before
content reads. Both fields, identity, mode, link count, contents, empty channels
and zero status must agree. Four new harness regressions check the oracle,
incorrect fields/identity/content/channels/status, failed/rounded setup and
failed-exec/timeout cleanup in all four modes. Existing assertions are retained.

These are private ordinary files with representable timestamps. No privileged
provisioning, libc injection, kernel fault or filesystem exhaustion is involved.
Arbitrary J/n/M values, nondefault transition times, skipped/repeated times,
geographical timezone databases, unsupported ranges, creation/current clocks,
races and permission/ACL boundaries remain unqualified. Providers and selected
allowances are unchanged.

## Results

All required targets passed on native macOS 14.8.7 arm64 UID 501 and Debian 12
arm64 Docker UID 10001. Both platforms passed 10 ownership tests and 100
filesystem harness tests. All 512 new assertions pass with zero selected-profile
allowances. Selected filesystem totals are 3115/0 on macOS and 3155/0 on Linux.
The general host profile passes 1162 assertions with zero gaps on each platform.
Stock full/provider audits retain exactly CSH-099's failure IDs and modes:
macOS 73/16 failures and Linux 42/8 failures. Their nonzero statuses remain failures.
No sanitizer or hosted-CI result is claimed.

| Target/report | macOS pass/fail | Linux pass/fail |
| --- | --- | --- |
| host-filesystem-allocation | 240 / 0 | 200 / 0 |
| host-filesystem-audit | 3022 / 73 | 3089 / 42 |
| host-filesystem-calendar | 160 / 0 | 160 / 0 |
| host-filesystem-creation | 104 / 0 | 104 / 0 |
| host-filesystem-cwd-logical | 48 / 0 | 48 / 0 |
| host-filesystem-cwd | 32 / 0 | 32 / 0 |
| host-filesystem-datetime | 256 / 0 | 256 / 0 |
| host-filesystem-day-rules | 512 / 0 | 512 / 0 |
| host-filesystem-decisions | 68 / 0 | 68 / 0 |
| host-filesystem-interactive | 39 / 0 | 39 / 0 |
| host-filesystem-isolated | 112 / 0 | 112 / 0 |
| host-filesystem-magic | 184 / 0 | 184 / 0 |
| host-filesystem-metadata | 64 / 0 | 64 / 0 |
| host-filesystem-output | 32 / 0 | 56 / 0 |
| host-filesystem-path-limits | 32 / 0 | 32 / 0 |
| host-filesystem-profile | 3115 / 0 | 3155 / 0 |
| host-filesystem-provider-audit | 168 / 0 | 184 / 0 |
| host-filesystem-recursive | 30 / 0 | 30 / 0 |
| host-filesystem-reference | 112 / 0 | 112 / 0 |
| host-filesystem-residual | 104 / 0 | 104 / 0 |
| host-filesystem-stock-provider-audit | 152 / 16 | 176 / 8 |
| host-filesystem-timezone | 416 / 0 | 416 / 0 |
| host-profile-results | 1162 / 0 | 1162 / 0 |

Final build/test source digest: `99e480486080b2da5a823414b22036e4aee6dae9bf782c637f417df8109bf675`.

The passing verifier generates `summary.json` and `stock-failure-comparison.json`.
Provider manifests, configure/build logs, source identities, per-case channels/status/
effects/probes, cleanup and image/container identities are retained. The native
gfind helper was copied from CSH-099; pinned providers were rebuilt locally. Linux
uses the CSH-099 Debian image with the recorded overlay, Docker init and no host
mounts.

## Validation and reproduction

```sh
# Native PATH must provide gtest, g[, gfind and gdd. Wait for the build to finish.
make -j4 cshell host-profile
python3 docs/evidence/csh-100/validate.py native

docker build -f docs/evidence/csh-100/Dockerfile.linux -t cshell-test:csh-100 .
docker create --init --name cshell-csh100-validation cshell-test:csh-100 \
  python3 docs/evidence/csh-100/validate.py linux
docker start -a cshell-csh100-validation
docker cp cshell-csh100-validation:/work/build/csh100-validation ./build/csh100-linux-results
docker rm cshell-csh100-validation

# Retain native/Linux records in this directory before verification.
python3 docs/evidence/csh-100/verify.py
```

`validate.py` runs all ticket-required targets and the new day-rules target,
then separate stock full/provider audits; expected statuses are 0, 2 and 1.
`verify.py` requires every previous selected assertion and its exact authored expectations
(only per-run device/inode observations are allowed to differ), precisely 512 new passing assertions, armed inode probes, exact effects,
empty channels, zero status, cleanup, provider-manifest agreement and one
build/test source digest across platforms. Stock failure IDs/modes must equal
CSH-099 exactly. `SHA256SUMS` covers retained artifacts except this narrative
and itself. Historical evidence is unchanged.

## Retained initial build failures

`native-overlapping-build-failure.log` records a focused test launched while
the initial provider build was still running. Both invocations used the same
ignored coreutils build directory. The second configure failed with a missing
`conftest.er1`; the first build then failed with malformed/generated-header
compile errors, retained in `native-initial-build-failure.log`. Neither reached
provider assertions. The affected build/source directories were moved aside,
and a fresh provider build was completed before starting native validation.
This is a build orchestration failure, not a passing utility run. The final
provider configuration/build logs are retained separately.

## Remaining ownership

[CSH-101](../../tickets/CSH-101-filesystem-environment-residuals.md)
([#213](https://github.com/melliott18/cshell/issues/213)) owns all 21 utility
residuals and four original U-040 conditions, with explicit environments,
reasons and utility/libc/platform implementation ownership. This uses CSH-100's
explicit-disposition alternative; it does not qualify whole utilities or
complete U-034/U-040.
