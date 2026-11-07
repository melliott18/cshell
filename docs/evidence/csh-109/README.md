# CSH-109 directory removal graph qualification

This increment adds 19 independently authored rmdir cases, required in direct
execution and cshell string/file/stdin modes (76 assertions). It is stacked on
CSH-108 commit `39f81fc`; integration remains gated on that dependency. No
selected-profile allowances or production/vendor source changes are introduced.

## Contract and independent oracle

The [rmdir DESCRIPTION and OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rmdir.html)
require ordered operands, removal equivalent to rmdir(), and recursive parent
removal with `-p`. The normative page digest matches the retained CSH-012 source.
The authored graphs cover chains of one, two and four components; explicit
child-first and sibling-before-parent orders; nonempty file, dangling-link and FIFO
ancestors; duplicate operands; shared parents; and continuation past missing,
regular-file and directory-symlink operands.

Four permission cases use private owner-mode write denial (0500) or search
denial (0000) at a prefix, with one or two child components. An independent
rmdir syscall against an empty probe child must produce EACCES before provider
execution. The probe is removed with restored permissions, then denial is
rearmed and read back. The child provider inherits the same unprivileged
identity. This is a real kernel owner-mode permission failure, not injection,
an ACL/privileged identity test, a mount, or filesystem exhaustion.

Pre-exec lstat records establish the device/inode/mode of every authored
object. Post-exec checks require exact removed paths and surviving identities,
modes, file bytes and link targets. The denied prefix mode is recorded and
checked before restoring owner access for inspection; identity is checked after
restoration. Success requires empty channels and zero status; failures require
empty stdout, nonempty diagnostics and positive status. Diagnostic wording and
positive error numbers are not prescribed. Every fixture must be removed.

The harness adds five regression tests for the matrix, deliberate corruption of
removal/preservation and channel/status results, partial setup and failed probes
without dispatch, rejection of incorrect probe errors, failed exec and timeouts
in all four modes, and symlink boundaries during permission restoration. Timeout
checks require the helper to be reaped and the private fixture removed. These
checks do not establish utility signal behavior or arbitrary namespace races.

## Selected providers and residual ownership

Native Apple rmdir and Linux GNU rmdir are selected without overrides. Their
exact paths, executable hashes and host/package identities are retained, together
with the full selected profile's unchanged vendor archives and build manifests.
The verifier requires every CSH-108 expectation and stock failure unchanged,
exactly 76 new full-profile assertions, independent permission observations,
cleanup, and one final source digest across both platforms.

All 21 utility dispositions and four original U-040 conditions remain open under
[CSH-110](../../tickets/CSH-110-filesystem-environment-residuals.md)
([#231](https://github.com/melliott18/cshell/issues/231)). Arbitrary parent graphs,
ACLs and other identities, mounts, total depth/path limits, namespace races,
other filesystem failures and diagnostic locales remain unqualified.
Utility/libc/platform vendors retain implementation ownership. U-034/U-040
remain partial; the historical evidence is unchanged.

## Validation record

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 11811 pass, 0 fail | 11851 pass, 0 fail |
| New removal assertions | 76 pass | 76 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 138 pass | 10 / 138 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Stock full / provider failures | 745 / 16 retained | 578 / 8 retained |
| General harness | 93 tests pass | 93 tests, one Darwin-only skip |
| Format / compiled database | 14 / 5 pass | 14 / 5 pass |

Final counts and command statuses are retained in `summary.json` and the
platform command records. The selected filesystem profile and focused targets
require zero failures; the strict stock audits require their existing nonzero
results. Runtime, terminal and general harness checks use unchanged source
files and providers; their passing supplemental records precede the final
fixture-only operand-order correction. No supplemental assertion uses the
changed removal module or filesystem ledgers.

## Reproduction

```sh
# Native provisioning requires gtest, g[, gfind and gdd on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-109/validate.py native
python3 docs/evidence/csh-109/supplement.py native

docker build -f docs/evidence/csh-109/Dockerfile.linux -t cshell-test:csh-109 .
docker create --init --name cshell-csh109-validation cshell-test:csh-109 \
  sh -c 'python3 docs/evidence/csh-109/validate.py linux && python3 docs/evidence/csh-109/supplement.py linux'
docker start -a cshell-csh109-validation
docker cp cshell-csh109-validation:/work/build/csh109-validation ./build/csh109-linux-results
docker cp cshell-csh109-validation:/work/build/csh109-supplement ./build/csh109-linux-supplement
docker rm cshell-csh109-validation

python3 docs/evidence/csh-109/retain.py build/csh109-validation build/csh109-supplement \
  build/csh109-linux-results build/csh109-linux-supplement
python3 docs/evidence/csh-109/verify.py
```

Native provisioning uses a copy of the predecessor's qualified gfind in ignored
`build/local-bin`. Linux validation uses an unprivileged Debian Docker identity;
no separately hosted native-Linux or sanitizer run is claimed. No C code changed.
`SHA256SUMS` covers retained files except itself. Raw failed development checks
remain separate from final validation, with no relaxation of expectations or
deadlines.

## Development dispositions

The initial native inventory and first validation attempt hit missing helper
PID files at the unchanged one-second harness deadline while builds and other
test processes were active. Focused timeout checks and a full 138-test rerun
passed unchanged. The raw failures and reruns are retained in `development/`.

Final specification review replaced two passing parent-first examples: rmdir
DESCRIPTION requires applications to place subdirectories before their parents.
The replacements are valid sibling-before-parent orders at two depths. This
correction was independent of provider behavior; both vendors had passed the
original examples. Pre-correction platform records are retained separately and
do not qualify the final matrix. No production or vendor code changed.
