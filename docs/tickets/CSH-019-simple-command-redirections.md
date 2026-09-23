# CSH-019: Execute simple commands with ordered redirections

- Status: backlog
- Type: feat
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-005, CSH-022
- Branch: Assigned when work starts
- Issue: [#20](https://github.com/melliott18/cshell/issues/20)

## Goal

Create the AST execution entry point and an explicit expanded-command contract,
with correct lookup, child ownership, and redirection restoration.

## Scope

- Execute simple-command AST nodes through a temporary literal-word adapter.
- Define owned expanded argv, assignment, and redirection inputs for CSH-008.
- Centralize lookup, exec/wait, status conversion, and executable-format fallback.
- Apply ordered file, descriptor, and here-document input redirections.
- Support builtin dispatch in the parent with saved/restored descriptors.

## Acceptance criteria

- [ ] Lookup tests distinguish command-not-found status 127 from applicable
  found-but-unexecutable status 126 and cover executable-format fallback.
- [ ] `2>&1 >file` and `>file 2>&1`, descriptor closure, and here-document input
  have distinct specified effects tested through AST/API or supported syntax.
- [ ] Parent builtin redirections restore descriptors on success and failure;
  failed external execution cannot return into the parent's input loop.
- [ ] Child ownership is explicit: waits target owned children, and fork/open/
  duplication failures release every acquired descriptor and command allocation.
- [ ] Adapter/dispatch interfaces document ownership and execution categories,
  with focused tests that permit later expansion and assignment integration.

## Validation

Run native and Docker fixtures for lookup, fallback, redirection order, closed
descriptors, here-document delivery, and builtin descriptor restoration. Exercise
failures through controlled hooks or resource limits and run focused sanitizer
checks. Use AST/API fixtures where syntax or expansion is deliberately pending.

## Implementation notes/evidence

CSH-022 supplies the state storage contract without waiting for the CSH-007
milestone. CSH-023 adds assignment lifetime rules to this dispatch boundary.
Here-document collection belongs to the front end and expansion to CSH-008;
this ticket delivers the prepared input and owns its descriptor lifecycle.
