# CSH-002: Contain memory and process defects in the legacy shell

- Status: backlog
- Type: fix
- Depends on: CSH-001
- Branch: Assigned when work starts

## Goal

Make the existing implementation safe to exercise while its language front end
and executor are replaced.

## Scope

- Replace unchecked lexer buffer writes with owned, bounds-checked storage and
  report allocation and input-limit failures without partial command execution.
- Verify per-command argument counts and release per-command allocations.
- Fix off-by-one command arrays and access to the nonexistent third pipe end.
- Make failed execution and redirection terminate the child; ensure `cd` does
  not fall through into external execution.
- Close unused descriptors, check system-call results, and reap owned children.
- Distinguish EOF from an empty command and end the input loop at EOF.

## Acceptance criteria

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
