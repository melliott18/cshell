# CSH-087 operand and recursive decision evidence

Collected 2026-10-11 in a separate worktree based on CSH-086 published commit
`dfdb773581a765d8c79d02f234ade2263d80eaeb` (implemented, unmerged). This change
adds 22 cases / 68 assertions and uses the ticket's explicit-disposition
alternative for unsupplied environments. No complete utility is qualified.

## Results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Inventory + 10 inventory and 40 filesystem harness tests pass | Same checks pass |
| `make test-host-profile`: integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1133 pass, 0 fail | 1149 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-isolated` | 112 pass, 0 fail | 112 pass, 0 fail |
| `make test-host-filesystem-interactive` | 39 pass, 0 fail | 39 pass, 0 fail |
| `make test-host-filesystem-decisions` | 68 pass, 0 fail | 68 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 1040 pass, **73 fail** | 1089 pass, **36 fail** |
| Stock `--extended-only --provider-audit` | 152 pass, **16 fail** | 176 pass, **8 fail** |

Selected commands exit zero; stock Make audits exit 2 and direct stock audits
exit 1. All filesystem records require successful cleanup, including failures.
Selected-PATH `make test-runtime test-pty` passes on both platforms. These are
local native/Docker runs, not hosted CI or a new sanitizer qualification claim.
Final build/test source-input SHA-256:
`a724c8c4d77b7b389e02b7d3d2a8a6cf793e3b2ad8d060ca0dda89123edd1ab5`.

## Independent oracles

The Issue-8 [cp](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cp.html),
[mv](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html) and
[rm](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) DESCRIPTION,
OPTIONS, STDIN, STDERR and EXIT STATUS sections define the exercised decisions.
`normative-sources.json` records the freshly retrieved page hashes. The web
reader returned HTTP 403; direct HTTPS retrieval supplied the pages for review.

Authored source and destination bytes check all four two-operand yes/no
combinations for cp/mv. Missing-middle cases require a diagnostic at that
position, nonzero status, the chosen first-operand effect, and successful
processing of the final operand. A two-level, one-child cp tree has recursive
overwrite yes/no cases. rm cases reject descent and continue, remove a child
then accept/decline final directory removal, remove a symlink without deleting
its target, and exercise last -f/-i precedence. Two ordinary mv cases replace an
empty destination directory or reject a nonempty destination while preserving
source and destination contents. These are bounded same-device graphs.

Twenty terminal cases run through direct provider exec and cshell string/file
dispatch. Each answer waits for its target and question mark; the full stderr
transcript must match the complete ordered sequence. Known Apple/GNU C-locale
prompt spellings are accepted because wording is unspecified. A missing-operand
diagnostic must identify the selected executable (basename or full path) and
the authored operand, occupy one line at the expected position, and cannot
absorb an extra prompt. The inherited helper independently marks terminal
ownership/descriptor setup and captures stdout separately. Two directory cases
also run through stdin dispatch; terminal cases make no stdin-script-mode claim.

No selected provider, source patch, build flags or allowance changes. The pinned
CSH-086 cp repair passes all new assertions. Apple stock cp adds twelve
nonzero-decline failures across the three terminal modes; its source/destination
effects still match. Linux stock adds no new failures. All earlier assertions
are retained and every old assertion ID remains in the current map and ledger.

## Setup, failure and cleanup regressions

Four added harness tests reject reordered, omitted and duplicated prompts;
missing/extra/unrelated diagnostics; stopped/reversed continuation; and retained
move sources. A partially constructed recursive symlink fixture must fail setup
and clean up. Timeout tests read the first response, acknowledge it, then stall
before the second prompt; all three terminal modes require timeout failure,
disappearance of the owned PID and removal of the fixture. Existing wrong-channel,
missing-marker and unavailable-terminal checks remain mandatory.

During development an over-specific diagnostic prefix expected GNU cp to print
its full path on every channel. Both platforms instead produced a basename in
error diagnostics while prompts used the full path. This caused six transcript
failures per selected run with correct status/effects. The final matcher accepts
both executable-name forms while preserving ordered prompts and diagnostic
content checks. A regression explicitly exercises both forms. The retained
`development-linux-profile.json.gz` records that harness failure; it is not final
evidence and has an earlier input hash. Initial macOS stock exploration likewise
reproduced the twelve decline failures before the selected profile was built.

## Reproduction and retained artifacts

```sh
# Native provisioning needs gtest, g[, gfind and gdd on PATH.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive \
  test-host-filesystem-decisions
make test-host-filesystem-audit # expected stock failure
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty

docker build -t cshell-test:csh-087 .
docker run --rm cshell-test:csh-087 make test-host-inventory test-host-profile \
  test-host-filesystem-allocation test-host-filesystem-provider-audit \
  test-host-filesystem-residual test-host-filesystem-isolated \
  test-host-filesystem-interactive test-host-filesystem-decisions
```

The native gfind is the unchanged CSH-086 binary copied into ignored
`build/native-findutils/bin` and prepended only to provisioning PATH. The
selected providers were rebuilt locally from the retained sources. Manifests,
cp configure/build logs, report executable hashes and source-input hashes retain
exact provenance. Linux used the Dockerfile's unprivileged UID 10001. Its
container was retained for report export, then removed. The two harness-file
corrections and profile README were copied into that private container before
final qualification; final source-input hashes equal the native worktree.

Compressed JSON retains actual argv/environment, raw terminal/stdout/status,
expected and observed effects, setup errors, capture errors, provider/package
identities and cleanup. Compressed logs retain Make commands and counts.
`SHA256SUMS` covers all retained artifacts.

## Open dispositions

The [current section map](../../../tests/host_filesystem_contracts.json),
[residual ledger](../../../tests/host_filesystem_residuals.json), ownership
manifest and [CSH-088](../../tickets/CSH-088-filesystem-remaining-environments.md)
retain every unsupplied utility contract with required environment, reason and
vendor implementation ownership. All four original condition IDs remain open.
Arbitrary graphs, negative recursive-child responses, non-C prompts, EXDEV,
mount/depth boundaries, ACL/privileged credentials, quotas, real capacity
exhaustion, namespace races and libc-internal faults are not supplied. Kernel
EFBIG/EPIPE, call-site ENOMEM and virtual-device ENOSPC retain their distinct
inherited scope. No privileged provisioning or host-volume filling occurred;
historical CSH-064 and prior qualification evidence is unchanged.
