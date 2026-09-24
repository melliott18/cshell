# CSH-034: Implement process groups and terminal job control

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-011
- Depends on: CSH-006, CSH-033
- Branch: `feature/CSH-034-job-control`
- Issue: [#35](https://github.com/melliott18/cshell/issues/35)

## Goal

Track interactive jobs and transfer the controlling terminal safely between the
shell and foreground process groups while preserving non-interactive execution.

## Scope

- Coordinate with the executor owner on process creation, group assignment,
  status collection, and single ownership of every child and descriptor.
- Implement foreground terminal handoff/restoration, background jobs, stopped and
  continued state, and required job-related builtins/options for the profile.
- Own `jobs`, `fg`, `bg`, `wait`, and applicable `kill` integration; provide safe
  signal notification plumbing, with full trap semantics deferred to CSH-035.

## Acceptance criteria

- [x] Foreground pipelines share the required process group and receive terminal
  signals; the shell regains control after completion or stop and stays usable.
- [x] Background, stopped, and resumed jobs have stable records, tested status
  reporting, and eventual reaping without double waits or lost children.
- [x] Job builtins and monitor-mode transitions validate operands and produce
  specified status/results, including missing jobs and interrupted waits.
- [x] Terminal capability checks disable unavailable job control cleanly while
  leaving scripts, redirected input, and non-interactive pipelines functional.
- [x] Timeout/error paths restore terminal state and release owned resources.

## Validation

Use CSH-033 for Ctrl-C, Ctrl-Z, background completion, foreground/background
continuation, and terminal restoration. Run native and Docker script regressions
and stress rapid child exits; record platform/profile applicability and skips.

## Implementation notes/evidence

The runtime now attaches an owned job manager to its persistent execution
context. The executor registers direct stage PIDs before releasing a launch
barrier; jobs.c alone collects those statuses. Parent/child group assignment,
blocked launch signals, terminal handoff, saved modes, and cancellation share
this boundary. Existing synchronous prepared-command APIs retain their direct
child contract. See [Job control](../job-control.md) for the implemented profile,
commands/options, status retention, and ownership details.

Validation on 2026-09-23:

- Native macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2: normal build,
  `make test test-pty test-harness`, and a full final ASan/UBSan
  `make test test-pty` with `-Wall -Wextra -Wpedantic -Wshadow -Werror` passed.
  The sanitizer job suite passed twice consecutively after integration with
  CSH-026, including its bounded ownership fixture.
- Debian bookworm Linux Docker, native arm64: full normal `make test test-pty`
  passed. The job target also passed with ASan/UBSan and leak detection enabled.
- `make test-jobs`: 115 builtin cases across command strings, files and stdin;
  direct ownership/foreign-child isolation, retained statuses, 150 rapid
  background pipelines, idle reaping/notification, and interrupted-wait checks.
  Allocation, pipe, fork and wait failure sweeps leave no owned child/fd leaks.
- `make test-jobs-pty`: 12 shell terminal cases plus a terminal fault fixture
  covering group assignment, terminal handoff/restoration, wait errors, and
  SIGINT/SIGTSTP delivered before child signal reset. No PTY capability skips.
- Existing runtime, execution, pipeline and context regressions remain passing:
  429 cross-mode runtime cases, 10 baseline PTY cases, and 61/52/60 respective
  behavior cases with their API/fault checks.

The signal tests cover Ctrl-C/Ctrl-Z, grouped pipelines, bg/fg, background
terminal reads, current/previous/ambiguous job IDs, monitor transitions, and
shell/job terminal settings. The bounded CSH-033 harness owns timeout cleanup.
Output-error fixtures also check closed descriptors without leaking libc stream
buffers. Full trap/input recovery, signal inheritance review, exit/hangup policy,
and the integrated CSH-011 acceptance review remain CSH-035 work; general option
and invocation parsing remains CSH-032. No full POSIX/UP/XSI claim is made.

## Integration record

- Implementation commits: `cdcb359` and `9887f8b`.
- CSH-026 integration merge: `a131847`.
- Merged by [PR #66](https://github.com/melliott18/cshell/pull/66) as
  `045a6fa`; [issue #35](https://github.com/melliott18/cshell/issues/35) closed.
- Both hosted workflow runs passed on Ubuntu, macOS, and Docker after rerunning
  one transient Ubuntu PTY timeout in the duplicate run.
