# CSH-074 expanded operation contracts

These continuation records preserve the original evidence directory unchanged.
The selected suite grew from 82 to 174 fixtures, plus required SIGINT and SIGHUP
checks. There are 705 assertions, including 12 explicitly instrumented ed checks
and eight supplemental XSI regressions; no known-gap allowance is used.

- `native-attempt1`: 642 pass / 11 fail. Stock xargs drops an empty NUL argument
  and skips empty input. The first private ed SIGINT driver signaled while
  `system()` temporarily ignored SIGINT; a subsequent editor prompt now gates it.
- `native-attempt2.log`: 653 pass / 0 fail after provider and driver repairs.
- `provider-attempt1`: rerun before the source-download adapter completed;
  retains the previous-provider failures.
- `provider-attempt2`: 81 pass / 12 fail. Upstream xargs shared-vfork errno did
  not propagate on Darwin, and logical EOF appended an empty invocation.
- `provider-attempt3`: 93 pass / 0 fail after portable fork/error-pipe reporting
  and the logical-EOF guard.

The first expanded full-profile run passed 1162 existing checks plus 677
language checks, but development continued during that run, so it is preliminary
and is not the final source-identity qualification. Final records are added
separately. Every JSON record contains selected paths/hashes, invocation,
source/build identity, limits, effects and cleanup results. `records.json` hashes
the uncompressed bytes; compressed files have deterministic gzip timestamps.

The initial `--remaining-contracts` run records 12 native m4 failures for wrap
order, missing mkstemp and nonnumeric substr status. The private GNU M4 provider
subsequently passes all 12 repaired checks, all 80 existing m4 checks, and a
24-check regression selection including wrap stress and unique mode-0600 files.
Those six cases now belong to the default 705-check suite.

Linux CI at `dda3a0d` passes all 681 ordinary assertions, then fails compilation
with GCC `-Werror` on xargs fallthrough/ignored-write diagnostics. The correction
makes both control flows explicit. Its raw job log and native record are retained.
Native full profile at that revision passes 1162 existing plus 681 new checks.
Native runtime passes 3950 checks; the subsequent existing PTY failure-injection
case fails and its log is retained. These earlier runs are separate from the
final expanded-provider validation.

Reproduce selected checks with `make test-host-languages`, the broader profile
with `make test-host-profile`, and open m4 contracts using the command in
[the scope document](../../../host-languages-evidence.md).

Linux CI at `12e5bbd` passes all 705 ordinary checks and builds all sanitizer
providers, then reports 693 pass / 12 fail. Native ASan/UBSan reproduces the same
12 ed failures: upstream regex replacement forms a pointer from NULL for a
zero-byte prefix copy. The adapter now skips those copies before allocation.
The signal runner additionally rejects child-editor sanitizer diagnostics, even
on the HOME recovery path where ordinary diagnostics are allowed. A negative
control proves that a recovered file cannot turn that sanitizer error into a pass.

## Final operation-suite qualification

| Platform | Ordinary | ASan/UBSan | Record |
| --- | --- | --- | --- |
| Native macOS | 705 pass / 0 fail | 705 pass / 0 fail | `native-ordinary-final-705.json.gz`, `native-sanitizer-final.json.gz` |
| Hosted Ubuntu 24.04 | 705 pass / 0 fail | 705 pass / 0 fail | `linux-ordinary-final-705.json.gz`, `linux-sanitizer-final-705.json.gz` |

All four records contain the identical source/build-input digest
`c32b44ba846703ba5a34fd7f6392fc0718492278c5a838a5a31cedfa1675d397`.
The Linux records and raw job log come from the successful
[dedicated contract job](https://github.com/melliott18/cshell/actions/runs/36650501560/job/109683266994)
at code revision `a058d5f`. The local ordinary rebuild restores uninstrumented
executables after sanitizer validation. M4's record preserves requested and
effective flags; its upstream build removes `-Werror` only, retaining both
sanitizers. Fixture-level sanitizer diagnostics remain strict failures.

Hosted macOS jobs remained queued during this validation; local macOS provides
the native platform evidence. The local Docker daemon remained unavailable;
the Ubuntu result is explicitly a hosted native run, not Docker evidence.
These results qualify the stated operation subset, not the entire eight pages.

The final local `make test-host-profile` passes all 1162 existing checks and all
705 language checks, with zero gaps. The subsequent selected-PATH
`make test-runtime` passes 3950 checks. The corresponding final logs and existing
profile JSON are retained separately. The earlier PTY failure remains recorded;
no whole-PTY or whole-system qualification is inferred from these results.
