# CSH-093 pathname utility output-error evidence

Collected 2026-10-17 in a separate worktree on published CSH-092 commit
`00a789336f9c3124941a38281868c90d38a79073`. Integration remains gated on the unmerged CSH-092 dependency.

## Scope and independent oracle

Issue 8 [pwd](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html),
[basename](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/basename.html)
and [dirname](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dirname.html)
STDOUT and EXIT STATUS define normal output and positive error status.
`normative-sources.json` records retrieved page hashes. Direct HTTPS retrieval
succeeded after the web reader returned 403.

The child-only helper closes stdout or replaces it with a pipe whose reader is
already closed, then independently requires EBADF or EPIPE from `os.write`.
SIGPIPE is ignored before the broken-pipe probe and remains ignored across exec,
so the utility can observe the write error. On Linux the helper opens `/dev/full`
without following symlinks, verifies a character device with major/minor 1/7,
and requires ENOSPC from a write before exec. No host volume is filled. This
virtual device is not actual filesystem exhaustion, quota evidence or libc
fault injection.

Eight cases exercise external pwd under both faults with `-P`, `-L`, `-L -P`
and `-P -L`. PWD is unset, so logical forms use the unchanged physical directory.
Linux adds the same four forms plus basename/dirname against the virtual device.
All cases run directly and through cshell string/file/stdin modes, totaling
32 assertions on macOS and 56 on Linux. The wrapper always execs the inventoried
external utility; these are not pwd builtin tests.

Assertions require positive status, empty captured stdout, a diagnostic, intact
fixture bytes/mode/symlink, and cleanup. Empty captured stdout follows from the
armed unusable descriptor. Nonempty diagnostics are a strict selected-provider
observation: pwd CONSEQUENCES OF ERRORS explicitly excludes stdout write errors
from its no-output/diagnostic rule. No exact vendor diagnostic wording is claimed.
Existing successful-output cases remain required in the full profile.

Missing, malformed, non-object, inconsistent, setup-failure and exec-failure
markers fail independently of the utility error oracle. Marker validation now
checks a positive integer PID and errno, and the Linux device identity. Five new
harness regressions cover immutable cases, marker/channel/status/effect corruption,
missing setup and failed exec in every mode, a falsely successful kernel probe,
invalid device markers, and bounded timeout/reaping/cleanup in every mode.
These injections qualify harness failure detection, not utility fault recovery.

## Results and reproduction

The required selected command set passes on macOS 14.8.7 arm64 UID 501 and
Debian 12 arm64 Docker UID 10001. Each platform passes 10 ownership tests and
71 harness tests. No sanitizer or hosted-CI run is claimed.

| Command / profile | macOS | Linux |
| --- | --- | --- |
| `make test-host-profile`: host integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1427 pass, 0 fail | 1467 pass, 0 fail |
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
| Stock `make test-host-filesystem-audit` | 1334 pass, 73 fail | 1401 pass, 42 fail |
| Stock `--extended-only --provider-audit` | 152 pass, 16 fail | 176 pass, 8 fail |

Stock Make audits exit 2 and direct stock provider audits exit 1, as expected.
`stock-failure-comparison.json` verifies exactly the same failure IDs/modes as
CSH-092. Every earlier selected assertion is retained, every filesystem case
reports successful cleanup, and all final native/Linux source maps match exactly.
Shared ticket identity validation passes with two historical shared-branch warnings.
`SHA256SUMS` covers retained artifacts other than this narrative.

All selected targets require zero allowances. Final reports record source hash
`e505f5625531637050c84684a530c8d899ba944b07c342e9c609af48bd4a91ee`.
Run:

```sh
# Native PATH must provide gtest, g[, gfind and gdd.
make -j4 cshell host-profile
python3 docs/evidence/csh-093/validate.py native

# A clean Linux build can use the repository Dockerfile.
docker build -t cshell-test:csh-093-clean .
docker run --rm --init cshell-test:csh-093-clean \
  python3 docs/evidence/csh-093/validate.py linux
```

The validation script runs every CSH-093 required selected target, the new output
target, and two separate stock audits. JSON retains expected/actual channels,
status, effects, setup errors, cleanup and provider/source identities. No selected
allowances are added and no provider sources or build flags change.

Native gfind was copied from the ignored CSH-092 build; other local providers
were rebuilt. Linux uses a private writable image based on the CSH-091 Debian
image, with updated sources and rebuilt providers, UID 10001 and Docker `--init`.
Archive metadata is removed before qualification. Retained image/build logs and
provider manifests identify the exact environment. No host filesystem is mounted.

## Remaining ownership

[CSH-094](../../tickets/CSH-094-filesystem-environment-residuals.md)
([#199](https://github.com/melliott18/cshell/issues/199)) retains every unsupplied
contract with its environment, reason and utility/libc/platform implementation
owner. Allocation failures, other output failures, logical namespace changes,
locales, credentials, ACLs and capacity remain open. All four original U-040
conditions remain open. Historical evidence and stock failures are preserved;
this uses CSH-093's explicit-disposition acceptance alternative and does not
qualify whole utilities.
