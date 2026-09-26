# CSH-055: Complete residual execution contracts

- Status: review
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-031, CSH-039
- Branch: `fix/CSH-055-execution-contract-gaps`
- Issue: [#92](https://github.com/melliott18/cshell/issues/92)

## Goal

Fix the prefix-PATH lookup defect and complete the narrower unverified
execution obligations identified by [CSH-049](CSH-049-execution-evidence.md).
The [clause map](../execution-evidence.md) retains passing witnesses; this
follow-up does not invalidate them or promote their whole families to verified.

## Original defect: EXEC-004 (fixed)

At baseline `daa1be1`, and with the unchanged runtime in CSH-049, a temporary
PATH prefix does not affect the selection of the PATH-associated `pwd` builtin.
Create executable `bin/pwd` containing `#!/bin/sh` and
`printf 'custom-pwd\n'`, then execute:

```sh
./cshell -c 'PATH=bin pwd'
```

Required: `custom-pwd\n`, empty stderr, status 0. Observed on native macOS and Debian Docker:
the absolute working directory plus newline, empty stderr, status 0.
`runtime_simple` resolves the category before prefix values are applied;
`path_builtin_category` consequently searches the old PATH. The external-only
prefix PATH witnesses do not expose this category-selection error.

Sources: [2.9.1.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_02)
and [2.9.1.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_04).
[The strict reproducer](../../tests/fixtures/execution-known-gaps.json) asserts
the required result, not the buggy output. It was intentionally separate from
passing default suites at baseline. CSH-055 now includes the same required
behavior in the default generator in all three invocation modes. Run it with the normal bounded harness:

```sh
python3 tests/smoke.py ./cshell --suite tests/fixtures/execution-known-gaps.json
```

## Residual clause scope (covered below)

- RED-001/EXEC-005: public-runtime initially closed stdout/stderr and combined
  standard-descriptor masks in string/file modes, inherited open descriptor
  flags and argv[0] after direct/PATH execution. Existing seven-mask pipeline
  tests are API evidence. POSIX permits reopening closed standard descriptors;
  sanitizer startup can do so, and the oracle must distinguish that permission
  from loss of a required inherited descriptor.
- EXEC-001/003: no-name redirection/substitution environment combinations with
  traps and expansion side effects. Preserve source-permitted alternatives.
- EXEC-015: inject unrecoverable command-read failures with already-buffered
  commands, asserting no subsequent command execution except EXIT actions;
  interactive failure must also exit. Cover the dot-file exception and
  `command .` suppression separately. EOF/EINTR/module errors are insufficient.
- EXEC-014: nested function syntax/error recovery and restoration combinations;
  keep documented parser/function recursion ceilings linked to CSH-046.
- U-003/U-004: continue from while/until condition lists and nested lexical
  combinations; distinguish function/eval/non-lexical enclosure policy from
  required same-environment lexical enclosure.

Other residual owners remain CSH-047 (expansion), CSH-048 (environment/state),
CSH-052 (host utilities/fallback), CSH-053 (multibyte lexical boundaries), and
CSH-054 (signals/jobs). SH-009/O-026 absolute filesystem capabilities remain
host-qualified in CSH-043/049, not a promise to test every filesystem.

## Acceptance criteria

- [x] Prefix PATH participates in PATH-associated builtin selection, including
  replacement PATH, repeated prefixes, restored attributes, functions,
  `command -p`, pipelines and failure cleanup. The strict reproducer passes
  in all three modes and joins the default suite.
- [x] Every remaining condition above has normative/policy classification,
  exact assertions and scoped native macOS/Linux run records or a concrete
  narrower follow-up owner.
- [x] Reverse links, matrix state and CSH-012's closed compliance gate remain
  accurate; expected failures are never counted as passes.

## Validation

Run `make test-execution-evidence test-execute test-pipeline test-context
 test-control test-runtime test-runtime-pty test-harness`, then full normal,
Docker and relevant ASan/UBSan checks. Record source, suite, binary identity,
compiler/flags, OS/libc and capability skips under the evidence policy.

## Implementation

- Expanded final PATH prefixes feed the shared search candidate construction
  before PATH-associated builtin selection. Prefix lookup ignores stale cached
  paths and leaves assignment export/lifetime restoration to the existing scope.
- Input exposes its sticky failure state. A sourced-file read error follows
  special-utility consequences, so interactive dot and `command .` can recover.
  Main command-read failure suppresses pending non-EXIT actions, including during
  EXIT evaluation.
- The [residual contract map](../execution-contracts.md) classifies every named
  condition and links exact assertions. Default runtime coverage adds 71 cases
  to CSH-049's 248 execution cases (319 total), plus 51 bounded descriptor/read
  probes. Allocation sweeps check prefix attributes, nested frames and cleanup;
  malformed prepared pwd assignments are rejected before category lookup.
- The [matrix](../posix-matrix.md), [utility map](../posix-utilities.md), and
  [CSH-049 reverse links](../execution-evidence.md) retain implemented-subset
  status. CSH-012 remains blocked on the broader conformance obligations.

## Validation record

Collected 2026-09-26 from integration base `3d1000baf1da70590548f6bbcd12a1355fcb5dc4`.
[Identity manifests and compressed logs](../evidence/csh-055/README.md) distinguish
initial and final source versions, binaries and generated suites. Tests use
exact outcomes from the source/policy map, not differential-shell agreement.

Environment: native macOS 14.8.7 build 23J520 / Darwin 23.6.0 arm64, Apple Clang
15.0.0, Python 3.12.2, libSystem; Docker Debian bookworm, Linux 6.4.16-linuxkit
arm64, GCC 12.2.0, glibc 2.36-9+deb12u14, Python 3.11.2, Docker engine 24.0.6.
Normal flags: `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`,
`CPPFLAGS=-D_POSIX_C_SOURCE=200809L -Iinclude`, empty LDFLAGS/LDLIBS.
The artifact README gives exact sanitizer flags and environment handling.

| Validation | Outcome |
| --- | --- |
| Requested native `make -j4 test-execution-evidence test-execute test-pipeline test-context test-control test-runtime test-runtime-pty test-harness` | PASS on the implementation with the initial 307-case execution generator; later added boundary cases are covered by the final runs below. Runtime 3,104 and all 69 harness tests passed. This preliminary run is not substituted for the final source manifests. |
| Initial native full normal and PTY | PASS: 3,116 runtime cases, all module/API/fault targets; 15 jobs PTY, one job fault PTY, 30 runtime PTY. |
| Initial native `make test-harness` | FAIL: 2/69 self-tests. `test_candidate_owns_a_controlling_terminal_with_fixed_attributes` exceeded the 1s ps cleanup deadline; `test_snapshot_failure_reports_teardown_error_and_reaps_leader` did not observe its setup marker. Unchanged isolated retry PASS: 69/69 in 25.153s. |
| Initial Docker full normal, execution evidence, PTY, harness | PASS: 3,116 runtime, 319 execution and 51 new contracts; all module targets, 15+1+30 PTY, and 69 harness tests. |
| Initial native ASan/UBSan focused targets | PASS, including 319 execution, 51 contracts, 210 control, 30 runtime PTY and execution/pipeline/context API and fault checks. No sanitizer findings. |
| Initial Docker ASan/UBSan `-j2` | FAIL: new descriptor launcher exceeded its unchanged 5s deadline; existing `options: terminal ignoreeof` and `options: terminal ignoreeof disable` timed out, statuses -9 instead of 7/0. Other 28 runtime PTY cases passed. Make stopped scheduling remaining targets. No sanitizer diagnostic was emitted. |
| Final native full normal and focused sanitizers | PASS: 3,116 runtime, 319 execution, 51 contracts, all module/API/fault targets; focused ASan/UBSan also passes 210 control and 30 runtime PTY, without sanitizer findings. |
| Final Docker normal | PASS: 3,116 runtime, 319 execution, 51 contracts, all module/API/fault targets; 15+1+30 PTY and 69 harness tests (10.154s). |
| Final Docker serial focused sanitizers | PASS: 319 execution, 51 contracts, 61 execution API behavior, 52 pipeline, 60 context, 210 control, 30 runtime PTY, and API/allocation cleanup checks. No sanitizer findings. Both initially timed-out ignoreeof cases passed with unchanged deadlines. |

The failed initial sanitizer descriptor run stopped before later descriptor/read
checks; it does not count those as passed. Contention is a possible cause of the
timeouts, not a proven diagnosis. Retried runs preserve deadlines and assertions.

No new execution-case skips are allowed. Existing default-suite capabilities
remain scoped: native untranslated libc diagnostic (CSH-042), and two unequal
uid/gid Linux-root probes (CSH-046). Twelve host-utility gaps per normal environment
remain explicitly labelled gaps under CSH-052/056, not passes. Native Linux outside Docker is not available locally; the hosted Ubuntu run
below supplies separate native-Linux evidence. CSH-049 retains the cross-platform
integration record. CSH-055 does not infer native-Linux success from Docker,
or full-family compliance from these cases.

### Hosted native Linux

[Native Ubuntu job 108450525750](https://github.com/melliott18/cshell/actions/runs/36258797305/job/108450525750)
passed on implementation commit `814cd0a` (final source manifest above), with
Ubuntu 24.04/GCC, runner image `20260920.314.1`, Python 3.11.16. It passed full normal and full ASan/UBSan runs, each including
3,116 runtime cases and all 51 new contract probes, plus PTY and 69 harness
self-tests. [Raw log and job metadata](../evidence/csh-055/README.md) are retained.
The hosted job does not publish binary hashes; it is supplementary integration
evidence, not a replacement for local binary/source identity manifests.


[Hosted Docker job 108450610484](https://github.com/melliott18/cshell/actions/runs/36258827067/job/108450610484)
also passed full normal, full ASan/UBSan, PTY and all 69 harness tests for the
same head `814cd0a`. Both runtime builds passed 3,116 cases and 51 new contracts.
Its log/metadata are retained separately from the local arm64 Docker runs;
this hosted Linux success does not erase the local timeout observations.

Review: [PR #104](https://github.com/melliott18/cshell/pull/104).
