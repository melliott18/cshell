# CSH-110 link destination graph qualification

This increment adds 29 independently authored ln cases, required in direct
execution and cshell string/file/stdin modes (116 assertions). It is stacked on
CSH-109 commit `79bf2f4`; integration remains gated on that dependency. There
are no selected-profile allowances or shell runtime/vendor source changes.

## Contract and independent oracle

The [ln DESCRIPTION, OPTIONS and OPERANDS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html)
define destination construction, collision handling and link creation. The
retrieved normative page digest matches the retained CSH-012 source map.
Authored cases cover directory destinations with and without a trailing slash,
a destination reached through a directory symlink, two-source hard/symbolic
links, valid/dangling source symlinks under explicit -L/-P and both orders,
and physical hard links to a directory symlink. Additional cases put existing
regular files, symlinks, dangling symlinks, FIFOs and directories between two
successful operands, with and without -f. Missing-middle and same-entry
hard/symbolic refusal cases require continuation to the later operand.

Pre-exec lstat and independent type/content/mode/link readback establish each
private object and its initial link count. Expected outputs come from authored
bytes and graph relationships, never from utility output. Post-exec checks
require lstat inode equality for hard links (including symlink inodes), exact
link counts, literal symbolic-link contents, unchanged source and referent
identities/modes/bytes, and the specified destination effects. Directory link
counts and symbolic-link modes are platform-dependent and are not assigned
portable constants. Preserved objects retain their measured original modes.

Success requires empty channels and zero status. Failure requires empty stdout,
nonempty stderr and positive status, alongside exact effects; diagnostic wording
and specific positive error numbers are not prescribed. All fixtures must be
removed. These are ordinary private filesystem graphs, not injected faults,
privileged identity tests, namespace races, mounts or resource exhaustion.

The five new harness tests check the case inventory, deliberate corruption of
inode/content/mode/referent/link/channel/status results, partial setup and failed
readback without dispatch, failed exec/timeouts in all four modes, and JSON encoding of setup bytes in
both passing and failing reports. Timeout
checks require reaped helpers and removed fixtures. The FIFO fixture also ensures
inspection and cleanup do not block by opening its contents.

## Selected providers and retained failures

Apple ln incorrectly replaces a same-entry source with a symbolic link under
`-fs`, returns success and emits no diagnostic. DESCRIPTION step 1b requires
preservation, diagnosis and continuation, regardless of -s. All four stock
mode failures are retained with their original expectations. The opt-in profile
selects unmodified ln from the already pinned GNU coreutils 9.7 archive; it
passes these assertions. No status translator or vendor patch was added.

Both platforms retain exact executable and archive hashes, configure options,
build logs, package/OS identities and the selected PATH manifest. The verifier
requires all CSH-109 expectations unchanged, exactly 116 new full-profile
assertions, every prior stock failure, the four additional Apple failures,
cleanup, and one final source digest across both platforms. System utilities
are not replaced; only the opt-in PATH selects the new provider.

All 21 utility dispositions and four original U-040 conditions remain open under
[CSH-111](../../tickets/CSH-111-filesystem-environment-residuals.md)
([#233](https://github.com/melliott18/cshell/issues/233)). Further graphs,
default-policy alternatives, cross-device/permission/ACL/identity environments,
hard-link count limits, races, filesystem failures, diagnostic locales and
resource exhaustion remain unqualified. Directory hard-link behavior and
repeated destinations created during an invocation are not assigned portable
expectations. Utility/libc/platform vendors retain implementation ownership;
U-034/U-040 remain partial. Historical evidence is unchanged.

## Validation record

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 11927 pass, 0 fail | 11967 pass, 0 fail |
| New link graph assertions | 116 pass | 116 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 143 pass | 10 / 143 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Stock full / provider failures | 749 / 16 retained | 578 / 8 retained |
| General harness | 93 tests pass | 93 tests, one Darwin-only skip |
| Format / compiled database | 14 / 5 pass | 14 / 5 pass |

Final results are recorded in `summary.json` and platform command records.
The selected and focused profiles require zero failures. Stock full and
provider audits intentionally require nonzero status with the unchanged strict
expectations. Native and Docker runtime/terminal suites and harness checks use
the selected PATH. No C source changed; no new sanitizer claim is made.

## Reproduction

```sh
# Native provisioning requires gtest, g[, gfind and gdd on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-110/validate.py native
python3 docs/evidence/csh-110/supplement.py native

docker build -f docs/evidence/csh-110/Dockerfile.linux -t cshell-test:csh-110 .
docker create --init --name cshell-csh110-validation cshell-test:csh-110 \
  sh -c 'python3 docs/evidence/csh-110/validate.py linux && python3 docs/evidence/csh-110/supplement.py linux'
docker start -a cshell-csh110-validation
docker cp cshell-csh110-validation:/work/build/csh110-validation ./build/csh110-linux-results
docker cp cshell-csh110-validation:/work/build/csh110-supplement ./build/csh110-linux-supplement
docker rm cshell-csh110-validation

python3 docs/evidence/csh-110/retain.py build/csh110-validation build/csh110-supplement \
  build/csh110-linux-results build/csh110-linux-supplement
python3 docs/evidence/csh-110/verify.py
```

Native provisioning copies the predecessor's qualified gfind into ignored
`build/local-bin`. Linux validation uses the unprivileged Debian Docker identity;
no separately hosted native-Linux run is claimed. `SHA256SUMS` covers retained
files except itself.

## Development disposition

The first Linux selected-profile run completed its case assertions but failed
while serializing the new setup readback: its byte strings were not converted
to the report's hexadecimal representation. The native run was interrupted
before it reached the same report boundary. Their raw logs are retained in
`development/`; they are not final evidence. The fix encodes the recorded setup
observations, preserves the internal oracle, and adds a regression requiring
JSON serialization for both passing and failing records. The focused 116-assertion
run and all five new harness tests then passed. Both complete platform
runs were restarted on the final inputs, without changing utility expectations.
