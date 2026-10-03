# CSH-071 chgrp observation follow-up

The historical five-second `chgrp staff subject data` stall remains unresolved.
These runs add observations and improve timeout diagnostics; they do not establish
a production shell or utility fix. The original failed evidence is unchanged.

On macOS 14.8.7 arm64, the same cshell and `/usr/bin/chgrp` executable hashes as
the historical failure passed another 2,000 assertions. Each 1,000-case run
alternates `staff` and numeric `20` across direct execution, cshell string/file/
stdin modes, and a `/bin/sh -c` control. Status, output, owner/group metadata,
leader reaping and fixture removal remain strict. The five-second limit is
unchanged. The [identity record](identity.json.gz) records executable hashes,
source revision and the different smoke.py hashes used for replays and tests.

| Run | Results | Median / maximum fixture elapsed |
| --- | --- | --- |
| Snapshot, then attempt sampling | [1,000 passes](replay.json.gz) | 0.049 / 0.843 s |
| Start leader sampling before the snapshot | [1,000 passes](early.json.gz) | 0.044 / 0.378 s |

A separate observer process checks for invocations lasting over 0.25 seconds,
then snapshots only their process group and attempts bounded macOS `sample`
captures. This keeps the Python runner single threaded before fork/preexec.
The observer can perturb timing; these numbers are diagnostic observations,
not benchmarks. The runs briefly overlapped. Their process observations and
sampling errors are retained in [replay observations](replay-observations.json.gz)
and [earlier sampling observations](early-observations.json.gz).

The first run captured eight snapshots, including Python wrapper, cshell and
`/bin/sh` process names. The second captured a direct numeric `chgrp` invocation.
No usable stack was captured from a naturally slow invocation: processes exited
before they could be sampled. The [deliberate sleep control](observer-control.json.gz)
did produce a stack sample and confirms the observer and sampling permissions
work on this host. This control is not a reproduction of the chgrp failure.
Short delays in both shells and direct invocation weaken a cshell-only hypothesis,
but do not identify the cause of the historical five-second failure.

The subsequent [macOS CI job](https://github.com/melliott18/cshell/actions/runs/36676310231/job/109761928063)
also passed all 12 chgrp cases ([extracted log](ci-chgrp.log.gz)). That overall
job failed on four `id -G` assertions; it is not a passing full qualification run.

## Diagnostic change and validation

Timeout evidence previously retained only the leader. A shell waiting normally
for a stuck utility could therefore look like the culprit. `tests/smoke.py` now
retains a `timeout_group` snapshot containing PID, parent PID, group ID, state,
wait channel and executable for the leader's group. The existing leader record
is preserved. The snapshot has the same 0.5-second deadline, a 1 MiB read bound
and a 16 KiB retained group bound. Other process rows and command arguments are
not retained. Snapshot errors do not replace the original timeout or prevent
cleanup.

A real forked parent/child regression confirms both are recorded, the runner is
excluded, and both processes are killed with the leader reaped. It fails against
[the previous implementation](baseline-regression.log.gz). Validation passes:

- [31 native pipe harness tests](harness.log.gz).
- [31 Linux pipe harness tests](linux-harness.log.gz), in a removed Docker container.
- [Six native permission-harness tests](permissions-harness.log.gz).

No extra macOS environment or manual test is needed to use this instrumentation.
A recurrence long enough to capture the stalled process is still needed before
choosing a production fix. No production shell or system utility code changed.

## Reproduction

From the worktree root on macOS, using new output directories:

```sh
python3 docs/evidence/csh-071-chgrp-observer/probe.py --output build/chgrp-observer-first
python3 docs/evidence/csh-071-chgrp-observer/early-probe.py --output build/chgrp-observer-early
python3 -m unittest discover -s tests -p test_harness.py
python3 -m unittest discover -s tests -p test_host_permissions.py
python3 docs/evidence/csh-071-chgrp-observer/verify.py
```

The retained probe scripts stop at the first failed assertion. Inspect their
`results.json` verdicts; their command exit status alone is not the evidence
oracle. A `slow-*.json` file is an observation attempt, not proof of a timeout.
