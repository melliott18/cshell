# CSH-121: mixed ls operands and symlink following

Based on CSH-120 commit `b095df6`, still awaiting integration. No shell or
selected-provider implementation changes. The retained Issue 8 `ls.html`
source is identical to CSH-120 and checked against the section-map SHA-256.
DESCRIPTION, OPTIONS (-H, -L, -F, -p, -i, -r, -1), OPERANDS and STDOUT define
the independent oracle.

Thirty-six private graphs run in direct exec and command-string, script-file
and stdin modes, for 144 assertions per platform. Interleaved operands include
a regular file, FIFO, populated directory, empty directory and file/directory
symlinks. The populated directory contains two further symlinks and a nested
directory with an unchanged guard that must never appear in the output.

Authored names and pre-exec lstat/stat probes establish object types, inodes
and distinct link/referent identities. Non-directory operands must precede
separately sorted directory operands. Both groups and each directory's entries
have exact C or reverse-C ordering. Multiple-operand headings and blank
separators are mandatory, including empty-directory sections. Without -F,
operand directory links are followed automatically; -F suppresses that default.
-H follows operand links only; -L also follows links in directory listings.
Only inode-column space padding is accepted. No provider output supplies an
expectation. Metadata, contents, link text and directory membership must remain
unchanged; access times are excluded because inspection may change them.

Harness regressions check literal grouping/type expectations throughout the
matrix, wrong/missing/duplicate/out-of-order sections, missing separators,
wrong names/inodes, fixture mutations, and four-mode execution controls.
Partial-setup failures are injected at the last new symlink, after independently
observing the new guard, FIFO and earlier alias. They require no provider
execution and complete cleanup in all four modes. Failed exec and real timeout
controls require cleanup and child reaping. The full 144-case provider matrix
runs separately through the selected profile with zero allowances.

Apple stock ls fails 48 new assertions: with default following, -i prevents
operand directory symlinks from being listed as directories; with -H, file-link
inode/type information remains that of the link. These observations are
retained as failures, not selected-profile allowances. Existing stock failures
and predecessor expectations remain unchanged. The selected GNU coreutils
9.7 ls provider was already introduced by CSH-115 and needs no change here.

CSH-122 / issue #256 owns all 21 remaining utility contracts and all four
retained conditions. Arbitrary graphs, devices, other credentials/ACLs,
terminal layouts, non-C locales, namespace races and resource failures remain
unqualified. U-034/U-040 remain partial. Historical evidence is unchanged.

## Reproduction

From the repository root, build `make -j4 cshell host-profile` with the
documented GNU providers on PATH. This run copied the predecessor's private
gfind binary into `build/prerequisites/`; its selected hash is retained in the
manifest. Create a private TMPDIR owned by the invoking user and primary group:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh121-tmp" \
  python3 docs/evidence/csh-121/validate.py native
```

Run `sh docs/evidence/csh-121/linux.sh` for Linux/Docker. It mounts this
checkout's tests, Makefile and accounting read-only over the CSH-119 image,
reusing unchanged shell/provider builds. The recorded image is
`sha256:78737251d7b568e1b88cfdb03050e7417859381091358b85600a85376c53a817`.
Fixtures run as uid/gid 10001 on
bounded executable tmpfs mounts. Reports are bound to this worktree. No
protected mount, host-volume filling or privileged fixture identity is used.

Validation uses `make -k` to collect every requested target while retaining
any failure status. Stock full and provider audits run separately and must
remain nonzero. Run `python3 docs/evidence/csh-121/collect.py` to archive reports
and losslessly compress logs, then `python3 docs/evidence/csh-121/verify.py`.
The verifier requires source/provider hashes, unchanged predecessor
expectations, the exact new case/mode set, channels/status, unchanged objects,
cleanup, unchanged old stock failures and the exact 48 new Darwin failures.

## Validation result — 2026-11-14

Native macOS 14.8.7 arm64 and Linux arm64/Docker (glibc 2.36) both pass every
selected filesystem target. Both host utility profiles pass 1,162 assertions
with zero failures or gaps. The evidence verifier passes, including all
predecessor expectations, exact provider/source identities, each new case/mode,
unchanged objects, cleanup and the exact stock failure sets.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Combined selected filesystem assertions | 13,371 pass / 0 fail | 13,411 pass / 0 fail |
| New mixed-operand ls assertions | 144 pass / 0 fail | 144 pass / 0 fail |
| Filesystem harness tests | 200 pass | 200 pass |
| Ownership tests | 13 pass | 13 pass |
| Stock full-audit failures | 901 (853 old + 48 new) | 578 unchanged |
| Stock provider-audit failures | 16 unchanged | 8 unchanged |
| Complete requested make command | **exit 2**, observer failures below | exit 0 |

The native broad command failed two existing CSH-073 text-boundary cases:
`cat/write-termination/direct` and `head/write-termination/direct`. Both
`/usr/bin/sample` subprocesses exceeded their unchanged four-second bound before
the termination assertion. The provider leaders were reaped and fixtures
removed. Initial text totals were 864 pass, 2 fail, 2 unavailable. The
unavailable cases are the pre-existing unsupplied Darwin filesystem-ENOSPC
boundary; neither is a new allowance. The raw failed command and
`native-text-initial.json.gz` are retained.

After the stock audits finished, `recheck_text.py` ran the exact text-profile
selection separately, with unchanged providers, inputs, limits and assertions:
866 pass, 0 fail, the same 2 unavailable; command status 0. Its log, full report
and command/timing record are retained. This passing recheck does not erase the
failed broad run or establish a cause for the sampler timeouts. No full broad
native rerun or root-cause fix is claimed. The existing
[CSH-073](../../tickets/CSH-073-host-text-streams.md) / U-040 other-interruptions
owner retains this observer limitation; CSH-121 does not alter text utilities or
their observer. Reproduce the separate check after the main validation with:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh121-tmp" \
  python3 docs/evidence/csh-121/recheck_text.py
```

All 24 ticket tests and offline/live identity checks pass with 122 reservations.
The task-owned Docker container was removed. No sanitizer, separately hosted
native-Linux run or hosted CI pass is claimed. The scoped implementation is in
review, stacked on CSH-120; neither integration nor full utility qualification
is claimed.
