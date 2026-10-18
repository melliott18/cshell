# CSH-094 logical cwd fallback evidence

Collected 2026-10-18 in a separate worktree on published CSH-093 commit
`7f13aaba40a39ba9edf4a6dc518842539c0e0f00`. Integration remains gated on that
unmerged dependency.

## Scope and independent oracle

Issue 8 [pwd](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html)
OPTIONS specifies physical fallback when PWD does not identify the current
directory, default logical mode and last-option selection. STDOUT and
CONSEQUENCES OF ERRORS define the pathname/newline and error channel/status
contracts. `normative-sources.json` records the retrieved page hash; direct
HTTPS retrieval succeeded after the web reader returned 403.

Twelve cases exercise external pwd with no options, `-L`, and `-P -L`, after
renaming the cwd or its parent and after removing the cwd alone or together
with its parent. Each runs directly and through cshell string/file/stdin modes,
for 48 assertions on each platform. These are external-provider assertions,
not pwd builtin tests, and only qualify the authored fallback conditions.

The child-only helper never assigns or unsets PWD. Direct exec inherits no
PWD; shell modes inherit the fixture root established by shell startup.
When present, the helper requires PWD to equal the physical fixture root and
records its device/inode. It changes into the private child directory, mutates
that namespace, and proves unchanged cwd device/inode, old-path ENOENT, and
exact getcwd resolution or ENOENT before execing the inventoried provider.
It checks PWD is unchanged and cannot identify the cwd. No valid logical
symlink pathname or arbitrary namespace race is supplied.

Rename cases require the exact independently measured physical pathname and
newline, empty stderr, status zero and expected directory effects. Removal
cases require empty stdout, a diagnostic, positive status and absent-directory
effects. Setup and exec failures cannot satisfy the error oracle. The existing
physical case specifications remain byte-for-byte equivalent as Python values.

Five new harness tests cover immutable specs and inherited environments in
all four modes; corrupted PWD markers, channels, status and effects; setup and
exec failures; rejected foreign or cwd-identifying PWD before mutation; and
bounded timeout, provider reaping and cleanup after both rename and removal
in every mode. Deliberately assigned PWD occurs only in harness self-tests,
not utility qualification. Errno marker validation also rejects non-integers.
No provider sources or build flags change; earlier selected assertions remain
mandatory with zero allowances.

## Results

All required selected targets pass on macOS 14.8.7 arm64 UID 501 and Debian 12
arm64 Docker UID 10001. Each platform passes 10 ownership tests and 76 harness
tests. No sanitizer or hosted-CI qualification is claimed.

| Command / profile | macOS | Linux |
| --- | --- | --- |
| `make test-host-profile`: host integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1475 pass, 0 fail | 1515 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass | 200 pass |
| `make test-host-filesystem-provider-audit` | 168 pass | 184 pass |
| `make test-host-filesystem-residual` | 104 pass | 104 pass |
| `make test-host-filesystem-isolated` | 112 pass | 112 pass |
| `make test-host-filesystem-interactive` | 39 pass | 39 pass |
| `make test-host-filesystem-decisions` | 68 pass | 68 pass |
| `make test-host-filesystem-metadata` | 64 pass | 64 pass |
| `make test-host-filesystem-recursive` | 30 pass | 30 pass |
| `make test-host-filesystem-path-limits` | 32 pass | 32 pass |
| `make test-host-filesystem-cwd` | 32 pass | 32 pass |
| `make test-host-filesystem-creation` | 104 pass | 104 pass |
| `make test-host-filesystem-output` | 32 pass | 56 pass |
| `make test-host-filesystem-cwd-logical` | 48 pass | 48 pass |
| Stock `make test-host-filesystem-audit` | 1382 pass, 73 fail | 1449 pass, 42 fail |
| Stock `--extended-only --provider-audit` | 152 pass, 16 fail | 176 pass, 8 fail |

Stock Make audits exit 2 and direct provider audits exit 1, as expected.
`verify.py` verifies every previous selected case/mode is retained, the exact
48 new assertions, identical stock failure IDs/modes to CSH-093, successful
cleanup for every filesystem case and identical final native/Linux source
identities. `summary.json` and `stock-failure-comparison.json` retain its results.
Every report records final source digest
`19e3d7f06c93c3f80f82cb7ea4ad4bf9662067b774b09379d3a2b7d0ccde5568`.
`SHA256SUMS` covers retained artifacts other than this narrative.

## Reproduction and provenance

```sh
# Native PATH must provide gtest, g[, gfind and gdd.
make -j4 cshell host-profile
python3 docs/evidence/csh-094/validate.py native

# Clean Linux build; copy the standalone validation driver into the container.
docker build -t cshell-test:csh-094-clean .
docker create --init --name cshell-csh094-clean cshell-test:csh-094-clean \
  python3 /work/validate-csh094.py linux
docker cp docs/evidence/csh-094/validate.py cshell-csh094-clean:/work/validate-csh094.py
docker start -a cshell-csh094-clean
docker cp cshell-csh094-clean:/work/build/csh094-validation ./build/csh094-linux-results
docker rm cshell-csh094-clean

# Verify the checked-in evidence without executing providers.
python3 docs/evidence/csh-094/verify.py
```

`validate.py` runs the entire required target set and retains separate stock
audits, failing if their command statuses differ from the required pattern.
JSON records provider executable hashes, source/build identity, exact channels,
status, effects, setup errors and cleanup. Native gfind was copied from the
ignored CSH-093 selected build; local providers were rebuilt from pinned sources.
The retained Linux run used the CSH-093 Debian image with a source overlay,
UID 10001, Docker `--init` and no host mounts. `Dockerfile.linux`, image/build
logs and provider manifests identify that environment; the final source digest
matches native exactly. Its provider binaries retain the CSH-093 pinned build.

## Remaining ownership

[CSH-095](../../tickets/CSH-095-filesystem-environment-residuals.md)
([#201](https://github.com/melliott18/cshell/issues/201)) retains every unsupplied
contract with its environment, reason and utility/libc/platform implementation
owner. Valid logical symlink namespaces, arbitrary races, inaccessible ancestors,
path limits, allocation/stdio faults, locales, credentials, ACLs and capacity
remain open. All four original U-040 conditions remain open. Historical evidence
and stock failures are unchanged. This uses the explicit-disposition acceptance
alternative and does not qualify whole utilities or close U-034/U-040.
