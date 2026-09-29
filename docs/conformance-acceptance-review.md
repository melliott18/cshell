# CSH-012 requirement, defect, platform and documentation review

Review baseline: `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`, integrated `main`,
2026-09-29 UTC. The review is complete; CSH-012 acceptance is **not complete**.
Two shell limitations are reproduced with strict probes, platform qualification
remains conditional, and the complete system utility inventory is still missing.
No POSIX compliance claim is made. Production code and default test oracles are
unchanged by this review.

This supersedes the current-state conclusions of the
[07ee1cb reconciliation](evidence-reconciliation-current.md), preserving its
historical records. CSH-050's partial-kill fixture repair is integrated and its
scoped ticket is done. CSH-064's mapped-platform work is integrated, while that
ticket retains qualification ownership for thirty stable residual conditions.

## Acceptance decisions

| Original criterion | Review disposition | Evidence / remaining action |
| --- | --- | --- |
| Each applicable requirement has implementation/passing evidence or an explicit open ticket/limitation | **Pending** | All 131 families are reconciled below, with 115 applicable and 16 exclusions. CSH-065/066 own reproduced unmet contracts; CSH-067 owns shell qualification gaps. CSH-068 must expand the broad U-034/U-040 system obligation into the complete required utility inventory before this can be described as accounting for every applicable requirement. |
| Conditional/unspecified/implementation-defined classifications and permitted choices | **Retain accepted** | Existing D decisions, clause maps and UP/XSI exclusions remain in force. Finite guards are limitations, not permitted implementation choices; locale capability absence is not automatically a semantic defect. |
| CI runs documented checks from a clean checkout on supported systems | **Accepted for baseline** | Baseline Linux/GCC, macOS 15/Clang and Docker jobs all pass normal, PTY, harness, host-profile and ASan/UBSan stages. Local macOS 14.8.7 full normal validation also passes. Host residual profiles remain separate. |
| Discovered defects have regression coverage and resolved or linked tickets; waivers have reason/scope | **Pending** | New strict review probes retain ten failures and fifteen controls, but repairs and default-suite integration are still CSH-065/066. H01–H10 require the finite CSH-069 disposition review. The existing CSH-057 retention disposition remains narrowly scoped. |
| Installation, invocation, architecture and contribution docs are coherent/current | **Accepted for this review** | Corrections and checked entry points are recorded below; no installation target or system-wide qualification is implied. |
| Compliance statements identify edition/scope/evidence and remain withheld | **Retain accepted** | POSIX.1-2024, base Shell Command Language and sh; UP/XSI excluded as documented. No family is promoted merely because a scoped ticket is done. |

Both original children and all four milestone prerequisites are done. The
combined gate stays unchecked. These decisions evaluate the original criteria;
they do not narrow them to obtain a completion result.

## Requirement review

The [family ledger](requirement-review-ledger.md) lists every matrix ID, original
normative/matrix reference, primary condition map and current open residual
owner. The [machine inventory](evidence/csh-012/acceptance-c8c1c91/ownership-audit.json)
checks 443 forward/reverse ownership pairs. The seven maps provide implementation
paths, exact fixture names and assertion scope, rather than a ticket-status
proxy for evidence:

| Map | Primary applicable families | Review result |
| --- | ---: | --- |
| [Invocation, lexical, grammar, aliases](invocation-syntax-evidence.md) | 21 | Source modes, argument mapping, nonblocking stdin and grammar witnesses retained. Main-parser recovery fails independently of eval recovery. Fixed nesting fails. CSH-055 public read-error evidence and fresh no-final-newline heredoc passes correct stale API-only claims. |
| [Expansion](expansion-evidence.md) | 13 | Context/order, parameter grid, arithmetic, splitting and pattern assertions retained. Signed-long representation and unspecified substitution policies remain distinct from fixed depth limits. Stateful encodings, multicharacter collating/equivalence behavior and public pathname error boundaries remain qualified only where witnessed. |
| [State and builtins](state-builtin-evidence.md) | 24 | Startup variables, attributes, nested evaluation, special-builtin errors, read/getopts and state lifetimes remain mapped. Mixed ENV-005 retains base PS2/read/heredoc and trace obligations despite UP exclusions. Host diagnostics/locale coverage is not silently inferred from C-locale tests. |
| [Execution and redirections](execution-evidence.md) | 25 | 883 runtime, 204 redirection-fault and 51 CSH-055 contract witnesses are bounded evidence. Source-read and prefix-PATH fixes retained. Parser errors, function/evaluation depth and pathname/locale conditions inherit the explicit owners below. |
| [Jobs/signals/traps](jobs-signals-evidence.md) | 11 | CSH-050/054/057/058 repairs and exact fixtures retained. Parent-directed stop fixture repair is separate from the unresolved historical retention observation. No permitted-scheduling variation is converted into a mandatory reference-shell oracle. |
| [Base shell options](shell-option-evidence.md) | 13 | Entry/enable/disable, execution context, inheritance and lifetime grids retained. Optional editing/history defaults remain excluded. Corrected Issue 8 execution-environment reference to §2.13. |
| [Host utilities and intrinsic lookup](host-utility-evidence.md) | 8 | Also shares U-026 external kill evidence. Qualified PATH resolves five selected stock gaps only. CSH-064 owns selected host residuals; CSH-068 owns the missing complete system inventory. |

This is an independent review of the existing clause/condition maps, their
implementation and retained evidence, with targeted normative rechecks and new
public-runtime probes. It is **not** a completed sentence-by-sentence audit of
the entire POSIX utility collection. Twenty-five official Issue 8 source pages
were retrieved with certificate verification; URLs, hashes and retrieval results
are in [sources.json](evidence/csh-012/acceptance-c8c1c91/sources.json).
The index identifies 16 wholly excluded families; conditional base portions of
mixed rows such as ENV-005 are not excluded.

### Findings requiring action

| Finding | Evidence and consequence | Owner |
| --- | --- | --- |
| F01 — Interactive main-parser syntax error exits | `src/main.c` breaks on parser error. A standalone `)` followed by a valid command exits 2 in forced-interactive string/file/stdin and closes a real PTY before the next prompt. XCU §2.8.1 requires interactive continuation. Four failures; three noninteractive and three eval-recovery controls pass. | [CSH-065](tickets/CSH-065-interactive-parser-recovery.md) |
| F02 — Arbitrary nesting guards reject valid commands | Brace depth 127 succeeds in all three modes; 128 fails executor validation and 129 fails parser validation (six failures). Source inspection also finds fixed evaluation/function/substitution, expansion and arithmetic guards. This conflicts with the command-size obligation; guard-rejection fixtures prove safety, not compliance. | [CSH-066](tickets/CSH-066-resource-bounded-nesting.md) |
| F03 — Shell locale/pathname qualification incomplete | State-dependent/non-UTF decoding, multicharacter collating/equivalence elements, diagnostic locale applicability, raw filenames and selected public permission/I/O/symlink boundaries lack complete qualification. These are evidence limits unless a wrong result is demonstrated. | [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md) |
| F04 — Selected host witnesses are not a system utility inventory | U-034/U-040 currently aggregate required host behavior; a finite harness utility list cannot establish the full XCU §1.6 obligation. Preserve the exact qualified PATH and /bin/sh fallback dependency. | [CSH-068](tickets/CSH-068-host-system-contract-inventory.md) |
| F05 — Historical failures lack supported final dispositions | Later unchanged passes do not diagnose earlier timeouts/output mismatches. H01–H10 below need finite, evidence-backed accounting. | [CSH-069](tickets/CSH-069-historical-failure-dispositions.md) |
| F06 — Supplied host profiles still fail strict contracts | Unequal-ID ACL predicates, mapped private-device setup, tmpfs ACL setup, fakeowner socket metadata and chmod semantics retain measured failures. Thirty stable conditions plus per-run conditional limits remain. | [CSH-064](tickets/CSH-064-host-platform-external-prerequisites.md) |

The [probe](evidence/csh-012/acceptance-c8c1c91/probe-contracts.py) uses the
unchanged bounded runner against a clean built archive. All inputs, expected and
actual streams/statuses, PTY steps and cleanup results are retained in
[contracts.json](evidence/csh-012/acceptance-c8c1c91/contracts.json).
It exits nonzero deliberately because the required behavior fails; it does not
make those failures expected-success regressions. Three no-final-newline
heredoc cases and three noninteractive eval-error controls also pass, giving
25 total cases: 15 PASS and 10 FAIL. The PTY early-close report is the observed
failure of recovery, not an unexplained teardown failure.

## Defect review

The following records separate production defects, fixture/harness defects,
host contracts and unresolved observations. Linked tickets contain the exact
before/after fixtures and validation revisions. “Resolved” means that scoped
repair has causal evidence and integrated regression coverage; it does not
promote all requirements exercised by the same suite.

| Record | Classification and disposition | Regression / evidence |
| --- | --- | --- |
| CSH-040 Darwin EPERM during owned-zombie cleanup | Harness repair integrated; only verified no-live-member zombie groups may be accepted. | [CSH-040](tickets/CSH-040-macos-harness-cleanup.md), deterministic owned-zombie cleanup checks. |
| CSH-042 locale length/IFS/read/collation and restoration | Runtime repairs integrated; encoding breadth remains F03. | [CSH-042](tickets/CSH-042-locale-semantics.md), portability fixtures. |
| CSH-043 redirection offset / resource boundary | Native syscall comparison and explicit off_t/filesystem policies; host append difference is not a shell defect. | [CSH-043](tickets/CSH-043-redirection-offset.md), 36 focused cases. |
| CSH-044 interrupted prompt write | Runtime repair integrated with injected EINTR and repeated-resume regression. | [CSH-044](tickets/CSH-044-intermittent-bg-prompt.md). |
| CSH-045 aggregate jobs watchdog | Fixture repaired to enforce individual progress-phase bounds. Does not diagnose later retention timeouts. | [CSH-045](tickets/CSH-045-jobs-fixture-timeout.md). |
| CSH-046 nonblocking stdin in -c/file | Runtime repair integrated, including unchanged descriptor flags except O_NONBLOCK. Allocator environment forwarding was a separate runner correction. | [CSH-046](tickets/CSH-046-invocation-syntax-evidence.md), nine positive/four exclusion cases. |
| CSH-048 startup variables, output failures, read semantics, long logical cd, pwd/hash allocation ownership | Runtime repairs integrated; finite fault and public-runtime partitions remain distinct. | [CSH-048](tickets/CSH-048-state-builtin-evidence.md) and [clause map](state-builtin-evidence.md). |
| CSH-049 noclobber empty-target setup | Fixture correction retained; assertions unchanged. | [CSH-049](tickets/CSH-049-execution-evidence.md), `990e706`. |
| CSH-050/054 TERM, kill names and EXIT-trap status | Runtime repairs integrated with targeted signal/status regressions. | [CSH-054](tickets/CSH-054-signal-contract-gaps.md), `943e987`. |
| CSH-054 ps enumeration and readiness races | Harness/fixture corrections supported by controlled delayed enumeration and readiness checks. Not a blanket explanation for every H entry. | [CSH-054](tickets/CSH-054-signal-contract-gaps.md); case bounds retained, enumeration and reap budgets distinguished. |
| CSH-055 prefix PATH and main/dot source-read consequences | Runtime repairs integrated; read failures include pending-trap behavior. | [CSH-055](tickets/CSH-055-execution-contract-gaps.md), 32 descriptor, 7 main-read and 12 dot-read contracts. |
| CSH-051 generated suite byte limit | Harness input-size correction integrated with exact-limit and limit-plus-one checks; child limits unchanged. | [CSH-051](tickets/CSH-051-shell-option-evidence.md). |
| CSH-052/056 five stock-host gaps | Selected profile supplies ed, compatible kill mapping, printf numbered/b-precision behavior and test timestamp semantics. Stock hosts remain unqualified. | [Qualified profile](host-contract-profile.md), unchanged stock-gap records. |
| CSH-053 syntax-valued multibyte constituent bytes | Runtime decoder repair integrated; lexical startup locale distinguished from expansion locale. | [CSH-053](tickets/CSH-053-multibyte-lexical-boundaries.md), raw-byte and feed-boundary fixtures. |
| CSH-057 lifecycle runtime/fixture defects | Integrated repairs for stop/notification/retention state, fixture borrowed-state lifetime, launch synchronization and terminal barriers. Evidence distinguishes each mechanism. | [CSH-057](tickets/CSH-057-job-lifecycle-boundaries.md), continuation and PTY-fix records. |
| CSH-057 historical retention timeout | Unknown cause; formally accepted only for scoped completion, with same-ticket recurrence ownership. Not fixed or proven load. | [Formal disposition](evidence/csh-057-retention-disposition/README.md), unchanged 619-child/5-second-phase/60-second-outer test. |
| CSH-058 signal inheritance, CHLD auto-reap, monitored INT and TTOU reclaim | Four runtime repairs integrated with native/Docker causal before/after probes. Launcher alarm leaking through exec was a distinct fixture defect, subsequently canceled before exec. | [CSH-058](evidence/csh-058/README.md), exact four defects and initial/final fixture identities. |
| CSH-050 partial-kill stopped-state bookkeeping | Runtime repair integrated; invalid/EPERM operands no longer conceal successful sibling CONT. | [CSH-050](tickets/CSH-050-jobs-signals-evidence.md), `6498859`, eight before failures plus six controls. |
| CSH-050 self-stop fixture race | Darwin failure reproduced without cshell; parent-directed STOP repair integrated in `d1ca90b`/`cf73bba`. Distinct from historical CSH-057 retention. | [CSH-050](tickets/CSH-050-jobs-signals-evidence.md), retained minimal diagnostics, 3,000 repetitions and 14-case rotations at unchanged bounds. |
| Current F01/F02/F06 | Open shell and host defects; neither review-only probes nor successful default tests repair them. | CSH-065/066/064, above. |

### Historical observations

All entries below are **unknown cause unless a narrower cited diagnosis applies**.
“Concurrent” describes a run, not its root cause. CSH-069 owns disposition of this
finite list, including checking duplicates against known repairs. Original
records are retained at their linked locations; when only a narrative record
exists, this review does not invent missing raw logs or exact identities.

| ID | Original observation | Retained source and current decision |
| --- | --- | --- |
| H01 | CSH-042 Docker portability/context timeouts | [CSH-042 validation](tickets/CSH-042-locale-semantics.md). Later passes remain separate; concurrency is not a diagnosis. |
| H02 | CSH-043 local sanitizer ps cleanup and offset timeouts, including 17 passes/19 timeouts; chained stages not run | [CSH-043](tickets/CSH-043-redirection-offset.md). Compare the ps mechanism with CSH-054 before assigning a causal repair; offset timeouts remain unexplained. |
| H03 | CSH-046 empty-input and CSH-047 arithmetic-depth/adjacent-punctuation timeouts | [CSH-046](tickets/CSH-046-invocation-syntax-evidence.md), [CSH-047](tickets/CSH-047-expansion-evidence.md). Same-source retries do not resolve the observations. |
| H04 | CSH-048 times/ulimit timeouts despite expected bytes, plus early cleanup observations | [CSH-048](tickets/CSH-048-state-builtin-evidence.md). Separate semantic output from process completion; compare cleanup evidence with known harness repairs. |
| H05 | CSH-049 one-second cleanup failure and three Docker offset timeouts, unrun remaining targets | [CSH-049](tickets/CSH-049-execution-evidence.md). Later isolated passes do not establish cause. |
| H06 | CSH-051 initial leak-scanning two timeouts and process-setup self-test deadline | [CSH-051](tickets/CSH-051-shell-option-evidence.md). Leak-disabled pass is not LeakSanitizer qualification; compare setup mechanism with CSH-054. |
| H07 | CSH-053 local invocation/offset timeouts and hosted repeated-resume output mismatch (7,328 vs 7,216 bytes) | [CSH-053](tickets/CSH-053-multibyte-lexical-boundaries.md). Twenty-one later local successes do not diagnose the hosted mismatch. |
| H08 | CSH-055 initial native harness cleanup/setup failures and Docker descriptor/ignoreeof deadlines | [CSH-055](tickets/CSH-055-execution-contract-gaps.md). Preserve stopped/not-run stages and compare specific setup failures with causal harness evidence. |
| H09 | CSH-057 Linux sanitizer control-flow batch timeouts | [CSH-057](tickets/CSH-057-job-lifecycle-boundaries.md). Not covered by the formal retention disposition. |
| H10 | CSH-058 initial native PTY/ps bounds, Docker EOF-helper setup and native sanitizer case-fallthrough timeout | [CSH-058 initial failures](evidence/csh-058/README.md#earlier-failures-retained). Separate these from the diagnosed launcher-alarm-through-exec fixture defect. |

## Platform review

The [evidence directory](evidence/csh-012/acceptance-c8c1c91/README.md) retains
commands, UTC intervals, source/binary/helper identities, complete compressed
logs and CI metadata. The clean native archive is built from the exact baseline;
the source manifest excludes only evidence documentation and generated caches.

| Environment | Evidence / result | Qualification boundary |
| --- | --- | --- |
| macOS 14.8.7 arm64, Apple Clang 15, Python 3.12.2 | Clean `make -j4`; `make test test-pty test-host-profile test-harness`: PASS. Runtime 3,905; jobs PTY 30; runtime PTY 32; harness 86; profile 1,162 with zero assertion failures/gaps. | Stock host still reports 12 gap instances; native unequal-ID invocation skips 2; raw-filename capability skips 4 and missing translated libc catalog 1. Profile emits 32 limitation records (30 stable plus 2 conditional). No fresh local sanitizer run claimed. |
| Hosted Ubuntu 24.04/GCC, exact c8c1c91 | [Baseline CI](https://github.com/melliott18/cshell/actions/runs/36507732235): completed success; normal, PTY, profile, harness and full ASan/UBSan. | Runner/image metadata and installed package details are retained in logs. The workflow does not collect a dedicated compiler/libc identity manifest or hosted binary hashes. |
| Docker Linux on hosted Ubuntu, exact c8c1c91 | Same run: completed success, including controlled identities/private devices, unequal invocation IDs, helpers and full ASan/UBSan. | Debian image/base digest and installed toolchain package details are in build logs; container checks do not validate Darwin. Strict unequal-ID ACL residual profiles from CSH-064 are not this ordinary passing controlled profile. |
| Hosted macOS 15/Clang, exact c8c1c91 | Completed success: normal, PTY, profile, harness and ASan/UBSan stages. | All required workflow steps completed; runner/image metadata is retained. This does not qualify unavailable locales, special filesystems or credentials. |
| CSH-064 special host profiles | Native 1,162 and ordinary sid 2,281 pass; mapped 2,269 pass/12 setup failures; unequal-ID 204 assertion failures; tmpfs 1,098 setup failures; fakeowner 1,110 setup/9 assertion failures. | Source-qualified historical records, not new reruns. Mapped credentials measured; fakeowner socket metadata/chmod defects independently diagnosed. No complete special-profile qualification. |

CI ASan/UBSan uses `detect_leaks=0`; neither that pass nor this review establishes
Linux LeakSanitizer coverage. Workflow job budgets and per-case deadlines are
separate. Existing reference-shell comparisons in CSH-037 retain their recorded
versions and selected scope; no new reference-shell run is claimed here.

## Documentation review

Reviewed README/CONTRIBUTING, the documentation and ticket indexes, architecture,
runtime invocation, POSIX profile/matrices/owners, testing commands, workflow,
implementation plan and seven condition maps against the baseline implementation.

- Build remains repository-local `make` producing `cshell`; there is no install
  target. Native/Docker entry points correspond to actual Make targets and CI
  uses clean checkouts with the documented dependencies and sanitizer flags.
- Architecture now identifies implemented trap integration, state initialization,
  functions and builtin dispatch; the ownership table describes existing APIs.
  Historical bootstrap/cutover evidence is labeled as such.
- Runtime docs now describe literal PS2 continuation prompts (default `> `),
  distinguish unselected UP prompt/startup processing from the base parser
  recovery defect, and retain noninteractive prompt behavior.
- POSIX documentation now reflects integrated `$!`, `pipefail`, dot and trap
  behavior, without turning those features into a conformance claim.
- Current owner links identify CSH-064 and thirty host conditions, CSH-065–068
  for newly allocated requirements, and CSH-069 for historical dispositions.
  Earlier reconciliation snapshots are explicitly historical; immutable raw
  evidence/manifests are not rewritten.
- Invocation evidence now points to CSH-055 public read-failure cases and the
  fresh heredoc source-end probes. The option map references Issue 8 §2.13 for
  execution environments. Roadmap's first parallel-work section is historical.

Validation includes link/file/anchor checks, unchanged diagram checks, requirement
ownership reconciliation and retained artifact hashing. The review does not
change diagrams, runtime code, fixture deadlines or the selected standard profile.
