# CSH-032: Complete shell option behavior and interactions

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-008, CSH-009, CSH-029, CSH-031
- Branch: feature/CSH-032-shell-options
- Issue: [#33](https://github.com/melliott18/cshell/issues/33)

## Goal

Make supported invocation and runtime options produce their specified effects
across control flow, expansions, redirections, and pipelines.

## Scope

- Inventory non-job-control options and invocation operands with CSH-029; implement
  `errexit`, `nounset`, `noclobber`, `noglob`, tracing, no-execution mode,
  Issue 8 `pipefail`, and remaining applicable options.
- Connect invocation parsing and `set` option handling to shared state, with
  documented inheritance and restoration in functions/subshells/substitutions.
- Coordinate monitored job-control options with CSH-034; complete cross-feature
  checks for evaluation builtins and aliases from CSH-031.

## Acceptance criteria

- [x] Option parsing, reporting, enabling, disabling, invalid operands, and `--`
  behavior are mapped to tests for invocation and runtime `set` usage.
- [x] `errexit` and `pipefail` fixtures cover conditionals, AND/OR lists, pipelines,
  functions, negation, and substitutions with explicit expected shell status.
- [x] `nounset`, `noclobber`, and `noglob` tests cover normal and error paths and
  demonstrate the required interaction with expansion and redirection contexts.
- [x] Tracing and no-execution behavior have output/side-effect assertions;
  remaining inventoried options have equivalent requirement-to-test mappings.
- [x] Option state propagates or restores correctly across execution environments.
- [x] Evaluation and alias interactions pass integrated option tests before this
  ticket closes; job-specific option integration remains with CSH-034/035.

## Validation

Run focused option fixtures and cross-feature scripts on native and Docker builds.
Use explicit expected behavior grounded in the targeted standard, documenting
permitted choices instead of accepting a single reference shell as the oracle.

## Implementation notes/evidence

The shared `options.h` inventory now drives invocation, runtime `set`, option
reports and `$-`. Input observers implement verbose/ignoreeof; execution tracks
errexit test contexts, immediate noexec and PS4 tracing. Pipeline status selection
captures pipefail, including retained job results. Redirection preparation selects
exclusive noclobber opens; shared assignment state applies allexport consistently.
Existing nounset/noglob expansion paths are exposed through both entry points.

[Shell options](../shell-options.md) documents the full inventory, API boundaries,
inheritance and permitted choices, including default-off hashall, no-op nolog,
noexec honored interactively, omitted `c`/`s` letters in `$-`, and invocation `-o`
without a name diagnosed. The current base profile remains unchanged: `vi`,
history/mail, and the remaining UP prompt/variable obligations stay open under
CSH-037 and the existing profile-allocation gates. PS4 is the implemented subset.

Validation on 2026-09-24:

- Native macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2:
  `make -j4 test test-pty` passed, including 1,237 runtime cases, 20 runtime PTY
  cases, 12 job PTY cases, and all module/API/failure suites.
- `make test-options` passed all 258 focused cases across command strings,
  files and stdin. The tests also run in the full runtime suite. They assert
  statuses, diagnostics, output and filesystem effects, including concurrent
  noclobber creation, FIFOs, symlinks, loop activation of noexec, nested errexit,
  eval/dot/aliases, invocation monitor overrides and background pipefail snapshots.
- `make test-harness` passed all 62 harness tests.
- `make docker-build DOCKER_IMAGE=cshell-test:csh-032`, then
  `docker run --rm --init cshell-test:csh-032 make -j4 test test-pty` passed the
  same complete suites on Linux aarch64, Debian GCC 12.2.0 and Python 3.11.2.
- Linux AddressSanitizer/UndefinedBehaviorSanitizer validation: pending final run.
  The first run caught a glibc `dprintf` allocation leak on closed stdout in the
  new option report. Reports, traces and state-builtin diagnostics now use
  allocation-free checked writes. Regression cases cover closed trace stderr
  and reports with both output descriptors closed.
- `git diff --check` and Python fixture compilation passed.

Expected outcomes follow Issue 8 rather than a reference-shell oracle. Targeted
reference checks helped investigate the distinction between exempt compound
statuses and ordinary function/eval/dot call statuses; fixtures encode the
standard's simple-command/compound-command distinction explicitly. Job-specific
signal/trap integration remains CSH-034/035. This ticket alone does not establish
whole-shell POSIX compliance.
