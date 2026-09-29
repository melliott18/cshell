# CSH-064 acceptance reconciliation

**The implementation is integrated; ticket acceptance is not complete.**
[PR #131](https://github.com/melliott18/cshell/pull/131) merged reviewed head
`c0e61ef7a374f0030f804d9e278d3a65ba0774d1` as
`3e82c1d4fcb8d3f5552dfbbb57335ed59e5f8595`. The original ticket's “not integrated”
text was stale. The acceptance review found one project-owned P2 defect, retained
below. [CSH-064 / #127](../../tickets/CSH-064-host-platform-external-prerequisites.md)
is `in-progress` and remains open for that repair.

This reconciliation preserves the four original acceptance criteria and their
supporting evidence. An explicit additional cleanup gate records the newly
reproduced defect; existing assertions are not weakened or reclassified.

## Acceptance disposition

| Criterion or gate | Disposition |
| --- | --- |
| Individual residual provenance and qualification/implementation ownership | Supported. Thirty stable conditions and separate conditional limitations retain sources, actual environment/executable identities, reasons and owners. |
| Predicate/setup failures remain strict and separate from limitations | Supported by the retained records. Independently recomputed 12,616 non-setup assertion verdicts agree. Strict vendor and unsupported setup failures remain failures. |
| Claimed runtime/PTY integration; sanitizer validation for changed C | Original evidence retained: native, ordinary Linux and mapped Linux each record 3,905 runtime assertions and 64 terminal checks. No C changed. Review/reconciliation does not claim another full runtime/PTY or sanitizer run. |
| Queries, credentials, bounds and unmet requirements remain separate; no parent promotion | Supported. No parent utility or CSH-012 completion claim changes. |
| New acceptance-review regression: timeout cleans the complete owned process tree | **Open.** The selected chmod can survive the timed-out Python wrapper. Project repair and a regression are required. |

## P2: nested timeout leaves the utility running

At the reviewed head, `tests/host_platform_probe.py:41-47` uses
`subprocess.run(..., timeout=5)`, which kills its direct child on timeout. The
chmod route calls this helper twice: the outer call launches `_chmod-child`,
whose line 64 launches the selected chmod through another `command()` call.
The outer deadline starts first. Killing the wrapper therefore does not ensure
its selected utility has terminated before the probe reports or removes fixtures.

[The retained reproduction](timeout.json) uses the actual `_chmod-child` path,
a private file owned by 10001:10002 and a selected test executable that writes
its PID then sleeps for 30 seconds. The wrapper returns a five-second timeout
while `/proc/PID/status` still reports the utility sleeping with measured
UID/GID 10002 and zero effective capabilities. The review explicitly kills its
owned survivor, and the disposable container's init handles reaping. A sleeping
state is checked to distinguish a running survivor from an already-dead zombie.

This is a failure of the **cshell test harness**, owned for repair by CSH-064 /
#127. It is not a vendor defect, unavailable platform or waiver. The ordinary
profile passes and the eight passing overlay controls do not cover this path.
The cleanup repair needs no external prerequisite.

Required resolution: establish one deadline and cleanup owner for the full
owned process tree; terminate/reap descendants before returning or deleting
fixtures; preserve timeout diagnostics as a strict failure; and add a bounded
regression through the actual nested wrapper/utility path. A passing retry of
ordinary probes alone is insufficient. This change records the finding and does
not implement or claim that repair.

## Retained checks

All source-sensitive checks use a clean archive of exact reviewed head
`c0e61ef`, not later main (which includes an independent CSH-050 test repair).
The source digest is
`fe524b6a90519e622a00f21f792e201bdaa3f7de7ed9323200479a9ff2be1319`.
The original [CSH-064 artifacts](../csh-064/README.md) and their manifest are
unchanged. `commands.json` and `identity.json` retain command outcomes and
review environment; `artifacts.json` hashes this reconciliation's artifacts.

| Check | Retained result |
| --- | --- |
| Exact-head CSH-064 evidence audit | Pass; [audit.json](audit.json). |
| Independent assertion recomputation | 12,616 verdicts agree across seven qualification records; [verdicts.json](verdicts.json). |
| Fresh native `make test-harness` | 86 tests pass; `harness.log.gz`. |
| Fresh disposable Linux overlay probe | Eight checks pass; [overlay-probe.json](overlay-probe.json). |
| Nested timeout reproduction | **FAIL**: selected utility remains alive; [timeout.json](timeout.json). Reproducer exit zero means it successfully observed the defect and cleaned up, not that the cleanup assertion passed. |

[Hosted CI snapshot](hosted.json) records the exact PR head and merge identity,
with each job's current state: both Ubuntu/GCC and Docker jobs succeeded; both
macOS jobs were cancelled. The earlier review saw those macOS jobs in progress;
this newer snapshot is not a macOS pass or a full green run. CI completion cannot
discharge the separately reproduced cleanup defect without a repair and regression.

## Reproduction

From a repository checkout, create an ordinary source archive for the reviewed
head (not a new Git worktree), then run:

```sh
mkdir -p build/csh064-reviewed
git archive c0e61ef7a374f0030f804d9e278d3a65ba0774d1 | tar -x -C build/csh064-reviewed
python3 build/csh064-reviewed/docs/evidence/csh-064/audit.py
python3 docs/evidence/csh-064-acceptance/check_verdicts.py build/csh064-reviewed
make -C build/csh064-reviewed test-harness
```

The retained Linux checks use the existing `cshell-test:csh-063-sid` image;
[image.json](image.json) identifies it exactly. The source archive is mounted
read-only, and only private temporary files/processes are changed:

```sh
docker run --rm --init -i --user 0 \
  --mount "type=bind,source=$PWD/build/csh064-reviewed,target=/review,readonly" \
  --workdir /review cshell-test:csh-063-sid \
  python3 - /review < docs/evidence/csh-064-acceptance/reproduce_timeout.py
```

The script verifies Linux root, drops child supplementary groups and saved root
credentials through the reviewed helper, records the actual surviving process,
and explicitly kills that survivor in cleanup. No real accounts, protected
mounts or device contents are changed. The focused overlay control is:

```sh
docker run --rm --init --user 0 \
  --mount "type=bind,source=$PWD/build/csh064-reviewed,target=/review,readonly" \
  --workdir /review cshell-test:csh-063-sid sh -c \
  'python3 tests/host_platform_probe.py --fixture-root /tmp --record /tmp/probe.json >&2 && cat /tmp/probe.json'
```

No new vendor implementation, ACL filesystem, privileged Darwin environment or
physical terminal is claimed. The thirty existing external residual conditions
remain with their existing qualification/vendor owners and required capabilities.
