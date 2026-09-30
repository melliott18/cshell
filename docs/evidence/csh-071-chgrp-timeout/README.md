# CSH-071 named-group timeout triage

The original `chgrp staff subject data` string-mode invocation exceeded the
five-second case deadline and reported failure to reap within one second. Its
[failed record](../csh-071-resolutions/native-permissions.json.gz) remains
unchanged. That record has no PID, process snapshot or timing breakdown, so it
cannot distinguish a shell stall, directory-service delay or host scheduling.

**The original command stall was not reproduced.** This change fixes a separately
demonstrated harness deadline bug; it does not claim to have fixed chgrp or a
cshell execution defect.

| Experiment | Retained result |
| --- | --- |
| Before harness change, named `staff` and numeric `20`, all four invocation modes | [80 passes](before-probe.json.gz); median 0.051 s, maximum 0.098 s. Fixtures under `/tmp`. |
| After change, same matrix in the original native temporary directory | [320 passes](probe.json.gz); median 0.060 s, maximum 2.838 s. Every leader was reaped and every fixture removed. |
| Full native permission suite | [980 passes, zero failures](permissions.json.gz); the five-second case limit is unchanged. |
| Native harness checks | [88 harness tests and six permission-harness tests pass](harness.log.gz). |
| Linux harness checks | [88 harness tests and six permission-harness tests pass](linux-harness.log.gz); disposable Docker container removed. |
| New regression against the old smoke.py | [Fails with the exhausted reap budget](baseline-regression.log.gz). |
| Same regression and cleanup-error control after the fix | [Both pass](cleanup-regression.log.gz), killing/reaping actual child processes. |

The [identity record](identity.json.gz) confirms that both cshell and the selected
`/usr/bin/chgrp` have exactly the same hashes as the original failed run. The
record also captures source hashes, macOS 14.8.7 build 23J520 and the current
high host load (one-minute load average over 600). High load is a possible
contributor, not a proved cause of the historical stall. The slowest focused
rerun was named-group string mode: spawning took 0.013 s and the process returned
success after 2.829 s, with negligible cleanup time.

## Fixed cleanup budget

Final pipe cleanup previously established one deadline, used it for group
killing/snapshot work, and passed only the remainder to `process.wait`. It could
therefore call `wait(timeout=0)` and claim the leader could not be reaped within
one second without actually giving that wait one second. The regression advances
the cleanup clock beyond the deadline, kills a real child and verifies a separate
full reap budget. It fails against the old implementation.

Final pipe cleanup now matches the PTY separation: up to five seconds for group
cleanup, followed by one second for leader reaping. Timeout failures remain
failures. This does not add time to the command's five-second deadline or claim
that an unkillable process has been reaped.

Permission records now include leader PID, spawn/elapsed/cleanup durations,
return status and reaped state. A timeout also attempts a separate bounded
0.5-second `ps` snapshot of the leader's process state, wait channel and executable.
Snapshot failures are retained without replacing command stdout/stderr or the
original timeout. The forced-timeout regression verifies these fields and actual
PID disappearance.

## Reproduction

From the repository root on the same macOS account (`staff` group):

```sh
mkdir -p build/chgrp-triage
python3 docs/evidence/csh-071-chgrp-timeout/probe.py
make test-host-permissions
make test-harness test-host-permissions-harness
python3 docs/evidence/csh-071-chgrp-timeout/verify.py
```

The [probe](probe.py) alternates named and numeric operands and direct, string,
file and stdin execution over 40 rounds. It stops after a failing round and
retains strict metadata/status/output assertions. If it encounters a live stalled
leader during cleanup it additionally samples only that owned process group;
sampling time is excluded from the cleanup budget, not the case deadline. That
path was never invoked in the passing retained runs.

No production shell or system utility code changed for this triage. The previous
PTY process in UE and full remaining CSH-071 contract obligations are separate.
