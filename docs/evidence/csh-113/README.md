# CSH-113 touch creation and current-time qualification

This increment adds 60 authored cases, required in direct execution and cshell
string/file/stdin modes (240 assertions). The worktree is stacked on CSH-112
commit `636cdb8`; integration remains gated on that open dependency. Runtime,
selected providers and vendor sources are unchanged.

## Contract and oracle

The [touch specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html)
requires creation with mode 0666 modified by the creation mask, current time
when no time source is specified, selective access/modification updates, and
silent `-c` handling of absent operands. The normative HTML retained by CSH-112
was read locally; its SHA-256 matches the current section map and the copied
source record. No new successful network retrieval is claimed.

Five boundaries cover default, `-a`, `-m` and explicit `-a -m` selections under
child-only umasks 027, 077 and 777:

- Current-time updates to an existing middle file.
- Current-time creation of an absent middle file.
- Silent no-create handling of an absent middle file.
- Creation with authored UTC time `200109090146.40`.
- Creation using distinct fractional access and modification reference times.

Accessible first and last files require continued processing in every case.
All existing files start with independently read-back, distinct fractional
baselines and mode 0640. Fixed times and reference times are authored integer
nanoseconds; the utility never supplies its own expected values. The reference
file's timestamps, contents and identity must remain unchanged. Existing files
retain inode/device, mode, size, link count and bytes. Newly created files must
be empty regular files, with one link and literal modes 0640, 0600 or 0000.
Checking zero length establishes empty contents without opening mode-000 files.

The helper sets only its own umask and independently creates a regular file
with mode 0666, checks its actual mode and removes it before exact-provider
exec. A missing, malformed, wrong-provider, wrong-identity, wrong-mask or
failed setup/exec record fails the assertion. A setup error cannot masquerade
as a utility result. These helper-dispatched cases do not independently qualify
bare-name PATH lookup.

Realtime and monotonic clocks bracket capture. Selected current-time fields
and unselected fields of newly created files must lie between the realtime
start rounded down to a whole second and the observed realtime end. The floor
explicitly allows up to one second of timestamp truncation: these are bounded
seconds-resolution witnesses, not subsecond accuracy claims. Negative intervals
or a realtime/monotonic elapsed-time discrepancy exceeding one second fail.
This guard does not prove the absence of smaller or offsetting clock changes.
Preserved fields on existing files and selected fixed/reference fields require
exact nanoseconds. Snapshots precede content reads that could change atime.

All cases require empty stdout/stderr, zero status and complete fixture cleanup.
Harness regressions cover every case/mode, corrupted timestamps and metadata,
channels/status, missing/invalid dispatch records, invalid clock intervals,
unproved timestamps/masks, partial setup, failed exec and timeout/reaping. The
failure path retains capture diagnostics even when creation never occurred.

## Scope and remaining owners

The 21 utility dispositions and four original U-040 conditions stay individually
open under [CSH-114](../../tickets/CSH-114-filesystem-environment-residuals.md).
That follow-up is recorded locally with GitHub allocation pending. Utility,
libc and platform vendors retain implementation ownership. No ACLs, alternate
identities, clock changes, arbitrary graphs/races, libc fault injection or
filesystem exhaustion are supplied. U-034/U-040 remain partial and historical
evidence is unchanged.

## Reproduction

```sh
# Provisioning requires GNU gfind and coreutils on PATH on native macOS.
make -j4 cshell host-profile
python3 docs/evidence/csh-113/validate.py native

docker build -f docs/evidence/csh-113/Dockerfile.linux -t cshell-test:csh-113 .
docker run --init --name cshell-csh113-validation cshell-test:csh-113 \
  python3 docs/evidence/csh-113/validate.py linux
docker cp cshell-csh113-validation:/work/build/csh113-validation ./build/csh113-linux-results
# Copy both platform result directories here before verification.
python3 docs/evidence/csh-113/verify.py
docker rm cshell-csh113-validation
```

The Linux image layers the changed files on the retained CSH-112 image and runs
as its unprivileged fixture identity. This is Linux/Docker evidence, not a
separate hosted native-Linux run. Native provisioning uses a local copy of the
same CSH-112 `gfind` executable. Build/configuration and exact provider/source
identities are retained by platform. No new sanitizer/general-runtime sweep is
claimed.

## Validation

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12331 pass, 0 fail | 12371 pass, 0 fail |
| New creation/current-time assertions | 240 pass | 240 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 159 pass | 10 / 159 pass |
| Stock full / provider failures | 749 / 16 retained | 578 / 8 retained |

Every ticket-listed selected target passes with zero allowances. Separate stock
full and provider audits retain their failure records; the verifier compares
them against CSH-112. Raw commands, exit statuses, timings and output are
retained by platform. The verifier requires unchanged predecessor expectations,
exactly 240 new assertions, current source identities, exact provider/build
provenance, independent clock/mask/timestamp records and complete cleanup.

`python3 docs/evidence/csh-113/verify.py` passes all comparisons. Its retained
outputs are `summary.json` and `stock-failure-comparison.json`. Both platforms
record selected/stock-full/stock-provider command statuses `[0, 2, 1]`.
