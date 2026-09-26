# CSH-054 signal contract evidence

The [exact clause map](../../jobs-signals-evidence.md#csh-054) identifies normative
sources, assertions, scope and remaining owners. The implementation/test revision
is `943e987` on `fix/CSH-054-signal-contracts`, based on `3d1000b`. Subsequent
commits only record documentation/evidence. Final identity JSON includes the full
source manifest and hash over Makefile, Dockerfile, src, include and tests
(excluding Python caches), binary/helper hashes, compiler, flags, platform,
Python and libc/system-library identity. Collection timestamps are UTC.
The final source fingerprint is `99f5bd59826094723bb6de3d8b3de39a8b66fa07473212692c46f213eb965d21`.
Native is macOS 14.8.7 (23J520), arm64, Apple Clang 15.0.0; Docker is
Linux/aarch64, Debian GCC 12.2.0, glibc 2.36-9+deb12u14.
Native, Docker and sanitizer final manifests match.

## Baseline and diagnosis

`baseline-native.log.gz` and `baseline-docker.log.gz` run the ticket's exact
probes through `tests/execute.py:bounded_run`, new sessions, stdin `/dev/null`,
LC_ALL=C, five-second bounds. Before the change:

| Probe | macOS and Linux observed | Required result |
| --- | --- | --- |
| `-ic 'kill -s TERM $$; echo alive'` | -15, empty stdout/stderr | 0, `alive\n`, empty stderr |
| `-c 'kill -s term $$'` | 1, empty stdout, invalid-signal diagnostic | Terminated by TERM (-15), empty stdout/stderr |
| `-c "trap 'false; exit' EXIT; exit 7"` | 1, empty stdout/stderr | 7, empty stdout/stderr |

The final S cases exercise these as passing assertions, not expected failures.
The before Docker image is retained by immutable ID in `docker-images.json`.

The historical CSH-050 macOS timeout had consumed a one-second **cleanup**
budget in `/bin/ps`, without any terminal assertion failure. The new controlled
`test_slow_snapshot_has_budget_and_reap_has_its_own_deadline` models a 1.2-second
snapshot and an exhausted snapshot deadline. `baseline-cleanup-unit.log.gz`
executes that regression against the `3d1000b` harness and fails at the old
one-second deadline. The updated test passes within a five-second enumeration
budget and proves that final leader reaping still gets a separate second after
snapshot failure; the failure itself is never hidden. Total PTY teardown is
bounded by these budgets, separately from the case's five seconds.

The historical snapshot-failure self-test used a 150ms case deadline, including
Python startup, before asserting that setup had written its marker. It now
requires `hanging\n` before sending KILL and injecting the enumeration failure.
The terminal signal helper now consumes a signal wakeup pipe with select,
removing buffered blocking readline from its signal-observation path. It retains
exact `signals ready/interrupt/quit/eof` assertions. The old Linux transcript
alone cannot establish the exact interpreter scheduling of that historical
failure; the new mechanism and concurrent runs address the observed boundary
without declaring the historical run a pass.

Implementation-time logs are retained: `focused.log.gz` caught the ignored
TSTP fork race and host-header spelling mismatch; `focused2.log.gz` caught a
noninteractive inherited-ignore regression in the temporary fork preparation;
`focused3.log.gz` caught a CHLD test action spawning further children. The final
implementation prepares signals only for interactive jobs, retains inherited
ignores and restores actions on launch failure. The CHLD name test uses an
assignment action to avoid generating additional CHLD as its own oracle.

## Runs

The native, sanitizer and Docker initial full commands overlapped to reproduce
the documented load conditions. Their runtime source is identical to `943e987`;
the final test-only change splits one large 256-value exit case into sixteen
16-value batches, preserving all exact expected statuses and five-second case
bounds. A later header comment only clarifies omitted exit status.

| Record / command | Result |
| --- | --- |
| `native-full.log.gz`: `make -j4 test test-pty test-harness` | Status 0; 3,042 runtime cases, 30 runtime PTY, 17 job PTY, one PTY fault fixture, 70 harness self-tests; module/fault checks pass. Preliminary S suite: 316 pass. |
| `docker-full.log.gz`: same command in `cshell-csh054:after` with `--init` | Status 0; same runtime/PTY/harness counts; module/fault checks pass. Preliminary S suite: 409 pass. |
| `sanitizer-full.log.gz`: same command in a separate source/build copy with ASan/UBSan | Status 2: three oversized exit-enumeration cases exceeded five seconds under load. Other prerequisites, module/fault checks, 30+17+1 PTY cases and all 70 harness tests pass. No sanitizer diagnostic. The top-level runtime target was not reached. |
| `native-final.log.gz`: `make -j4 test-traps` | Status 0: final S 361 pass, entry-ignore 20 pass, W 6 pass. |
| `docker-final.log.gz`: `make -j4 test-traps` in `cshell-csh054:final` | Status 0: final S 454 pass, entry-ignore 20 pass, W 6 pass. |
| `sanitizer-final.log.gz`: `make -j4 test-traps test-runtime` in the instrumented copy | Status 0: final S 361, entry-ignore 20, W 6 and all 3,042 runtime cases pass; no sanitizer diagnostics. |

The initial sanitizer failure is retained; batching fixes fixture granularity,
not a shell result or an expanded timeout. The final focused runs rerun every
changed assertion. The remaining full-suite assertions were unchanged.

Native host utility evidence retains 784 passes and 12 known host gaps; Linux
retains 781 passes and 12 known host gaps under CSH-056. These are not new signal
failures. Existing SH-004 unequal uid/gid tests skip without Linux root (CSH-046),
and native translated ENOENT skips because installed candidate locales lack the
translation (CSH-042). No new signal or PTY case is capability-skipped. This
records macOS and Linux Docker/aarch64, not a bare-metal Linux or hosted CI run.

## Reproduction and bounds

```sh
make -j4 test test-pty test-harness
make -j4 test-traps

docker build -t cshell-csh054:final .
docker run --rm --init cshell-csh054:final make -j4 test test-pty test-harness

# Use a separate clean copy to keep native and instrumented objects separate.
make -j4 test test-pty test-harness CC=clang \
  CFLAGS='-Wall -Wextra -Wpedantic -Wshadow -std=c99 -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Runtime cases use smoke.py's controlled PATH=os.defpath, LANG=C, LC_ALL=C,
per-case HOME/TMPDIR, umask 077, resource limits, 65,536-byte combined output
limit and five-second case deadline. W uses the bounded session executor,
FIFO setup, PATH=os.defpath, LANG=C, LC_ALL=C, isolated HOME/TMPDIR and only its
CSH_WAIT_SIGNALS selector; output limit is 2 MiB and time bound five seconds.
Entry-ignore probes use inherited environment and a five-second communicate
bound, with explicit pre-exec dispositions. API fixtures inherit the recorded
harness environment and use their existing watchdogs. No reference-shell vote
sets any expectation; host sh in entry-ignore probes is identified by hash.

PTYs use new controlling sessions, canonical ISIG input, no echo, exact LF
output, 24x80 dimensions, explicit foreground predicates and bounded session
cleanup. The old failed cleanup runs remain historical failures. Passing these
runs does not claim arbitrary-load reliability or complete conformance.
Remaining clauses are explicitly assigned to
[CSH-057](../../tickets/CSH-057-job-lifecycle-boundaries.md) and
[CSH-058](../../tickets/CSH-058-signal-edge-evidence.md).
