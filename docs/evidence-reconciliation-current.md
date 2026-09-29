# CSH-012 evidence reconciliation at `07ee1cb`

The [final audit closure](conformance-closure.md) supersedes earlier acceptance-gate
decisions. Recorded failures and source-qualified evidence below remain unchanged.

This is a historical snapshot. See the [current acceptance review](conformance-acceptance-review.md)
for the subsequent requirement, defect, platform and documentation decisions.

Reviewed integrated main `07ee1cb26ffcec0470977d03789ce0ebb156603a` on
2026-09-29 UTC (2026-09-28 local). **CSH-012 remains in progress; its completion
gate is not satisfied.** This review reconciles ticket lifecycle, requirement
ownership, retained artifacts and a fresh native sample. It makes no new
normative interpretation or complete-family conformance claim.

The [earlier `8ffb99e` review](evidence-reconciliation.md) remains a historical
snapshot. Its 319-case execution sample, then-open CSH-049/057 work, CSH-061
handoff and pending CI are not today's lifecycle or validation inventory.

## Current dispositions

| Scope | Reconciled disposition |
| --- | --- |
| CSH-036/037 children; CSH-008/009/010/011 prerequisites | All done. The dependency gate is satisfied independently of milestone acceptance. |
| CSH-046/047/048 | Done for their mapped invocation/syntax, expansion and state/builtin scopes. Clause-map capability and complete-family limits remain. CSH-046's GitHub issue #78 was stale at `review`/open despite integrated Markdown `done` (`dd5abda`); its body and state are synchronized to the existing integrated disposition. |
| [CSH-049](tickets/CSH-049-execution-evidence.md) | Done. The [residual review](execution-residuals.md) and [retained platform results](evidence/csh-049-residuals/README.md) replace the old unnamed wider-combinations hold with 883 runtime cases, 204 controlled redirection probes and 51 existing execution contracts. The former unchecked platform criterion is satisfied for this ticket's scope. |
| [CSH-050](tickets/CSH-050-jobs-signals-evidence.md) | Still `review`, with its platform criterion unchecked. PRs #120/#121/#124 and the subsequent retention disposition are integrated. The older [acceptance review](evidence/csh-050-review/README.md) predates the disposition: its request for one is superseded, but it is not itself a new acceptance of CSH-050. |
| [CSH-057](tickets/CSH-057-job-lifecycle-boundaries.md) | Done under the [formal disposition](evidence/csh-057-retention-disposition/README.md). The historical retention timeout remains a failed, unknown-cause observation. #99 owns recurrence; the 619-child test and its deadlines remain enforced. No passing retry or documentation change diagnoses that failure. |
| CSH-051/052 and CSH-056/059/060/061/062/063 | Done as scoped option/host qualification work. CSH-063 is integrated (`ff10a0b`, completion `07ee1cb`). Qualified PATHs, selected vendors and supplied fixtures are the scope of those passes. |
| [CSH-064](tickets/CSH-064-host-platform-external-prerequisites.md) | Open, currently `backlog`; CSH-063 dependency is done. Owns qualification of the current host residual inventory. A concrete new external capability is required before repeating qualification; vendor implementation ownership remains separate. |

The repository ticket files own lifecycle status. The retained
[before](evidence/csh-012/integrated-07ee1cb/issues-before.json) and
[after](evidence/csh-012/integrated-07ee1cb/issues-after.json) issue snapshots
record synchronization. No other completed ticket is reopened merely because
the milestone still needs broader evidence.

## Requirement and artifact accounting

The [reproducible audit](evidence/csh-012/integrated-07ee1cb/audit.py) accounts
for **131 unique families, 115 applicable families and 416 matching
forward/reverse ownership pairs**. The 16 existing UP/XSI profile exclusions
are unchanged; a missing capability is never an exclusion. The original primary
allocations remain 21/13/24/25/11/13/8 for CSH-046 through CSH-052. U-026's
external-host portion overlaps CSH-050/052 and is not an extra primary family.
The [JSON inventory](evidence/csh-012/integrated-07ee1cb/reconciliation.json)
retains every row's current evidence text and owners, including completed ones.
This is consistency evidence, not proof that each family has a complete oracle.

Across 21 retained manifests/inventories, **638 of 640 entries match exactly**.
Two README entries have explained documentation drift:

| Retained manifest | Exact historical blob and later change |
| --- | --- |
| CSH-056 `README.md` | The manifest matches `0b4dc08`; `30c2866` corrected the host-boundary follow-up number/link from CSH-057 to CSH-059. Byte length is unchanged. |
| CSH-057-pty-fix `README.md` | The manifest matches `7879834`; `fe989b1` withdrew an unsupported load-only classification of a historical PTY failure, adding 190 bytes. The failed run remains failed. |

[Document-drift evidence](evidence/csh-012/integrated-07ee1cb/document-drift.json)
retains old/current hashes, byte counts, matching Git revisions and exact diffs.
The checker verifies both versions explicitly and rejects unexplained changes.
Original manifests, raw logs, identities and results are untouched. The two
current READMEs are not falsely reported as matching their older manifests.
These 640 entries cover the selected `artifacts.json` and two retention
`inventory.json` files; they are not an assertion that every historical file in
the repository has a manifest.

## Host residuals and failures

[CSH-063's audit](evidence/csh-063/audit.py) passes against current source,
including its source digest, exact result accounting and all 28 stable residual
conditions. Every residual has a source, actual environment, executable identity,
reason, qualification owner CSH-064 and separate implementation owner.
Conditional missing-root/locale/block conditions remain distinct: the fresh
unprivileged native/no-block sample retains 30 limitation rows.

The [retained CSH-063 records](evidence/csh-063/README.md) still report:

- Each Debian 13/sid strict unequal-ID run: 2,077 passes and **204 predicate
  failures** (132 rejected grants, 72 false grants); actual-operation controls
  pass. These are utility/libc failures, not expected-success qualifications.
- Supplied tmpfs: **1,098 setup failures**, separate from utility assertions.
- Supplied `fakeowner` bind: **1,110 setup failures and nine assertion failures**
  involving socket predicates and cross-user chmod. No full bind profile is qualified.
- Missing privileged Darwin, physical terminals, additional locales/catalogs,
  printf/echo boundaries and per-utility filesystem/resource/interruption scope
  remain individually retained capabilities or limitations.

No local rerun of those Linux/vendor failures is claimed here. Hash and result
checks preserve their historical outcomes. U-034/U-040, other incomplete host
contracts and the system-wide §1.6 obligation remain open.

## Fresh native reproduction

[Commands, timestamps and unmodified compressed logs](evidence/csh-012/integrated-07ee1cb/README.md)
come from a clean `git archive` of `07ee1cb`, built independently of the shared
checkout. Commands ran serially after `make -j4`; no fixture, oracle, capability
rule or deadline changed. The archive extraction emitted a locale warning and
returned zero. Environment: macOS 14.8.7 (23J520), Darwin 23.6.0 arm64,
Apple Clang 15.0.0, Python 3.12.2, normal Makefile flags, no sanitizer overrides.

| Command | Observed result |
| --- | --- |
| `make -j4` | Exit 0. |
| `make test-execution-evidence` | 883 runtime cases, 204 redirection-edge probes and 51 execution contracts pass. |
| `make test-jobs-signals` | 148 jobs, 207 trap/exit, 2,464 signal-edge and 361 signal-contract cases pass; lifecycle/retention, 14 partial-kill cases, inherited-ignore/wait, API/fault/watchdog, 30 jobs PTY and 32 runtime PTY checks pass. |
| `make test-host-profile` | 1,162 passes, zero failures/gaps; 30 separately retained limitation rows. No privileged identity or block device was supplied. |
| `CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty` | 3,905 runtime cases, 30 jobs PTY and 32 runtime PTY cases, notification and terminal-fault cases pass. |
| `make test-harness` | 83 tests pass. |

All six commands exit zero; no case skips are reported in this sample. The
[identity record](evidence/csh-012/integrated-07ee1cb/native-identity.json) records
source SHA-256 `5e31af8c3ea25888d033fe9c01bcd642fe28821f4d5b304c25e5db54e243b48a`
and binary SHA-256 `6b35714e477b6f2cb43221af3f18d1e15dc2d0321e9e12536f6738cd2d1cec81`,
generated-suite/helper hashes, compiler/system identities and environment.
The host record separately identifies each selected utility. Normal smoke/PTY
fixtures use their controlled environment; API/harness processes inherit the
recorded caller environment. Absolute archive paths affect generated-suite hashes.

This is not a new full `make test`, native Linux, Docker, sanitizer, differential
or fresh normative-source audit. Existing records supply their own bounded
evidence at their named revisions; they are not relabeled as fresh executions.

## Hosted CI and acceptance gates

[Run 36499777317](https://github.com/melliott18/cshell/actions/runs/36499777317)
tests exact `07ee1cb`. At the
[retained snapshot](evidence/csh-012/integrated-07ee1cb/hosted-current.json),
Ubuntu/GCC and Docker succeeded, while macOS/Clang was in progress. It is not
a complete current three-platform pass.
[Run 36495093736](https://github.com/melliott18/cshell/actions/runs/36495093736)
at `66f8900` ultimately **cancelled** its macOS job; the earlier pending snapshot
cannot now be read as a pass. The latest retained complete green run is
[36487917937](https://github.com/melliott18/cshell/actions/runs/36487917937) at
`faf2e95`. Shell runtime and workflow paths agree with that revision, but
[nine host-test/image inputs differ](evidence/csh-012/integrated-07ee1cb/ci-source-comparison.json).
Its full workload is not identical to current main. Hosted metadata has no
binary hashes and `detect_leaks=0` supplies no leak-check claim.

| Original CSH-012 acceptance criterion | Current decision and remaining work |
| --- | --- |
| Every applicable requirement has passing evidence or an explicit open limitation | Unchecked. Family allocation and links reconcile, but completed scoped audits do not establish a combined clause-level accounting of all 115 families. CSH-012 owns that review; CSH-050/064 retain the named open acceptance/qualification work. |
| Conditional, unspecified and implementation-defined behavior labeled | Checked, based on the existing base profile, D-001–D-008 and clause maps; no classification changes here. |
| Documented clean-checkout CI on supported systems | Unchecked. Workflow coverage is present; exact-current-main macOS validation remains incomplete in the snapshot. Native Linux/Docker/normal/sanitizer results must retain their individual provenance and limits. |
| All discovered defects resolved or linked; waivers scoped | Unchecked. This review reconciles CSH-057's formal disposition and CSH-064's strict failures/capabilities, but does not establish a complete cross-feature defect/waiver ledger. CSH-050's independent platform acceptance remains open. |
| Installation, invocation, architecture and contributor docs coherent | Unchecked as a milestone-wide criterion. Current navigation and ownership are corrected here; a final integrated documentation audit remains with CSH-012. The README explicitly retains the absence of an installation target. |
| Compliance statements name scope and are withheld while unmet | Checked. POSIX.1-2024 base shell/`sh`, UP/XSI unselected; no complete conformance claim. |

The next CSH-012 work is the combined requirement/defect/documentation review
and appropriate supported-platform acceptance. CSH-064 requires new supplied
capabilities for its remaining qualification. Closing narrower tickets, waiting
for CI, or rerunning a passing native sample alone does not close this milestone.
