# CSH-091 physical working-directory evidence

Collected 2026-10-15 in a separate worktree based on published CSH-090 commit
`5873782cbcfdf24fddd9778128aaf8585dd8ab83`. CSH-090 remains unmerged; integration is gated on that dependency.
Eight cases add 32 assertions without changing selected providers.

## Independent environments and oracles

Issue 8 [pwd](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html)
DESCRIPTION, OPTIONS, STDOUT, STDERR, EXIT STATUS and CONSEQUENCES OF ERRORS
supply the physical-path, output-channel and error-status requirements.
`normative-sources.json` records the retrieved source hash, matching the current
section map. The web reader returned HTTP 403; direct HTTPS retrieval succeeded.

Each fixture contains an owned `cwd-parent/cwd-leaf`. A child-only helper enters
the leaf and either renames the leaf, renames its parent, removes the leaf, or
removes both leaf and parent. It compares cwd device/inode before and after the
change with the harness's independent pre-dispatch measurement. It requires
ENOENT for the old pathname, then proves either the authored renamed pathname
with getcwd or ENOENT for a deleted cwd. The marker lives outside the changed
namespace. The parent process never changes its cwd.

The helper execs the exact inventoried external pwd. Both `-P` and `-L -P` are
checked through direct execution and cshell command string, file and stdin
modes. These are external-provider assertions, not tests of cshell's pwd builtin.
No helper assignment to PWD is made; application-written PWD values have
unspecified behavior in the selected standard. Logical-mode namespace changes
remain open. The mutations complete before exec, so these are deterministic
namespace states, not concurrent-race qualification.

Renamed directories require the exact physical pathname plus newline, empty
stderr and status zero. Deleted directories require empty stdout, a diagnostic
and positive error status. Namespace effects and cleanup are also mandatory.
A missing, malformed, inconsistent, unarmed or exec-failure marker fails the
assertion; helper failure cannot satisfy the expected utility error.

Six harness regressions cover all authored states and immutable specifications,
marker/output/status/effect corruption, incomplete setup, failed exec in every
input mode, wrong probes and partial mutations in a separate child, and timeout
cleanup with provider PID disappearance in every mode. The timeout check includes
a separate bounded reaping window for container init. These fault injections
validate the harness; they are not provider, libc or filesystem-fault evidence.

## Results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64 container, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Inventory + 10 ownership + 60 harness tests pass | Same checks pass |
| `make test-host-profile`: host integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1291 pass, 0 fail | 1307 pass, 0 fail |
| `make test-host-filesystem-allocation` | 240 pass, 0 fail | 200 pass, 0 fail |
| `make test-host-filesystem-provider-audit` | 168 pass, 0 fail | 184 pass, 0 fail |
| `make test-host-filesystem-residual` | 104 pass, 0 fail | 104 pass, 0 fail |
| `make test-host-filesystem-isolated` | 112 pass, 0 fail | 112 pass, 0 fail |
| `make test-host-filesystem-interactive` | 39 pass, 0 fail | 39 pass, 0 fail |
| `make test-host-filesystem-decisions` | 68 pass, 0 fail | 68 pass, 0 fail |
| `make test-host-filesystem-metadata` | 64 pass, 0 fail | 64 pass, 0 fail |
| `make test-host-filesystem-recursive` | 30 pass, 0 fail | 30 pass, 0 fail |
| `make test-host-filesystem-path-limits` | 32 pass, 0 fail | 32 pass, 0 fail |
| `make test-host-filesystem-cwd` | 32 pass, 0 fail | 32 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 1198 pass, 73 fail | 1241 pass, 42 fail |
| Stock `--extended-only --provider-audit` | 152 pass, 16 fail | 176 pass, 8 fail |

All selected commands exit zero and require zero allowances. Stock Make audits
exit 2; direct stock provider audits exit 1. `stock-failure-comparison.json`
confirms that every failure ID and input mode is unchanged from CSH-090 on each
platform. Every filesystem record reports successful cleanup.

All final JSON reports record build/test input SHA-256
`30c1f6308293524d04e18cf061dadad0d773cf65bc1f2a7a2ad586ce67542ace`.
Native and Linux source maps match exactly. The Linux allocation report was
refreshed after an owner-title metadata correction; both allocation runs passed.
The extra command and log are retained separately.

## Provenance and reproduction

The native gfind executable was copied from the ignored CSH-090
`build/native-findutils/bin/gfind`; its exact hash appears in the selected
manifest. Other providers were built/provisioned in this worktree. Build and
configure logs preserve the pinned source, patches and build flags. No host
executable was replaced.

The Docker image uses Debian 12 arm64 and unprivileged UID 10001, with `--init`.
Updated source/test inputs were copied into the private container before their
qualification; source identity records enumerate the actual inputs. The image
identity and separate provider manifests are retained. No privileged, sanitizer
or hosted-CI qualification is claimed.

```sh
# Native PATH must contain gtest, g[, gfind and gdd.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive \
  test-host-filesystem-decisions test-host-filesystem-metadata \
  test-host-filesystem-recursive test-host-filesystem-path-limits \
  test-host-filesystem-cwd
make test-host-filesystem-audit # separate nonzero stock result
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json

docker build -t cshell-test:csh-091 .
# Run the same make targets and stock command above in the unprivileged image.
docker run --rm --init cshell-test:csh-091 make test-host-filesystem-cwd
```

Compressed JSON retains expected/actual output, status, effects, setup errors,
cleanup, credentials, providers and source identities. Command records preserve
argv and exit status. `SHA256SUMS` covers every retained artifact other than this
narrative. The shared allocator reserved CSH-092/#195; live identity validation
passes with two historical shared-branch warnings.

## Remaining ownership

[CSH-092](../../tickets/CSH-092-filesystem-environment-residuals.md)
([#195](https://github.com/melliott18/cshell/issues/195)) retains all unsupplied
contracts, with utility/libc/platform vendors retaining implementation ownership.
All four original U-040 conditions remain open. Physical cwd rename/removal does
not supply inaccessible ancestors, total PATH_MAX, allocation/stdio errors,
logical-mode namespace behavior, arbitrary races, mounts, quotas or capacity
exhaustion. No whole utility is qualified. Historical CSH-064 and later evidence
is unchanged. This uses the explicit-disposition acceptance alternative.
