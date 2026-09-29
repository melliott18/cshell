# CSH-012 defect accounting and scoped dispositions

This completes the remaining **audit accounting** criterion. It does not claim
that unresolved defects are repaired. The user authorized completion of the
inventory, defect dispositions and audit integration/closure. The original
acceptance criterion permits defects in linked open tickets; neither it nor
this disposition requires all follow-up implementation work to be completed.

## Confirmed defects and regression coverage

| Scope | Required oracle and existing coverage | Status / owner |
| --- | --- | --- |
| Interactive main-parser syntax recovery | [Strict 25-case review probe](evidence/csh-012/acceptance-c8c1c91/probe-contracts.py) asserts following-command output/status and PTY prompt; four recovery failures are retained in [results](evidence/csh-012/acceptance-c8c1c91/contracts.json). | Unfixed, [CSH-065](tickets/CSH-065-interactive-parser-recovery.md); integrate repaired cases into normal CI there. |
| Arbitrary nesting limits | Same probe requires valid depths 127/128/129 to execute in all source modes; six failures retained. Existing guard tests separately check bounded rejection. Source-inspected function/expansion guards are explicit limitations. | Unfixed, [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| Host ACL/namespace/fakeowner defects | Strict CSH-064 credential, ACL, socket metadata and chmod fixtures retain failed actual predicates and setup separately. No expected-success allowance added. | Unqualified profiles, [CSH-064](tickets/CSH-064-host-platform-external-prerequisites.md). |
| Missing/unqualified utility contracts | The [complete inventory](host-system-inventory.md) identifies each required utility, actual provider gap and normative page; absence checks are reproducible using provider-inventory.py. Availability is not behavior coverage. | [CSH-068](tickets/CSH-068-host-system-contract-inventory.md) owns the named unqualified contracts; no system conformance claim. |
| Diagnosed and integrated runtime/harness/fixture defects | The [original defect review](conformance-acceptance-review.md#defect-review) links each causal repair and enforced regression. | Scoped resolved records remain unchanged. |
| Historical CSH-057 retention | Existing strict 619-child test and [formal disposition](evidence/csh-057-retention-disposition/README.md). | Unknown cause, same-ticket recurrence ownership; distinct from CSH-050 fixture repair and H09. |

Failing review reproducers are retained outside the green default suite and
remain runnable with required-success oracles. This satisfies evidence and
linked-ticket accounting without relabeling failure as success. Default-suite
integration belongs to the repair ticket; no original CSH-012 criterion required
every known defect to be fixed before its audit could close.

## Historical and new observations

Each H entry is accepted **only as an unresolved observation for this audit's
completion**. This waives an additional causal-repair demonstration for that
past attempt; it does not waive, skip, relax or normalize any current/future
test, approve a known failing product behavior, or establish reliable operation
under arbitrary load. [CSH-069 / #138](tickets/CSH-069-historical-failure-dispositions.md)
retains diagnosis and recurrence ownership for all eleven entries.

The reason for this scoped acceptance is that the observed failures, test
oracles, available identities and missing details are explicit and independently
owned; the audit can truthfully describe them without establishing a cause.
The independently passing baseline run demonstrates only its own bounded
results. It never changes a historical failed, cancelled or not-run outcome.

| ID / observation | Identity and retained evidence | Regression / bounds | Specific disposition boundary |
| --- | --- | --- | --- |
| <a id="h01"></a>H01 — Nine portability deadlines and one context deadline (CSH-042) | 7bf7025 is the final repair revision; the earlier failed attempt is not independently identified in the narrative. [CSH-042-locale-semantics.md](tickets/CSH-042-locale-semantics.md) | [tests/portability.py](../tests/portability.py); [tests/contexts.py](../tests/contexts.py). 5s portability, 10s context. | Narrative retains the failed attempt and later independent hosted passes. Exact initial source identity and raw failed log are unavailable in the ticket; do not reconstruct them from a later passing identity. Accepted unresolved for audit only; CSH-069. |
| <a id="h02"></a>H02 — CSH-043 native ps cleanup and Docker offset timeouts | Final focused evidence is c37890d; exact failed-attempt identity is not separately retained in the narrative. [CSH-043-redirection-offset.md](tickets/CSH-043-redirection-offset.md) | [tests/redirection_offsets.py](../tests/redirection_offsets.py); [tests/pty_harness.py](../tests/pty_harness.py). 1s original ps cleanup; 5s offset cases. | Narrative preserves 17 passes/19 failures and not-run chained stages. Raw local failed logs are not linked by that record. Later ps-budget repair is not assigned as cause without an exact match. Accepted unresolved for audit only; CSH-069. |
| <a id="h03"></a>H03 — CSH-046 empty file; CSH-047 arithmetic and field timeouts | 5e77577e892192567c091d0c20658ce4f01f6327; 2153c39ea6fa56f1c68dc304a1304f9973ef792e [docker-sanitizer.log.gz](evidence/csh-046/docker-sanitizer.log.gz), [validation.json](evidence/csh-046/validation.json), [docker-sanitizer.log.gz](evidence/csh-047/docker-sanitizer.log.gz), [validation.json](evidence/csh-047/validation.json) | [tests/input.py](../tests/input.py); [tests/portability.py](../tests/portability.py); [tests/fields.py](../tests/fields.py). 5s original case deadlines. | Initial logs and binary/source manifests retained. Passing same-source serial attempts demonstrate bounded witnesses, not a causal repair. Accepted unresolved for audit only; CSH-069. |
| <a id="h04"></a>H04 — CSH-048 times/ulimit completion and native cleanup deadlines | ae993de53f2efcfd179e93ec3c632aa6b524b755 initial; per-attempt manifest in validation.json distinguishes later 1e08f41 correction. [docker-sanitizer.log.gz](evidence/csh-048/docker-sanitizer.log.gz), [native.log.gz](evidence/csh-048/native.log.gz), [validation.json](evidence/csh-048/validation.json) | [tests/state_builtin_cases.py](../tests/state_builtin_cases.py); [tests/pty_harness.py](../tests/pty_harness.py). 5s runtime; original cleanup bound in raw log. | Correct bytes before termination do not establish successful completion. The later dprintf leak repair is a separately diagnosed defect and does not establish the cause of every timeout. Accepted unresolved for audit only; CSH-069. |
| <a id="h05"></a>H05 — CSH-049 cleanup and three offset timeouts | 9f755dec9d7c8840f3e38e95011eceb64e55e662; per-platform manifests retained. [native-harness.log.gz](evidence/csh-049/native-harness.log.gz), [docker-asan.log.gz](evidence/csh-049/docker-asan.log.gz), [validation.json](evidence/csh-049/validation.json) | [tests/redirection_offsets.py](../tests/redirection_offsets.py); [tests/test_harness.py](../tests/test_harness.py); [tests/test_pty_harness.py](../tests/test_pty_harness.py). 1s original ps cleanup; 5s three offset cases. | All three source modes of the first rejected positioned byte timed out. Remaining make targets were not run; later full passes remain separate. Accepted unresolved for audit only; CSH-069. |
| <a id="h06"></a>H06 — CSH-051 leak-enabled timeouts and setup deadline | e1091a5fd818a85ec6a7b2ddc90a54cf1fdd8c9d [docker-sanitizer.log.gz](evidence/csh-051/docker-sanitizer.log.gz), [docker.log.gz](evidence/csh-051/docker.log.gz), [README.md](evidence/csh-051/README.md) | [tests/option_evidence_cases.py](../tests/option_evidence_cases.py); [tests/test_harness.py](../tests/test_harness.py); [tests/test_pty_harness.py](../tests/test_pty_harness.py). 5s option/PTY cases; 150ms original setup marker. | Leak-disabled ASan/UBSan results do not qualify LeakSanitizer. Measured startup slowdown is not a complete causal diagnosis of both failures. Accepted unresolved for audit only; CSH-069. |
| <a id="h07"></a>H07 — CSH-053 invocation/offset deadlines and hosted repeated-resume mismatch | 4b81c6380e43fbcd0f46c58ead57cc4bddb4639c is the PR evidence revision; duplicate push job identity remains linked in the ticket. [CSH-053-multibyte-lexical-boundaries.md](tickets/CSH-053-multibyte-lexical-boundaries.md) | [tests/invocation.py](../tests/invocation.py); [tests/redirection_offsets.py](../tests/redirection_offsets.py); [tests/jobs_cases.py](../tests/jobs_cases.py). 5s local case bounds; hosted mismatch is bytes, not a timeout. | Hosted output was 7,328 versus 7,216 expected bytes. Local successes do not resolve that mismatch. Preserve linked job 108450341412 and its source attribution rather than assign the separate prompt repair as its cause. Accepted unresolved for audit only; CSH-069. |
| <a id="h08"></a>H08 — CSH-055 harness setup/cleanup and descriptor/ignoreeof deadlines | Initial source digest a6b1b54ef172b710be3b8d704b676911ace0d3a6fcf1c7e967979302de64ce48; identities retain exact manifests. [native-harness-failed.log.gz](evidence/csh-055/native-harness-failed.log.gz), [docker-initial-sanitizer-failed.log.gz](evidence/csh-055/docker-initial-sanitizer-failed.log.gz), [docker-initial-sanitizer-identity.json](evidence/csh-055/docker-initial-sanitizer-identity.json), [README.md](evidence/csh-055/README.md) | [tests/execution_contracts.py](../tests/execution_contracts.py); [tests/runtime_cases.py](../tests/runtime_cases.py); [tests/test_harness.py](../tests/test_harness.py); [tests/test_pty_harness.py](../tests/test_pty_harness.py). 1s original ps cleanup, fixture setup marker, 5s descriptor/PTY. | Preserve the descriptor stop and later unrun stages. CSH-054 readiness fixes require matching evidence before being called causal repairs for these attempts. Accepted unresolved for audit only; CSH-069. |
| <a id="h09"></a>H09 — CSH-057 four Linux sanitizer control-flow deadlines | adb9e5c103f7183836eb5f8f19ba180b134a004a; batch manifests qualify tested bytes. [docker-sanitizer-runtime-0.log.gz](evidence/csh-057/docker-sanitizer-runtime-0.log.gz), [docker-sanitizer-runtime-1.log.gz](evidence/csh-057/docker-sanitizer-runtime-1.log.gz), [docker-sanitizer-runtime-2.log.gz](evidence/csh-057/docker-sanitizer-runtime-2.log.gz), [docker-sanitizer-runtime-3.log.gz](evidence/csh-057/docker-sanitizer-runtime-3.log.gz), [docker-sanitizer-runtime-batches.json](evidence/csh-057/docker-sanitizer-runtime-batches.json) | [tests/control_flow_cases.py](../tests/control_flow_cases.py). 5s cases; same exact cases retained in batch manifest. | These control-flow timeouts are outside the formal CSH-057 retention disposition. Serial unchanged passes do not establish cause. Accepted unresolved for audit only; CSH-069. |
| <a id="h10"></a>H10 — CSH-058 ps/PTY/setup bounds and native case-fallthrough deadline | 74bcc04e67a6b42503b86d52828a00aae903c50b; fixture correction 0dbf8d6 is distinguished in the source record. [native-full.log.gz](evidence/csh-058/native-full.log.gz), [docker-full.log.gz](evidence/csh-058/docker-full.log.gz), [sanitizer-full.log.gz](evidence/csh-058/sanitizer-full.log.gz), [README.md](evidence/csh-058/README.md) | [tests/pty_harness.py](../tests/pty_harness.py); [tests/test_harness.py](../tests/test_harness.py); [tests/test_pty_harness.py](../tests/test_pty_harness.py); [tests/control_flow_cases.py](../tests/control_flow_cases.py). 5s ps snapshot; 0.3s EOF-helper setup; 2s observation; 5s control plus 1s reap. | Separate these observations from the diagnosed four-second launcher alarm leaking through exec, which is repaired. No blanket load explanation. Accepted unresolved for audit only; CSH-069. |
| <a id="h11"></a>H11 — New Docker context_fixture WNOWAIT assertion | 5b56328143adc72f48f8af581b93fcb758af060e; push run 36512726060, job 109228225575. [ci-36512726060.json](evidence/csh-012/closure-5b56328/ci-36512726060.json), [ci-job-109228225575.log.gz](evidence/csh-012/closure-5b56328/ci-job-109228225575.log.gz) | [tests/context_fixture.c:136](../tests/context_fixture.c); [tests/contexts.py](../tests/contexts.py). Existing context fixture assertion and runner bound, unchanged. | waitid(P_PID, background_pid, WEXITED | WNOWAIT) returned nonzero; fixture aborted with status -6. Errno was not printed. Early child collection is a hypothesis only. The separate PR Docker job passed without a rerun; this does not diagnose the failed push job. Accepted unresolved for audit only; CSH-069. |

[Machine disposition records](evidence/csh-012/closure-5b56328/defect-dispositions.json)
include hashes and byte counts for every cited local original record. For H01/H02
and the local part of H07, the original ticket narrative is the retained record;
missing raw logs or exact failed-attempt identities are explicitly unavailable.
No passing revision is substituted as their failed source identity. The H07
hosted job remains linked in its ticket.

## CI reconciliation and reopening

At `5b56328`, push run 36512726060 has a failed Docker normal stage and passing
Ubuntu/macOS jobs. PR run 36512740736 has passing Ubuntu/Docker jobs and a
cancelled macOS job. Cancellation is not a pass; subsequent stages skipped after
the Docker abort were not run. Both complete snapshots and available job logs
are retained. These are separate from the all-green c8c1c91 baseline and from
any later integration run. No repeat-until-green workflow was requested.

H11 remains an assertion failure with unrecorded errno; source inspection alone
does not prove ECHILD or a race. The unchanged default `test-context` continues
to detect this condition. CSH-069 must record a causal fix or explicit further
disposition when new evidence arrives.

Reopen the relevant defect/qualification ticket on recurrence. Reopen CSH-012
only if a new finding invalidates the completeness or truthfulness of its audit
accounting (for example, an omitted applicable requirement or evidence falsely
reported as passing). An already-owned, accurately disclosed defect does not
by itself invalidate completion of the audit.
