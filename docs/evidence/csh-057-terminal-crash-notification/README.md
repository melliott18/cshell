# CSH-057: isolate terminal fault children from inherited crash receivers

The 2026-10-01 investigation reproduces an actionable test-fixture timeout on
macOS. An inherited task-level Mach `EXC_CRASH` receiver can hold a child that
the terminal fixture deliberately terminates with SIGQUIT. Clearing that port
in this one test child removes the dependency while preserving SIGQUIT's
default disposition and exact wait status. No production source, terminal
oracle or timeout changes. The original incident's receiver was not recorded;
this is a demonstrated fixture repair, not proof of an operating-system bug
or an unsolvable shell failure.

## Historical localization and its limits

The [diagnostic review](../csh-057-retention-diagnostics/README.md) retained a
five-second `execute_faults --jobs-terminal` timeout with empty output, status
-9 and a cleanup snapshot-budget failure. Its leader was 18494. Child 18538
remained under PID 1 in `UE` state after an exact SIGKILL. The stack sample
places that child in `context_job` through `sigprocmask`.

Before rebuilding, the original executable was preserved: Mach-O UUID
`E63293CC-41B2-3479-AE16-DD49D6908CC9`, SHA-256
`d1f736eb2ac98c1a80bea7ea8f71904bf1e9b263470dc2b3f619bb14df50fb76`.
[Offline analysis](historical-analysis.json) checks the UUID against the
sample, translates its return addresses and verifies the preceding ARM64 call
instructions. The inherited `main` frame identifies the pending launch-signal
loop; the child frame identifies its pre-exec unmask operation. That loop
tests INT, TSTP, TERM and QUIT. These files do **not** identify which signal
was pending in child 18538, or any Mach receiver.

An [adjacent crash report](adjacent-crash.json) for distinct PID 99059 has the
same executable UUID and frames, SIGQUIT/EXC_CRASH, launch on September 29 and
capture about 22 hours later on September 30, with parent PID 1. This supports
investigating delayed crash handling but does not establish the original
incident's cause. Only relevant report fields are retained; its source hash
is recorded. The old PIDs were already absent at this review, without a host
reboot since their launches. Their disappearance time and cause are unknown.
No old PID was signaled again. Leader-group EPERM does not describe a signal
to child 18538's separate group, and a shared snapshot deadline does not prove
one slow `ps` call.

The distinct CSH-058 child 99718 was sampled in `raise(SIGQUIT)` through
`__pthread_kill`. Its evidence is preserved for comparison, with ownership
remaining [CSH-058 / #100](../../tickets/CSH-058-signal-edge-evidence.md).
This change does not modify that fixture.

## Controlled cause and repair

A receiver owned by the experiment installs its own task `EXC_CRASH` port,
forks the fixture driver so the port is inherited, then restores its own
original ports. It deliberately holds the crash reply for six seconds.
The actual terminal fixture still has its original five-second PTY deadline
and five-second cleanup budget.

| Actual terminal fixture | Result with the controlled receiver |
| --- | --- |
| Preserved original executable | Notification at 0.218 s; five-second timeout, -9, empty output; reply at 6.219 s releases exit; bounded cleanup completes |
| Fixed normal executable | Exact original output/status passes in 0.058 s; no notification |
| Fixed ASan/UBSan executable | Exact original output/status passes in 0.901 s; no notification |

The failed case's measured 6.195 seconds includes cleanup after the five-second
case deadline; it is not an increased case budget. The original failure remains
a failure in the archive. Earlier uncontrolled repetitions (100 terminal
cases, 50 standalone QUIT and 50 TERM probes) passed; they did not diagnose it.

The shipping change calls the shared test-only helper immediately after fork,
only when the terminal fault fixture's selected launch signal is SIGQUIT,
while that signal remains blocked. The helper clears the child's inherited
task crash port. The parent retains its ports. All mask, terminal ownership,
signal-result and child-reaping assertions remain intact. Clearing this port
does not disable host/thread fallback or corpse reporting.

`make test-job-crash-notification`, also included in `test-jobs`, provides a
deterministic regression. Its negative control holds a real exception reply,
checks that the exact child remains unreaped after SIGKILL, then replies and
requires exact SIGQUIT termination. Its isolated control requires no request
and the same SIGQUIT status. Both scenarios have finite deadlines; failure
cleanup releases held requests/rights before reaping owned children. A no-op
mutation of the isolation call fails the regression and still cleans up.
Non-macOS builds explicitly report this Mach-specific control unavailable.

Apple's public XNU base explains this mechanism: the
[core-file limit](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/kern_core.c#L421-L425)
does not remove the separate
[crash-notification path](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/kern_exit.c#L1914-L1967).
Notification uses an
[uninterruptible exception exchange](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/osfmk/kern/exception.c#L856-L883).
The process is already
[marked exiting](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/kern_exit.c#L1608-L1618),
so later signals are
[discarded](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/bsd/kern/kern_sig.c#L2138-L2146).
[Port inheritance](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/osfmk/kern/ipc_tt.c#L255-L267)
and [exception-level fallback](https://github.com/apple-oss-distributions/xnu/blob/xnu-10063.141.1/osfmk/kern/exception.c#L674-L709)
explain the narrow isolation choice. This source review uses `xnu-10063.141.1`;
the host's additional `.712.16` patch suffix was not source-compared. The
controlled runtime observations are the direct evidence on this host. Neither
Apple ReportCrash nor any other particular historical receiver is identified.

## Validation and retained artifacts

On macOS 14.8.7 arm64 / Apple Clang 15 and independently on Linux Docker /
GCC 12.2, the normal jobs, PTY and harness checks passed: 94 harness tests,
148 jobs cases, 30 public jobs PTY cases, 14 lifecycle PTY cases, plus the
notification, terminal-fault, retention, ownership and watchdog checks.
Focused terminal ASan/UBSan checks passed on both platforms. The Mach
regression passed natively with normal and sanitizer builds; Linux recorded
it as unavailable. Exact flags, environment, commands and identities are in
the manifests. No new complete `make test` pass or fixed-branch hosted result
is claimed here.

- [Historical provenance](historical-provenance.json) and
  [archive](historical-artifacts.tar.gz): unchanged old logs/samples, original
  binaries, source snapshots and disassembly. `analyze_history.py` verifies
  these offline against the earlier evidence archive.
- [Native manifest](native-validation.json) and
  [archive](native-validation.tar.gz): controlled before/after/sanitizer runs,
  initial mutation, baseline repetitions, temporary observer patch, standalone
  probes and native validation logs. An initial strict reproducer compile
  rejected deprecated `mach_port_destroy`; the corrected build uses receive
  right release and compiled before any experiment ran.
- [Final regression checks](final-regression/): cleanup hardening and its
  normal/sanitizer/error-path controls. These supersede the earlier regression
  source hashes in the native/Linux manifests; original validation artifacts
  remain unchanged. The production fixture change is identical.
- [Linux manifest](linux-validation.json) and
  [archive](linux-validation.tar.gz): independent normal and focused sanitizer
  runs using the repository's strict flags, without additional no-PIE flags.
- [Fixture driver](fixture_case.py), [controlled receiver](reproduce_fixture.c)
  and [temporary observer patch](phase-observer.patch): reproducible experiment
  inputs. The observer patch was used only in the exploratory temporary build.
  The editable receiver includes later cleanup hardening; its originally run
  source remains unchanged in the native archive.

From the repository root on macOS, reproduce the actual fixture comparison
without changing the runner's limits:

```sh
evidence=docs/evidence/csh-057-terminal-crash-notification
probe_dir=$(mktemp -d)
tar -xzf "$evidence/historical-artifacts.tar.gz" -C "$probe_dir" execute_faults-original
chmod u+x "$probe_dir/execute_faults-original"
cc -std=c99 -Wall -Wextra -Wpedantic -Werror "$evidence/reproduce_fixture.c" -o "$probe_dir/receiver"
make build/tests/execute_faults test-job-crash-notification
"$probe_dir/receiver" 1 "$(command -v python3)" "$evidence/fixture_case.py" "$probe_dir/execute_faults-original" "$probe_dir/before.json"
"$probe_dir/receiver" 0 "$(command -v python3)" "$evidence/fixture_case.py" "$PWD/build/tests/execute_faults" "$probe_dir/after.json"
python3 "$evidence/analyze_history.py" > "$probe_dir/history.json"
cmp "$probe_dir/history.json" "$evidence/historical-analysis.json"
```

The first receiver command succeeds only when it observes the expected
deliberate fixture failure; inspect `before.json` for that retained failure.
The second requires the original exact fixture oracle to pass without a
notification. The preserved binary is arm64 macOS-specific. For other macOS
architectures, build the parent revision's fault fixture in a separate checkout
and record the resulting binary identity instead of claiming it is the
historical executable.

## Disposition

This branch builds on retention-budget [PR #172](https://github.com/melliott18/cshell/pull/172),
itself based on diagnostic [PR #167](https://github.com/melliott18/cshell/pull/167).
[CSH-057 / #99](../../tickets/CSH-057-job-lifecycle-boundaries.md) remains at
review pending integration and hosted validation. There is no basis to close
it as unsolvable: the controlled vulnerability has a tested fix. The exact
historical cause remains a **potential host/fixture bug**, explicitly
unconfirmed. A recurrence after isolation, unexpected signal status, sanitizer
finding, ownership failure or cleanup failure remains a failure owned by #99;
capture the selected launch signal, inherited exception-port configuration,
phase and process samples before proposing any further disposition.

## Subsequent hosted closure audit

The [2026-10-01 hosted verification](hosted-verification/README.md) confirms
the terminal repair, including sanitizer coverage. A separate CSH-057 public
PTY timeout and cleanup failure prevent closing the whole ticket. This later
audit supersedes the earlier pending-hosted-validation statement above while
preserving all original observations and their limits.
