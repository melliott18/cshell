# CSH-123: ls output errors

Based on CSH-122 commit `4749b81`, still awaiting integration. The retained
Issue 8 `ls.html` is byte-for-byte unchanged from the predecessor. STDOUT,
STDERR, EXIT STATUS and CONSEQUENCES OF ERRORS define the error oracle; OPTIONS
and OPERANDS define the eight invocations. No diagnostic wording is prescribed.

Sixteen private cases on macOS and 24 on Linux run through direct exec, command
strings, script files and stdin: 64 / 96 assertions. Directory, multiple-operand,
long, numeric, allocation, inode/type, recursive and followed-link listings each
receive closed stdout (EBADF) and a readerless pipe (EPIPE). Linux also receives
the independently identified `/dev/full` character device (ENOSPC). The existing
child-only helper performs an actual failing write and checks its errno before
exec of the exact selected provider. SIGPIPE is ignored so the provider can
observe EPIPE. Setup and exec failures retain different marker phases.

Each invocation must return nonzero, with empty captured stdout and nonempty
stderr. Raw status and channels are retained. Diagnostics are implementation
defined; no wording or exact failure status is inferred from a reference utility.
The existing private regular/empty/seek-created/hard-link/directory/FIFO/symlink
graph is independently measured before execution. Post-exec checks require
unchanged inode, mode, owner/group, size, link count, allocation, mtime/ctime,
file bytes, link text and directory entries. Access time is excluded because
inspection may change it. FIFOs are never opened. A nested leaf is preserved.

Harness regressions exercise all four modes, corrupted status/channels/markers,
fixture mutations, partial setup failure before provider execution, failed exec,
real timeout, child reaping and cleanup. No selected provider source, allowance,
predecessor expectation or deadline changes. CSH-124 / issue #260 owns all 21
remaining utility contracts and all four retained conditions. These witnesses
do not supply actual filesystem exhaustion, arbitrary or partial writes,
libc-internal faults, terminal layouts, other locales, namespace races or general
resource limits. U-034/U-040 stay partial.

## Reproduction

Build `make -j4 cshell host-profile` with documented GNU providers on PATH.
The private `build/prerequisites/gfind` was copied from the CSH-122 worktree;
its exact identity is recorded in the selected manifest. Use a private TMPDIR
owned by the invoking user and primary group:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh123-tmp" \
  python3 docs/evidence/csh-123/validate.py native
sh docs/evidence/csh-123/linux.sh
python3 docs/evidence/csh-123/collect.py
python3 docs/evidence/csh-123/verify.py
```

Linux reuses the unchanged CSH-119 shell/provider image and mounts this
checkout's tests and accounting read-only. Fixtures run as uid/gid 10001 on
bounded executable tmpfs mounts. Remove the task-owned validation container
after collecting its results. Stock full and provider audits run separately and
retain nonzero results. No privileged fixture, protected mount or host-volume
filling is used. Native providers are rebuilt from the pinned sources.

## Validation result — 2026-11-16

The complete requested make command passes on native macOS 14.8.7 arm64 and
Linux arm64/Docker (glibc 2.36). Both platforms pass all 208 filesystem harness
tests, 13 ownership tests and 1,162 host-profile assertions with zero gaps.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Selected full filesystem profile | 13,627 pass / 0 fail | 13,699 pass / 0 fail |
| New output-error assertions | 64 pass / 0 fail | 96 pass / 0 fail |
| Filesystem harness tests | 208 pass | 208 pass |
| Stock full-audit failures | 901 unchanged | 578 unchanged |
| Stock provider-audit failures | 16 unchanged | 8 unchanged |
| Complete requested make command | exit 0 | exit 0 |

All 24 ticket tests and offline/live identity checks pass with 124 shared
reservations. Only the pre-existing historical shared-branch warnings for
CSH-044/045 remain. No sanitizer, separately hosted native-Linux or hosted CI
pass is claimed. Integration depends on the unmerged CSH-122 stack; neither
integration nor whole-utility qualification is claimed.

The evidence verifier passes: source and provider hashes, every new case/mode,
output/status/effects, cleanup, unchanged predecessor expectations and exact
stock failure identities are checked. There are no new stock failures or
allowances. The task-owned Docker container was removed. CSH-123 is ready for
review; CSH-124 owns every remaining contract and the four retained conditions.
