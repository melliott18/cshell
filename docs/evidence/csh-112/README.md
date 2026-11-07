# CSH-112 touch permission qualification

This increment adds 20 independently authored touch cases, required in direct
execution and cshell string/file/stdin modes (80 assertions). It is stacked on
CSH-111 commit `2489a44`; integration remains gated on that dependency. Shell
runtime, selected providers and vendor sources are unchanged.

## Contract and oracle

The [touch specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html)
requires per-operand creation or timestamp updates, selective access/modification
fields, silent no-create handling and a positive status on errors. The retrieved
normative page digest matches the retained section map. Five boundaries each
cover default, `-a`, `-m` and explicit `-a -m` selections:

- Search denial for an existing middle operand.
- Search denial for a missing middle operand.
- Creation denial for a missing middle operand in a non-writable parent.
- Silent `-c` handling of that missing operand.
- Successful explicit timestamp changes on an owned, non-writable existing
  file inside a non-writable but searchable parent.

Every invocation also changes accessible files before and after the middle
operand, requiring continuation even after its failure. Authored UTC time
`200109090146.40` corresponds to integer nanoseconds `1000000000000000000`.
Distinct fractional access/modification baselines detect unselected-field
changes. The fixture proves both timestamp values representable on each actual
inode before dispatch; neither the provider nor another utility supplies them.

All regular files have mode 0400. Independent write-open probes must return
kernel EACCES, while owner timestamp updates must succeed. Immediately before
dispatch, a stat probe through the unsearchable parent, or an exclusive-create
probe in the non-writable parent, must return EACCES. Unexpected success or a
different error is a setup failure. Probe files are removed before execution.
The directory's armed mode is checked afterward. Restoration always precedes
inspection and teardown and does not follow an unexpectedly substituted symlink.

Metadata snapshots precede all content reads. Checks require exact selected and
preserved timestamps, unchanged device/inode, type/mode, link counts and bytes,
and continued absence of missing operands. Successful cases require empty
channels and zero status; failing cases require empty stdout, nonempty stderr
and positive status. Diagnostic wording and the particular positive status are
not prescribed. Every fixture must be removed.

A helper records the exact provider and unprivileged identity before exec, and
records any returned exec error separately. Missing, malformed, wrong-provider,
wrong-identity and failed-exec records fail, preventing launch errors from
satisfying negative utility cases. The shell modes exercise helper dispatch and
exact-provider exec; these additions do not independently qualify bare-name
PATH lookup.

Five added harness tests cover all case/mode combinations, deliberately changed
timestamps/identities/content/modes/link counts/channels/status, dispatch-record
corruption, unexpected probe success and wrong errno, partial setup, failed exec,
timeout/reaping and symlink-safe cleanup.

## Scope and remaining owners

These are ordinary owner-mode kernel permission witnesses with fixed times.
They do not supply alternate credentials, ACLs, libc/call-site injection,
filesystem exhaustion, live clocks or arbitrary namespaces. The existing GNU
coreutils 9.7 + IANA tzcode 2025b touch provider is unchanged. Its executable,
source/archive, build and configuration identities are retained per platform.

All 21 utility dispositions and four original U-040 conditions remain open under
[CSH-113 / #237](../../tickets/CSH-113-filesystem-environment-residuals.md).
Utility/libc/platform vendors retain implementation ownership. U-034/U-040 and
whole-utility contracts remain partial; historical evidence is unchanged.

## Reproduction

```sh
# Native: gfind, gtest, g[ and gdd must be on the provisioning PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-112/validate.py native

docker build -f docs/evidence/csh-112/Dockerfile.linux -t cshell-test:csh-112 .
docker run --init --name cshell-csh112-validation cshell-test:csh-112 \
  python3 docs/evidence/csh-112/validate.py linux
docker cp cshell-csh112-validation:/work/build/csh112-validation ./build/csh112-linux-results
# Retain both result directories here before verifying:
python3 docs/evidence/csh-112/verify.py
docker rm cshell-csh112-validation
```

The Linux image layers source/tests on the preserved CSH-111 image and executes
as its unprivileged fixture account. This is Linux/Docker evidence, not a separate
hosted native-Linux run. No new sanitizer or general-runtime sweep is claimed.

The initial native build/provisioning attempts failed because `gfind` was absent
from PATH. The prematurely started validation was interrupted during its harness
checks and is not a pass. These logs remain under `development/`. Final native
provisioning uses a local copy of CSH-111's exact `gfind` executable (SHA-256
`cc04c2a28dce26e175e85a84d51ec897d0b4d77cb2de0a897602781282338776`)
and the same installed GNU coreutils. No assertions or allowances were changed.

## Validation record

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12091 pass, 0 fail | 12131 pass, 0 fail |
| New touch permission assertions | 80 pass | 80 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 154 pass | 10 / 154 pass |
| Stock full / provider failures | 749 / 16 retained | 578 / 8 retained |

All ticket-listed selected targets pass without allowances. Separate strict stock
audits deliberately return nonzero; the verifier compares their failure sets to
CSH-111. Raw output, commands, exit statuses and timings are retained by platform.
The final verifier also requires unchanged predecessor expectations, exactly 80
new profile assertions, current source identities, exact provider provenance,
independent permission/timestamp probes, checked filesystem effects and cleanup.

`python3 docs/evidence/csh-112/verify.py` passes all exact comparisons; its
results are retained in `summary.json` and `stock-failure-comparison.json`.
