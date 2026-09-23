# CSH-014: Make legacy input and command storage safe

- Status: superseded
- Type: fix
- Kind: implementation
- Parent: CSH-002
- Depends on: CSH-001
- Branch: Assigned when work starts
- Issue: [#15](https://github.com/melliott18/cshell/issues/15)

## Disposition

Superseded by the replacement implementation plan in CSH-038. The prototype is
only a starting reference; investing in a separate legacy rewrite is no longer
planned. This ticket is closed as **not planned**, not as implemented or safe.
The former scope and acceptance criteria below are retained as defect history.

Required safety coverage transfers to [CSH-016](CSH-016-input-and-invocation.md)
and [CSH-004](CSH-004-lexer-and-words.md) for input, EOF, and allocation ownership;
[CSH-019](CSH-019-simple-command-redirections.md) for child and descriptor cleanup;
and [CSH-020](CSH-020-pipeline-lifecycle.md) for pipeline failures and deadlocks.
[CSH-039](CSH-039-legacy-retirement.md) deletes the prototype and its build paths.
No replacement ticket depends on completing this legacy hardening work. A narrow
containment fix requires a demonstrated blocker and its own ticket.

## Historical goal

Safely accept, release, and exhaust legacy input while the replacement front end
is developed, without overflowing buffers or reusing command arguments.

## Historical scope

- Replace unchecked scanner writes with owned, bounds-checked token storage.
- Define ownership of token/argument allocations across the input-loop boundary.
- Handle allocation/input-limit errors before dispatching a partial command.
- Distinguish blank input from EOF and stop the loop when input is exhausted.
- Keep process and descriptor changes in CSH-015; agree on the shared boundary.

## Historical acceptance criteria

- [ ] Long tokens and many arguments either execute safely or produce a clear
  bounded-input diagnostic; no truncated command is dispatched.
- [ ] Repeated commands and blank lines release command storage and cannot reuse
  arguments from a previous iteration.
- [ ] Empty stdin and EOF after a command terminate within the regression timeout;
  a final line without a newline is handled without invalid memory access.
- [ ] Allocation-failure fixtures release owned storage and prevent execution of
  a partially constructed command.
- [ ] Focused scanner/input tests pass under ASan and UBSan, and the ownership
  contract and remaining language limitations are documented.

## Validation

Run `make test` and `make docker-test`, plus bounded fixtures for empty input,
large tokens, large argument counts, repeated commands, and missing final newline.
Run the same focused cases with AddressSanitizer and UndefinedBehaviorSanitizer.
Use a controlled allocator failure hook or equivalent deterministic fixture to
exercise allocation cleanup; record commands and the selected input limits.

## Implementation notes/evidence

The legacy scanner's fixed token buffer is the principal target. CSH-001 already
resets the argument count per input iteration; preserve and regress that fix.
Agree with CSH-015 on whether the input loop or executor frees command storage
before concurrent edits to `src/main.c` or their shared interface.
