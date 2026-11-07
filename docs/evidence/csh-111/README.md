# CSH-111 link permission qualification

This increment adds 21 independently authored ln cases, required in direct
execution and cshell string/file/stdin modes (84 assertions). It is stacked on
CSH-110 commit `5b915fe`; integration remains gated on that dependency. No shell
runtime or vendor source changes, provider substitutions or allowances are added.

## Contract and oracle

The [ln DESCRIPTION, OPTIONS and OPERANDS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html)
specify link creation, literal symbolic-link contents, forced unlink and
continuation after failure. The retrieved normative page digest matches the
retained requirement map. Five cases deny search on the middle source's parent:
`-L` and `-P` fail for that operand while linking the surrounding operands;
`-s`, `-s -L` and `-s -P` instead create literal symbolic links for all operands.
Sixteen destination cases cross denied write/search with hard/symbolic linking
and absent/regular/symlink/FIFO destinations. Existing destinations use `-f`;
all failures preserve the original objects and symlink referents.

Fixtures use private owned directories under one unprivileged real/effective
identity. Before dispatch, independent `link`, `symlink` and `unlink` probes
must return kernel EACCES. Unexpected success or another error is a setup
failure, never a utility result. Probe objects are removed before dispatch,
and the denied directory's exact mode is checked again afterward. Restoration
precedes content/identity inspection and always runs during teardown, including
partial setup, failed exec and timeouts. Cleanup does not follow guard symlinks.

Pre-exec lstat and type/content/mode/link readback establish the authored objects.
Post-exec checks require exact hard-link inode relationships, link counts,
literal symbolic-link contents, unchanged identities/modes/bytes and referents.
Success requires empty channels and zero status. Errors require empty stdout,
nonempty stderr and positive status; no diagnostic wording or specific positive
exit value is prescribed. Every fixture must be removed.

The new cases use an exec helper in all four modes. It records the exact selected
provider and credentials before `execv`, records any returned exec error, and
otherwise preserves the provider's channels and status. A missing, malformed,
wrong-provider, wrong-identity or failed-exec record fails the case. Thus a
shell/interpreter launch error cannot satisfy an expected ln permission failure.
The shell modes exercise dispatch of this helper and the exact provider; these
new cases do not independently qualify PATH lookup of the bare `ln` name.

Six harness regressions cover the full case/mode matrix, deliberate effects and
channel/status corruption, missing/corrupt dispatch records, unexpectedly
successful/wrong-errno probes, partial setup, failed exec, timeout/reaping and
symlink-safe cleanup. Development exposed the false-pass risk from a broken
interpreter in a negative case; the exec record repair is required by the final
regressions. The initial failure log is retained separately under `development/`.

## Scope and remaining owners

These are ordinary owner-mode kernel permission witnesses, not libc/call-site
injection, ACL/other-identity tests, namespace races or filesystem exhaustion.
The selected GNU coreutils 9.7 ln remains unchanged. Exact executable, archive,
configure/build and source identities are retained on each platform. The evidence
verifier requires every predecessor expectation and stock failure unchanged,
exactly 84 added full-profile assertions, zero selected failures, matching
provider/source identities and successful cleanup.

All 21 utility dispositions and four original U-040 conditions remain open under
[CSH-112 / #235](../../tickets/CSH-112-filesystem-environment-residuals.md).
Further graph/default-policy alternatives, cross-device and other permission/ACL
errors, other identities, hard-link count limits, namespace races, filesystem
failures, diagnostic locales and exhaustion remain unqualified. Utility/libc/
platform vendors retain implementation ownership; U-034/U-040 remain partial.
Historical evidence is unchanged.

## Validation record

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12011 pass, 0 fail | 12051 pass, 0 fail |
| New link permission assertions | 84 pass | 84 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 149 pass | 10 / 149 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Stock full / provider failures | 749 / 16 retained | 578 / 8 retained |
| General harness | 93 pass | 93 tests, one Darwin-only skip |
| Format / compiled database | 14 / 5 pass | 14 / 5 pass |

Commands, statuses, durations and raw reports are retained separately by
platform. The exact predecessor comparison is recorded in `summary.json` and
`stock-failure-comparison.json`. Stock audits deliberately return nonzero.
The selected profile requires zero failures and zero allowances.

## Reproduction

```sh
# Native provisioning requires gtest, g[, gfind and gdd on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-111/validate.py native
python3 docs/evidence/csh-111/supplement.py native

docker build -f docs/evidence/csh-111/Dockerfile.linux -t cshell-test:csh-111 .
docker create --init --name cshell-csh111-validation cshell-test:csh-111 \
  sh -c 'python3 docs/evidence/csh-111/validate.py linux && python3 docs/evidence/csh-111/supplement.py linux'
docker start -a cshell-csh111-validation
docker cp cshell-csh111-validation:/work/build/csh111-validation ./build/csh111-linux-results
docker cp cshell-csh111-validation:/work/build/csh111-supplement ./build/csh111-linux-supplement
docker rm cshell-csh111-validation

python3 docs/evidence/csh-111/retain.py build/csh111-validation build/csh111-supplement \
  build/csh111-linux-results build/csh111-linux-supplement
python3 docs/evidence/csh-111/verify.py
```

Native provisioning uses the predecessor's qualified gfind copied to ignored
`build/local-bin`. Linux runs use the unprivileged Debian Docker identity;
no separately hosted native-Linux or new C sanitizer run is claimed.
`SHA256SUMS` covers retained files except itself.
