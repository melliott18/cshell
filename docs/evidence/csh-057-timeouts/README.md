# CSH-057 timeout diagnosis

Base: `8ffb99e73cfd21bb1b5ad66829544350f78b69ae`. Runtime/tests: `fe989b1`. Branch:
`fix/CSH-057-timeout-diagnostics`. This follows PRs #109 and #112.
The earlier [resume evidence](../csh-057-pty-fix/README.md) is retained;
its load-only interpretation of a matching output prefix is withdrawn.

## What the observations establish

The public case still requires all 32 cycles, exact output, foreground predicates,
status 130, and the original five-second deadline. Instrumentation records
completed-step times in memory and, in subsequent probes, terminal state just
before writes. Post-deadline probes never turn a failed case into a pass.

| Observation | Evidence and conclusion |
| --- | --- |
| Ctrl-Z stops having any effect | `pty-baseline` round 22 completes 14 cycles in about 61 ms, then stalls for almost five seconds. `pty-signal-probe-2` round 3 repeats Ctrl-Z after the deadline without effect; a direct SIGTSTP immediately stops the eligible foreground child. |
| Handoff can fail with EINVAL | `pty-signal-probe` round 95 captures `cannot give terminal to job: Invalid argument`. The prior prefix-only logger would hide that late message. |
| Concurrent group assignment reproduces outside cshell | `group_race.c` contains no cshell code. With both parent and child calling `setpgid`, `minimal-both` round 38 reproduces the lost terminal stop. Parent-only assignment passes 200 × 64 launches (`minimal-parent`). |
| Ctrl-C stalls have another cause | Removing the child `setpgid` leaves a cycle-29 Ctrl-C timeout in `pty-fixed`, after only 78 ms of progress. The child can still be stopped by terminal Ctrl-Z. |
| SIGINT was blocked from child entry | `pty-mask-probe` round 80 records `initial_int=1 current_int=1 pending_int=1 ignored_int=0`. Direct SIGINT also remains pending. Darwin's `ps`/`kinfo_proc` mask field is deprecated and showed zero; it was not evidence of the thread's mask. |
| Parent bookkeeping masks escape a wait | `parent-mask-origin.log` records INT and CHLD blocked at a later `csh_jobs_read_ready` entry. The child then inherits them. `mask-before` removes only the restoration workaround from the final runtime: round 30 fails the strengthened helper's explicit inherited-mask check. |
| A rejected continuation can precede waitable exit | `pty-exit-refusal-2` round 424 records SIGCONT EPERM, positive-PID `getpgid` ESRCH, and `waitid(WEXITED\|WNOHANG\|WNOWAIT)` with no exit yet. Later output reports the same child's SIGINT exit. Polling once after EPERM was insufficient. |

The group-object explanation follows the affected host's observable behavior
and Apple's [group assignment implementation](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/kern_proc.c)
and [terminal group lookup](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/tty.c).
User-space observations cannot inspect kernel object identity directly.

Apple's [pselect implementation](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/sys_generic.c)
retains a deferred saved mask for signal delivery and clears that state on a
non-interrupted zero-time call. The Darwin workaround does that while event
signals remain blocked, then restores the actual caller's mask. It preserves
errno and introduces no elapsed delay. The leaked mask is directly observed;
the exact internal kernel interleaving is an inference from this source, not a
kernel trace. The standalone mask flood/handshake probes did **not** reproduce
the leak; their passing records are retained and are not proof against it. The
sigsuspend flood variants instead deadlocked their diagnostic pipe/signal
protocol and reached SIGALRM; `minimal-mask-suspend-result.json` records that
failed experiment.

The kernel sources above match the host's XNU base tag, not a claim that the
published tag contains every patch in the installed kernel build.

## Changes and regressions

- The existing launch barrier gives the parent sole ownership of `setpgid`.
  A pipe-controlled fork regression holds the child before disposition reset
  while the parent groups it and sends INT, TSTP, TERM, or QUIT. It fails before
  the change (`fault-before`) and passes afterward, including masks and cleanup.
- Darwin job/read waits clear deferred mask restoration before restoring their
  caller's mask. `jobs_helper hold` now diagnoses unexpected blocked INT/CHLD
  before declaring readiness. The shell preserves deliberately inherited masks.
- A rejected SIGCONT first polls statuses. For remaining owned children, only
  positive-PID `getpgid` ESRCH permits a final blocking wait. Every member must
  be complete before accepting the original rejection. Live/stopped EPERM
  rejection remains covered. The portable fault regression models the observed
  group-departure/status gap and fails without this repair (`gap-fault-before`).
- Runner failures include the last output/step progress time and a bounded
  output prefix **and tail**. Retention emits exact, flushed checkpoints.
  Deadlines, signal assertions, cleanup budgets, and retained-status assertions
  are unchanged. Harness self-tests cover stalled output, PTY progress, and
  late diagnostics.

## Retention is a separate, still-unclassified observation

[Hosted macOS job 109041175577](https://github.com/melliott18/cshell/actions/runs/36455644289/job/109041175577)
killed the sanitizer retention fixture at its 60-second outer deadline, with
empty stdout. Its original `puts` output was fully buffered, so this does not
identify the failing phase or prove a stalled child. The hosted log is retained.

With the unchanged base runtime, `retention-trace.patch` adds file-backed
per-child progress only. The serial sanitizer probe passes in 31.422 seconds;
two concurrent probes pass in 27.567 and 27.582 seconds. These do not reproduce
or explain the historical hosted failure. The production test now flushes
capacity/round checkpoints and live/formatting phase markers so a recurrence
will carry useful evidence. It retains the 60-second outer bound and original
five-second alarms. No load classification or deadline increase is substituted
for a diagnosis.

The [merged-repair review](../csh-057-retention-review/README.md) adds hosted
timings and local fork/wait measurements. It also corrects this directory's
`diagnose_retention.py`: the historical concurrent probes used threads around
a runner with `preexec_fn`; future probes use independent spawned processes.
The historical results remain unchanged. The diagnostic-launch defect did not
affect the single-threaded hosted runner and does not explain its timeout.

## Reproduction and provenance

Build the normal target with `make -j4 test-jobs test-pty test-harness`.
For native Darwin diagnostic snapshots:

```sh
cc -Wall -Wextra -Werror docs/evidence/csh-057-timeouts/process_signals.c -o build/tests/process_signals
python3 docs/evidence/csh-057-timeouts/diagnose_pty.py --rounds 1000 --output /tmp/csh057-observations
cc -std=c99 -Wall -Wextra -Werror docs/evidence/csh-057-timeouts/group_race.c -o build/tests/group_race
python3 docs/evidence/csh-057-timeouts/diagnose_group.py --both --rounds 200 --output /tmp/csh057-group-race
python3 docs/evidence/csh-057-timeouts/diagnose_group.py --rounds 200 --output /tmp/csh057-parent-only
```

Diagnostic probes evolved as evidence narrowed the question. The baseline had
only step timestamps and an unsuccessful three-second sampling attempt.
Subsequent probes also read termios/foreground state before writes. Early
post-deadline probes always tried Ctrl-Z; later probes repeat the last control
and then its direct signal. The helper mask patch and parent trace patches are
diagnostic-only. No probing or logging remains in the shipping runtime.
The current diagnostic scripts implement the final observers; the recorded
JSON distinguishes which fields each earlier version collected.

`rejected-running-fg.patch` retains an abandoned experiment: suppressing a
redundant SIGCONT for running jobs did **not** fix the mask leak (`pty-running-fg`
round 458 and `pty-dispositions` round 325). It is not in the final runtime.
Standalone resume probes with/without exec and with diagnostic scheduling
windows all passed; they did not establish SIGCONT overlap as the timeout cause.
The initial resume-helper length assertion and mask-probe EINTR assertion were
fixture mistakes, retained as `*-helper-error` records. `diagnostic-tests` also
retains intermediate observer/self-test mistakes corrected in the final checks.

All failed trace records and text logs are retained compressed without changing
their content. Successful trace rows retain per-round identity, timings and
outcomes; verbose successful step/write traces are kept locally under
`build/csh057-diagnostic-traces/` and hashed in `trace-storage.json`. They are
not required to reproduce or review the failures.
`observations.json` indexes repetition results and failed snapshots;
`inventory.json` records artifact hashes. Final native/sanitizer/Linux source
identities and validation results are recorded alongside them.

## Final validation

Runtime/tests: `fe989b1`; all three source identities share SHA-256
`7a8ce2b56a28b07a26ba0d92d0e64afaed326015d6e1dcb5fc45fc2e9291433a`.
Native host: macOS 14.8.7 arm64, Apple clang 15. Docker: Debian 12 arm64,
GCC 12.2 and glibc 2.36; container validation is not a native Linux host claim.
The Docker identity records the image's normal executable; sanitizer binaries
were built and tested in the disposable container using the retained commands.

| Check | Result |
| --- | --- |
| Native `make -j4 test-jobs test-pty test-harness` | Pass: 148 public jobs cases, 30 jobs PTY cases, 30 runtime PTY cases, lifecycle/API/fault checks, 76 harness tests. |
| Native ASan/UBSan `make -j4 test-jobs test-pty` | Pass, including the new fault and mask regressions. |
| Docker normal jobs/PTY/harness and ASan/UBSan jobs/PTY | Both pass; no sanitizer diagnostics or capability skips. |
| Native trap runtime and signal checks | Pass: 207 trap cases, 2,464 signal-edge cases, six blocked-wait handshakes, 20 inherited-ignore checks. |
| Unchanged public 32-cycle repetitions | 1,000/1,000 normal and 200/200 sanitizer cases pass: 38,400 cycles, original bytes/status and five-second bound. |
| Before-fix checks | The group writer and exit-gap module regressions fail before their fixes. Removing only the mask workaround makes the public helper report blocked INT/CHLD at round 30. |

Sanitizer flags: `-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer`, with matching sanitizer
link flags; native sanitizer runs set `MallocNanoZone=0`. No ASan/UBSan options
were added to the controlled fixture environment to suppress diagnostics.

This is focused verification of the changed paths. It does not claim a fresh
full general-runtime conformance sweep or resolve the historical retention
failure by inference from later successful runs.
