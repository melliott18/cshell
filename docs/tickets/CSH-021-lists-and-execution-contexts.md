# CSH-021: Execute lists, groups, and background contexts

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-020
- Branch: Assigned when work starts
- Issue: [#22](https://github.com/melliott18/cshell/issues/22)

## Goal

Complete AST composition around pipelines with explicit current-shell, subshell,
and asynchronous execution contexts in the replacement runtime.

## Scope

- Execute sequential lists, AND/OR lists, groups, and asynchronous lists.
- Define context ownership for state, descriptors, children, and last status.
- Isolate subshell state and preserve current-shell mutations where required.
- Register background children and expose the last background identifier.
- Build on the new executor without a legacy fallback; CSH-039 independently
  owns the default-binary cutover and complete legacy deletion.

## Acceptance criteria

- [ ] Sequential and AND/OR lists run only required commands, preserving specified
  precedence, short-circuiting, and final statuses in behavioral fixtures.
- [ ] Brace-group mutations persist in the current shell, while parenthesized
  subshell mutations remain isolated; group redirections have correct lifetimes.
- [ ] Asynchronous lists return without waiting for completion, publish the
  applicable background identifier, and eventually reap their owned children.
- [ ] Nested contexts and failed redirections preserve parent state/descriptors;
  cleanup tests include background children and interrupted waits.
- [ ] All list/group behavior uses the shared replacement executor; architecture
  docs describe context ownership and remaining limitations.

## Validation

Run native and Docker fixtures for nested groups, filesystem/state effects,
short-circuiting, list statuses, and asynchronous completion under timeouts.
Use helper synchronization instead of sleep-only assertions for background
behavior and child reaping. Run the retained regression suite and sanitizer
checks against the replacement runtime, recording whether CSH-039 has already
switched the default executable. Coordinate changes to build/entry-point files
with CSH-039 if these tickets proceed in parallel.

## Implementation notes/evidence

This ticket supplies execution contexts consumed by later compound commands and
functions; their syntax and full behavior remain CSH-009. Background execution
here does not establish interactive job control. Coordinate stored background
identifiers and status fields through the CSH-022 state interface.
