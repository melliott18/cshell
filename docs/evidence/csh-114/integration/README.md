# CSH-114 integration review — 2026-11-07

The original isolated implementation `52ccffa` was omitted from the earlier
integration. Its evidence verifier passed on that original checkout before
rebasing: every predecessor expectation, exactly 112 new assertions per platform,
unchanged stock failure sets, source/provider provenance and cleanup. The retained
full profiles contain 12,443 native and 12,483 Linux passing assertions. Those
records remain unchanged; the original verifier intentionally checks its original
source inputs and is not a verifier for this later integration tree.

The implementation is reconciled with main `25b4733` in `cee800e`. Review found
no changes to production `src/` or `include/` between the original implementation
and the integration, and the touch object cases, exec helper, reference timestamps
and permission-case constants remain byte-identical. Current unrelated Make
targets, documentation and harness changes were retained when resolving conflicts.

## Fresh validation

| Check | Native macOS | Debian Linux container |
| --- | --- | --- |
| Touch object/namespace assertions | 112 pass, 0 fail | 112 pass, 0 fail |
| Complete filesystem harness | 166 pass | 166 pass |

The new records preserve the exact original expected values and touch executable
hashes on each platform. Every assertion records successful cleanup and no errors.
All four dispatch modes run against the integration's rebuilt cshell. Harness
checks reject wrong timestamps, metadata, bytes, output channels, namespace probes
and execution markers, and verify failed-exec/timeout cleanup and symlink handling.

Native ownership validation passes all 13 regressions. All 24 ticket tests and
the live identity check pass with 115 shared reservations. The registry assigns
CSH-114 to issue #240 and its pre-existing residual follow-up CSH-115 to issue #242.
The 21 utility rows and four original U-040 conditions remain individually open
under CSH-115. No full utility or system conformance is claimed.

Commands were `make -j4 cshell`, `python3 tests/test_host_filesystem.py`, and:

```sh
python3 tests/host_filesystem.py ./cshell --touch-objects-only \
  --path "$PWD/build/host-profile/bin:/usr/bin:/bin" \
  --record build/csh114-integration/native-touch-objects.json
python3 tests/test_ticket_registry.py
python3 tools/tickets.py check --live
```

Linux uses `/work/build/host-profile/bin:/usr/bin:/bin` and a `linux-` record
prefix. Its task-owned container starts from `cshell-test:csh-114`; current
`src`, `include`, `tests`, `tools`, Makefile, Dockerfile and ticket documents are
copied in, then cshell is rebuilt. It runs as the image's unprivileged identity.
The container was removed after collecting the records. Existing native and
container touch providers have the same hashes as the original retained runs.

Compressed logs and JSON records are listed in [records.json](records.json),
with uncompressed SHA-256 checksums. Each execution record carries the actual
source-file manifest, provider identity, platform, expectations, results and cleanup.
This fresh pass is focused integration validation, not a new full-profile,
sanitizer or hosted-CI qualification. Earlier failed attempts remain in the
parent evidence directory.
