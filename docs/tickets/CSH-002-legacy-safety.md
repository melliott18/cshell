# CSH-002: Contain memory and process defects in the legacy shell

- Status: superseded
- Type: fix
- Kind: milestone
- Parent: None
- Depends on: CSH-001
- Children: CSH-014, CSH-015
- Branch: Assigned when work starts
- Issue: [#3](https://github.com/melliott18/cshell/issues/3)

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

Make the existing implementation safe to exercise while its language front end
and executor are replaced.

## Historical scope

- Replace unchecked lexer buffer writes with owned, bounds-checked storage and
  report allocation and input-limit failures without partial command execution.
- Verify per-command argument counts and release per-command allocations.
- Fix off-by-one command arrays and access to the nonexistent third pipe end.
- Make failed execution and redirection terminate the child; ensure `cd` does
  not fall through into external execution.
- Close unused descriptors, check system-call results, and reap owned children.
- Distinguish EOF from an empty command and end the input loop at EOF.

## Historical acceptance criteria

- [ ] Long tokens, many arguments, blank lines, and repeated commands do not
  overflow buffers, use invalid memory, or execute stale arguments.
- [ ] Unknown commands and failed redirections cannot create a second shell loop.
- [ ] Two-command pipelines terminate, transfer data, and reap both children.
- [ ] Pipe, fork, allocation, and redirection failures release acquired resources.
- [ ] EOF exits instead of repeatedly executing or prompting.
- [ ] Unsupported legacy operator spellings are documented or rejected safely;
  they are not described as POSIX behavior.

## Validation

Run focused regression cases under AddressSanitizer and UndefinedBehaviorSanitizer.
Use bounded subprocess timeouts for EOF, failed exec, and pipeline cases. Verify
that a producer exceeding pipe capacity completes with a consuming command.
Check process and descriptor cleanup without relying on timing alone.

## Implementation notes/evidence

The original lexer writes tokens into a fixed buffer without checking remaining
capacity. The original executor also indexes beyond command-array allocations,
uses `pipefd[2]`, and returns from failed child execution into the input loop.
These defects motivate this ticket; sanitizer results belong here when rerun
against the implementation under review.

CSH-001 resets the argument count on each input iteration and removes the unused
series helper. The remaining active pipeline allocation and scanner defects are
still in scope here.

## Historical completion gate

- [ ] [CSH-014: Input and memory safety](CSH-014-input-memory-safety.md) is done.
- [ ] [CSH-015: Process and pipe safety](CSH-015-process-pipe-safety.md) is done.
- [ ] The original acceptance criteria above pass together on the integrated
  code, with sanitizer and bounded process-cleanup evidence recorded here.

The children can proceed in parallel after CSH-001. Coordinate changes to the
input/execution boundary so command storage has one documented owner.
