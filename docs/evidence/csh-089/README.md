# CSH-089 recursive decision evidence

Collected 2026-10-13 in a separate worktree based on published CSH-088 commit
`3bb23df15fd49456f2bfc38606fc8813ec111ec4`. CSH-088 remains unmerged; this
implementation is stacked on that branch and integration remains gated on it.
Ten cases add 30 assertions. No complete utility is newly qualified.

## Results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64 container, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Inventory, 10 inventory tests, 49 filesystem harness tests pass | Same checks pass |
| `make test-host-profile`: integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1227 pass, 0 fail | 1243 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-isolated` | 112 pass, 0 fail | 112 pass, 0 fail |
| `make test-host-filesystem-interactive` | 39 pass, 0 fail | 39 pass, 0 fail |
| `make test-host-filesystem-decisions` | 68 pass, 0 fail | 68 pass, 0 fail |
| `make test-host-filesystem-metadata` | 64 pass, 0 fail | 64 pass, 0 fail |
| `make test-host-filesystem-recursive` | 30 pass, 0 fail | 30 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 1134 pass, **73 fail** | 1177 pass, **42 fail** |
| Stock `--extended-only --provider-audit` | 152 pass, **16 fail** | 176 pass, **8 fail** |

Selected commands exit zero; stock Make audits exit 2 and direct stock audits
exit 1. Every filesystem case records successful cleanup. The stock failure
comparison preserves all CSH-088 failure IDs and modes. Linux adds six failures
for declined nested descent followed by either parent answer, in three terminal
modes. Stock GNU skips the required parent prompt and moves to the next operand;
the bounded harness times out waiting for that prompt and kills/reaps the owned
process. Its captured status is a harness timeout termination, not a normal
utility exit. These results remain failures, never allowances.

Native selected-PATH `make test-runtime test-pty` also passes: 3950 runtime
assertions plus the prompt and terminal suites. No new Linux runtime/PTY,
sanitizer or hosted CI qualification is claimed.

## Independent oracles and provider repair

Issue 8 [rm](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html)
DESCRIPTION 2b-2e and 3-4 define separate descent, child and final-directory
decisions and continuation; STDERR and EXIT STATUS define the output channel
and error class. `normative-sources.json` retains the retrieved source hash,
identical to the existing section map. The web reader returned HTTP 403;
direct HTTPS retrieval succeeded.

Each fixture is private and has at most one child per traversed directory, so
no expected prompt depends on readdir ordering. Authored bytes and symlink text
supply the effect oracle. Each response waits for the expected target and a
question mark. Complete C-locale transcripts, empty stdout, status, surviving
bytes/directories/link text, absent entries and an untouched outside target are
checked. Error transcripts must name exactly the retained parent, not a path
sharing its prefix. Accepting removal of a still nonempty parent requires a
positive error and a diagnostic before the later operand is processed; the
oracle does not claim a kernel errno from vendor diagnostic wording. Apple
reports Permission denied and GNU reports Directory not empty for these cases.

An exec helper independently records controlling-terminal ownership, foreground
process group and terminal stdin/stderr, while capturing stdout separately.
The three modes are direct provider exec and cshell command string/script file;
shell stdin mode is excluded because stdin carries interactive responses.

The selected profile now builds rm alongside the existing cp from the pinned
GNU coreutils 9.7 archive. `rm-parent-prompt.patch` bypasses the marked-ancestor
shortcut only for explicit `-i`, retaining the final parent decision required
by DESCRIPTION 2d. Existing root protection, traversal, ordinary removal and
non-interactive shortcuts remain. No wrapper rewrites output or status. Both
platforms select this source; manifests retain archive, patch and executable
hashes plus configure options, and configure/build logs are retained. This is a
local provider repair, not an accepted upstream change. NLS, ACL, SELinux and
GMP remain disabled and those environments remain outside this qualification.

Five new harness regressions reject omitted/reordered prompts, missing or
wrong-parent diagnostics, wrong effects/status/output channels, incomplete
setup and stalled providers after a declined response in all three modes.
They also check complete Apple/GNU simple-prompt spellings independently of
the host OS. These tests qualify the harness's failure detection, not utilities.

## Source and environment provenance

All final JSON reports retain actual build/test input SHA-256
`5f008099b5ce74f8882997846ba31262fdb1f72b759bc24f48dd2720ec68e44c`.
Native provisioning uses the existing CSH-088 gfind executable copied to ignored
`build/native-findutils/bin`, with that directory prepended to provisioning PATH.
No host utility is overwritten.

`docker-image.json` identifies the Linux image. The final runner and harness
files were copied into the test container before final validation;
`container-source-sync.json` records their hashes. The actual source identity
matches native for every final report. The container runs as UID 10001 with
`--init`; it was removed after exporting evidence. A fresh build of this final
checkout includes those files directly.

Two development attempts are retained separately. The initial Linux container
omitted `--init`, leaving orphan zombies and correctly failing timeout cleanup
checks. Recreating it with an init process resolves that setup error. The first
native full profile found six failures in an older harness check that assumed
Apple prompt wording on Darwin. The check now accepts only the complete known
Apple/GNU spellings, and a regression rejects wrong targets and extra output.
Neither attempt is used as passing qualification.

## Remaining ownership and reproduction

All previous assertion IDs and normative source hashes are preserved. Current
section maps, the ownership manifest and the residual ledger assign each
unsupplied environment and all four original conditions to
[CSH-090](../../tickets/CSH-090-filesystem-environment-residuals.md) ([#191](https://github.com/melliott18/cshell/issues/191)).
Utility/libc/platform vendors retain implementation ownership. Arbitrary
branching and recursion, non-C prompts, mount/depth/path limits, races,
privileged identities, ACLs, quotas, real capacity exhaustion and libc-internal
faults remain unqualified. Prior evidence is unchanged; inherited call-site
ENOMEM, kernel EFBIG/EPIPE and virtual-device ENOSPC retain their distinct scope.
This uses the ticket's explicit-disposition acceptance alternative.

```sh
# Native provisioning PATH must include gtest, g[, gfind and gdd.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive \
  test-host-filesystem-decisions test-host-filesystem-metadata \
  test-host-filesystem-recursive
make test-host-filesystem-audit # expected nonzero stock result
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty

docker build -t cshell-test:csh-089 .
docker run --rm --init cshell-test:csh-089 make test-host-inventory test-host-profile \
  test-host-filesystem-allocation test-host-filesystem-provider-audit \
  test-host-filesystem-residual test-host-filesystem-isolated \
  test-host-filesystem-interactive test-host-filesystem-decisions \
  test-host-filesystem-metadata test-host-filesystem-recursive
```

Compressed JSON retains expected and actual outputs/effects, statuses, setup
errors, capture errors, cleanup, credentials and provider identities. Logs and
exit-status records retain commands and outcomes. `SHA256SUMS` covers retained
artifacts other than this narrative. Live ticket identity validation passes
with 90 reservations and two pre-existing historical shared-branch warnings.
