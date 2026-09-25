# CSH-044: Diagnose intermittent background-resume prompt stall

- Status: backlog
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-037
- Branch: Assigned when work starts
- Issue: [#76](https://github.com/melliott18/cshell/issues/76)

## Goal

Make the interactive prompt after `bg` reliable under the Linux PTY suite.

## Scope

- Reproduce or isolate the intermittent `Ctrl-Z jobs bg fg Ctrl-C` failure in
  [`tests/jobs_cases.py`](../../tests/jobs_cases.py), especially after the job
  reports `Running` but the next primary prompt does not appear.
- Determine whether the shell stalls, the harness misses output, or host load
  exceeds the fixture deadline. Preserve exact PTY output and process-group
  assertions; do not turn a genuine shell stall into a passing skip.
- Add a timing-independent regression or a bounded stress fixture for the
  confirmed cause. Keep terminal and child cleanup checks intact.

## Acceptance criteria

- [ ] The root cause is identified with a bounded reproducer and a failing
  pre-fix observation.
- [ ] The fix passes repeated native Ubuntu and Docker PTY checks, including
  ASan/UBSan, with no hidden deadline or output relaxation.
- [ ] The [JOB-002](../posix-matrix.md#job-002) and
  [JOB-003](../posix-matrix.md#job-003) evidence records are updated.

## Validation

Run the focused PTY case with `make test-jobs-pty`, repeat it under the GitHub
Ubuntu runner, then run full `make test test-pty test-harness` on native Linux,
macOS and Docker. Record both failing and passing run URLs.

## Implementation notes/evidence

The first CSH-037 push failed in the Ubuntu 24.04/GCC job of
[run 36156253758](https://github.com/melliott18/cshell/actions/runs/36156253758).
The shell printed `[1]+ Running ... hold\n` after `bg`, but the expected `$ `
prompt did not appear within five seconds. Session cleanup killed the shell.
The same revision passed in the second Ubuntu job of
[run 36156295337](https://github.com/melliott18/cshell/actions/runs/36156295337).
Mac and local Docker PTY runs passed this case. The cause remains unknown.
