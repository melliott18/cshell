# Implementation tickets

Use the [visual implementation plan](../implementation-plan.md) to understand
the dependency paths and parallel work. Ticket files own scope, acceptance,
and status; their GitHub links connect to the matching issues.

CSH-016, CSH-017, and CSH-036 were the first parallel tasks. Legacy repair
tickets CSH-002, CSH-014, and CSH-015 are superseded, not completed; they retain
defect history, while replacement tickets own the safety requirements.
CSH-039 explicitly switches the default executable and deletes the legacy code.

## Milestones

Active milestones collect child completion. Close them only after their
children, completion prerequisites, and acceptance criteria pass. CSH-002 is
retained below only as a superseded historical milestone.

| Milestone | Scope | Children | GitHub |
| --- | --- | --- | --- |
| [CSH-002](CSH-002-legacy-safety.md) | Contain memory and process defects in the legacy shell | [CSH-014](CSH-014-input-memory-safety.md), [CSH-015](CSH-015-process-pipe-safety.md) | [#3](https://github.com/melliott18/cshell/issues/3) |
| [CSH-003](CSH-003-invocation-and-test-harness.md) | Define invocation, input lifecycle, and behavioral testing | [CSH-016](CSH-016-input-and-invocation.md), [CSH-017](CSH-017-test-harness-and-ci.md), [CSH-018](CSH-018-status-and-cli-integration.md) | [#4](https://github.com/melliott18/cshell/issues/4) |
| [CSH-006](CSH-006-execution-and-redirection.md) | Execute syntax trees with explicit resource ownership | [CSH-019](CSH-019-simple-command-redirections.md), [CSH-020](CSH-020-pipeline-lifecycle.md), [CSH-021](CSH-021-lists-and-execution-contexts.md), [CSH-039](CSH-039-legacy-retirement.md) | [#7](https://github.com/melliott18/cshell/issues/7) |
| [CSH-007](CSH-007-variables-and-parameters.md) | Model variables, environments, and positional parameters | [CSH-022](CSH-022-shell-state-storage.md), [CSH-023](CSH-023-assignment-environments.md) | [#8](https://github.com/melliott18/cshell/issues/8) |
| [CSH-008](CSH-008-word-expansion.md) | Implement context-sensitive word expansion | [CSH-024](CSH-024-value-expansions.md), [CSH-025](CSH-025-field-and-pathname-expansion.md), [CSH-026](CSH-026-substitution-and-heredoc-integration.md), [CSH-041](CSH-041-arithmetic-substitution-replay.md) | [#9](https://github.com/melliott18/cshell/issues/9) |
| [CSH-009](CSH-009-compounds-and-functions.md) | Add compound commands and shell functions | [CSH-027](CSH-027-compound-syntax.md), [CSH-028](CSH-028-control-flow-and-functions.md) | [#10](https://github.com/melliott18/cshell/issues/10) |
| [CSH-010](CSH-010-builtins-options-and-aliases.md) | Complete required builtins, options, and aliases | [CSH-029](CSH-029-state-builtins.md), [CSH-030](CSH-030-alias-substitution.md), [CSH-031](CSH-031-evaluation-builtins.md), [CSH-032](CSH-032-shell-options.md) | [#11](https://github.com/melliott18/cshell/issues/11) |
| [CSH-011](CSH-011-signals-and-job-control.md) | Implement signals, traps, and interactive job control | [CSH-033](CSH-033-pty-test-harness.md), [CSH-034](CSH-034-job-control.md), [CSH-035](CSH-035-traps-and-signal-semantics.md) | [#12](https://github.com/melliott18/cshell/issues/12) |
| [CSH-012](CSH-012-conformance-and-portability.md) | Audit POSIX conformance and portability | [CSH-036](CSH-036-conformance-matrix.md), [CSH-037](CSH-037-portability-audit.md) | [#13](https://github.com/melliott18/cshell/issues/13) |

## Standalone work

Foundation, front-end implementation, roadmap maintenance, and test infrastructure:

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-001](CSH-001-project-foundation.md) | Establish the cshell project foundation | None | [#2](https://github.com/melliott18/cshell/issues/2) |
| [CSH-004](CSH-004-lexer-and-words.md) | Preserve shell tokens and quoting | [CSH-016](CSH-016-input-and-invocation.md), [CSH-017](CSH-017-test-harness-and-ci.md) | [#5](https://github.com/melliott18/cshell/issues/5) |
| [CSH-005](CSH-005-parser-and-ast.md) | Parse commands into an owned syntax tree | [CSH-004](CSH-004-lexer-and-words.md) | [#6](https://github.com/melliott18/cshell/issues/6) |
| [CSH-013](CSH-013-visual-roadmap.md) | Document visual architecture and parallel implementation work | [CSH-001](CSH-001-project-foundation.md) | [#14](https://github.com/melliott18/cshell/issues/14) |
| [CSH-038](CSH-038-legacy-retirement-plan.md) | Remove legacy constraints from the implementation roadmap | [CSH-013](CSH-013-visual-roadmap.md) | [#40](https://github.com/melliott18/cshell/issues/40) |
| [CSH-040](CSH-040-macos-harness-cleanup.md) | Make repeated macOS harness cleanup reliable | [CSH-017](CSH-017-test-harness-and-ci.md) | [#48](https://github.com/melliott18/cshell/issues/48) |
| [CSH-042](CSH-042-locale-semantics.md) | Complete locale-sensitive shell behavior found by the portability audit | [CSH-037](CSH-037-portability-audit.md) | [#73](https://github.com/melliott18/cshell/issues/73) |
| [CSH-043](CSH-043-redirection-offset.md) | Define and verify the redirection offset maximum | [CSH-037](CSH-037-portability-audit.md) | [#74](https://github.com/melliott18/cshell/issues/74) |
| [CSH-044](CSH-044-intermittent-bg-prompt.md) | Diagnose intermittent background-resume prompt stall | [CSH-034](CSH-034-job-control.md) | [#76](https://github.com/melliott18/cshell/issues/76) |
| [CSH-045](CSH-045-jobs-fixture-timeout.md) | Diagnose intermittent macOS sanitizer jobs fixture timeout | [CSH-034](CSH-034-job-control.md) | [#77](https://github.com/melliott18/cshell/issues/77) |
| [CSH-046](CSH-046-invocation-syntax-evidence.md) | Close invocation, lexical, grammar and alias evidence gaps | [CSH-036](CSH-036-conformance-matrix.md), [CSH-039](CSH-039-legacy-retirement.md) | [#78](https://github.com/melliott18/cshell/issues/78) |
| [CSH-047](CSH-047-expansion-evidence.md) | Close expansion, parameter and locale evidence gaps | [CSH-036](CSH-036-conformance-matrix.md), [CSH-039](CSH-039-legacy-retirement.md) | [#79](https://github.com/melliott18/cshell/issues/79) |
| [CSH-048](CSH-048-state-builtin-evidence.md) | Close shell state and builtin integration evidence gaps | [CSH-036](CSH-036-conformance-matrix.md), [CSH-039](CSH-039-legacy-retirement.md) | [#80](https://github.com/melliott18/cshell/issues/80) |
| [CSH-049](CSH-049-execution-evidence.md) | Close execution, redirection and control-flow evidence gaps | [CSH-036](CSH-036-conformance-matrix.md), [CSH-039](CSH-039-legacy-retirement.md) | [#81](https://github.com/melliott18/cshell/issues/81) |
| [CSH-050](CSH-050-jobs-signals-evidence.md) | Close jobs, signal and trap evidence gaps | [CSH-036](CSH-036-conformance-matrix.md), [CSH-039](CSH-039-legacy-retirement.md) | [#82](https://github.com/melliott18/cshell/issues/82) |
| [CSH-051](CSH-051-shell-option-evidence.md) | Close base shell-option evidence gaps | [CSH-036](CSH-036-conformance-matrix.md), [CSH-039](CSH-039-legacy-retirement.md) | [#83](https://github.com/melliott18/cshell/issues/83) |
| [CSH-052](CSH-052-host-utility-evidence.md) | Close host utility and intrinsic lookup evidence gaps | [CSH-036](CSH-036-conformance-matrix.md), [CSH-039](CSH-039-legacy-retirement.md) | [#84](https://github.com/melliott18/cshell/issues/84) |
| [CSH-053](CSH-053-multibyte-lexical-boundaries.md) | Preserve syntax-valued bytes inside multibyte source characters | [CSH-004](CSH-004-lexer-and-words.md) | [#86](https://github.com/melliott18/cshell/issues/86) |
| [CSH-054](CSH-054-signal-contract-gaps.md) | Complete residual jobs and signal contracts | [CSH-034](CSH-034-job-control.md), [CSH-035](CSH-035-traps-and-signal-semantics.md) | [#90](https://github.com/melliott18/cshell/issues/90) |
| [CSH-055](CSH-055-execution-contract-gaps.md) | Complete residual execution contracts | [CSH-031](CSH-031-evaluation-builtins.md), [CSH-039](CSH-039-legacy-retirement.md) | [#92](https://github.com/melliott18/cshell/issues/92) |
| [CSH-056](CSH-056-host-contract-gaps.md) | Resolve residual host utility contracts | [CSH-039](CSH-039-legacy-retirement.md) | [#97](https://github.com/melliott18/cshell/issues/97) |
| [CSH-057](CSH-057-job-lifecycle-boundaries.md) | Verify remaining job lifecycle boundaries | [CSH-034](CSH-034-job-control.md), [CSH-035](CSH-035-traps-and-signal-semantics.md) | [#99](https://github.com/melliott18/cshell/issues/99) |
| [CSH-058](CSH-058-signal-edge-evidence.md) | Complete signal inheritance and permission evidence | [CSH-035](CSH-035-traps-and-signal-semantics.md) | [#100](https://github.com/melliott18/cshell/issues/100) |
| [CSH-059](CSH-059-host-boundary-capabilities.md) | Extend qualified host boundary capabilities | [CSH-056](CSH-056-host-contract-gaps.md) | [#101](https://github.com/melliott18/cshell/issues/101) |
| [CSH-060](CSH-060-extended-host-environments.md) | Qualify remaining host environments and limits | [CSH-059](CSH-059-host-boundary-capabilities.md) | [#106](https://github.com/melliott18/cshell/issues/106) |
| [CSH-061](CSH-061-host-environment-residuals.md) | Resolve remaining host environment contracts | [CSH-060](CSH-060-extended-host-environments.md) | [#110](https://github.com/melliott18/cshell/issues/110) |
| [CSH-062](CSH-062-host-contract-controlled-platforms.md) | Supply remaining controlled host platforms | [CSH-061](CSH-061-host-environment-residuals.md) | [#116](https://github.com/melliott18/cshell/issues/116) |
| [CSH-063](CSH-063-host-platform-residual-qualification.md) | Qualify remaining supplied host platforms | [CSH-062](CSH-062-host-contract-controlled-platforms.md) | [#122](https://github.com/melliott18/cshell/issues/122) |
| [CSH-064](CSH-064-host-platform-external-prerequisites.md) | Supply external prerequisites for remaining host contracts | [CSH-063](CSH-063-host-platform-residual-qualification.md) | [#127](https://github.com/melliott18/cshell/issues/127) |

| [CSH-065](CSH-065-interactive-parser-recovery.md) | Recover from interactive main-parser syntax errors | [CSH-039](CSH-039-legacy-retirement.md) | [#134](https://github.com/melliott18/cshell/issues/134) |
| [CSH-066](CSH-066-resource-bounded-nesting.md) | Remove arbitrary shell nesting limits | [CSH-005](CSH-005-parser-and-ast.md), [CSH-028](CSH-028-control-flow-and-functions.md), [CSH-041](CSH-041-arithmetic-substitution-replay.md) | [#135](https://github.com/melliott18/cshell/issues/135) |
| [CSH-067](CSH-067-shell-locale-pathname-qualification.md) | Qualify remaining shell locale and pathname boundaries | [CSH-042](CSH-042-locale-semantics.md), [CSH-047](CSH-047-expansion-evidence.md), [CSH-053](CSH-053-multibyte-lexical-boundaries.md) | [#136](https://github.com/melliott18/cshell/issues/136) |
| [CSH-068](CSH-068-host-system-contract-inventory.md) | Inventory the complete required host utility contract | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#137](https://github.com/melliott18/cshell/issues/137) |
| [CSH-069](CSH-069-historical-failure-dispositions.md) | Disposition retained unexplained validation failures | [CSH-046](CSH-046-invocation-syntax-evidence.md), [CSH-047](CSH-047-expansion-evidence.md), [CSH-048](CSH-048-state-builtin-evidence.md), [CSH-049](CSH-049-execution-evidence.md), [CSH-051](CSH-051-shell-option-evidence.md), [CSH-055](CSH-055-execution-contract-gaps.md), [CSH-058](CSH-058-signal-edge-evidence.md) | [#138](https://github.com/melliott18/cshell/issues/138) |

| [CSH-070](CSH-070-host-formatted-output.md) | Qualify host printf and echo contracts | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#142](https://github.com/melliott18/cshell/issues/142) |
| [CSH-071](CSH-071-host-permissions-identities.md) | Qualify host predicates, permissions and identities | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#143](https://github.com/melliott18/cshell/issues/143) |
| [CSH-072](CSH-072-host-filesystem-paths.md) | Qualify host filesystem and pathname utilities | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#144](https://github.com/melliott18/cshell/issues/144) |
| [CSH-073](CSH-073-host-text-streams.md) | Qualify host text and byte stream utilities | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#145](https://github.com/melliott18/cshell/issues/145) |
| [CSH-074](CSH-074-host-languages-editors.md) | Qualify host languages, editors and argument construction | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#146](https://github.com/melliott18/cshell/issues/146) |
| [CSH-075](CSH-075-host-execution-processes.md) | Qualify host execution and process utilities | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#147](https://github.com/melliott18/cshell/issues/147) |
| [CSH-076](CSH-076-host-locale-catalogs.md) | Qualify host locale and message catalog utilities | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#148](https://github.com/melliott18/cshell/issues/148) |
| [CSH-077](CSH-077-host-terminal-utilities.md) | Qualify host terminal and session utilities | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#149](https://github.com/melliott18/cshell/issues/149) |
| [CSH-078](CSH-078-host-service-utilities.md) | Qualify host scheduling, mail and service utilities | [CSH-052](CSH-052-host-utility-evidence.md), [CSH-056](CSH-056-host-contract-gaps.md) | [#150](https://github.com/melliott18/cshell/issues/150) |
| [CSH-080](CSH-080-filesystem-remaining-contracts.md) | Qualify remaining filesystem provider and fault contracts | [CSH-072](CSH-072-host-filesystem-paths.md) | [#158](https://github.com/melliott18/cshell/issues/158) |
| [CSH-084](CSH-084-filesystem-residual-environments.md) | Supply residual filesystem environments and contract oracles | [CSH-080](CSH-080-filesystem-remaining-contracts.md) | [#178](https://github.com/melliott18/cshell/issues/178) |
| [CSH-085](CSH-085-filesystem-isolated-contracts.md) | Supply remaining filesystem contracts and isolated environments | [CSH-084](CSH-084-filesystem-residual-environments.md) | [#181](https://github.com/melliott18/cshell/issues/181) |

## Child implementation tickets

### CSH-002: Legacy safety (superseded)

Parent acceptance: [CSH-002](CSH-002-legacy-safety.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-014](CSH-014-input-memory-safety.md) | Make legacy input and command storage safe | [CSH-001](CSH-001-project-foundation.md) | [#15](https://github.com/melliott18/cshell/issues/15) |
| [CSH-015](CSH-015-process-pipe-safety.md) | Contain legacy child and pipe failures | [CSH-001](CSH-001-project-foundation.md) | [#16](https://github.com/melliott18/cshell/issues/16) |

### CSH-003: Define invocation, input lifecycle, and behavioral testing

Parent acceptance: [CSH-003](CSH-003-invocation-and-test-harness.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-016](CSH-016-input-and-invocation.md) | Introduce input sources and shell invocation modes | [CSH-001](CSH-001-project-foundation.md) | [#17](https://github.com/melliott18/cshell/issues/17) |
| [CSH-017](CSH-017-test-harness-and-ci.md) | Build a bounded behavioral harness and continuous integration | [CSH-001](CSH-001-project-foundation.md) | [#18](https://github.com/melliott18/cshell/issues/18) |
| [CSH-018](CSH-018-status-and-cli-integration.md) | Integrate invocation modes with command and shell exit statuses | [CSH-016](CSH-016-input-and-invocation.md), [CSH-017](CSH-017-test-harness-and-ci.md), [CSH-019](CSH-019-simple-command-redirections.md) | [#19](https://github.com/melliott18/cshell/issues/19) |

### CSH-006: Execute syntax trees with explicit resource ownership

Parent acceptance: [CSH-006](CSH-006-execution-and-redirection.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-019](CSH-019-simple-command-redirections.md) | Execute simple commands with ordered redirections | [CSH-005](CSH-005-parser-and-ast.md), [CSH-022](CSH-022-shell-state-storage.md) | [#20](https://github.com/melliott18/cshell/issues/20) |
| [CSH-020](CSH-020-pipeline-lifecycle.md) | Execute pipelines with explicit child and descriptor ownership | [CSH-019](CSH-019-simple-command-redirections.md) | [#21](https://github.com/melliott18/cshell/issues/21) |
| [CSH-021](CSH-021-lists-and-execution-contexts.md) | Execute lists, groups, and background contexts | [CSH-020](CSH-020-pipeline-lifecycle.md) | [#22](https://github.com/melliott18/cshell/issues/22) |
| [CSH-039](CSH-039-legacy-retirement.md) | Switch cshell to the replacement runtime and delete the legacy code | [CSH-018](CSH-018-status-and-cli-integration.md), [CSH-020](CSH-020-pipeline-lifecycle.md) | [#41](https://github.com/melliott18/cshell/issues/41) |

### CSH-007: Model variables, environments, and positional parameters

Parent acceptance: [CSH-007](CSH-007-variables-and-parameters.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-022](CSH-022-shell-state-storage.md) | Define shell variable and parameter storage | [CSH-016](CSH-016-input-and-invocation.md) | [#23](https://github.com/melliott18/cshell/issues/23) |
| [CSH-023](CSH-023-assignment-environments.md) | Apply assignment prefixes by execution category | [CSH-019](CSH-019-simple-command-redirections.md), [CSH-022](CSH-022-shell-state-storage.md) | [#24](https://github.com/melliott18/cshell/issues/24) |

### CSH-008: Implement context-sensitive word expansion

Parent acceptance: [CSH-008](CSH-008-word-expansion.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-024](CSH-024-value-expansions.md) | Implement value expansions with quote provenance | [CSH-004](CSH-004-lexer-and-words.md), [CSH-022](CSH-022-shell-state-storage.md) | [#25](https://github.com/melliott18/cshell/issues/25) |
| [CSH-025](CSH-025-field-and-pathname-expansion.md) | Complete field splitting and pathname expansion | [CSH-024](CSH-024-value-expansions.md) | [#26](https://github.com/melliott18/cshell/issues/26) |
| [CSH-026](CSH-026-substitution-and-heredoc-integration.md) | Integrate substitutions and context-sensitive expansion | [CSH-005](CSH-005-parser-and-ast.md), [CSH-006](CSH-006-execution-and-redirection.md), [CSH-007](CSH-007-variables-and-parameters.md), [CSH-025](CSH-025-field-and-pathname-expansion.md) | [#27](https://github.com/melliott18/cshell/issues/27) |
| [CSH-041](CSH-041-arithmetic-substitution-replay.md) | Resolve arithmetic-first command-substitution ambiguity | [CSH-005](CSH-005-parser-and-ast.md), [CSH-024](CSH-024-value-expansions.md) | [#64](https://github.com/melliott18/cshell/issues/64) |

### CSH-009: Add compound commands and shell functions

Parent acceptance: [CSH-009](CSH-009-compounds-and-functions.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-027](CSH-027-compound-syntax.md) | Parse compound commands and function definitions | [CSH-005](CSH-005-parser-and-ast.md) | [#28](https://github.com/melliott18/cshell/issues/28) |
| [CSH-028](CSH-028-control-flow-and-functions.md) | Execute control flow and shell functions | [CSH-027](CSH-027-compound-syntax.md), [CSH-006](CSH-006-execution-and-redirection.md), [CSH-007](CSH-007-variables-and-parameters.md), [CSH-008](CSH-008-word-expansion.md) | [#29](https://github.com/melliott18/cshell/issues/29) |

### CSH-010: Complete required builtins, options, and aliases

Parent acceptance: [CSH-010](CSH-010-builtins-options-and-aliases.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-029](CSH-029-state-builtins.md) | Implement state builtins and allocate the utility inventory | [CSH-019](CSH-019-simple-command-redirections.md), [CSH-022](CSH-022-shell-state-storage.md) | [#30](https://github.com/melliott18/cshell/issues/30) |
| [CSH-030](CSH-030-alias-substitution.md) | Implement alias storage and token substitution | [CSH-004](CSH-004-lexer-and-words.md), [CSH-005](CSH-005-parser-and-ast.md) | [#31](https://github.com/melliott18/cshell/issues/31) |
| [CSH-031](CSH-031-evaluation-builtins.md) | Complete evaluation, lookup, and remaining utility builtins | [CSH-008](CSH-008-word-expansion.md), [CSH-009](CSH-009-compounds-and-functions.md), [CSH-029](CSH-029-state-builtins.md), [CSH-030](CSH-030-alias-substitution.md) | [#32](https://github.com/melliott18/cshell/issues/32) |
| [CSH-032](CSH-032-shell-options.md) | Complete shell option behavior and interactions | [CSH-008](CSH-008-word-expansion.md), [CSH-009](CSH-009-compounds-and-functions.md), [CSH-029](CSH-029-state-builtins.md), [CSH-031](CSH-031-evaluation-builtins.md) | [#33](https://github.com/melliott18/cshell/issues/33) |

### CSH-011: Implement signals, traps, and interactive job control

Parent acceptance: [CSH-011](CSH-011-signals-and-job-control.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-033](CSH-033-pty-test-harness.md) | Add a bounded pseudo-terminal test harness | [CSH-017](CSH-017-test-harness-and-ci.md) | [#34](https://github.com/melliott18/cshell/issues/34) |
| [CSH-034](CSH-034-job-control.md) | Implement process groups and terminal job control | [CSH-006](CSH-006-execution-and-redirection.md), [CSH-033](CSH-033-pty-test-harness.md) | [#35](https://github.com/melliott18/cshell/issues/35) |
| [CSH-035](CSH-035-traps-and-signal-semantics.md) | Complete traps and shell signal semantics | [CSH-009](CSH-009-compounds-and-functions.md), [CSH-031](CSH-031-evaluation-builtins.md), [CSH-032](CSH-032-shell-options.md), [CSH-034](CSH-034-job-control.md) | [#36](https://github.com/melliott18/cshell/issues/36) |

### CSH-012: Audit POSIX conformance and portability

Parent acceptance: [CSH-012](CSH-012-conformance-and-portability.md).

| Ticket | Deliverable | Depends on | GitHub |
| --- | --- | --- | --- |
| [CSH-036](CSH-036-conformance-matrix.md) | Map POSIX requirements to implementation and test evidence | [CSH-001](CSH-001-project-foundation.md) | [#37](https://github.com/melliott18/cshell/issues/37) |
| [CSH-037](CSH-037-portability-audit.md) | Audit integrated conformance and platform portability | [CSH-008](CSH-008-word-expansion.md), [CSH-009](CSH-009-compounds-and-functions.md), [CSH-010](CSH-010-builtins-options-and-aliases.md), [CSH-011](CSH-011-signals-and-job-control.md), [CSH-036](CSH-036-conformance-matrix.md) | [#38](https://github.com/melliott18/cshell/issues/38) |

Read the [contribution workflow](../../CONTRIBUTING.md) before starting work.
Use the [ticket template](TEMPLATE.md) for new work. A child uses its own
explicit prerequisites; it does not inherit all parent completion gates.
Milestones are not closed merely because they were split.

Use [requirements by ticket](../posix-owners.md) to find the POSIX requirements
and intended fixtures assigned to each implementation ticket. Each requirement
links its source, owner, scope and current evidence; update both directions when
splitting or reallocating work.

Tests and conformance evidence grow with each implementation ticket.
CSH-037 is the final audit, not the first testing milestone.
