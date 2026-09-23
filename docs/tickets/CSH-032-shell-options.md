# CSH-032: Complete shell option behavior and interactions

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-008, CSH-009, CSH-029, CSH-031
- Branch: Assigned when work starts
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

- [ ] Option parsing, reporting, enabling, disabling, invalid operands, and `--`
  behavior are mapped to tests for invocation and runtime `set` usage.
- [ ] `errexit` and `pipefail` fixtures cover conditionals, AND/OR lists, pipelines,
  functions, negation, and substitutions with explicit expected shell status.
- [ ] `nounset`, `noclobber`, and `noglob` tests cover normal and error paths and
  demonstrate the required interaction with expansion and redirection contexts.
- [ ] Tracing and no-execution behavior have output/side-effect assertions;
  remaining inventoried options have equivalent requirement-to-test mappings.
- [ ] Option state propagates or restores correctly across execution environments.
- [ ] Evaluation and alias interactions pass integrated option tests before this
  ticket closes; job-specific option integration remains with CSH-034/035.

## Validation

Run focused option fixtures and cross-feature scripts on native and Docker builds.
Use explicit expected behavior grounded in the targeted standard, documenting
permitted choices instead of accepting a single reference shell as the oracle.

## Implementation notes/evidence

Record evidence here. This ticket owns final evaluation/alias/option integration
for CSH-010. Job-specific interactions remain CSH-011 checks; this ticket alone
does not prove the whole shell's POSIX compliance.
