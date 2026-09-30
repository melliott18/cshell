# CSH-074 expanded operation contracts

These continuation records preserve the original evidence directory unchanged.
The selected suite grew from 82 to 168 fixtures, plus required SIGINT and SIGHUP
checks. There are 681 assertions, including 12 explicitly instrumented ed checks
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

`--remaining-contracts` is a separate strict failing suite for native m4 wrap
order, mkstemp and nonnumeric substr status (12 failures). It is not counted
as qualified coverage. Full CSH-074 page acceptance remains open.

Reproduce selected checks with `make test-host-languages`, the broader profile
with `make test-host-profile`, and open m4 contracts using the command in
[the scope document](../../../host-languages-evidence.md).
