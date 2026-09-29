# Requirement review ledger at c8c1c91

The [final audit closure](conformance-closure.md) supersedes earlier acceptance-gate
decisions. Recorded failures and source-qualified evidence below remain unchanged.

This accompanies the [CSH-012 review](conformance-acceptance-review.md). All 131
matrix families are listed: 115 applicable and 16 excluded under the unchanged
base profile. A condition map links implementation paths, precise assertions,
normative sources, policies and retained revisions. A map reference means
bounded evidence was reviewed; it does not mark an entire family verified.

Open owners supplement historical implementation/evidence owners. CSH-064 records scoped qualification evidence; CSH-070–078 are now
the open qualification owners, not replacements for utility/vendor implementation
owners. CSH-069 dispositions apply to run observations, not every requirement
touched by a timed-out suite. U-034/U-040 have a [complete system inventory](host-system-inventory.md);
CSH-012 is complete as an accounting audit while external contracts remain open.

| Family / normative scope | Condition evidence reviewed | Current disposition |
| --- | --- | --- |
| [SH-001](posix-matrix.md#sh-001) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [SH-002](posix-matrix.md#sh-002) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [SH-003](posix-matrix.md#sh-003) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-003) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [SH-004](posix-matrix.md#sh-004) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-004) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [SH-005](posix-matrix.md#sh-005) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-005) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [SH-006](posix-matrix.md#sh-006) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-006) | Open residual: [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [SH-007](posix-matrix.md#sh-007) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-007) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [SH-008](posix-matrix.md#sh-008) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#sh-008) | Open residual: [CSH-065](tickets/CSH-065-interactive-parser-recovery.md). |
| [SH-009](posix-matrix.md#sh-009) | [CSH-049 clause/condition map](execution-evidence.md#sh-009) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [LEX-001](posix-matrix.md#lex-001) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#lex-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [LEX-002](posix-matrix.md#lex-002) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#lex-002) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [LEX-003](posix-matrix.md#lex-003) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#lex-003) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [LEX-004](posix-matrix.md#lex-004) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#lex-004) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [LEX-005](posix-matrix.md#lex-005) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#lex-005) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [LEX-006](posix-matrix.md#lex-006) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#lex-006) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [GRAM-001](posix-matrix.md#gram-001) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#gram-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [GRAM-002](posix-matrix.md#gram-002) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#gram-002) | Open residual: [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [GRAM-003](posix-matrix.md#gram-003) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#gram-003) | Bounded mapped evidence retained; no additional defect identified in this review. Fresh source-end heredoc witness passes in all three modes. |
| [GRAM-004](posix-matrix.md#gram-004) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#gram-004) | Open residual: [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [GRAM-005](posix-matrix.md#gram-005) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#gram-005) | Open residual: [CSH-065](tickets/CSH-065-interactive-parser-recovery.md), [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [ENV-001](posix-matrix.md#env-001) | [CSH-048 clause/condition map](state-builtin-evidence.md#env-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [ENV-002](posix-matrix.md#env-002) | [CSH-047 clause/condition map](expansion-evidence.md#env-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [ENV-003](posix-matrix.md#env-003) | [CSH-048 clause/condition map](state-builtin-evidence.md#env-003) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [ENV-004](posix-matrix.md#env-004) | [CSH-047 clause/condition map](expansion-evidence.md#env-004) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [ENV-005](posix-matrix.md#env-005) | [CSH-048 clause/condition map](state-builtin-evidence.md#env-005) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXP-001](posix-matrix.md#exp-001) | [CSH-047 clause/condition map](expansion-evidence.md#exp-001) | Open residual: [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [EXP-002](posix-matrix.md#exp-002) | [CSH-047 clause/condition map](expansion-evidence.md#exp-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXP-003](posix-matrix.md#exp-003) | [CSH-047 clause/condition map](expansion-evidence.md#exp-003) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXP-004](posix-matrix.md#exp-004) | [CSH-047 clause/condition map](expansion-evidence.md#exp-004) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [EXP-005](posix-matrix.md#exp-005) | [CSH-047 clause/condition map](expansion-evidence.md#exp-005) | Open residual: [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [EXP-006](posix-matrix.md#exp-006) | [CSH-047 clause/condition map](expansion-evidence.md#exp-006) | Open residual: [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [EXP-007](posix-matrix.md#exp-007) | [CSH-047 clause/condition map](expansion-evidence.md#exp-007) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [EXP-008](posix-matrix.md#exp-008) | [CSH-047 clause/condition map](expansion-evidence.md#exp-008) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [EXP-009](posix-matrix.md#exp-009) | [CSH-047 clause/condition map](expansion-evidence.md#exp-009) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [EXP-010](posix-matrix.md#exp-010) | [CSH-047 clause/condition map](expansion-evidence.md#exp-010) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [EXP-011](posix-matrix.md#exp-011) | [CSH-047 clause/condition map](expansion-evidence.md#exp-011) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [RED-001](posix-matrix.md#red-001) | [CSH-049 clause/condition map](execution-evidence.md#red-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [RED-002](posix-matrix.md#red-002) | [CSH-049 clause/condition map](execution-evidence.md#red-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [RED-003](posix-matrix.md#red-003) | [CSH-049 clause/condition map](execution-evidence.md#red-003) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [RED-004](posix-matrix.md#red-004) | [CSH-049 clause/condition map](execution-evidence.md#red-004) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [RED-005](posix-matrix.md#red-005) | [CSH-049 clause/condition map](execution-evidence.md#red-005) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [RED-006](posix-matrix.md#red-006) | [CSH-049 clause/condition map](execution-evidence.md#red-006) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-001](posix-matrix.md#exec-001) | [CSH-049 clause/condition map](execution-evidence.md#exec-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-002](posix-matrix.md#exec-002) | [CSH-049 clause/condition map](execution-evidence.md#exec-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-003](posix-matrix.md#exec-003) | [CSH-049 clause/condition map](execution-evidence.md#exec-003) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-004](posix-matrix.md#exec-004) | [CSH-049 clause/condition map](execution-evidence.md#exec-004) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-005](posix-matrix.md#exec-005) | [CSH-049 clause/condition map](execution-evidence.md#exec-005) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-006](posix-matrix.md#exec-006) | [CSH-049 clause/condition map](execution-evidence.md#exec-006) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-007](posix-matrix.md#exec-007) | [CSH-049 clause/condition map](execution-evidence.md#exec-007) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-008](posix-matrix.md#exec-008) | [CSH-049 clause/condition map](execution-evidence.md#exec-008) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-009](posix-matrix.md#exec-009) | [CSH-050 clause/condition map](jobs-signals-evidence.md#exec-009) | Bounded mapped evidence retained; no additional defect identified in this review. Historical retention disposition remains scoped; recurrence CSH-057. |
| [EXEC-010](posix-matrix.md#exec-010) | [CSH-049 clause/condition map](execution-evidence.md#exec-010) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-011](posix-matrix.md#exec-011) | [CSH-049 clause/condition map](execution-evidence.md#exec-011) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-012](posix-matrix.md#exec-012) | [CSH-049 clause/condition map](execution-evidence.md#exec-012) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [EXEC-013](posix-matrix.md#exec-013) | [CSH-049 clause/condition map](execution-evidence.md#exec-013) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [EXEC-014](posix-matrix.md#exec-014) | [CSH-049 clause/condition map](execution-evidence.md#exec-014) | Open residual: [CSH-066](tickets/CSH-066-resource-bounded-nesting.md). |
| [EXEC-015](posix-matrix.md#exec-015) | [CSH-049 clause/condition map](execution-evidence.md#exec-015) | Open residual: [CSH-065](tickets/CSH-065-interactive-parser-recovery.md). |
| [EXEC-016](posix-matrix.md#exec-016) | [CSH-049 clause/condition map](execution-evidence.md#exec-016) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [ENV-006](posix-matrix.md#env-006) | [CSH-048 clause/condition map](state-builtin-evidence.md#env-006) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [JOB-001](posix-matrix.md#job-001) | [CSH-050 clause/condition map](jobs-signals-evidence.md#job-001) | Bounded mapped evidence retained; no additional defect identified in this review. Historical retention disposition remains scoped; recurrence CSH-057. |
| [JOB-002](posix-matrix.md#job-002) | [CSH-050 clause/condition map](jobs-signals-evidence.md#job-002) | Bounded mapped evidence retained; no additional defect identified in this review. Historical retention disposition remains scoped; recurrence CSH-057. |
| [JOB-003](posix-matrix.md#job-003) | [CSH-050 clause/condition map](jobs-signals-evidence.md#job-003) | Bounded mapped evidence retained; no additional defect identified in this review. Historical retention disposition remains scoped; recurrence CSH-057. |
| [SIG-001](posix-matrix.md#sig-001) | [CSH-050 clause/condition map](jobs-signals-evidence.md#sig-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [SIG-002](posix-matrix.md#sig-002) | [CSH-050 clause/condition map](jobs-signals-evidence.md#sig-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [SIG-003](posix-matrix.md#sig-003) | [CSH-050 clause/condition map](jobs-signals-evidence.md#sig-003) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-001](posix-utilities.md#u-001) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-002](posix-utilities.md#u-002) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-003](posix-utilities.md#u-003) | [CSH-049 clause/condition map](execution-evidence.md#u-003) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-004](posix-utilities.md#u-004) | [CSH-049 clause/condition map](execution-evidence.md#u-004) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-005](posix-utilities.md#u-005) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-005) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-006](posix-utilities.md#u-006) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-006) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-007](posix-utilities.md#u-007) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-007) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-008](posix-utilities.md#u-008) | [CSH-050 clause/condition map](jobs-signals-evidence.md#u-008) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-009](posix-utilities.md#u-009) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-009) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-010](posix-utilities.md#u-010) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-010) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-011](posix-utilities.md#u-011) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-011) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-012](posix-utilities.md#u-012) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-012) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-013](posix-utilities.md#u-013) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-013) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-014](posix-utilities.md#u-014) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-014) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-015](posix-utilities.md#u-015) | [CSH-050 clause/condition map](jobs-signals-evidence.md#u-015) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-016](posix-utilities.md#u-016) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-016) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-017](posix-utilities.md#u-017) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#u-017) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [U-018](posix-utilities.md#u-018) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [U-019](posix-utilities.md#u-019) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-019) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-020](posix-utilities.md#u-020) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-020) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-021](posix-utilities.md#u-021) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [U-022](posix-utilities.md#u-022) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [U-023](posix-utilities.md#u-023) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-023) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-024](posix-utilities.md#u-024) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-024) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-025](posix-utilities.md#u-025) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [U-026](posix-utilities.md#u-026) | [CSH-050 clause/condition map](jobs-signals-evidence.md#u-026) | Open residual: [CSH-075](tickets/CSH-075-host-execution-processes.md) (retained CSH-064 evidence). |
| [U-027](posix-utilities.md#u-027) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-027) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [U-028](posix-utilities.md#u-028) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [U-029](posix-utilities.md#u-029) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-029) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-030](posix-utilities.md#u-030) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-030) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-031](posix-utilities.md#u-031) | [CSH-046 clause/condition map](invocation-syntax-evidence.md#u-031) | Open residual: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| [U-032](posix-utilities.md#u-032) | [CSH-050 clause/condition map](jobs-signals-evidence.md#u-032) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-033](posix-utilities.md#u-033) | [CSH-048 clause/condition map](state-builtin-evidence.md#u-033) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [U-034](posix-utilities.md#u-034) | [CSH-052 clause/condition map](host-utility-evidence.md#u-034) | Open residual: [CSH-070](tickets/CSH-070-host-formatted-output.md), [CSH-071](tickets/CSH-071-host-permissions-identities.md), [CSH-072](tickets/CSH-072-host-filesystem-paths.md), [CSH-073](tickets/CSH-073-host-text-streams.md), [CSH-074](tickets/CSH-074-host-languages-editors.md), [CSH-075](tickets/CSH-075-host-execution-processes.md), [CSH-076](tickets/CSH-076-host-locale-catalogs.md), [CSH-077](tickets/CSH-077-host-terminal-utilities.md), [CSH-078](tickets/CSH-078-host-service-utilities.md) (retained CSH-064 evidence). |
| [U-035](posix-utilities.md#u-035) | [CSH-052 clause/condition map](host-utility-evidence.md#u-035) | Open residual: [CSH-070](tickets/CSH-070-host-formatted-output.md) (retained CSH-064 evidence). |
| [U-036](posix-utilities.md#u-036) | [CSH-052 clause/condition map](host-utility-evidence.md#u-036) | Open residual: [CSH-070](tickets/CSH-070-host-formatted-output.md) (retained CSH-064 evidence). |
| [U-037](posix-utilities.md#u-037) | [CSH-052 clause/condition map](host-utility-evidence.md#u-037) | Open residual: [CSH-071](tickets/CSH-071-host-permissions-identities.md) (retained CSH-064 evidence). |
| [U-038](posix-utilities.md#u-038) | [CSH-052 clause/condition map](host-utility-evidence.md#u-038) | Open residual: [CSH-075](tickets/CSH-075-host-execution-processes.md) (retained CSH-064 evidence). |
| [U-039](posix-utilities.md#u-039) | [CSH-052 clause/condition map](host-utility-evidence.md#u-039) | Open residual: [CSH-075](tickets/CSH-075-host-execution-processes.md) (retained CSH-064 evidence). |
| [U-040](posix-utilities.md#u-040) | [CSH-052 clause/condition map](host-utility-evidence.md#u-040) | Open residual: [CSH-070](tickets/CSH-070-host-formatted-output.md), [CSH-071](tickets/CSH-071-host-permissions-identities.md), [CSH-072](tickets/CSH-072-host-filesystem-paths.md), [CSH-073](tickets/CSH-073-host-text-streams.md), [CSH-074](tickets/CSH-074-host-languages-editors.md), [CSH-075](tickets/CSH-075-host-execution-processes.md), [CSH-076](tickets/CSH-076-host-locale-catalogs.md), [CSH-077](tickets/CSH-077-host-terminal-utilities.md), [CSH-078](tickets/CSH-078-host-service-utilities.md) (retained CSH-064 evidence). |
| [U-041](posix-utilities.md#u-041) | [CSH-052 clause/condition map](host-utility-evidence.md#u-041) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-001](posix-utilities.md#o-001) | [CSH-051 clause/condition map](shell-option-evidence.md#o-001) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-002](posix-utilities.md#o-002) | [CSH-051 clause/condition map](shell-option-evidence.md#o-002) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-003](posix-utilities.md#o-003) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-004](posix-utilities.md#o-004) | [CSH-051 clause/condition map](shell-option-evidence.md#o-004) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-005](posix-utilities.md#o-005) | [CSH-051 clause/condition map](shell-option-evidence.md#o-005) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-006](posix-utilities.md#o-006) | [CSH-051 clause/condition map](shell-option-evidence.md#o-006) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-007](posix-utilities.md#o-007) | [CSH-051 clause/condition map](shell-option-evidence.md#o-007) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-008](posix-utilities.md#o-008) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-009](posix-utilities.md#o-009) | [CSH-051 clause/condition map](shell-option-evidence.md#o-009) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-010](posix-utilities.md#o-010) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-011](posix-utilities.md#o-011) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-012](posix-utilities.md#o-012) | [CSH-051 clause/condition map](shell-option-evidence.md#o-012) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-013](posix-utilities.md#o-013) | [CSH-051 clause/condition map](shell-option-evidence.md#o-013) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-014](posix-utilities.md#o-014) | [CSH-051 clause/condition map](shell-option-evidence.md#o-014) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-015](posix-utilities.md#o-015) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-016](posix-utilities.md#o-016) | [CSH-051 clause/condition map](shell-option-evidence.md#o-016) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-017](posix-utilities.md#o-017) | [CSH-051 clause/condition map](shell-option-evidence.md#o-017) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-018](posix-utilities.md#o-018) | [CSH-051 clause/condition map](shell-option-evidence.md#o-018) | Bounded mapped evidence retained; no additional defect identified in this review. |
| [O-020](posix-utilities.md#o-020) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-021](posix-utilities.md#o-021) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-022](posix-utilities.md#o-022) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-023](posix-utilities.md#o-023) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-024](posix-utilities.md#o-024) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-025](posix-utilities.md#o-025) | Matrix option/profile exclusion and source | Inapplicable for selected profile; no base portions of mixed rows excluded. |
| [O-026](posix-utilities.md#o-026) | [CSH-049 clause/condition map](execution-evidence.md#o-026) | Bounded mapped evidence retained; no additional defect identified in this review. |
