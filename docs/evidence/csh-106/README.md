# CSH-106 opaque symbolic-link byte qualification

This change supplies 1088 independently authored readlink cases, required in
native direct execution and cshell string/file/stdin modes (4352 assertions).
It is stacked on CSH-105 commit `626e514`; integration remains gated on that
dependency. No selected-profile allowances are introduced.

## Contract and independent oracle

[POSIX readlink DESCRIPTION and OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/readlink.html)
require the link contents without following the link, followed by a newline
unless `-n` is present. Every expected byte comes from the authored target,
not provider output. Each byte from 1 through 255 appears in its own target.
Additional targets cover valid two/three/four-byte UTF-8 boundaries, composed
and decomposed text, overlong encodings, surrogates, out-of-range code points,
truncated sequences, embedded newlines, and shell metacharacters. Seven mixed
byte targets have lengths 255, 256, 257, 511, 512, 513 and 1023. Each is tested
in C and an installed UTF-8 locale, with and without `-n`.

Before execution, byte-path lstat/readlink probes establish that the private
filesystem stored exactly the intended bytes. These probes are setup evidence;
they do not supply the output oracle. After execution, link device/inode, mode,
size and target bytes must match the pre-exec observation. Access times are
not required to remain unchanged. Exact stdout, empty stderr, zero status,
provider identity and fixture cleanup are mandatory in all four modes.

The four new harness regressions check case completeness, reject altered
channels/status and changed/replaced/non-link/missing fixtures, require setup
failures to prevent execution, and prove cleanup after missing interpreters
and timed-out children in all modes. Missing UTF-8 capability fails setup.

No shell or provider C code changed. These are finite byte and sequence
witnesses, not arbitrary encoding or filesystem-limit qualification. NUL is
not a possible symlink-content byte. The authored sizes do not assert a maximum
supported length. No mounts, privileges, capacity exhaustion, kernel faults,
libc fault injection or namespace races are supplied. All 21 individual utility
dispositions and four original U-040 conditions remain open under
[CSH-107](../../tickets/CSH-107-filesystem-environment-residuals.md) ([#225](https://github.com/melliott18/cshell/issues/225)).
U-034/U-040 remain partial; utility/libc/platform vendors retain implementation ownership.

## New stock-provider failure

The macOS stock readlink omits the required additional newline when the
stored link target already ends in newline. The authored `absent/\n\r\n\n`
target must produce `absent/\n\r\n\n\n` without `-n`; stock output is the target
alone. Both C/UTF-8 locales and all four modes fail (eight assertions).
The selected host-paths provider passes; Linux stock also passes. This adds
eight native stock failures while retaining all previous ones, with no allowance.

## Validation

| Check | macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 11207 pass, 0 fail | 11247 pass, 0 fail |
| New link-byte assertions | 4352 pass | 4352 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 124 pass | 10 / 124 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Harness suite | 93 pass | 93 pass, one Darwin-only skip |
| Stock full / provider audit failures | 689 / 16 retained | 578 / 8 retained |
| Regular format / compiled-database checks | 14 / 5 pass | 14 / 5 pass |

Final counts and source identities are recorded in `summary.json` and checked
by `verify.py`. The verifier requires every CSH-105 selected expectation and
stock failure to remain, exact new oracles, matching source/provider identities,
and successful cleanup. Per-run inode identities are compared within each run.
All original CSH-064 evidence and all prior retained reports remain unchanged.

Native means macOS; Linux runs as the unprivileged cshell user in a Debian
Docker container. No hosted native-Linux or sanitizer run is claimed. The
provider sources are unchanged; exact hashes, compiler/build information,
channels/status/effects, setup and cleanup are retained with each platform's
reports. The regular provider format and compiled-database checks also run.

Two initial native provider builds overlapped. Both owned process trees were
stopped, their coreutils directories set aside, and a fresh build started before
qualification. Their logs are retained under `development/`; they are not passing
evidence. A preliminary inventory run caught the not-yet-updated human-readable
ownership table; the final inventory requires all 21 rows to point to CSH-107.
The preliminary focused native probe passed all 4352 new assertions, then the
complete matrix was run. A final review added the new case IDs to the residual
ledger and a consistency assertion. `refresh.py` reruns inventory/harness checks
and any early reports with an older source digest.
The first Linux refresh detected additional stale focused reports and stopped;
its nonzero result is retained. The resumed refresh reruns every stale report,
including the complete profile, and requires the same strict expected statuses.
Those earlier reports remain under `development/`; all final reports must match
the final build/test inputs.

## Reproduction

```sh
# Provision gtest, g[, gfind and gdd on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-106/validate.py native
python3 docs/evidence/csh-106/supplement.py native

docker build -f docs/evidence/csh-106/Dockerfile.linux -t cshell-test:csh-106 .
docker create --init --name cshell-csh106-validation cshell-test:csh-106 \
  sh -c 'python3 docs/evidence/csh-106/validate.py linux && python3 docs/evidence/csh-106/supplement.py linux'
docker start -a cshell-csh106-validation
docker cp cshell-csh106-validation:/work/build/csh106-validation ./build/csh106-linux-results
docker cp cshell-csh106-validation:/work/build/csh106-supplement ./build/csh106-linux-supplement
docker rm cshell-csh106-validation

# Package native and copied Linux reports; logs are losslessly compressed.
python3 docs/evidence/csh-106/retain.py build/csh106-validation build/csh106-supplement \
  build/csh106-linux-results build/csh106-linux-supplement
# Retain any recovery run's status/source identity before verifying.
python3 docs/evidence/csh-106/verify.py
```

Selected validation must return zero; stock full/provider audits must remain
nonzero. Native provisioning uses an exact copy of the predecessor worktree's
qualified gfind under this worktree's build/local-bin. System installations
are unchanged. `SHA256SUMS` covers retained files here except itself.
