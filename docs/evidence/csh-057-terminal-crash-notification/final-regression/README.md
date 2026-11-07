# Final cleanup regression checks

[results.json](results.json) records the final source/binary hashes, commands,
expected exit codes and 25 command outcomes. The normal and ASan/UBSan Mach
regression pass; disabling the isolation call fails as expected.

The regression and editable receiver save SIGCHLD, set its default disposition
without SA_NOCLDWAIT before fork, and restore it after cleanup. This prevents
auto-reaping from invalidating PID ownership between a wait and a signal.
Cleanup checks the exact child and does not signal a reaped child or ECHILD.
A constructor in `observe_kill.c` in the [artifacts archive](artifacts.tar.gz) deliberately starts with
SIGCHLD ignored; normal and sanitizer checks pass and verify restoration.
Archived `mutations.json` controls remove the default-disposition setup to exercise
ECHILD failures, with no additional cleanup signal or unreaped-child warning.
The final process snapshot found no surviving experiment processes.

The final editable receiver also reran the actual terminal oracle: the original
binary timed out at five seconds with empty output/-9 (6.040 seconds including
cleanup); the fixed binary passed in 0.060 seconds. Its two result files and
logs are retained here. Archived `make-target.log` additionally records
the final repository Make target passing at its normal O2 flags.

The earlier exact-wait-only cleanup version and its unsuccessful attempt to
inherit SIGCHLD ignore through Darwin exec are preserved in
[cleanup-ownership-regression](../cleanup-ownership-regression/). That exec
attempt reset the disposition and did not exercise the intended error path;
its result is not claimed as an ECHILD witness. Source snapshots distinguish
that intermediate version from the final version here. The original native
and Linux validation archives remain unchanged.

All referenced logs, source snapshots, mutation inputs and survivor checks are
in `artifacts.tar.gz`, with member paths matching the manifest. Extract to a
temporary directory to inspect them; no archived experiment is run by extraction.
