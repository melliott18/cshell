# CSH-096 calendar timestamp evidence

Collected 2026-10-20 in a separate worktree based on CSH-095 commit
`4f8cd29fb2f00ed78b374cd2822f584e715b99e1`. Integration remains gated on that unmerged dependency.

## Scope and independent oracle

Issue 8 [touch](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html)
DESCRIPTION and OPTIONS define timestamp changes, two-digit century inference,
default seconds, second-60 rollover, and field selection. ENVIRONMENT VARIABLES
specifies TZ; STDOUT, STDERR and EXIT STATUS define the channel/status contract.
`normative-sources.json` records the retrieved page hash (direct HTTPS retrieval
after the web reader returned 403).

`tests/host_filesystem_calendar.py` supplies 40 cases, each run by direct exec
and cshell string/file/stdin dispatch: 160 assertions per platform. Ten authored
dates cover the Epoch, inferred years 70/99/00/68, omitted seconds, leap day,
second-60 rollover into a new year, January 2038 and the signed-32-bit timestamp
boundary. Each uses default, access-only, modification-only and explicit-both
field selection. UTC0 is fixed; the suite never consults the current year.

Integer Gregorian datetime subtraction supplies expected seconds independently
of touch, libc date parsing, floating-point timestamps and the local timezone.
Before execution, Python sets and reads back the exact target timestamps on the
private target inode, then sets and reads back unequal fractional baselines.
Unrepresentable values or setup errors fail before provider execution. Records
retain requested/observed timestamps, inode/device, exact arguments, provider
hashes, channels, status, content, effects and cleanup. Assertions require both
timestamp fields exactly, including the unselected field, empty stdout/stderr,
status zero, and unchanged nonempty file contents. Metadata is captured before
content reads can change atime.

Dates after January 2038 qualify the selected provider/filesystem capability;
they do not assert that every POSIX implementation supports that range. The
suite does not exercise pre-Epoch policy, current-clock tolerances, DST, arbitrary
dates, unsupported-range errors, permission/ACL failures or symlink graphs.
These are ordinary private regular-file environments; no allocation injection,
kernel error injection, filesystem exhaustion or privileged provisioning occurs.

Four harness regressions check independently fixed epoch/century values,
corrupt timestamps/content/channels/status, failed or rounded target/baseline
setup, and failed exec/timeout cleanup in every invocation mode. The initial
harness run preceded the clause-map update and failed only its complete-inventory
check; its log is retained separately. All older assertions remain required.

## Results

Every required selected target passed on native macOS 14.8.7 arm64 UID 501 and
Debian 12 arm64 Docker UID 10001. Each run includes 10 ownership tests and 84
filesystem harness tests. Stock failures match the retained CSH-095 IDs/modes
exactly; selected profiles have no allowances.

| Profile/target | macOS | Linux |
| --- | --- | --- |
| Host integration | 1162 pass, 0 fail | 1162 pass, 0 fail |
| Selected filesystem profile | 1819 pass, 0 fail | 1859 pass, 0 fail |
| Allocation faults | 240 pass, 0 fail | 200 pass, 0 fail |
| Selected provider audit | 168 pass, 0 fail | 184 pass, 0 fail |
| Private residual environments | 104 pass, 0 fail | 104 pass, 0 fail |
| Isolated environments | 112 pass, 0 fail | 112 pass, 0 fail |
| Owned terminal overwrites | 39 pass, 0 fail | 39 pass, 0 fail |
| Operand/recursive decisions | 68 pass, 0 fail | 68 pass, 0 fail |
| Metadata/timestamps | 64 pass, 0 fail | 64 pass, 0 fail |
| Recursive prompts | 30 pass, 0 fail | 30 pass, 0 fail |
| Pathname limits | 32 pass, 0 fail | 32 pass, 0 fail |
| Physical cwd | 32 pass, 0 fail | 32 pass, 0 fail |
| Creation modes | 104 pass, 0 fail | 104 pass, 0 fail |
| Output errors | 32 pass, 0 fail | 56 pass, 0 fail |
| Logical cwd fallback | 48 pass, 0 fail | 48 pass, 0 fail |
| Numeric magic | 184 pass, 0 fail | 184 pass, 0 fail |
| New calendar timestamps | 160 pass, 0 fail | 160 pass, 0 fail |
| Stock full audit | 1726 pass, 73 fail | 1793 pass, 42 fail |
| Stock provider audit | 152 pass, 16 fail | 176 pass, 8 fail |

Final source identity: `c131a7acd2772416444ba8e5560983dce4b1513be094bc5301a53e3d71092ec3`. The retained reports
and current build/test inputs have the same digest on both hosts.

## Validation and reproduction

```sh
# Native PATH must provide gtest, g[, gfind and gdd.
make -j4 cshell host-profile
python3 docs/evidence/csh-096/validate.py native

docker build -f docs/evidence/csh-096/Dockerfile.linux -t cshell-test:csh-096 .
docker create --init --name cshell-csh096-validation cshell-test:csh-096 \
  python3 docs/evidence/csh-096/validate.py linux
docker start -a cshell-csh096-validation
docker cp cshell-csh096-validation:/work/build/csh096-validation ./build/csh096-linux-results
docker rm cshell-csh096-validation

python3 docs/evidence/csh-096/verify.py
```

`validate.py` runs every ticket-required target plus the calendar target. It
retains nonzero stock full and provider audits separately, requiring command
statuses 0, 2 and 1. `verify.py` checks prior selected IDs/modes, exactly 160 new
passing assertions, armed timestamp probes, exact fields and channels, unchanged
stock failure IDs/modes, cleanup, and one final source digest across hosts.
`summary.json` records final totals; command logs and provider manifests retain
full diagnostics and build identities. `SHA256SUMS` covers retained artifacts
other than this narrative.

Native qualification uses an unprivileged macOS identity; the gfind executable
was copied from CSH-095's ignored build and other local providers were rebuilt
from pinned sources. Linux uses the recorded CSH-095 Debian image with the final
test/tool overlay, Docker `--init`, UID 10001 and no host mounts. No provider
implementation, build flag or selected-profile allowance changes. No sanitizer
or hosted-CI qualification is claimed.

## Remaining ownership

[CSH-097](../../tickets/CSH-097-filesystem-environment-residuals.md)
([#205](https://github.com/melliott18/cshell/issues/205)) retains all 21 utility
residuals with explicit environments, reasons and utility/libc/platform
implementation ownership. All four original U-040 conditions remain open.
Historical evidence and stock failures are preserved. This uses the ticket's
explicit-disposition alternative; no whole utility or U-034/U-040 completion
is claimed.
