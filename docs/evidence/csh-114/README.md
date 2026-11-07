# CSH-114 touch object and namespace qualification

This increment adds 28 authored cases in direct execution and cshell
string/file/stdin modes (112 assertions). It is stacked on a local snapshot
`e1c6ecb` of the CSH-113 worktree, whose committed parent was CSH-112 `636cdb8`.
The original worktrees were left untouched. Integration remains gated on these
open dependencies. Shell/runtime and selected provider sources are unchanged.

## Contract and independent oracle

The [touch specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html)
DESCRIPTION specifies an existing-file operation equivalent to `utimensat` with
flags zero. OPTIONS defines selective access/modification updates, and EXIT
STATUS distinguishes successful changes from errors. The same normative HTML
used by CSH-112/113 was read locally and its SHA-256 checked against the section
map and `normative-source.json`. A new network retrieval returned HTTP 403;
no successful fresh retrieval is claimed.

Seven boundaries cover default, `-a`, `-m` and explicit `-a -m` selections:

- Existing directories addressed directly or through a two-link symlink chain.
- Existing FIFOs addressed directly, by a hard link or through a symlink chain.
- A regular-file prefix that produces kernel ENOTDIR.
- A two-link cycle that produces kernel ELOOP.

All cases process accessible files before and after the middle operand, so
continued processing and earlier effects are checked independently of the
nonzero error status. The directory contains a regular child that must retain
its bytes, identity, permissions and timestamps. An unrelated regular obstruction
and both alias/cycle graphs also remain intact.

Python constructs each private fixture. Before execution, `os.utime` and stat
readback prove that the actual regular-file, directory and FIFO inodes can
represent both the authored UTC target and distinct fractional baselines.
Alias resolution must lead to the intended inode. On error cases, an independent
stat must yield exactly the authored kernel error before provider execution and
again afterward. ELOOP's numeric value differs on Darwin and Linux; this is
recorded separately. No faults are injected into the utility or libc.

A child helper records the exact provider and credentials and replaces itself
with that provider. Failed exec, missing/malformed records and identity changes
fail the assertion. These helper-dispatched cases do not independently qualify
bare-name PATH lookup. The fixture requires one unprivileged identity.

Snapshots precede content reads or directory enumeration that could change
access times. Selected fields require exact authored nanoseconds, and unselected
fields preserve their distinct baselines. Inodes, modes, sizes and link counts
must remain unchanged. Directory children and symlink texts are checked;
symlink modification times persist, while symlink access times are not asserted
because resolution can update them. FIFOs are never opened or used for transfer.
Successful cases require empty stdout/stderr and zero status; namespace failures
require empty stdout, a diagnostic and nonzero status.

Six harness tests exercise the complete case/mode matrix, timestamp/metadata/
content/channel corruption, missing/invalid exec markers, wrong kernel probes,
unrepresentable timestamps, partial setup, failed exec, timeout/reaping and
symlink-safe cleanup. The initial corruption test exposed a cleanup failure
when a provider removed directory search permission. The failed observation is
retained under `development/`; cleanup now restores only the owned directory,
using lstat to avoid following a replacement link.

## Remaining scope and ownership

All 21 utility dispositions and four original U-040 conditions remain open
under [CSH-115](../../tickets/CSH-115-filesystem-environment-residuals.md), recorded
locally with GitHub allocation pending. Vendor implementation ownership stays
unchanged. No other identities, ACLs, arbitrary graphs, races, devices, clock
changes, filesystem capacity limits or resource exhaustion are supplied.
U-034/U-040 remain partial and historical evidence is unchanged.

## Reproduction

```sh
# Native provisioning requires GNU gfind and coreutils on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-114/validate.py native

docker build -f docs/evidence/csh-114/Dockerfile.linux -t cshell-test:csh-114 .
docker run --init --name cshell-csh114-validation cshell-test:csh-114 \
  python3 docs/evidence/csh-114/validate.py linux
docker cp cshell-csh114-validation:/work/build/csh114-validation ./build/csh114-linux-results
# Copy both platform result directories here before verification.
python3 docs/evidence/csh-114/verify.py
docker rm cshell-csh114-validation
```

The Linux image layers the changed files on retained `cshell-test:csh-113` and
runs as its unprivileged fixture identity. This is Linux/Docker evidence, not a
separately hosted native-Linux run. Native provisioning uses a local copy of
the same CSH-113 `gfind` executable. Exact source, binary, provider, build and
platform identities are retained with the results. No new sanitizer or general
shell-runtime sweep is claimed because production C is unchanged.

## Validation

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12443 pass, 0 fail | 12483 pass, 0 fail |
| New object/namespace assertions | 112 pass | 112 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 165 pass | 10 / 165 pass |
| Stock full / provider failures | 749 / 16 retained | 578 / 8 retained |

Every ticket-listed selected target passes with zero allowances. Both platforms
record selected/stock-full/stock-provider command statuses `[0, 2, 1]`.
`python3 docs/evidence/csh-114/verify.py` passes unchanged predecessor expectation,
exactly 112 new assertions, independent setup/effect, complete cleanup, current
source identity and exact provider provenance comparisons. The stock failure
sets exactly match CSH-113. Retained outputs are `summary.json` and
`stock-failure-comparison.json`; platform records contain all commands, statuses,
timings, output and identities.
