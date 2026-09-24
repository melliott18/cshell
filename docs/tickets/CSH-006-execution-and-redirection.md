# CSH-006: Execute syntax trees with explicit resource ownership

- Status: done
- Type: feat
- Kind: milestone
- Parent: None
- Depends on: CSH-005
- Children: CSH-019, CSH-020, CSH-021, CSH-039
- Branch: Assigned when work starts
- Issue: [#7](https://github.com/melliott18/cshell/issues/7)

## Goal

Replace ad hoc operator dispatch with one executor that owns children,
descriptors, execution environments, and command statuses.

## Scope

- Execute simple commands, arbitrary-length pipelines, lists, conditional lists,
  groups, and asynchronous lists from the AST.
- Centralize command lookup, fork/exec, wait handling, and status conversion.
- Implement ordered POSIX redirections, descriptor duplication/closure, and
  here-document input delivery; connect context-aware expansion in CSH-008.
- Define parent execution for state-changing builtins and temporary descriptor
  restoration, plus isolated environments for subshells.
- Switch the default executable to replacement modules and delete all legacy
  code/build paths in CSH-039 after bootstrap commands and pipelines pass.
  Prototype quirks and extensions are not compatibility requirements.

## Acceptance criteria

- [x] Pipeline stages run concurrently and unused descriptors are closed.
- [x] The executor tracks and reaps the children it owns without stealing another
  operation's child status.
- [x] Default pipeline/list statuses and short-circuiting follow POSIX rules;
  enabled `pipefail` option semantics are completed in CSH-010.
- [x] `2>&1 >file` and `>file 2>&1` have their distinct, specified effects.
- [x] Failed command lookup returns 127; found but unexecutable commands return
  126 where required, including the specified executable-format fallback.
- [x] Temporary builtin redirections are restored on success and failure.
- [x] Partial pipeline creation and failed redirections leave no child or
  descriptor leaks and do not return a child to the shell input loop.

## Validation

Run behavioral cases for three or more stages, high-volume pipes, missing
commands, descriptor closure, redirection order, grouping, and asynchronous
execution. Include resource-failure tests where the platform permits controlled
failure injection. Use sanitizer checks and timeouts for all hang-prone cases.

## Implementation notes/evidence

The executor should consume expanded command data through a defined interface,
allowing CSH-008 to replace any temporary literal-word adapter. Interactive
process groups and terminal ownership are completed in CSH-011.

## Completion gate

- [x] [CSH-019: Simple commands and redirections](CSH-019-simple-command-redirections.md)
  is done.
- [x] [CSH-020: Pipeline lifecycle](CSH-020-pipeline-lifecycle.md) is done.
- [x] [CSH-021: Lists and execution contexts](CSH-021-lists-and-execution-contexts.md)
  is done.
- [x] [CSH-039: Complete legacy retirement](CSH-039-legacy-retirement.md) is done.
- [x] The acceptance criteria above pass together through the new
  executor, the legacy executor is removed, and resource-ownership evidence is
  recorded here.

CSH-019, CSH-020, and CSH-021 form the execution sequence. CSH-039 joins
CSH-020 pipeline evidence with CSH-018 invocation evidence and need not wait for
CSH-021 lists/groups. CSH-019 also consumes the state-storage
API from CSH-022, which can be built independently of the parser.

All four child tickets are complete. The final public runtime passed 73 simple
execution cases, 55 pipeline cases, 60 context behavior cases, 279 cross-mode
runtime cases, and 9 PTY cases, including deterministic allocation, descriptor,
pipe, fork, wait, and child-ownership fault sweeps. Full native and Docker suites,
their ASan/UBSan variants, and both hosted workflows passed before CSH-039 merged
through pull request #61 on 2026-09-23. The legacy executor and scanner are gone.
