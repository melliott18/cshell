# CSH-065 validation

Implementation: `81d2f0b31b1336b25c587b85c1979bed1e1f654a`, based on
`f075682`. The subsequent documentation commit does not change runtime or test
sources. Validation ran on 2026-09-29 in the separate
`fix/CSH-065-interactive-parser-recovery` worktree.

The [retained probe rerun](contracts.json) uses the unmodified CSH-012
`probe-contracts.py` and the new native sanitizer binary. Its historical
hardcoded revision label is preserved as `probe_historical_source_revision`;
`source_revision` identifies this implementation. All four interactive recovery
cases, all three noninteractive controls and all three interactive-eval controls
pass. Overall the probe returns 1: 19 pass, six fail. All six failures are the
existing CSH-066 depth-128/129 nesting defect, not recovery failures.

## Checks

| Environment | Command | Result |
| --- | --- | --- |
| macOS arm64, Apple Clang 15.0.0 | `make -j4 test` | Passed; default runtime 3,950/3,950, parser 239/239, execution contracts 53/53. Existing host capability gaps/skips remain outside CSH-065. |
| macOS arm64, Apple Clang 15.0.0 | `make -j4 test-runtime test-pty` | Passed; runtime 3,950/3,950; default runtime PTY 33/33, plus job-terminal dependencies. |
| Linux aarch64, Debian GCC 12.2.0 | `make docker-test docker-test-pty DOCKER_IMAGE=cshell:csh-065` | Passed, including runtime 3,950/3,950 and default runtime PTY 33/33. |
| macOS ASan/UBSan | `make -j2 test-parser test-runtime test-pty test-execution-contracts` with sanitizer flags below | Passed: parser 239/239, runtime 3,950/3,950, default runtime PTY 33/33 and execution contracts 53/53. |
| Linux LeakSanitizer | Parser suite with `detect_leaks=1` | 239/239 parser checks and AST ownership fixture passed, including exhaustive allocation sweeps. |
| Linux ASan/UBSan/LeakSanitizer | Focused recovery runtime/PTY suite with `detect_leaks=1` | 46/46 passed: 42 recovery cases, three noninteractive controls and one controlling-PTY case. |

Sanitizer flags: `-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer`; link with
`-fsanitize=address,undefined`. Linux adds `-fno-pie`/`-no-pie`.
`ASAN_OPTIONS=halt_on_error=1:detect_leaks=0` and
`UBSAN_OPTIONS=halt_on_error=1` apply to the full grids; native macOS also uses
`MallocNanoZone=0`. Linux leak checks override `detect_leaks=1`.

Two Linux full sanitizer runtime attempts (first with leak detection enabled,
then disabled) were intentionally stopped because the grids progressed slowly.
Their completed parser/AST checks and the separately completed 46-case recovery
suite are recorded; neither interrupted runtime grid is counted as a full pass.
The full native sanitizer grid and both platforms’ normal default suites passed.

The [invocation map](../../invocation-syntax-evidence.md#interactive-parser-recovery)
records the exact scoped assertions. Recovery fixtures retain five-second
bounds, exact streams/status/prompts and file effects. No whole-family POSIX
conformance promotion is claimed.

[Run summaries and source/log hashes](runs.json) retain the completed scope.
Full local logs are saved under `build/validation/csh-065/` in the worktree.
