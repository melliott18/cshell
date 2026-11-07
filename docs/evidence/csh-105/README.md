# CSH-105 default numeric magic qualification

This change adds 280 independently authored `file` cases, required in direct
execution and cshell string/file/stdin modes (1120 assertions on both LP64
hosts). It is stacked on CSH-104 commit `9d37825`; integration remains gated on
that dependency. The selected profile has no failure allowances.

## Contract and repair

[POSIX file, EXTENDED DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html#tag_20_46_13)
defines `d`/`u` default widths as a basic integer type chosen by the implementation.
The selected file 5.46 provider uses four-byte native int/unsigned int on the
qualified hosts. This is a documented provider choice, not a requirement that
every provider choose int. POSIX separately requires byte/short/long to mean
dC/dS/dL, respectively; `long` therefore uses native C long storage.

The fixtures use ctypes widths, cross-checked with struct before execution,
and Python integer-to-byte conversion in native order. They cover signed
minimum/maximum, unsigned high-bit ordering, hexadecimal/octal masks and
constants, bit tests, every incomplete field length, and nonzero trailing
bytes. Every predicate has positive and negative witnesses, both at top level
and in continuations. Literal output avoids coupling numeric comparison to
printf conversion. Pre-exec readback, exact channels/status, unchanged database
and sample bytes, and cleanup are required. Fault regressions reject changed
output/status/input, failed setup, missing interpreters and timed-out children.

The selected provider previously interpreted the textual `long` keyword as
four bytes on LP64, causing 112 failures in the new assertions. The repair maps
it to native dL when loading text rules. The vendor `-C` compilation extension
retains the original four-byte encoding used by the bundled system database.
Five separate checks exercise compilation and both text/compiled loading at
four-byte and native-long boundaries. The default compiled database's hash
must remain equal to CSH-104's on each platform. This does not claim POSIX
qualification for the vendor compilation interface or arbitrary default file
classification. All CSH-103/104 patches remain applied.

All fixtures use private regular files. No mount, credential, kernel fault,
libc injection or real capacity exhaustion is added. Other numeric/message
combinations, cross-database -m/-M/-d precedence, classifications, encodings,
locales and resource failures remain individually open in
[CSH-106](../../tickets/CSH-106-filesystem-environment-residuals.md), along with
all other utility residuals and the four original U-040 conditions. U-034 and
U-040 remain partial. Utility/libc/platform vendors retain implementation ownership.

## Validation

Final results are recorded in `summary.json` and checked by `verify.py`.

| Check | macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 6855 pass, 0 fail | 6895 pass, 0 fail |
| New default/alias assertions | 1120 pass | 1120 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Allocation probes | 240 pass | 200 pass |
| Ownership / filesystem harness | 10 / 120 pass | 10 / 120 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Harness suite | 93 tests pass | 93 tests pass, one Darwin-only skip |
| Focused ASan/UBSan magic assertions | 3540 pass | 3540 pass |
| Format / compiled-database checks, regular and sanitized | 14 / 5 pass | 14 / 5 pass |
| Stock full / provider audit failures | 681 / 16 retained | 578 / 8 retained |
| Unpatched file 5.46 new failures | 308 retained | 308 retained |

The previous selected CSH-104 provider fails 112 new assertions on macOS;
unpatched file 5.46 fails 308 on both hosts because it also lacks the earlier
textual rule-order repair. Every prior selected expectation and stock failure
is retained. Original and intermediate failures are not converted to passes.

Native means macOS; Linux evidence comes from an unprivileged Debian Docker
container, not a separately hosted native-Linux runner. Both use the same
source digest. Exact binary, archive, patch, build script, compiled database,
platform, compiler and fixture identities are retained in the reports and
manifests. Logs include actual channels/status/effects, setup and cleanup.

Focused ASan/UBSan validation instruments file/libmagic only, with regular
cshell and other providers. All five magic suites and both provider regression
scripts are required. No whole-project sanitizer or hosted CI run is claimed.
The verifier compares every previous selected expectation (except independently
measured per-run inode identities), preserves every earlier stock failure,
and requires that added stock failures belong to this increment. It checks
exact new oracles, provider/source hashes and fixture cleanup.

The `development/` directory retains the previous-provider failures and
preliminary provisioning logs separately. An initial focused Make invocation
omitted the local gfind provisioning PATH and failed setup; the final commands
supply it. The first draft compiled-database regression reused smoke.capture's
private .home/.tmp directories, producing FileExistsError before its second
capture; the regression now removes those owned directories between captures.
Neither setup mistake is accepted as passing behavior. The preliminary unit
log may be incomplete; final inventory logs contain the complete result.
The first Linux inventory run also failed the existing metadata timeout test's
immediate PID-disappearance assertion. Twelve isolated repeats reproduced two
failures; /proc recorded both children as zombies adopted by PID 1, with SIGKILL
exit status. A controlled subreaper reproduced the same failure with delayed
reaping. The test now waits at most two seconds for actual PID disappearance,
matching other timeout fixtures; live children and unreaped zombies still fail
at the deadline. A controlled 100-ms delayed reaper passes the repaired test.
Raw failed attempts, process states and diagnostic scripts are retained in
`development/`; the repaired controlled check is `linux-delayed-reaper-check.log`.
Native reports produced across that test-source edit are retained as preliminary,
then rerun for one final source digest. No prior evidence is rewritten.

## Reproduction

```sh
# Supply gtest, g[, gfind and gdd on the provisioning PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-105/validate.py native
python3 docs/evidence/csh-105/supplement.py native
python3 docs/evidence/csh-105/provider_checks.py native

docker build -f docs/evidence/csh-105/Dockerfile.linux -t cshell-test:csh-105 .
docker create --init --name cshell-csh105-validation cshell-test:csh-105 \
  sh -c 'python3 docs/evidence/csh-105/validate.py linux && python3 docs/evidence/csh-105/supplement.py linux && python3 docs/evidence/csh-105/provider_checks.py linux'
docker start -a cshell-csh105-validation
docker cp cshell-csh105-validation:/work/build/csh105-validation ./build/csh105-linux-results
docker cp cshell-csh105-validation:/work/build/csh105-supplement ./build/csh105-linux-supplement
docker cp cshell-csh105-validation:/work/build/csh105-provider-checks ./build/csh105-linux-provider-checks
docker rm cshell-csh105-validation

# Retain reports here before verifying.
python3 docs/evidence/csh-105/verify.py
```

Selected validation must return zero; stock full/provider audits must remain
nonzero. Native provisioning uses an exact copy of the CSH-104 qualified gfind
in this worktree's build/local-bin. System installations are unchanged.

`SHA256SUMS` covers every retained file in this directory except itself.
