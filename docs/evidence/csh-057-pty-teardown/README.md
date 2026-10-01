# CSH-057: PTY output drain, repeated-resume timing and CI job budget

The 2026-10-01 follow-up to [#99](https://github.com/melliott18/cshell/issues/99)
and [#173](https://github.com/melliott18/cshell/pull/173) finds a reproducible
harness defect: retaining the PTY master while waiting for a killed session
leader can prevent the leader from completing exit when terminal output is
still queued. It also demonstrates insufficient aggregate headroom for the
32-cycle fixture and for the complete native CI job. No production C source
changes are needed for these repairs.

## Reproduced cleanup dependency

The [earlier hosted failure](../csh-057-terminal-crash-notification/hosted-verification/README.md)
completed 25 cycles and sent cycle 26's helper command at 4.973 seconds before
its five-second deadline. It then reported an unreaped leader after SIGKILL.
The log did not capture every step time or the leader's kernel state, so it
cannot alone establish the cause of either elapsed interval.

The local experiment uses the real ASan/UBSan shell and unchanged 32-cycle
oracle, with a temporary 160 ms delay before each helper readiness message.
At the original five-second limit it reproduces the timeout and cleanup
failure. Cleanup successfully kills the child and leader groups, then finds
an empty live-session snapshot, but the one-second exact-child wait expires.
In a second controlled occurrence, the owned leader has `getsid=ESRCH` and
`ps` state `?Es`; another 0.3-second wait still fails while the master remains
open. Closing that master immediately makes the same child waitable with
status -9 (observed wait duration about 10 microseconds). No additional signal
or wait-budget increase is required.

An independent, smaller control writes seven PTY bytes, confirms completion
through a separate pipe, and retains an extra slave descriptor as a descendant
may do during exit. Old cleanup fails after 1.108 seconds; closing the master
then permits exact -9 reaping in 1.5 ms. The close-before-wait variant succeeds
in 0.107 seconds. The shipping regression uses the same pipe handshake and
retained-slave arrangement. It fails the old implementation with the exact
one-second cleanup error and passes the repair. Its own failure path closes
all owned descriptors and reaps the child.

Earlier exploratory bare-helper controls without the extra slave reference
sometimes reaped after roughly 0.6 seconds and did not reproduce the one-second
error; these results remain archived. A separate exit-visibility probe found
100 short intervals where `getsid=ESRCH` preceded a successful wait, maximum
0.136 ms. That observation only shows that session visibility is insufficient
reaping evidence; it does not explain the hosted one-second failure.

Apple's public XNU base corroborates the mechanism:
[session-leader exit removes its TTY association before waiting for output](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/kern_exit.c#L2106-L2125),
[ttywait waits while output remains queued and the terminal is connected](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/tty.c#L1698-L1726),
and [master close disconnects and flushes the queues](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/tty_dev.c#L550-L562).
The [last slave close also has a temporary drain timeout](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/tty_dev.c#L302-L347),
which explains why the bare-helper control is weaker. These links cover the
local macOS 14 XNU base, not its additional `.712.16` patch suffix or the hosted
macOS 15 kernel. The controlled runtime observations establish the defect
locally; they do not retrospectively measure the old hosted kernel state.

The repair makes `cleanup_session` consume the master descriptor. It performs
owned-session enumeration and group cancellation first, closes the master,
then performs the existing one-second exact-child wait. `capture` transfers
ownership before calling cleanup to prevent double-close. Transcript capture
has already ended, so discarded queued bytes cannot make an incomplete oracle
pass. Existing failures remain failures. The five-second group cleanup budget
and one-second reap budget remain unchanged.

## Separate aggregate budgets

All 20 unmodified local sanitizer repetitions pass in 0.980–1.583 seconds.
Those passes are observations, not a diagnosis of the historical failure.
The controlled 160 ms per-launch delay contributes at least 5.12 seconds across
32 children. The same binary fails the old five-second limit but passes all
419 steps and the exact transcript/status in 6.334 seconds under a ten-second
diagnostic limit. With repaired cleanup but the old five-second limit, the
case still fails as intended and reaps the leader as -9 without cleanup errors.
With both repairs it passes three runs in 6.311, 6.395 and 6.351 seconds.

Only this repeated-resume case receives a ten-second aggregate budget. Its 32
cycles, 419 steps, foreground predicates, byte-exact output and status 130
remain identical. The other 29 public jobs PTY cases explicitly retain five
seconds. The Make target sets a ten-second CLI ceiling because `smoke.run_case`
uses the minimum of the CLI and case bounds. Custom callers keep that same cap
semantics. This trades up to five additional seconds for detecting a whole-case
stall in this one long fixture; it does not reset time on progress or excuse a
future timeout. Controlled delay is not shipped, and the evidence does not
claim every historical step interval was short.

The next [push macOS job](https://github.com/melliott18/cshell/actions/runs/36898227146/job/110490529268)
and [PR macOS job](https://github.com/melliott18/cshell/actions/runs/36898234219/job/110490557080)
both have explicit GitHub annotations that the 45-minute job maximum expired.
They were still reporting passing cases 45 ms and 73 ms before cancellation.
They passed the normal/sanitized Mach, retention, repeated-resume and terminal
checks. Sanitized retention took 66.070 and 75.113 seconds within its repaired
120-second case budget. Neither log reports unexpected case failures or
sanitizer findings. The newer checkout changed only documentation from the
prior implementation; the PR merge has identical contents to its head.

Native CI therefore receives a separate 60-minute aggregate budget. Docker
retains 30 minutes. This is finite headroom for the complete normal/sanitizer
matrix, not a guarantee under arbitrary host scheduling. The original failed
and cancelled runs remain so. Later passing CSH-054 exit-operand tests do not
erase that separate earlier failure.

## Validation and reproduction

| Check | Result |
| --- | --- |
| Native macOS harness | 95 passed, including the new queued-output regression and existing timeout/descriptor/descendant controls |
| Native normal jobs and PTY | 148 jobs, 30 public PTY, 14 lifecycle PTY, notification, terminal fault, retention, ownership and watchdog checks passed |
| Native ASan/UBSan | All 30 public PTY cases, notification and terminal-fault cases passed |
| Linux Docker normal | 95 harness tests, 30 public PTY cases, notification and terminal-fault checks passed |
| Linux ASan/UBSan | Real repeated-resume and terminal-fault cases passed with strict repository flags |
| Generated oracle comparison | All 30 cases identical to the parent after removing only the new timeout field; exactly one case has 10 s, 29 have 5 s |
| Old/fixed cleanup control | Old implementation reports the one-second reap failure; fixed implementation returns exact SIGKILL status |

Run `make test-harness test-jobs test-jobs-pty` for the focused normal checks.
The new regression can be selected with:

```sh
python3 -m unittest discover -s tests -p test_pty_harness.py -k test_cleanup_reaps_a_killed_leader_with_unread_terminal_output -v
```

[Native metadata](native-validation.json) and [artifacts](native-artifacts.tar.gz)
retain step/cleanup traces, all controlled outcomes, source and binary identities,
temporary delay patch, minimal PTY probes, old/fixed regression logs and native
normal/sanitizer logs. The first delayed before/after invocations briefly
overlapped at teardown; the explicit hold/close comparison and independent
synchronized regression separately establish the dependency. Exploratory
passes and unsuccessful controls are retained, not counted as failing witnesses.
[Linux metadata](linux-validation.json) and [artifacts](linux-validation.tar.gz)
record independent container validation and the nonbehavioral comment/import
changes after its exact tested snapshot; normalized ASTs match.
[Hosted audit](hosted-audit.json) and [artifacts](hosted-artifacts.tar.gz) retain
full logs, cancellation annotations, identities and retention artifacts.

The ticket remains at review pending integration and hosted validation of this
repair. The retained historical uncertainties are potential bugs, not proof of
an unsolvable shell defect. No failure is deleted, skipped or converted to a
pass by this diagnosis.
