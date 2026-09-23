# CSH-015: Contain legacy child and pipe failures

- Status: ready
- Type: fix
- Kind: implementation
- Parent: CSH-002
- Depends on: CSH-001
- Branch: Assigned when work starts
- Issue: [#16](https://github.com/melliott18/cshell/issues/16)

## Goal

Make the retained legacy execution paths terminate predictably and release their
children and descriptors before the AST executor replaces them.

## Scope

- Correct command-array sizing and invalid accesses to pipe descriptors.
- Make child exec/redirection failures exit the child rather than return to input.
- Prevent `cd` from falling through into external-command execution.
- Check fork, pipe, wait, and redirection results; close unused descriptors.
- Keep scanner/input storage in CSH-014 and coordinate the main-loop interface.

## Acceptance criteria

- [ ] Missing commands and failed redirections cannot spawn a second input loop;
  a following command runs once in bounded regression fixtures.
- [ ] Two-command pipelines transfer output larger than pipe capacity, complete
  within a timeout, and reap both owned children.
- [ ] Partial fork/pipe/redirection failures release acquired descriptors and
  reap existing children; child failures terminate through a child-only path.
- [ ] Successful and failing `cd` cases execute only the builtin, with no attempt
  to launch an external command of the same name.
- [ ] Sanitizer fixtures show no command-array or pipe-index invalid accesses;
  unsupported legacy operator spellings are rejected safely or documented.

## Validation

Run `make test` and `make docker-test` and focused ASan/UBSan execution fixtures.
Use bounded tests with high-volume producers, failed executable lookup, failed
redirection, and deterministic system-call failure injection where supported.
Inspect owned-child reaping and descriptor counts using test hooks or platform
facilities rather than inferring cleanup from a short sleep.

## Implementation notes/evidence

The existing executor indexes `pipefd[2]` and undersizes command arrays. This
ticket contains those defects without adding a new language implementation.
Coordinate any `src/main.c` edits with CSH-014 so one layer owns each allocation.
New status and invocation behavior is integrated in CSH-018.
