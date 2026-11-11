# CSH-118: measured ls socket pathname rendering

This separate `test/CSH-118-filesystem-environments` worktree starts at CSH-117
commit `de194ba`, under review in PR #249. Its prerequisite is not represented
as integrated. No shell C sources or selected providers change.

## Contract and independent oracle

The [Issue 8 ls specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html)
OPTIONS defines the `-F` socket suffix, `-p` directory suffix, `-i` file serial
number, and `-d`, `-H` and `-L` link rules. DESCRIPTION and STDOUT supply C-locale
ordering and one-entry-per-line output. The retained HTTPS source matches the
section map's SHA-256. Browser retrieval returned 403; curl retrieved the source.

Thirty-six cases run through direct exec and cshell string/file/stdin modes,
for 144 assertions per platform. Plain, `-F` and `-p` output combine with optional
`-i`, physical/`-H`/`-L` handling, and either a directory listing or reverse-authored
explicit `-d` operands. The private graph has AF_UNIX stream and datagram socket
pathnames, symlinks to both, and regular-file/directory controls. The datagram
socket has owner execute permission to distinguish socket classification from
executable-file classification.

A bounded Python child binds relative names in the private directory, checks
its bound names, closes both socket descriptors, and exits before provider exec.
No listener, connection or data transfer is used. Relative binding avoids
sun_path limits caused by long harness temporary directories without changing
the parent cwd. A successful exact child protocol is retained in each record.
Independent pre-exec lstat probes require socket types, authored modes and
positive inode numbers; stat probes verify the symlink referent identities.

Expected output is derived from those measurements and authored option rules,
never provider output. Exact names, suffixes, inode numbers, C order, empty
stderr and zero status are required; only inode-column space padding is allowed.
Device/inode, type/mode, owner/group, link count, size, allocation, mtime/ctime,
regular-file bytes, link text and directory entries must remain unchanged.
Access times are excluded because inspection can update them. Setup, execution,
capture and cleanup failures fail the assertion.

Eight harness tests cover all cases/modes, literal suffix/inode relationships,
wrong channels/status/order/suffixes, changed objects, rejected bind protocols,
partial setup, long parent paths, failed exec and timeout cleanup. A real bounded
bind-child timeout checks reaping; provider timeout checks run in all four modes.
The synthetic capture derives output from live directory entries and argv
independently of the fixture's expected-entry function.

## Boundaries and residual ownership

These cases qualify closed socket pathnames on the supplied filesystems only.
They do not qualify socket communication, devices, arbitrary graphs, other
identities or ACLs, terminal layouts, non-C locales, namespace races, resource
exhaustion, kernel fault injection or libc-internal failures. All 21 full utility
contracts and four original U-040 conditions remain individually open under
[CSH-119](../../tickets/CSH-119-filesystem-environment-residuals.md) / [#250](https://github.com/melliott18/cshell/issues/250).
U-034/U-040 remain partial. Utility/libc/platform vendors retain implementation
ownership. Historical evidence and predecessor fixture expectations are retained.

## Reproduction

```sh
# Native provisioning needs the documented GNU tools, including gfind, on PATH.
make -j4 cshell host-profile
csh118_tmp=$(mktemp -d /tmp/csh118.XXXXXX)
chgrp "$(id -gn)" "$csh118_tmp"
TMPDIR="$csh118_tmp" python3 docs/evidence/csh-118/validate.py native
rmdir "$csh118_tmp"

docker build -f docs/evidence/csh-118/Dockerfile.linux -t cshell-test:csh-118 .
docker run --init --name cshell-csh118-validation cshell-test:csh-118 \
  python3 docs/evidence/csh-118/validate.py linux
docker cp cshell-csh118-validation:/work/build/csh118-validation ./build/csh118-linux-results
# Collect reports/provider headers here; gzip raw logs losslessly and append
# .gz to the command records' log paths, then:
python3 docs/evidence/csh-118/verify.py
docker rm cshell-csh118-validation
```

The image layers current sources onto `cshell-test:csh-117`
(`sha256:ff6fc106474e5ef1f0ff79b3dd7fc932880f454d46425f8d2e71ccb12307f1c5`) and uses its
unprivileged `cshell` identity. Native provisioning uses a private copy of the
predecessor's gfind. Final validation runs targets and stock audits sequentially, with separate
reports and private fixture roots. Initial concurrent runs are retained below.
This is native macOS and Linux/Docker evidence, not separately hosted native
Linux. No new sanitizer or standalone runtime/PTY qualification is claimed. The task-owned Linux container was removed after final evidence collection and verification.

## Development records

The preliminary filesystem harness passed 188 tests before the final real
bind-child timeout regression was added. The focused final socket harness passed
eight tests. A second full inventory run overlapped provider builds, that
preliminary harness, and platform qualification: two existing timeout tests
(parent-graph and path-limit stdin children) expired before emitting their PID
markers. Their setup/timeout errors are retained in `development/`; assertions
and timeouts were not weakened. Final qualification results are recorded
separately below.

The initial parallel selected commands also encountered pre-existing timeout
failures in native permissions, link-byte cleanup and touch-object harness cases,
and Linux residual/parent-graph cleanup cases. Both full command sets and exact
failure summaries are retained under `development/*-parallel/`. A subsequent
sequential macOS harness reported 13 missing-PID-marker errors in existing
cleanup tests, while an isolated rerun of the link-permission test passed.
The private-temporary-root rerun and final results are distinguished below;
these observations do not establish the underlying platform cause.

The unchanged native filesystem harness passed all 189 tests with a private
`/tmp` root, including the new socket cleanup checks. The diagnostic used a private root via TMPDIR; final full validation uses the
explicitly group-corrected root described below. The failed default-root run and the successful
private-root diagnostic are retained separately. No assertion or timeout was
changed, and a filesystem or scheduler root cause is not claimed.

The first full private-root run passed inventory but failed 20 permissions
assertions: macOS inherited gid 0 (`wheel`) from `/tmp`, while those existing
fixtures require the current primary gid 20. Setgid bits were consequently
cleared for the nonmember identity. The final private root is explicitly changed
to gid 20 before fixture creation; independent child-file group and setgid
readback probes pass. The failed run is retained under
`development/native-private-wheel-group/`. This is a fixture provisioning
correction, with no selected-provider, expectation or timeout change.

## Final validation — 2026-11-11

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12939 pass, 0 fail | 12979 pass, 0 fail |
| New socket assertions | 144 pass | 144 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 13 / 189 pass | 13 / 189 pass |
| Stock full / provider failures | 853 / 16 retained | 578 / 8 retained |

Every ticket-listed selected target passes with zero allowances. Final selected,
stock-full and stock-provider command statuses are `[0, 2, 1]` on each platform.
The source/provider and oracle verifier passes; every predecessor expectation
and stock failure is retained. All 12795 / 12835 predecessor selected assertions
remain unchanged. All shell C/header and provider tooling sources are unchanged.

The native stock audit adds exactly 16 socket `-H` failures: plain/`-p` with
`-i`, and `-F` with or without `-i`, on explicit symlink operands. Apple ls uses
the link inode/type instead of the socket referent. These are stdout mismatches
with zero status, empty stderr, unchanged objects and successful cleanup. The
selected GNU coreutils 9.7 provider passes without changes. No Linux stock
failure is added. All 837 native and 578 Linux predecessor full-audit failures
and 16 / 8 provider-audit failures persist.

Native runs on macOS 14.8.7 arm64 as uid 501 with the private root explicitly
assigned primary gid 20; Linux/Docker runs LinuxKit 6.4.16 aarch64 with glibc 2.36
as uid 10001. Linux evidence was collected and verified before removing the
task-owned container. Initial failed runs and provisioning corrections remain
separate from these final results.

Ticket checks pass 24 tests and the live registry check with 119 reservations;
the two historical shared-branch warnings are unchanged. CSH-118 is ready for
review, stacked on CSH-117, and is not integrated. CSH-119 retains all unsupplied
environments and the four original conditions; full utility qualification is
not claimed.

Raw command logs are retained with lossless gzip compression; command records
point to the compressed artifacts. Their whitespace and captured bytes are
preserved exactly.
