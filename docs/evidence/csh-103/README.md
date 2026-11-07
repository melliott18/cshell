# CSH-103 magic message formatting and selected file provider

Implemented on 2026-10-27 in a separate worktree based on CSH-102 commit
`6cb5db4`, branch `test/CSH-103-filesystem-environments`. Integration remains
conditional on the CSH-102 dependency.

## Scope and independent oracle

Issue 8 [file](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html)
EXTENDED DESCRIPTION specifies printf-style message rendering using the value
from the matched input. STDOUT, STDERR and EXIT STATUS supply the channel and
status requirements. `normative-sources.json` retains the retrieved source hash;
the web reader returned 403 and direct HTTPS retrieval succeeded.

`tests/host_filesystem_magic_messages.py` supplies 108 cases, each executed
directly and through cshell string/file/stdin dispatch: 432 assertions per
platform. Twenty-two numeric descriptions are applied to native signed byte and
short inputs, and ten descriptions to a string with extra trailing bytes.
Every description is tested at top level and as a continuation. Literal
expected bytes cover signs, field widths, precision, zero padding, decimal,
octal and hexadecimal conversions, alternate forms, character conversion and
literal percent signs. Brackets expose padding and empty conversions. String
arguments must contain the matched value without the trailing input bytes.
Unsigned conversions use only nonnegative values representable as signed int.

No formatter, provider output, default classifier or escape decoder generates
the expected descriptions. Independently packed native numeric values, literal
string bytes, setup readback, exact channels/status and unchanged input contents
supply the oracle. The existing byte/short ABI check is reused. No privileged
credentials, fault injection, mounts or filesystem exhaustion are introduced.

Four harness regressions check independent arguments, reject changed channels,
status and inputs, reject corrupt setup before execution, and exercise failed
exec/timeout cleanup in all four dispatch modes. Fourteen selected-provider
regressions separately require rejection of malformed, extra-argument,
wrong-type, pointer-write and oversized numeric formats, with bounded capture
and cleanup. These negative inputs are validator regression checks, not positive
POSIX qualification cases.

## Selected provider and retained failures

The opt-in profile now selects pinned file 5.46 and statically linked libmagic.
The release archive, license, checksum and local patch are in
[`tools/host-profile/vendor/file`](../../../tools/host-profile/vendor/file/README.md).
The repair lets one-byte files reach custom magic tests, accepts plus/space
flags and promoted short character arguments, and counts literal percent pairs
without treating them as additional arguments. Textual rule databases preserve
source order; compiled system databases retain vendor ranking. The existing
single-argument, type and numeric width/precision checks remain enforced.

Builds verify the pinned archive and run offline. Source, patch, build-script,
executable and matching compiled default database hashes are in the profile
manifest. Configure/build logs are retained per platform. System installations
are untouched; no wrapper rewrites output or exit status.

Apple/Linux stock audits remain separate from selected results. Unpatched
file 5.46 is also built and tested separately for message rendering and the
existing numeric/precedence suite. None of these failures become allowances.
Focused ASan/UBSan builds instrument file/libmagic, run the new 432 assertions,
the existing 184 numeric assertions and 364 string assertions, and repeat the
14 malformed-format regressions. cshell and the other providers in those runs
are regular builds; this is not whole-project sanitizer coverage.

## Reproduction

```sh
# Native PATH must supply gtest, g[, gfind and gdd.
make -j4 cshell host-profile
python3 docs/evidence/csh-103/validate.py native
python3 docs/evidence/csh-103/supplement.py native
python3 docs/evidence/csh-103/provider_checks.py native

# Reuse the preceding unprivileged provider image; no host mounts are exposed.
docker build -f docs/evidence/csh-103/Dockerfile.linux -t cshell-test:csh-103 .
docker create --init --name cshell-csh103-validation cshell-test:csh-103 \
  sh -c 'python3 docs/evidence/csh-103/validate.py linux && python3 docs/evidence/csh-103/supplement.py linux && python3 docs/evidence/csh-103/provider_checks.py linux'
docker start -a cshell-csh103-validation
docker cp cshell-csh103-validation:/work/build/csh103-validation ./build/csh103-linux-results
docker cp cshell-csh103-validation:/work/build/csh103-supplement ./build/csh103-linux-supplement
docker cp cshell-csh103-validation:/work/build/csh103-provider-checks ./build/csh103-linux-provider-checks
docker rm cshell-csh103-validation

# Retain the reports and logs here, then verify their content and source identity.
python3 docs/evidence/csh-103/verify.py
```

`validate.py` runs every required selected target and the new focused target,
then stock full/provider audits (expected command statuses 0, 2 and 1).
`supplement.py` runs runtime, terminal and harness suites with the selected PATH,
then the format validator regressions. `provider_checks.py` records unpatched
failures and focused sanitizer runs. `verify.py` requires every previous
expectation unchanged except independently measured inode facts, exact new
assertions, retained prior stock failure IDs, clean teardown, provider/build
provenance and one current source identity across platforms.

## Development record

The first provider passed all new assertions but failed eight existing
CSH-095 precedence assertions on each platform. file 5.46 ranks tied tests by
entry contents, allowing the second source rule to win. The initial selected
reports and failed sanitizer numeric run remain in `development/`. The final
patch preserves textual rule order; all original expectations stay unchanged.
The final validation reruns the complete required target list after that repair.

Native GNU find is copied unchanged from the CSH-102 worktree; its exact source,
destination and hash are recorded in `native-find-provenance.json`. Remaining
native providers are built here from pinned sources. Linux uses unprivileged
UID 10001 in the private Docker container. Development smoke runs using `/bin/sh`
are not substituted for final cshell qualification.

## Remaining ownership

[CSH-104](../../tickets/CSH-104-filesystem-environment-residuals.md)
([#219](https://github.com/melliott18/cshell/issues/219)) retains every one of the
21 utility residual rows and the four original U-040 conditions. Other numeric
types/widths, unsigned ranges, arbitrary formats, database precedence, default
classification, encodings/locales and utility resource failures remain open.
Utility/libc/platform vendors retain implementation ownership. U-034/U-040
remain partial; neither whole-utility qualification nor POSIX compliance is
claimed. Historical evidence is unchanged. No hosted-CI result is claimed.

## Final results

Native macOS and unprivileged Linux/Docker pass every ticket-required selected
target with zero allowances: **4,295 / 4,335** full filesystem assertions,
including all **432** new assertions per platform. Both general host profiles
pass **1,162** assertions with zero gaps. Both pass **10** ownership and **112**
filesystem harness tests, **3,950** runtime cases, **33** terminal cases and the
**93-test** harness suite (one Darwin-only test skipped on Linux).

Each platform passes **980** focused file/libmagic ASan/UBSan assertions and
**14** format-validator checks in both regular and sanitizer builds. Unpatched
file 5.46 retains **140** new message failures and **8** old precedence failures.
Stock full/provider failures remain separately recorded: **277 / 16** on macOS
and **182 / 8** on Linux. Each full audit preserves every earlier failure and
adds exactly 140 message failures; no earlier failure disappears.

The retained verifier passes exact prior/new expectations, clean teardown,
provider provenance, sanitizer build flags and current source identity
`22b1ae0f897628a22f9c8c22c437ec5a93ac3f74a5ad9fe84782ebbd2d11fa65`.
`SHA256SUMS` covers retained files except this narrative and the checksum file
itself. Final platform records are shown below.

| Target/report | macOS pass/fail | Linux pass/fail |
| --- | --- | --- |
| host-filesystem-allocation | 240 / 0 | 200 / 0 |
| host-filesystem-audit | 3998 / 277 | 4129 / 182 |
| host-filesystem-calendar | 160 / 0 | 160 / 0 |
| host-filesystem-creation | 104 / 0 | 104 / 0 |
| host-filesystem-cwd-logical | 48 / 0 | 48 / 0 |
| host-filesystem-cwd | 32 / 0 | 32 / 0 |
| host-filesystem-datetime | 256 / 0 | 256 / 0 |
| host-filesystem-day-rules | 512 / 0 | 512 / 0 |
| host-filesystem-decisions | 68 / 0 | 68 / 0 |
| host-filesystem-interactive | 39 / 0 | 39 / 0 |
| host-filesystem-isolated | 112 / 0 | 112 / 0 |
| host-filesystem-magic-messages | 432 / 0 | 432 / 0 |
| host-filesystem-magic-strings | 364 / 0 | 364 / 0 |
| host-filesystem-magic | 184 / 0 | 184 / 0 |
| host-filesystem-metadata | 64 / 0 | 64 / 0 |
| host-filesystem-output | 32 / 0 | 56 / 0 |
| host-filesystem-path-limits | 32 / 0 | 32 / 0 |
| host-filesystem-profile | 4295 / 0 | 4335 / 0 |
| host-filesystem-provider-audit | 168 / 0 | 184 / 0 |
| host-filesystem-recursive | 30 / 0 | 30 / 0 |
| host-filesystem-reference | 112 / 0 | 112 / 0 |
| host-filesystem-residual | 104 / 0 | 104 / 0 |
| host-filesystem-stock-provider-audit | 152 / 16 | 176 / 8 |
| host-filesystem-timezone | 416 / 0 | 416 / 0 |
| host-filesystem-transition-times | 384 / 0 | 384 / 0 |
| host-profile-results | 1162 / 0 | 1162 / 0 |
