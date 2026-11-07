# CSH-097 reference timestamp evidence

Collected 2026-10-21 in a separate worktree based on CSH-096 commit
`cf59e86`. Integration remains gated on that unmerged dependency.

## Scope and independent oracle

Issue 8 [touch](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html)
DESCRIPTION and OPTIONS define reference timestamps, field selection, following
operand symlinks through utimensat with flags zero, and silent no-create behavior.
STDOUT, STDERR and EXIT STATUS define the channel/status contract.
`normative-sources.json` records the retrieved page hash (direct HTTPS retrieval
after the web reader returned 403).

`tests/host_filesystem_reference.py` supplies 28 cases, each run by direct exec
and cshell string/file/stdin dispatch: 112 assertions per platform. Three reference
spellings (regular file, one symlink, two-link chain) and two target spellings
(hard link, two-link chain) each use default, access-only, modification-only and
explicit-both selection. Four additional cases require silent `-c` continuation
past a missing path and dangling chain to an existing target.

Python authors two distinct fractional reference timestamps and two different
fractional target baselines. Before execution, the exact target and reference
inodes are set and independently read back; the target is restored to its
baseline. stat/lstat independently confirm distinct reference/target inodes,
target hard-link identity, symlink resolution and absent referents. Failed or
rounded setup fails before provider execution. Expected timestamps are never
learned from touch, a second utility, the current clock or provider output.

All graph metadata is captured before any content read can change a shared
inode's atime. Both target names must show the exact selected fields; reference
fields and unselected target fields must persist. Inode identities, modes, link
counts, symlink modification times and link texts must persist, as must file
content and absent paths. Symlink access times are deliberately not asserted:
pathname traversal/readlink can update them. Status must be zero and both
channels empty. Records retain pre/post metadata, exact arguments, authored
expectations, provider hashes, output/status, effects and cleanup.

These are ordinary private inode graphs. No privileged provisioning, allocation
injection, kernel faults or filesystem exhaustion occurs. The cases do not
qualify arbitrary graphs, new-file timestamps, current-clock behavior, unsupported
ranges, namespace races, inaccessible paths, ACLs or different identities.

Four harness regressions check independently fixed field expectations, corrupted
timestamps/content/identities/links/absence/channels/status, failed or rounded
setup, and failed exec/timeout cleanup in every invocation mode. Timeout tests
verify that the owned child has exited and the private fixture is removed.

## Results

All required targets passed on native macOS 14.8.7 arm64 UID 501 and Debian 12
arm64 Docker UID 10001. Each platform passed 10 ownership tests and 88 filesystem
harness tests. The selected profiles have zero allowances. Stock failure IDs
and invocation modes are identical to CSH-096.

| Profile/target | macOS pass/fail | Linux pass/fail |
| --- | --- | --- |
| Host integration | 1162 / 0 | 1162 / 0 |
| Selected filesystem profile | 1931 / 0 | 1971 / 0 |
| Allocation faults | 240 / 0 | 200 / 0 |
| Selected provider audit | 168 / 0 | 184 / 0 |
| Private residual environments | 104 / 0 | 104 / 0 |
| Isolated environments | 112 / 0 | 112 / 0 |
| Owned terminal overwrites | 39 / 0 | 39 / 0 |
| Operand/recursive decisions | 68 / 0 | 68 / 0 |
| Metadata/timestamps | 64 / 0 | 64 / 0 |
| Recursive prompts | 30 / 0 | 30 / 0 |
| Pathname limits | 32 / 0 | 32 / 0 |
| Physical cwd | 32 / 0 | 32 / 0 |
| Creation modes | 104 / 0 | 104 / 0 |
| Output errors | 32 / 0 | 56 / 0 |
| Logical cwd fallback | 48 / 0 | 48 / 0 |
| Numeric magic | 184 / 0 | 184 / 0 |
| Calendar timestamps | 160 / 0 | 160 / 0 |
| New reference timestamps | 112 / 0 | 112 / 0 |
| Stock full audit | 1838 / 73 | 1905 / 42 |
| Stock provider audit | 152 / 16 | 176 / 8 |

Final source identity: `c6c1e8008cf3feb48e62b29dd934ccad82065a84874e901917f50e446cd948a3`. All retained final
reports and current build/test inputs share this digest.

Initial all-pass command logs are retained separately. Review corrected the
report ticket/predecessor metadata, then every required target and both stock
audits ran again. The Linux container received the corrected runner before its
second run; `linux-environment.json` records the base image, overlay, unprivileged
identity, init setting and absence of host mounts. No behavioral expectation
changed between runs.

## Validation and reproduction

```sh
# Native PATH must provide gtest, g[, gfind and gdd.
make -j4 cshell host-profile
python3 docs/evidence/csh-097/validate.py native

docker build -f docs/evidence/csh-097/Dockerfile.linux -t cshell-test:csh-097 .
docker create --init --name cshell-csh097-validation cshell-test:csh-097 \
  python3 docs/evidence/csh-097/validate.py linux
docker start -a cshell-csh097-validation
docker cp cshell-csh097-validation:/work/build/csh097-validation ./build/csh097-linux-results
docker rm cshell-csh097-validation

python3 docs/evidence/csh-097/verify.py
```

`validate.py` runs every ticket-required target plus the reference target. It
retains nonzero stock full and provider audits separately, requiring command
statuses 0, 2 and 1. `verify.py` checks prior selected IDs/modes, exactly 112 new
passing assertions, independently armed timestamp/inode probes, exact fields
and channels, unchanged stock failure IDs/modes, cleanup, and one final source
digest across hosts. `summary.json` records final totals; command logs and provider
manifests retain diagnostics and build identities. `SHA256SUMS` covers retained
artifacts other than this narrative.

Native qualification uses an unprivileged macOS identity; gfind was copied from
CSH-096's ignored build and other local providers were rebuilt from pinned sources.
Linux uses the recorded CSH-096 Debian image with the test/tool overlay, Docker
`--init`, UID 10001 and no host mounts. No provider implementation, build flag or
selected allowance changes. No sanitizer or hosted-CI qualification is claimed.

## Remaining ownership

[CSH-098](../../tickets/CSH-098-filesystem-environment-residuals.md)
([#207](https://github.com/melliott18/cshell/issues/207)) retains all 21 utility
residuals with explicit environments, reasons and utility/libc/platform
implementation ownership. All four original U-040 conditions remain open.
Historical evidence and stock failures are preserved. This uses the ticket's
explicit-disposition alternative; no whole utility or U-034/U-040 completion
is claimed.
