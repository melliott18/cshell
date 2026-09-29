# CSH-049/050 review and CSH-012 evidence reconciliation

Reviewed on 2026-09-28 against integrated main
`8ffb99e73cfd21bb1b5ad66829544350f78b69ae`. This is an evidence and integration
review with an independently built, scoped runtime reproduction. It is not a
fresh sentence-by-sentence POSIX audit or a complete runtime code review.

This is a retained review snapshot. The subsequent
[CSH-057 formal retention disposition](evidence/csh-057-retention-disposition/README.md)
supersedes its open-timeout hold for that scoped ticket: the repaired PTY races
are integrated and the historical retention failure remains unknown-cause with
same-ticket reopening ownership. It does not complete CSH-050 or CSH-012 or
rewrite the older failed runs and accounting below. The
[later CSH-050 review at `07ee1cb`](evidence/csh-050-disposition/README.md)
applies that disposition to its own criteria. Its platform criterion remains
unchecked for a new partial-kill SIGALRM, not the old retention observation;
CSH-050 / #82 owns the new failure. CSH-063 is scoped complete and CSH-064 owns
remaining external platform prerequisites.

## Review dispositions

| Ticket / integrated change | Review result | Remaining acceptance work |
| --- | --- | --- |
| [CSH-049](tickets/CSH-049-execution-evidence.md), [PR #113](https://github.com/melliott18/cshell/pull/113), `04c5230` | Accept the scoped execution evidence: all 25 scope IDs match matrix/reverse ownership; all 15 integration-artifact hashes match. The 319 focused cases and original strict prefix-PATH reproducer pass again. No runtime or fixture change requested by this review. | Keep `review`. The ticket explicitly retains wider filesystem/target-expansion combinations and cross-feature limits. Its unchecked remaining-applicable-cases criterion is not satisfied by this sample. |
| [CSH-050](tickets/CSH-050-jobs-signals-evidence.md), [PR #114](https://github.com/melliott18/cshell/pull/114), `9f05719` | Accept the focused-suite wiring and scoped jobs/signal evidence: all 11 IDs match ownership; all 17 artifact hashes match. All 207 selected trap/exit cases have unique names, unchanged selection, and exact structural equality with their full-runtime counterparts. The combined target reaches jobs, traps/signals, lifecycle/fault and both terminal suites and passes. | Keep `review`. CSH-057's distinct PTY/retention timeouts and the mapped host/capability limitations remain open. The status-1 continuation defect is corrected and must no longer be described as awaiting integration. |

PR #113 changes evidence/documentation only. PR #114's executable test changes
are the `traps.json` selection, its Makefile dependency/runner target, and the
combined `test-jobs-signals` target. The review inspected those changes, the
clause maps and retained identities/results; it did not infer a full-family
pass from a test count. The 3,341-case full runtime suite was generated for
structural comparison, not executed in full during this review.

### Reconciled findings

- CSH-049 still described its integrated record as awaiting integration.
  CSH-050 and its live clause map still described PR #112 as proposed. The
  current descriptions now name their merge revisions; historical artifacts
  keep their original source identities and failures.
- [CSH-057's continuation correction](evidence/csh-057-pty-fix/README.md),
  integrated as `19cd70e`, has deterministic failing-before/passing-after
  evidence for status 1 versus 130. Separate integration observations hit the
  five-second public PTY and 60-second retention deadlines. Those remain owned
  by CSH-057; neither a passing retry nor the continuation fix diagnoses them.
- CSH-012's child checklist omitted completed CSH-037 and its host gate still
  assigned residual work to completed CSH-059. It now records both completed
  children and the current [CSH-061](tickets/CSH-061-host-environment-residuals.md)
  residual inventory, including the six strict unequal-ID ACL grant failures.
- No ownership defect was found: all **416** forward/reverse pairs agree.
  The U-026 reverse link uses the descriptive label “U-026 external host
  portion”; the check uses link destinations rather than assuming bare labels.

## Current evidence accounting

The two matrices retain 131 unique requirement families. The selected base
profile excludes 16 UP/XSI-only rows (U-018/021/022/025/028 and
O-003/008/010/011/015/020–025); the other 115 have applicable portions.
Mixed base/conditional rows and terminal conditions remain applicable as
documented. Capability skips are not profile exclusions.

| Original primary allocation | Families | Current ticket disposition and evidence |
| --- | --- | --- |
| CSH-046 invocation/syntax | 21 | Done; [mapped witnesses and limits](invocation-syntax-evidence.md). |
| CSH-047 expansion | 13 | Done; [mapped witnesses and limits](expansion-evidence.md), including CSH-053 encoding capabilities. |
| CSH-048 state/builtins | 24 | Done; [runtime partitions and limits](state-builtin-evidence.md), including integrated PR #115. |
| CSH-049 execution | 25 | Review; [remaining obligations](execution-evidence.md#remaining-obligations). |
| CSH-050 jobs/signals | 11 | Review; [remaining obligations](jobs-signals-evidence.md#remaining-obligations), including open CSH-057 timeouts. |
| CSH-051 options | 13 | Done; [mapped option assertions](shell-option-evidence.md). |
| CSH-052 host utilities | 8 | Done as a scoped audit; [qualified profile](host-contract-profile.md), CSH-056/059/060 results and open CSH-061 residuals. Its additional U-026 host ownership overlaps CSH-050 and is not a 116th primary family. |

“Done” records the scoped ticket outcome, not complete-family verification.
The [CSH-037 review](audit-review.md) remains a historical snapshot; its table
of then-open tickets must not serve as today's lifecycle inventory. No matrix
family or profile exclusion changes in this reconciliation.

## Independent native reproduction

A clean `git archive` of the reviewed revision was built in a separate temporary
directory. No shared build objects or existing executable were reused. Commands
ran serially after the parallel build, with unchanged fixtures, expected bytes,
capability rules and deadlines. Archive extraction emitted a locale warning
but returned zero. [Run timestamps/statuses](evidence/csh-012/runs.json),
[source/binary/helper identities](evidence/csh-012/native-identity.json), and
[compressed raw logs](evidence/csh-012/README.md) are retained.

Environment: macOS 14.8.7 (23J520), Darwin 23.6.0 arm64, Apple Clang 15.0.0,
Python 3.12.2, default C99 warning/optimization flags. No sanitizer flags were
supplied. The source manifest (Makefile, Dockerfile, src/include/tests) hashes
to `ed2ed97620164fe0d95f5d4f0f7e03aec953c777775526d334e8b711ed02caf2`.
The binary hashes to
`f72d4cfa4cf624b9e7a1c09f271e76989a828d23bc89a24b3ed8bddda3421bc9`.

| Command | Observed result |
| --- | --- |
| `make -j4` | Exit 0. |
| `make test-execution-evidence` | 319 passed, zero failures/skips. |
| `python3 tests/smoke.py ./cshell --suite tests/fixtures/execution-known-gaps.json` | The strict prefix-PATH case passes: `custom-pwd\n`, empty stderr, status 0. |
| `make test-jobs-signals` | Exit 0: 148 jobs, 207 trap/exit, 2,464 signal-edge, 361 signal-contract cases; inherited-ignore/interposed-wait, lifecycle/API/fault/watchdog checks; 30 jobs PTY and 32 runtime PTY cases. No skips or failed assertions. |
| `make test-harness` | 74 tests pass. |

The [fixture conditions](jobs-signals-evidence.md#run-record) remain
authoritative: smoke/PTY cases use a controlled C-locale environment, fresh
HOME/TMPDIR, umask 077, exact streams/status and bounded cleanup. API runners
inherit the recorded caller environment. The extra two runtime PTY cases versus
CSH-050's earlier 30-case record come from integrated CSH-048; historical counts
are not rewritten.

No fresh local Docker, native Linux, sanitizer, full runtime or differential
suite is claimed. Those environments retain their separately identified
CSH-049/050/057 and host-profile records. Current-main CI is recorded separately
below; source changes since older runs prevent treating their hashes as current.

## CI and normative-source limits

[Main run 36468260838](https://github.com/melliott18/cshell/actions/runs/36468260838)
tests the exact reviewed main revision. At the retained
[metadata snapshot](evidence/csh-012/hosted-main.json), native Ubuntu/GCC and
Docker jobs passed; macOS/Clang remained in progress. This is **not a complete
three-platform pass**. The workflow includes normal, terminal, host-profile,
harness and ASan/UBSan stages and controlled Docker host/identity checks.
Hosted jobs do not publish binary hashes, and `detect_leaks=0` is not leak-check
evidence. This snapshot does not erase the failed runs retained by CSH-057.

The earlier [run 36449808979](https://github.com/melliott18/cshell/actions/runs/36449808979)
passed all three jobs at `b1b6b15`, as retained by CSH-049. It predates the
combined CSH-048/050/057/060 integration and cannot substitute for its result.

Direct retrieval of the official Issue 8 Chapter 2 and wait pages returned
HTTP 403 during this review. Existing source/choice classifications were
checked against the repository's clause maps; no new normative interpretation,
complete fresh source audit, or reference-shell oracle is claimed.

## CSH-012 disposition

Both children (CSH-036/037) and all four completion prerequisites
(CSH-008/009/010/011) are done. CSH-012 moves from stale `backlog` to
`in-progress` for this reconciliation. Its classification and claim-policy
criteria have documented support; the combined completion gate remains unsatisfied.

Closing CSH-012 still requires the original requirement-level review across
the 115 applicable families, current cross-feature/platform evidence, and an
explicit disposition for all residual conditions. In particular, retain
CSH-049/050's unchecked criteria, CSH-057's timeouts, and CSH-061's host/ACL
conditions. Completed narrower tickets and qualified PATH results do not
qualify stock hosts, waive missing locales/credentials/physical terminals, or
resolve the system-wide utility obligation. No POSIX compliance claim is made.
