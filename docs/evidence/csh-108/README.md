# CSH-108 mkdir parent graph qualification

This increment adds 60 independently authored mkdir cases, required in direct
execution and cshell string/file/stdin modes (240 assertions). It is stacked on
CSH-107 commit `66974f8`; integration remains gated on that dependency. No
selected-profile allowances or production/vendor source changes are introduced.

## Contract and independent oracle

The [mkdir OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html)
contract gives intermediate parents owner write/search permissions in addition
to the unmasked default permissions, independently of the final `-m` mode.
Existing directory operands are ignored. The symbolic final modes follow the
[chmod rules](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html).
The authored matrix uses literal intermediate modes 0750, 0700 and 0300 for
child-only masks 027, 077 and 777, and literal final modes for default, numeric
0700, empty symbolic assignment and omitted-who copy assignment.

Five graphs cover sibling leaves sharing parents, repeated new and existing
operands, a directory symlink both as an operand and as a prefix, and continuation
past a middle regular-file or dangling-symlink prefix obstruction. All fixture
objects are private. Pre-exec lstat records independently establish existing
directory/file/link identities and modes; post-exec checks require preservation,
unchanged file bytes and link targets, and absence of the dangling target.
The child helper sets and reads back the mask, then independently creates a
probe directory and FIFO and requires their exact masked modes before exec.
Missing or incorrect probe markers fail the case.

Successful cases require empty output channels and zero status. Obstruction
cases require empty stdout, a nonempty diagnostic and positive status, plus both
successfully created sibling leaves. Diagnostic wording and positive error codes
are not prescribed. Every authored final/intermediate mode and cleanup must
match. These observations do not measure transient permissions or qualify
arbitrary namespaces, races, ACLs, special bits, capacity or path limits.

## Harness regressions

Five new tests cover the matrix and literal expected modes, rejection of
corrupted parent/leaf/existing modes, inode identities, link targets, channels,
status and mask markers; partial setup failure without dispatch; failed exec
and timeout in all four modes; symlink boundaries during restoration; and
timeout after an owned provider creates the restrictive parent/leaf graph.
Timeout cases require the provider to be reaped and the fixture removed.
Restoration checks each authored path component with lstat, restores directories
top-down after assertions, and avoids following symlinks. This is bounded cleanup
of owned children after collection, not a general namespace-race guarantee.

The initial timeout regression exposed an unreadable harness PID file under
mask 777. The harness now restores that test-owned file's read permission after
child collection. Initial failure and final focused results are retained under
`development/`; no utility expectation was changed.

## Selected providers and boundaries

The selected GNU coreutils 9.7 mkdir is unchanged from CSH-107. Its exact path,
SHA-256, archive digest, configure flags and build targets are retained in each
platform manifest alongside the build logs. Apple mkdir retains masked group
bits in the copy-assignment final mode under masks 077 and 777, producing 0640
instead of 0600 or 0000. All five graphs and four invocation modes reproduce
this CSH-107 defect (40 additional stock failures). Linux stock passes these
new cases. Stock audits remain separate and strict. The verifier compares every CSH-107 expectation and stock failure and
requires the full new matrix, cleanup and one final source digest.

Every unsupplied environment has an explicit individual disposition and next
owner in the current residual ledger and section map:
[CSH-109](../../tickets/CSH-109-filesystem-environment-residuals.md)
([#229](https://github.com/melliott18/cshell/issues/229)). All 21 utility rows and
four original U-040 conditions remain open. Utility/libc/platform vendors retain
implementation ownership; U-034/U-040 remain partial.

## Validation

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 11735 pass, 0 fail | 11775 pass, 0 fail |
| New parent graph assertions | 240 pass | 240 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 133 pass | 10 / 133 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Stock full / provider failures | 745 / 16 retained | 578 / 8 retained |
| Harness suite | 93 tests pass | 93 tests, one Darwin-only skip |
| Regular format / compiled database | 14 / 5 pass | 14 / 5 pass |

Final command statuses, assertion counts and source identity are recorded in
`summary.json`, platform command records and `stock-failure-comparison.json`.
Native macOS and unprivileged Debian/Linux Docker validation use the same
selected assertions. No separately hosted native-Linux or sanitizer run is
claimed; this increment changes Python fixtures and accounting, not C code.

## Reproduction

```sh
# Native provisioning requires gtest, g[, gfind and gdd on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-108/validate.py native
python3 docs/evidence/csh-108/supplement.py native

docker build -f docs/evidence/csh-108/Dockerfile.linux -t cshell-test:csh-108 .
docker create --init --name cshell-csh108-validation cshell-test:csh-108 \
  sh -c 'python3 docs/evidence/csh-108/validate.py linux && python3 docs/evidence/csh-108/supplement.py linux'
docker start -a cshell-csh108-validation
docker cp cshell-csh108-validation:/work/build/csh108-validation ./build/csh108-linux-results
docker cp cshell-csh108-validation:/work/build/csh108-supplement ./build/csh108-linux-supplement
docker rm cshell-csh108-validation

python3 docs/evidence/csh-108/retain.py build/csh108-validation build/csh108-supplement \
  build/csh108-linux-results build/csh108-linux-supplement
python3 docs/evidence/csh-108/verify.py
```

Native provisioning uses a copy of the predecessor's qualified gfind in ignored
`build/local-bin`. Selected commands must exit zero; full stock and stock provider
audits must remain nonzero. `SHA256SUMS` covers retained files except itself.
