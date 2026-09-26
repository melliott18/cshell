# CSH-045: Diagnose intermittent macOS sanitizer jobs fixture timeout

- Status: done
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-034
- Branch: test/CSH-037-audit-follow-up
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

- [x] The timed-out phase and root cause are identified with a failing
  pre-fix observation or targeted diagnostic evidence.
- [x] A fix passes repeated macOS sanitizer jobs API checks and the full CI
  matrix while retaining a meaningful timeout and all existing assertions.
- [x] [JOB-003](../posix-matrix.md#job-003) and audit evidence cite the result.

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

### Diagnosis and correction, 2026-09-26

This failure also recurred at `8f86226` in
[run 36160489602](https://github.com/melliott18/cshell/actions/runs/36160489602).
The follow-up starts at merged `58ca5c3`; CSH-034 is the code prerequisite,
and CSH-037 owns the audit finding.

Phase timing isolated the cumulative cost of 150 rapid-exit pipelines. A
single Apple Clang ASan/UBSan fixture spent about 11.7 seconds there while its
other phases took less than 0.2 seconds each. Eight concurrent unmodified
fixtures all exited with SIGALRM after 20.31–20.45 seconds. Each reached
iteration 120/150 shortly before the alarm and was still making progress;
there was no individual five-second stalled operation in those traces.

The fixture now renews a five-second watchdog before each phase and each
rapid-exit pipeline. All 150 iterations and their ownership/status assertions
remain. The Python runner supplies a separate 60-second overall bound.
Timeouts use an async-signal-safe diagnostic naming the active phase.
Observer pipe writers are closed in the parent, successful exit is checked
with `WIFEXITED`, and notification handshakes are read explicitly, so observer
failure cannot masquerade as success or a silent input wait.

A deliberate `--stall-rapid-exit` mode launches two sleeping pipeline children
and stalls. `tests/jobs.py` requires watchdog status 124, the exact rapid-exit
phase diagnostic, and no live session descendants after runner cleanup.

Recorded validation:

- All eight concurrent fixed sanitizer fixtures passed in 22.80–23.54 seconds,
  exceeding the former aggregate alarm while satisfying the per-operation bound.
- The deliberate stall was detected and cleaned up in 5.45 seconds.
- The complete sanitizer `make -j2 test-jobs` passed: 115 runtime cases,
  ownership/fault checks and the watchdog regression, with zero skips/failures.
- Full normal native macOS and Docker suites passed with the fix. Independent
  code review found no actionable issue. The final hosted repetitions and
  integrated sanitizer result are recorded in the CSH-037 follow-up.

The diagnostic experiment used macOS 14.8.7 (23J520), Darwin arm64 and Apple
Clang 15.0.0, with `-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer` and matching linker flags.
The remaining jobs/signal coverage is [CSH-050](CSH-050-jobs-signals-evidence.md).

### Repeating aggregate sanitizer load

Build `build/tests/jobs_fixture` with the sanitizer flags above in a separate
checkout, then use eight single-threaded worker processes from that checkout:

```sh
python3 - <<'PY'
from pathlib import Path
import multiprocessing
import os
import sys
import time
sys.path.insert(0, 'tests')
from execute import bounded_run

def probe(index):
    start = time.monotonic()
    result = bounded_run([str(Path('build/tests/jobs_fixture').resolve())],
        cwd=Path('.'), env=dict(os.environ, ASAN_OPTIONS='halt_on_error=1',
                               UBSAN_OPTIONS='halt_on_error=1'), timeout=60)
    return index, time.monotonic() - start, result.returncode, result.stderr

if __name__ == '__main__':
    with multiprocessing.get_context('fork').Pool(8) as pool:
        results = pool.map(probe, range(8))
    for result in results:
        print(result)
        assert result[2:] == (0, b''), result
PY
```

At `58ca5c3` the fixture retains the former 20-second aggregate alarm. The
captured pre-fix diagnostic experiment additionally printed monotonic phase
and every-tenth-iteration timestamps, without changing its alarm, operations
or assertions. It used eight thread-dispatched runner calls; the fixed
experiment used eight fork-worker calls as above. The recommended driver
keeps each runner's `preexec_fn` in a single-threaded worker. Host load affects
total duration, so a fast pre-fix pass alone does not validate the old budget.


The integrated source `41c2eb6` passed full native macOS ASan/UBSan and
[all hosted native Ubuntu, macOS 15 and Docker jobs](https://github.com/melliott18/cshell/actions/runs/36217674357),
including sanitizer stages. See the [CSH-037 run record](CSH-037-portability-audit.md#integrated-follow-up-validation)
for identities and counts. Integrated as issue-specific commit `40583ad` in
[PR #85](https://github.com/melliott18/cshell/pull/85), merged as `c012aed`.
