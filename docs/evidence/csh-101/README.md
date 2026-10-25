# CSH-101 explicit transition clocks and daylight offsets

Collected 2026-10-25 in a separate worktree based on CSH-100 commit `4bd700f`.
Integration remains gated on that unmerged dependency.

## Scope and independent oracle

Issue 8 [touch](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html)
OPTIONS and ENVIRONMENT VARIABLES specify local -d/-t interpretation and timestamp
field selection. [XBD chapter 8](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html#tag_08)
defines the signs and minute/second components of TZ offsets, transition clocks
in the local time before the change, and negative or greater-than-24-hour clocks.
`normative-sources.json` records direct HTTPS source hashes; the web reader returned 403.

`tests/host_filesystem_transition_times.py` supplies 96 cases, each run by direct
exec and cshell string/file/stdin dispatch: 384 assertions per platform. Twelve
unique local times have both -d and -t spellings and default, access-only,
modification-only and explicit-both field selections.

| Explicit TZ | Authored distinction |
| --- | --- |
| `WST3:30:15WDT2:45:05,M3.2.0/1:15:20,M11.1.0/3:40:50` | West offsets with seconds; a 45m10s advance; transition clocks with seconds. |
| `EST-5:45:30EDT-6:15:45,J60/0:10:15,J300/23:50:40` | East offsets with seconds; a 30m15s advance; leap-day UTC rollover. |
| `NST0NDT-0:30,59/-1:30,299/26:15` | Leap-year day 59 transition on the previous day; day 299 transition on the next day. |

Expected UTC calendar fields are authored separately from local input strings.
Integer Gregorian subtraction supplies Epoch nanoseconds. Literal Epoch values
and independent elapsed-time checks in the harness regression catch offset
signs and rollover mistakes. No provider result, timezone database, local date
parser, mktime, live clock, or floating-point timestamp supplies the oracle.
Samples before fallback precede the repeated interval. Skipped/repeated local
times have no expected conversion here.

The existing target-inode setup probes exact expected timestamps, restores
distinct fractional baseline fields, and reads them back. Failed or rounded
setup fails before execution. Metadata is captured before content reads;
both fields, identity, mode, link count, contents, channels and status must
agree. Four new harness regressions cover exact boundary values, incorrect
results, failed/rounded setup, and failed-exec/timeout cleanup in every mode.
All previous expected assertions are preserved.

## Provider repair and stock evidence

The original Apple touch and installed GNU touch on macOS both used host
conversion that produced incorrect timestamps for the authored negative and
next-day transition clocks. The initial strict selected check failed 64 of
384 assertions; these remain failures in the stock audit. Linux's original
provider passed all 384. No expected timestamp or allowed-result set was changed.

Both selected profiles now use GNU coreutils 9.7 touch linked directly to
unmodified IANA tzcode 2025b conversion code. Selecting GNU touch alone on Darwin
is insufficient. The build pins and checks both source archives, records compiler
and linker commands, and records provider/archive/build-script hashes in the
manifest. See [provider provenance](../../../tools/host-profile/vendor/tzcode/README.md).
No wrapper transforms arguments, output, status, environment or expected results.
The optional IANA NetBSD API is disabled because gnulib supplies its own *_z API.
System utilities and timezone databases are unchanged; no shell runtime source changes.

These are private ordinary files with representable timestamps. No privileged
provisioning, libc fault injection, kernel fault, or filesystem exhaustion is
involved. Arbitrary rules/offsets, skipped/repeated times, geographical timezone
databases, unsupported ranges, creation/current clocks, races and permission/ACL
boundaries remain unqualified.

## Results

Native macOS 14.8.7 arm64 UID 501 and Debian 12 arm64 Docker UID 10001 pass
every required selected target. All 384 new assertions pass with zero allowances;
selected filesystem totals are 3499/0 and 3539/0. The general host profile passes
1162 assertions on each platform. All 10 ownership and 104 filesystem harness
tests pass. The independent verifier confirms every prior authored expectation,
all setup/cleanup records, selected provider identities and matching source inputs.

Both platforms also pass 3950 runtime cases, 33 runtime PTY cases, and the
93-test harness run under the profile PATH. Linux skips one Darwin-only libproc
ABI test; native macOS runs it. All 384 focused ASan/UBSan conversion assertions
pass per platform. No whole-provider sanitizer or hosted-CI result is claimed.

Stock full/provider audits remain nonzero: native 137/16 failures and Linux
42/8 failures. Native adds exactly the 64 specified timestamp failures to the
previous 73; every old stock failure is preserved. These are not allowances.

| Target/report | macOS pass/fail | Linux pass/fail |
| --- | --- | --- |
| host-filesystem-allocation | 240 / 0 | 200 / 0 |
| host-filesystem-audit | 3342 / 137 | 3473 / 42 |
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
| host-filesystem-profile | 3499 / 0 | 3539 / 0 |
| host-filesystem-provider-audit | 168 / 0 | 184 / 0 |
| host-filesystem-recursive | 30 / 0 | 30 / 0 |
| host-filesystem-reference | 112 / 0 | 112 / 0 |
| host-filesystem-residual | 104 / 0 | 104 / 0 |
| host-filesystem-stock-provider-audit | 152 / 16 | 176 / 8 |
| host-filesystem-timezone | 416 / 0 | 416 / 0 |
| host-filesystem-transition-times | 384 / 0 | 384 / 0 |
| host-profile-results | 1162 / 0 | 1162 / 0 |

Final build/test source digest: `8ba148843eb3250813426105157d36049863d8da3208418f02fa29e7e59e0288`.

## Validation and reproduction

```sh
# PATH must provide gtest, g[, gfind and gdd. Complete the build first.
make -j4 cshell host-profile
python3 docs/evidence/csh-101/validate.py native
python3 docs/evidence/csh-101/supplement.py native

docker build -f docs/evidence/csh-101/Dockerfile.linux -t cshell-test:csh-101 .
docker create --init --name cshell-csh101-validation cshell-test:csh-101 \
  sh -c 'python3 docs/evidence/csh-101/validate.py linux && python3 docs/evidence/csh-101/supplement.py linux'
docker start -a cshell-csh101-validation
docker cp cshell-csh101-validation:/work/build/csh101-validation ./build/csh101-linux-results
docker cp cshell-csh101-validation:/work/build/csh101-supplement ./build/csh101-linux-supplement
docker cp cshell-csh101-validation:/work/build/csh101-sanitizer ./build/csh101-linux-sanitizer
docker rm cshell-csh101-validation

# Retain native/Linux records here before verification.
python3 docs/evidence/csh-101/verify.py
```

`validate.py` runs every required ticket target plus the new transition-times
target, then separate stock full/provider audits. Expected statuses are 0, 2
and 1. `supplement.py` runs runtime, runtime PTY and harness checks with the
profile PATH, then a focused sanitizer check. `sanitize.py` instruments the newly
linked IANA localtime.c with ASan/UBSan; GNU touch/gnulib objects and cshell are
regular builds. This does not claim whole-provider sanitizer coverage.

`verify.py` compares every previous selected assertion and exact expected value
(only per-run inode observations may differ), precisely 384 new passing
assertions, armed inode probes, effects, empty channels, zero status, cleanup,
provider/manifest agreement and one build/test source digest across platforms.
All prior stock failure IDs/modes must remain; only the 64 specified new native
stock failures may be added. `SHA256SUMS` covers retained artifacts except this
narrative and itself. Historical evidence is unchanged.

## Retained development failures

The initial stock and selected native transition reports retain the 64 incorrect
timestamp results. `native-link.log.gz` records an exploratory link attempt
that overlapped a recursive configure launched by Make's dry-run/remake behavior;
that build failed before new provider execution. The owned exploratory processes
were stopped and the shared build directories replaced with a clean build. A
subsequent forced rebuild was canceled to prevent inherited Make flags from
repeating this work; its partial log is retained.

The first production touch build incorrectly used Make's `-W` option before
compiling touch.o, so a clean build attempted to link a missing object. The
native log and first replacement Linux command records retain that failure.
The corrected build explicitly compiles the object before forcing the relink.
The first sanitizer driver sent only direct exec to the instrumented binary;
its shell modes accidentally used the stock PATH and reproduced 48 native
failures. The initial report is retained. The corrected driver prepends the
instrumented provider directory for every mode, and the focused check is rerun.

An earlier complete Linux run against the original provider is retained as
initial evidence, separate from final replacement-provider results.

The final Linux run reuses the completed GNU build from the failed replacement
container via the documented optional `BASE_IMAGE` argument. Final source and
provider hashes are checked independently. The corrected sanitizer driver was copied into the final container before
the supplemental run; its retained hash identifies the executed source.
The default Dockerfile base remains the CSH-100 image; no host mounts or privileged fixture identity are used.

## Remaining ownership

[CSH-102](../../tickets/CSH-102-filesystem-environment-residuals.md)
([#215](https://github.com/melliott18/cshell/issues/215)) owns all 21 utility
residuals and four original U-040 conditions, with explicit environments,
reasons and utility/libc/platform implementation ownership. This uses CSH-101's
explicit-disposition alternative; it does not qualify whole utilities or
complete U-034/U-040. The compliance gate remains closed.
