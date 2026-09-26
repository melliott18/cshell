# CSH-045: Diagnose intermittent macOS sanitizer jobs fixture timeout

- Status: backlog
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-037
- Branch: Assigned when work starts
- Issue: [#77](https://github.com/melliott18/cshell/issues/77)

## Goal

Make the jobs API fixture reliably distinguish a shell stall from CI scheduling
or sanitizer overhead on macOS.

## Scope

- Isolate which phase of [`tests/jobs_fixture.c`](../../tests/jobs_fixture.c)
  exhausts its 20-second overall alarm on macOS 15 under ASan/UBSan.
- Determine whether a shell wait/reap operation stalls or the fixture bound is
  insufficient under runner load. Retain bounded execution and child cleanup.
- Fix the confirmed cause and add focused repeated coverage without weakening
  job status, signal, descriptor, and ownership assertions.

## Acceptance criteria

- [ ] The timed-out phase and root cause are identified with a failing
  pre-fix observation or targeted diagnostic evidence.
- [ ] A fix passes repeated macOS sanitizer jobs API checks and the full CI
  matrix while retaining a meaningful timeout and all existing assertions.
- [ ] [JOB-003](../posix-matrix.md#job-003) and audit evidence cite the result.

## Validation

Run `make test-jobs` with macOS Clang ASan/UBSan flags, repeat the focused
fixture under the hosted macOS runner, and run full native and Docker test,
PTY and sanitizer checks. Record failing and passing runs with their exact
conditions.

## Implementation notes/evidence

The first `ca42ac0` hosted macOS 15 sanitizer job in
[run 36156787452](https://github.com/melliott18/cshell/actions/runs/36156787452)
failed in the jobs API fixture: `tests/jobs.py` received return code `-14`
(SIGALRM) after the fixture's 20-second overall alarm. The normal build of
that fixture had passed earlier in the same job. A second hosted job for the
same commit in
[run 36156792625](https://github.com/melliott18/cshell/actions/runs/36156792625)
passed, including sanitizers. Local macOS sanitizer and Docker runs also
passed. The phase and cause remain unknown; merely extending the alarm would
hide a possible runtime stall.
