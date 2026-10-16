# CSH-092 creation-mask and final-mode evidence

Collected 2026-10-16 in a separate worktree stacked on published CSH-091 commit
`be04a3d6d00bb85b77c13f88e6a1b99041ccaae7`. CSH-091 remains unmerged; integration is gated on that dependency.
The change adds 26 cases / 104 assertions without changing selected providers.

## Independent environments and oracles

Issue 8 [mkdir](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html)
and [mkfifo](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkfifo.html)
DESCRIPTION, OPTIONS, OPERANDS, STDOUT, STDERR, EXIT STATUS and CONSEQUENCES OF
ERRORS supply creation, final permission, channel, status and continuation rules.
Their symbolic modes refer to
[chmod EXTENDED DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html).
`normative-sources.json` records the retrieved source hashes. The mkdir/mkfifo
hashes match the current section map. Direct HTTPS succeeded after the web reader
returned 403.

A child-only helper sets the authored mask and reads it back with `umask`. Before
exec it creates a separate directory with mode argument 0777 and FIFO with 0666,
measures their actual modes independently, and requires the exact masked values.
A mismatch, including a differing inherited-ACL effect, is a setup failure. The
helper removes both probes and execs the exact inventoried provider without
changing the mask again. Its marker remains readable under mask 0777 through an
explicit chmod of the marker alone. Neither the parent harness nor cshell's own
mask is modified by the helper.

Each of these five forms runs for both utilities under masks 027 and 077:

| Form | Final mkdir mode | Final mkfifo mode |
| --- | --- | --- |
| No `-m` | 0750 / 0700 | 0640 / 0600 |
| `-m go-w` | 0755 | 0644 |
| `-m u=rw,g=u,o=g,o-w` | 0664 | 0664 |
| `-m a-x,a+X` | 0777 | 0666 |
| `-m u=rx,g=u,o=` | 0550 | 0550 |

These are independently authored constants, not outputs from another utility.
The two utilities have different assumed initial modes; explicit `who` mode
operations do not use the mask. Conditional execute applies to directories, but
not to a FIFO with no initial execute permission. Copy clauses apply in order.

Two further cases use `first data last` operands, where `data` is an existing
regular file. Both new operands must be created with mode 0664 while the middle
operand keeps its original bytes and 0640 mode. Empty stdout, a diagnostic and a
positive error status are required. Four `mkdir -p` cases combine masks 027/777
with default/explicit final mode on `existing/new/a/leaf`. Intermediate modes are
0750/0300; the final default modes are 0750/0000, and explicit final mode is 0750.
The preexisting parent must retain both its inode and 0751 mode.

Every case runs through direct exec and cshell string/file/stdin modes. Types,
final modes, applicable bytes and identities, status and channels are checked.
No creation-time trace is captured: the requirements about permissions at every
instant remain explicitly unqualified. Missing, malformed, unarmed, inconsistent
or exec-failure markers cannot satisfy the utility's expected error. After
assertions, authored directories are restored top-down for removal, including on
setup failure and timeout.

Six harness regressions exercise all authored states and immutable specs,
marker/output/status/effect/identity corruption, partial setup before dispatch,
failed exec in every input mode, wrong mask/mode probes and partial helper setup,
and timeout/reaping/cleanup in every input mode with a mode-0000 directory.
These injections validate the harness, not utility fault recovery.

## Results

| Command / profile | macOS 14.8.7 arm64, UID 501 | Debian 12 arm64 container, UID 10001 |
| --- | --- | --- |
| `make test-host-inventory` | Inventory + 10 ownership + 66 harness tests pass | Same checks pass |
| `make test-host-profile`: host integration | 1162 pass, 0 fail/gaps | 1162 pass, 0 fail/gaps |
| Same command: filesystem | 1395 pass, 0 fail | 1411 pass, 0 fail |
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
| `make test-host-filesystem-creation` | 104 pass, 0 fail | 104 pass, 0 fail |
| Stock `make test-host-filesystem-audit` | 1302 pass, 73 fail | 1345 pass, 42 fail |
| Stock `--extended-only --provider-audit` | 152 pass, 16 fail | 176 pass, 8 fail |

All selected targets exit zero and require zero allowances. Stock Make audits
exit 2; direct stock provider audits exit 1. `stock-failure-comparison.json`
confirms that every stock failure ID and input mode is unchanged from CSH-091.
Every filesystem case reports successful cleanup.

All final JSON reports record build/test input SHA-256
`63d0e7983dad236f946da7fd352b92ea70afd976685fbd1636a4320f6d073b22`.
The complete native and Linux source maps match exactly. Shared ticket identity
validation passes with two historical shared-branch warnings. No sanitizer or
hosted-CI qualification is claimed.

## Provenance and reproduction

The native gfind executable was copied from the ignored CSH-091
`build/native-findutils/bin/gfind`; its exact hash is in the provider manifest.
Other selected providers were built/provisioned in this worktree. The retained
configure/build logs record the pinned GNU cp/rm source and patches, compiler
flags and pax build. No host executable was replaced.

The Linux runner uses the CSH-091 Debian 12 arm64 image, unprivileged UID 10001,
and Docker `--init`. Updated source/test and ownership inputs were copied into
its private writable filesystem. macOS archive metadata was removed before
qualification and the final source maps were compared byte-for-byte. No mounted
host filesystem was filled or modified by the container.

```sh
# Native PATH includes gtest, g[, gfind and gdd.
make -j4 cshell host-profile
make test-host-inventory test-host-profile test-host-filesystem-allocation \
  test-host-filesystem-provider-audit test-host-filesystem-residual \
  test-host-filesystem-isolated test-host-filesystem-interactive \
  test-host-filesystem-decisions test-host-filesystem-metadata \
  test-host-filesystem-recursive test-host-filesystem-path-limits \
  test-host-filesystem-cwd test-host-filesystem-creation
make test-host-filesystem-audit # separate nonzero stock result
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --record build/tests/host-filesystem-stock-provider-audit.json

# Fresh Linux source build alternative:
docker build -t cshell-test:csh-092 .
docker run --rm --init cshell-test:csh-092 make test-host-filesystem-creation
```

Compressed JSON preserves expected/actual output, status, effects, setup errors,
cleanup, credentials, provider hashes and source identities. Command records
preserve argv, exit status and elapsed time. `SHA256SUMS` covers all retained
artifacts other than this narrative.

## Remaining ownership

[CSH-093](../../tickets/CSH-093-filesystem-environment-residuals.md)
([#197](https://github.com/melliott18/cshell/issues/197)) owns all unsupplied
contracts, with utility/libc/platform vendors retaining implementation ownership.
Every remaining contract retains its environment and reason in the machine
ledger and the follow-up ticket. All four original U-040 conditions remain open.
The listed final modes do not establish every symbolic mode, omitted-who or
special-bit behavior, transient permissions, arbitrary parent graphs, ACL
inheritance, privileges, path limits, capacity exhaustion or whole utilities.
Historical CSH-064 and later evidence is unchanged. This uses CSH-092's
explicit-disposition acceptance alternative.
