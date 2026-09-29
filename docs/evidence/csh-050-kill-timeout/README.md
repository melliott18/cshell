# CSH-050 partial-kill SIGALRM investigation and fixture repair

Base: `3e82c1d4fcb8d3f5552dfbbb57335ed59e5f8595`. Fixture repair: `d1ca90b`.
Investigated on 2026-09-29 UTC. The latest completed failed hosted run was
[36497619126](https://github.com/melliott18/cshell/actions/runs/36497619126),
whose macOS normal job reported `kill state: ungrouped/CONT/after`, status -14
and empty stdout. Its original log remains in the
[preceding acceptance record](../csh-050-disposition/partial-kill-failure.log.gz).
The later passing duplicate does not erase that failure.

## Findings and repair

The unmodified fixture reproduced the same SIGALRM locally on attempt 722.
An otherwise unchanged phase probe reproduced it inside the final `wait`
builtin, after successful CONT delivery, immediate job-state assertions, and
writing both release bytes. Sampling another failure found the parent in
`wait_job` / `sigsuspend` and both children in
`raise` / `pthread_kill` / `__pthread_kill`. Their process states were sleeping,
not reported stopped. A separate alarm-time snapshot found one completed child
and one unfinished child, with no pending SIGCHLD and no waitable event for
the latter. Sampling and snapshots are from separate failed invocations.

[stop_minimal.c](stop_minimal.c) contains no cshell code. It forks two children,
uses the same launch/release pipes, observes real SIGSTOP with
`waitid(WSTOPPED|WNOWAIT)`, consumes the stop reports, sends CONT and waits for
exact exits 23/24. It reproduces the failure with self-directed `raise(SIGSTOP)`
and also with `kill(getpid(), SIGSTOP)`. Therefore changing only the self-stop
API is not a repair. The corresponding fixture experiment also failed.

The demonstrated boundary is a Darwin self-stop/continue sequence: a child can
remain inside the self-stop syscall after the parent has observed WSTOPPED
and delivered CONT. These observations do not identify the exact internal
kernel interleaving. The isolated reproducer establishes that cshell's job
bookkeeping is not necessary for this hang. It does not establish a general
claim about every Darwin stop/continue operation.

The repaired fixture sends SIGSTOP **from the observing parent** after creating
the children. Children remain bounded by the existing release pipe. It retains
the same two real children, process groups, WSTOPPED/WNOWAIT checks, immediate
stopped-state assertions, injected EPERM boundaries, exact diagnostics, final
pipeline-stage status and ECHILD check. The four-second alarm, five-second
runner deadline and descendant cleanup are unchanged. No sleeps, retries,
skips, expected-failure rules or production runtime changes are introduced.

The parent-stop minimal program and repaired original case each pass 3,000
repetitions. All 14 repaired cases additionally pass 100 repetitions each.
More importantly, substituting only the original pre-PR-120 `kill` bookkeeping
into the current runtime causes the same eight immediate-state assertion
failures with the repaired fixture (six controls pass). Thus the setup change
preserves the regression oracle; it does not hide the original delivery defect.

## Failed and passing experiments

All invocations retain the original four/five-second bounds. A repetition
stops on its first failure; numbers below include that failing attempt.
The detailed per-attempt records are compressed, and
[repetitions.json](repetitions.json) indexes their outcomes.

| Variant | Attempts | Result |
| --- | ---: | --- |
| Unmodified fixture (`baseline`) | 722 | SIGALRM, empty stdout |
| Verbose phase trace (`traced`) | 2,000 | Passed; instrumentation altered scheduling and did not reproduce |
| Minimal alarm-time phase (`phase`) | 235 | SIGALRM in phase 7, final wait |
| PID-printing sampler (`sampled`) | 5,000 | Passed; not used to infer absence of the race |
| Sampler without candidate PID writes (`sampled-minimal`) | 83 | SIGALRM; parent/child stacks retained |
| Alarm-time job/wait snapshot (`alarm`) | 286 | SIGALRM in final wait; one child still unfinished |
| Standalone self `raise` (`minimal-raise`) | 143 | SIGALRM |
| Standalone self `kill` (`minimal-kill`) | 425 | SIGALRM |
| Fixture self `kill` experiment (`after`) | 468 | SIGALRM; rejected approach, not the final fix |
| Standalone parent stop (`minimal-parent`) | 3,000 | Passed |
| Repaired original case (`parent`) | 3,000 | Passed |
| Repaired complete 14-case rotation (`all-parent`) | 1,400 | Passed |

[sample-0.txt](sample-0.txt), [sample-1.txt](sample-1.txt),
[sample-2.txt](sample-2.txt) and [stalled-ps.txt](stalled-ps.txt) preserve the
sampled failure. [phase.log](phase.log) contains `H` (phase 7).
[alarm.bin](alarm.bin) is ten native 32-bit integers:
`[7,0,0,2,-1,0,0,0,0,0]`: phase, blocked/pending CHLD, then each child's
`2*done+stopped`, `waitpid` return and status, followed by a spare zero.
The alarm observer samples after the deadline and re-raises SIGALRM; it cannot
turn a failed case into a pass. It is diagnostic code, not shipping code.

## Validation of the fixture repair

Normal and sanitizer source manifests have the same SHA-256:
`2fb1d6258665049fa2595355fd036d5ddd7df2c88be55523fd6a8bcfa7540d13`.
Native: macOS 14.8.7 (23J520), arm64, Apple Clang 15. Docker: Debian 12 arm64,
GCC 12.2, glibc 2.36. The identity JSON records source manifests, compiler/OS,
Python, flags and binary hashes. Docker is not a separate native Linux claim.

| Check | Result |
| --- | --- |
| Native `make -j4 test-jobs-signals test-harness` | Pass: 14 partial-kill cases, 148 public jobs, 207 trap/exit, 2,464 signal edges, 361 contracts, retention/API/fault/wait checks, 30 jobs PTY + one fault PTY, 32 runtime PTY, 86 harness tests. |
| Docker same normal command | Pass: corresponding suites, 2,495 signal edges, 454 contracts, 86 harness tests. |
| Native ASan/UBSan `make -j4 test-jobs test-jobs-pty` in a separate source copy | Pass: 14 partial-kill, 148 jobs, retention/API/fault/watchdog, notification and 30+1 PTY checks. No sanitizer diagnostic. |
| Docker ASan/UBSan same focused command after a clean rebuild | Pass: the same 14 partial-kill, 148 jobs, retention/API/fault/watchdog, notification and 30+1 PTY checks; no sanitizer diagnostic. Binary hashes are appended to the retained log. |
| Repaired fixture with old partial-delivery bookkeeping | Expected failure: eight immediate-state assertions fail; six controls pass. |

No capability skips occurred in these focused checks. This fixture-only change
does not claim a fresh full general-runtime or full sanitizer conformance sweep.
Normal flags are the Makefile defaults. Sanitizer flags are
`-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer`, with matching sanitizer
link flags. Native sanitizer calls set `MallocNanoZone=0` and halt-on-error
options; Docker's caller additionally sets `detect_leaks=0`. Smoke supplies its
controlled C-locale environment and does not inherit ASAN/UBSAN options; API
drivers inherit caller options. No blanket LeakSanitizer claim is made.

The original baseline and rejected self-kill fixture binaries were overwritten
before hashing; their source variants and run results are retained, not
retroactively assigned the final binary identity. Diagnostic binaries still
available at collection are hashed in `native-identity.json`. The standalone
binary hash is the final three-mode version (raise/self-kill/parent); its two
earlier failing runs used the version before adding the parent mode. No failed
result is attributed to a later passing binary.

## Reproduction and acceptance

For the production checks, use `make test-kill-job-state` and the validation
commands above. For the isolated reproducer:

```sh
mkdir -p build/csh050-investigation
cp docs/evidence/csh-050-kill-timeout/stop_minimal.c build/csh050-investigation/
cp docs/evidence/csh-050-kill-timeout/repeat-minimal.py build/csh050-investigation/
cc -std=c99 -Wall -Wextra -Wpedantic -O2 \
  build/csh050-investigation/stop_minimal.c -o build/csh050-investigation/stop_minimal
python3 build/csh050-investigation/repeat-minimal.py 3000 /tmp/self-stop.json raise
python3 build/csh050-investigation/repeat-minimal.py 3000 /tmp/parent-stop.json parent
```

The repetition script uses the production single-threaded smoke runner and
bounded descendant cleanup. A particular repetition count does not guarantee
reproduction. The retained C diagnostic variants and observer scripts preserve
the investigation, including approaches that did not reproduce or repair it;
they are outside CI and shipping runtime inputs.

CSH-050 / #82 owns this repair. It removes the reproduced fixture failure as
an unexplained acceptance blocker once validated, without reclassifying the
old hosted run as passed. Keep the ticket at `review` until integration.
Hosted metadata identifies the old failure and the main validation snapshot
separately; pending checks are not passes. The historical CSH-057 retention
timeout remains covered by its own unknown-cause disposition; this investigation
does not establish its cause or change its reopening policy. CSH-012 stays closed.
