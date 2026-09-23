# CSH-020: Execute pipelines with explicit child and descriptor ownership

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-019
- Branch: Assigned when work starts
- Issue: [#21](https://github.com/melliott18/cshell/issues/21)

## Goal

Compose simple execution into arbitrary-length concurrent pipelines that finish
without pipe deadlocks, leaked descriptors, or lost child statuses.

## Scope

- Create and connect pipeline stages through the CSH-019 execution interface.
- Record child ownership and each stage's status without waiting too early.
- Close unused pipe ends in parent and children, including partial setup failure.
- Implement default pipeline status and negation; reserve `pipefail` for CSH-010.
- Define the stage-status interface that later option and job-control work uses.

## Acceptance criteria

- [ ] Three-or-more-stage and high-volume pipelines run concurrently, deliver
  expected output, and terminate under bounded regression timeouts.
- [ ] Every unused descriptor is closed and owned child is reaped; an unrelated
  child fixture keeps its status available to its own owner.
- [ ] Default final-stage status and pipeline negation match specified behavior,
  including a failed earlier stage and a failed final stage.
- [ ] Injected pipe/fork/redirection failures after some stages have launched
  unwind the partial pipeline without hangs or leaked children/descriptors.
- [ ] Pipeline builtin state follows the documented execution-environment choice,
  and stage status/ownership APIs are documented for CSH-010 and CSH-011.

## Validation

Run native and Docker pipeline fixtures against the replacement runtime with
large-output, early-consumer-exit,
missing-command, builtin-stage, and status/negation fixtures. Run bounded resource
failure fixtures at each stage boundary and check ownership with deterministic
hooks or available platform facilities. Use sanitizer builds for cleanup paths.
Record the candidate target used before CSH-039 switches `make test` and
`make docker-test` to the replacement executable by default.

## Implementation notes/evidence

Pipe capacity must not determine whether a test succeeds: launch the necessary
stages before blocking on completion. Retain all stage statuses even though the
default result uses the final stage. Interactive process groups and terminal
ownership remain CSH-011 work; this ticket defines their child-lifecycle boundary.
