# CSH-075 provider repairs

These records extend the original and `edges/` evidence without changing either.
CSH-075 is still in progress: getconf Issue 8 remains a strict failure and the
six retained conditions and complete utility-page contracts remain open.

## Provider changes

- Linux execution profiles select the installed BusyBox 1.35.0 renice. PID
  increments are relative and stdout is empty. Independent getpriority checks
  cover increment, zero and positive clamping; group/user coverage is not implied.
- An explicit local build supplies GNU coreutils 9.11 timeout from the official
  archive, verified by the pinned SHA-256. The one-condition patch sends preserved
  signal termination through the existing core-disable/reset/unblock/raise path.
  `upstream-timeout.json.gz` retains the unpatched 9.11 comparison: three direct
  checks pass and two fail because expiry returns normal exit 143 instead of
  SIGTERM. The patched provider passes both and still preserves normal exit 143.
- The provider build manifests record the archive, patch, patched timeout source,
  builder and executable hashes, platform, compiler and commands. Compressed
  configure/header/build logs and compiler version output accompany them. GNU
  source/licenses remain in the local build directory; no binary is committed
  or installed over system utilities.

## Reproduction

Use the separate `test/CSH-075-host-execution-processes` worktree. The native
provider build used the already downloaded, hash-verified archive:

```sh
make host-timeout HOST_TIMEOUT_BUILD_FLAGS='--archive build/coreutils-9.11.tar.xz --jobs 4'
make test-host-execution-profile HOST_PROFILE_PROVISION_FLAGS='--timeout build/host-timeout'
# The full run above must still fail on the four getconf assertions.
make test-host-profile HOST_EXECUTION_SUBSET=tests/host_execution_subset_repaired.json \
  HOST_PROFILE_PROVISION_FLAGS='--timeout build/host-timeout'
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
make test-host-inventory
python3 -m unittest discover -s tests -p test_host_harness.py
```

Linux used the previously recorded `cshell:csh-075` Debian 12 image, current
`tests/`, `tools/`, and Makefile mounted read-only, and a private writable results
mount. Build timeout inside Linux with the same archive and Python builder;
copy `build/host-timeout` and its manifest to `/results/`. Select
`--timeout /results/host-timeout`. Before the full execution run:

```sh
make build/tests/host_execution_helper build/tests/host_execution_clock.so
python3 tests/host_execution.py ./cshell build/tests/host_execution_helper \
  --path /work/build/host-profile/bin:/bin:/usr/bin \
  --clock-library build/tests/host_execution_clock.so --controlled-identities \
  --record /results/repaired-full.json
```

The credential run requires disposable Linux root. Ordinary native tests ran
as the developer identity. The repaired subset contains every current ordinary
case except `getconf/issue8-environment`; no failing expectation is weakened.

## Results

| Run | macOS 14.8.7 arm64 | Debian 12 / LinuxKit arm64 |
| --- | --- | --- |
| Full repaired execution | 274 pass, 4 fail | 287 pass, 4 fail (13 additional controls) |
| Explicit repaired execution subset | 274 pass, 0 fail | 274 pass, 0 fail |
| Fallback/resource/timing edges | 80 pass, 0 fail | 80 pass, 0 fail |
| Existing host profile | 1162 pass, 0 fail, 0 gaps | 1144 pass, 0 fail, 0 gaps |
| Existing runtime fixtures | 3950 pass, 0 fail | 3950 pass, 0 fail |

Every full-run failure is getconf's required Issue 8 name, once per invocation
mode. The six combined-profile records share source digest
`80b32d219e77600d551e3ac4cde0502c7c6571245a8998e8cfaba3076ec8d39a`.
Full runs retain their own digests; clause-ledger wording was updated between
those runs. Source maps show the exact inputs, rather than claiming one digest
for different snapshots.

The final harness change preserves ceiling-control diagnostics before parsing
its result. Targeted final renice runs repeat all three cases in four modes,
plus the six standard fallback/threshold controls, on each platform. All 18 pass.
Fifteen execution-harness regressions and ten ownership tests pass on each
platform; the eighteen existing host-harness tests also pass natively.

`*-failed-oracle-setup.json.gz` retains an intermediate test error: the new
ceiling control initially reused a capture directory whose `.home` already
existed. Those twelve setup failures are not attributed to renice. A separate
owned control directory fixes the error. Native clamping uses an independently
observed ceiling of 20; Linux uses 19.

The first native runtime/PTY command passed runtime, notification and 30 job
fixtures but hit an existing five-second timeout in the job-terminal fault
helper. Its process-snapshot cleanup also exceeded its deadline. The failed
log is retained separately; no timeout is counted as a pass. Linux's full
runtime/PTY command exited 0 (3950 runtime plus 65 notification/job/terminal
assertions). The native retry also failed in that one fixture. The stock-PATH control in
`native-stock-pty-control.log.gz` reproduces the timeout without the repaired
profile. The separate native runtime PTY suite passes all 33 assertions
(`native-runtime-pty.log.gz`). This existing job-terminal fault fixture remains
an unresolved native validation issue; the serial retry is not reported as a
pass and no watchdog was relaxed.

See the [remaining work/environment map](../../../host-execution-evidence.md#provider-repairs-and-required-environments).
Additional deterministic instrumentation is implementation work; privileged
Darwin parity requires a disposable macOS VM. Ordinary tests need no manual
terminal observations or stopwatch measurements.

Run `python3 docs/evidence/csh-075/repairs/verify.py` to verify artifact hashes,
recorded totals, build/provider identity correspondence and failure boundaries.
This accounting check does not requalify a utility.
