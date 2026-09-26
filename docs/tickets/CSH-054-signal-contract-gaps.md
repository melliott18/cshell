# CSH-054: Complete residual jobs and signal contracts

- Status: ready
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-034, CSH-035
- Branch: Assigned when work starts
- Issue: [#90](https://github.com/melliott18/cshell/issues/90)

## Goal

Resolve the concrete defects and finish the narrower unverified obligations in
[CSH-050's clause map](../jobs-signals-evidence.md). This ticket owns residual
[EXEC-009, JOB-001–003, SIG-001–003](../posix-matrix.md), and
[U-008, U-015, U-026, U-032](../posix-utilities.md) evidence. CSH-050's new passing
witnesses do not close these requirement families or CSH-012.

## Confirmed defects

At CSH-050's source based on `b692aa5`, on macOS 14.8.7 arm64:

| Invocation | Required result and source | Observed |
| --- | --- | --- |
| `./cshell -ic 'kill -s TERM $$; echo alive'` with redirected stdin | Interactive sh ASYNCHRONOUS EVENTS requires ignoring untrapped TERM: stdout `alive\n`, status 0 | Empty stdout/stderr; process killed by TERM (`subprocess` return code -15) |
| `./cshell -c 'kill -s term $$'` | kill OPTIONS requires case-independent names: successful signal delivery terminates this noninteractive shell with TERM | Status 1, empty stdout, `cshell: kill: invalid signal\n` |

Both probes use the bounded session runner in `tests/execute.py`, five seconds,
`LC_ALL=C`, and no terminal. Reproduce using `bounded_run`, not a command that
could signal the invoking developer's shell. They were also reproduced in the
CSH-050 Linux image. They are failures, never expected-success regression
oracles. Add passing regressions when fixed, including inherited signal ignores,
trap overrides, child exec defaults and case-independent `-s 0`/signal names.

## Loaded macOS cleanup failure

A CSH-050 run of `make -j4 test test-pty test-harness`, concurrent with a
separate full sanitizer build/run and Docker build/run, failed P `Ctrl-Z jobs bg
fg Ctrl-C` in `pty_harness.cleanup_session`: `/bin/ps -axo pid=,stat=` timed out
at 0.99965 seconds. There was no transcript or foreground assertion failure.
This is a failed loaded run, not a recurrence proven to have CSH-044's prompt
write cause. CSH-054 owns reproducing and resolving this transport/load boundary
with the CSH-040 cleanup harness; isolated later passes do not erase it.
The concurrent sanitizer suite had the same cleanup timeout in `nested
background startup and restoration` (0.99924 seconds). A Docker harness run
also failed `test_snapshot_failure_reports_teardown_error_and_reaps_leader`
before process setup and `test_terminal_control_characters_deliver_interrupt_quit_and_eof`
waiting for `interrupt\n` after `signals ready\n`. CSH-054 owns reproducing
these with the CSH-033/040 transport fixtures; no shell defect is inferred
solely from these harness self-test failures.

## Remaining clause coverage

The exact passing cases and source anchors are in the linked clause map. The
following are unverified; do not infer that they are all implementation defects:

- EXEC-009/U-032: CHILD_MAX retention and permitted eviction, fg consumption of
  known IDs, selected trapped wait followed by a second wait.
- JOB-001: controlling-session-leader startup when a different group initially
  owns its terminal.
- JOB-002: background pipeline/compound group membership, permitted suspended
  compound membership, no replay of completed commands, SIGSTOP while the shell
  executes a builtin and subsequent CONT.
- JOB-003: notification timing while a foreground command runs, stop-signal
  variants, jobs output formats and completed/signal notification formatting.
- SIG-001/D-007: decide and test unmonitored TSTP/TTIN/TTOU actions; a caught
  no-op stop signal is not one of sh's permitted unmonitored actions. Test direct
  interactive QUIT/TSTP delivery and all inherited/overridden dispositions.
- SIG-002: replace delay-based wait scheduling with a deterministic blocked-wait
  handshake; test non-INT interruption, second wait and multiple-signal variants.
- SIG-003: reset caught actions across pipeline, background and general command
  substitution shapes; failed interactive exec restores traps.
- U-008: all 0–255 operands, applicable signal-derived operands, and omitted
  operand inside EXIT actions after intervening commands.
- U-015: exhaustive host condition listing/reinput including numeric host
  extensions, mixed invalid operands and output errors.
- U-026: isolated zero/negative group operands, all required symbolic names and
  `-l` conversions, multi-operand failures and permission errors. External host
  utility defects remain with CSH-052, including Debian procps status mapping.

## Acceptance criteria

- [ ] Fix the TERM and lowercase kill defects with bounded failing-before and
  passing-after native and Docker assertions.
- [ ] Resolve each clause above with exact cases or further explicitly owned
  tickets; retain UP/XSI and unspecified portions separately.
- [ ] Diagnose the recorded cleanup/setup/signal harness failures under load,
  retaining bounded cleanup and exact terminal assertions.
- [ ] Document the D-007 unmonitored stop policy and its process/terminal tests.
- [ ] Update forward and reverse requirement links and platform evidence without
  promoting whole families based on partial tests.

## Validation

Run `make test test-pty test-harness`, focused jobs/trap targets, Docker and
ASan/UBSan. Use the [evidence identity contract](../posix-evidence.md).
Capability skips must retain an owner and cannot stand in for passing behavior.
