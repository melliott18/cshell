# CSH-086 owned-terminal filesystem contracts

Collected 2026-10-10 in a separate worktree based on CSH-085 published commit
`483bd693989bd78c95b1bbb455f173d448a9cfee` (implemented, unmerged). This change
supplies 13 cases / 39 assertions and uses the ticket's explicit-disposition
alternative for unsupplied environments. No entire utility page is qualified.

## Results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Inventory + 10 inventory and 36 filesystem harness tests pass | Same checks pass |
| `make test-host-profile`: integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1065 pass, 0 fail | 1081 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-isolated` | 112 pass, 0 fail | 112 pass, 0 fail |
| `make test-host-filesystem-interactive` | 39 pass, 0 fail | 39 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 984 pass, **61 fail** | 1021 pass, **36 fail** |
| Stock `--extended-only --provider-audit` | 152 pass, **16 fail** | 176 pass, **8 fail** |

Selected commands exit zero. Stock Make audits exit 2 and direct stock audits
exit 1. All filesystem records require successful fixture cleanup, including
stock failures. The source-input hash for final reports is
`650149fe4cef31bba70ad46f7f72fe3c7c87f29e774015e8876e38de526a8d23`.
Selected-PATH `make test-runtime test-pty` passes on both platforms; logs retain
individual counts. These are local native/Docker runs, not hosted CI or a new
sanitizer qualification claim.

## Independent oracle and provider repair

[cp](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cp.html) and
[mv](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html) DESCRIPTION,
OPTIONS, STDIN, STDERR and EXIT STATUS define the tested behavior. Authored
source/destination bytes and exact status distinguish affirmative and negative
responses. cp's -f and -i remain independent in both orders; mv uses the last
option. Additional cp cases accept or decline the first overwrite and then
encounter a missing source: the real error must still produce nonzero status,
a diagnostic naming that operand, and the expected first-operand effects.

All 13 cases run in an owned foreground PTY, using direct provider exec and
cshell command-string/script dispatch. A test-only helper checks terminal
ownership, redirects stdout to a private file, records the armed environment,
then execs the exact inventoried provider. Prompt/error bytes must therefore
arrive through terminal stderr and ordinary stdout must remain empty. Full raw
capture, terminal output, status, invocation, setup marker and effects are
retained independently. This does not claim shell stdin-script-mode coverage
for interactions, arbitrary prompts, locales or recursive graphs.

The oracle permits exact known Apple/GNU C-locale prompt spellings because the
standard leaves wording unspecified. It never rewrites status or effects.
Stock Apple cp and native GNU coreutils 9.3 cp return 1 after a negative answer;
the preliminary 33-assertion stock/GNU reports retain these nine failures each.
The final stock macOS full audit has those nine additional failures. Debian's
stock GNU coreutils 9.1 cp passes all new cases; its 36 pre-existing failures
remain. Existing CSH-072/080/084/085 evidence is unchanged.

The selected provider on both platforms is pinned GNU coreutils 9.7 cp, built
from the retained release archive with a small patch to cp's declined-copy
return path. Explicit GNU `--update=none-fail` and actual copy failures retain
nonzero status. There is no runtime output/status adapter. The archive's source
and GPL license, patch, offline build script, exact configure flags and compiler
logs are retained; profile manifests record archive/patch/executable hashes.
The bounded build disables NLS, ACL, SELinux and GMP. No whole-provider or
privileged-attribute claim follows from these tests.

[ln](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html) has no -i
option in the selected base profile. The current ledger corrects that inherited
interactive-replacement item to a vendor extension. `normative-sources.json`
records the freshly read Issue-8 page hashes; historical sources are untouched.

## Harness failures and cleanup

Five new harness tests cover corrupted effects, status, stdout versus stderr,
missing/extra diagnostics, missing terminal markers, unavailable PTYs, partial
fixture setup, and timeout cleanup in all three modes. Timed-out providers
report their PID; the test requires that PID to disappear and removes the
private fixture. No mounts, credential changes or host-volume filling occur.
Call-site allocation faults, kernel EFBIG/EPIPE, virtual-device ENOSPC and actual
filesystem exhaustion remain distinct in inherited records and dispositions.

During development, the direct GNU program Make target omitted generated
gnulib headers; the build now first makes upstream BUILT_SOURCES. A new nested
destination prompt initially waited for the old target name; the authored step
now waits for its actual destination and all 39 assertions pass. These were
build/harness failures, not provider allowances. Linux's final inventory and
allocation checks were repeated after that step correction so final source
identities match; the initial allocation record is not the final evidence.

## Reproduction and residual ownership

```sh
# Native macOS provisioning needs the inherited gtest, g[, gfind and gdd.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive
make test-host-filesystem-audit # expected stock failure
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json

docker build -t cshell-test:csh-086 .
docker run --rm cshell-test:csh-086 make test-host-inventory test-host-profile \
  test-host-filesystem-allocation test-host-filesystem-provider-audit \
  test-host-filesystem-residual test-host-filesystem-isolated \
  test-host-filesystem-interactive
```

Native gfind is the unchanged CSH-085 binary copied into the ignored
`build/native-findutils/bin` directory and prepended to provisioning PATH.
The selected runtime checks use the built profile prefix plus the platform's
system PATH. Compressed reports retain argv/environment, actual output/status,
filesystem effects, platform/package identities and cleanup; compressed logs
retain the commands and compiler configuration. `SHA256SUMS` covers artifacts.

The current [section map](../../../tests/host_filesystem_contracts.json),
[residual ledger](../../../tests/host_filesystem_residuals.json), ownership
manifest and [CSH-087](../../tickets/CSH-087-filesystem-environment-followup.md)
retain each unsupplied contract and all four original condition IDs, with
required environments, reasons and vendor owners. Cross-device filesystems,
ACL/privileged credentials, quotas, real capacity exhaustion, namespace races,
libc-internal faults, complete locale repertoires and other listed contracts
remain open. The original CSH-064 reasons and evidence are unchanged.
