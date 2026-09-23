# CSH-038: Remove legacy constraints from the implementation roadmap

- Status: done
- Type: docs
- Kind: implementation
- Parent: None
- Depends on: CSH-013
- Branch: docs/CSH-038-legacy-retirement-plan
- Issue: [#40](https://github.com/melliott18/cshell/issues/40)

## Goal

Treat the prototype solely as a starting reference and make complete replacement
an explicit, testable delivery step without requiring disposable legacy repairs.

## Scope

- Supersede legacy-hardening tickets while preserving their defect records and
  assigning safety regression coverage to replacement module tickets.
- Remove legacy work from the input/front-end critical path and distinguish
  independent API work, candidate runtime integration, and default-binary cutover.
- Add CSH-039 for complete legacy deletion and update the architecture, diagrams,
  contributor workflow, ticket index, and GitHub Issues consistently.

## Acceptance criteria

- [x] No active replacement ticket depends on superseded legacy-hardening work.
- [x] Input, lexer, parser, state, and executor contracts do not require legacy
  adapters or preservation of prototype bugs, quirks, or extensions.
- [x] CSH-039 owns deletion of legacy source/header/build/runtime paths and
  temporary migration drivers, with native and Docker verification criteria.
- [x] Safety obligations retain explicit replacement owners and validation.
- [x] Documentation links and diagrams agree with an acyclic dependency graph.
- [x] GitHub Issues reflect the revised scope, statuses, and parent relationships.

## Validation

Check ticket references, parent/child consistency, dependency cycles, ready
statuses, and links. Render and inspect the changed Mermaid diagram. Verify
published issue bodies/states and the new parent/child relationship. This ticket
changes the plan only; the existing executable remains the prototype until
CSH-039 is implemented. Do not claim legacy removal based on documentation alone.

## Implementation notes/evidence

The earlier CSH-016 dependency on CSH-002, combined with command-execution
acceptance before a replacement executor existed, required investment in the
prototype. CSH-016 now delivers independent APIs, CSH-018 integrates the new
runtime, and CSH-039 switches the default executable and deletes the prototype.
Historical Git records and ticket evidence remain; no history rewrite is needed.

Validated 39 ticket records, 25 parent/child relationships, ready/superseded
status rules, an acyclic combined dependency/completion graph, 50 Markdown
files, and 254 local links. Diagram arrows and omitted transitive dependencies
were checked against ticket metadata. Rendered the changed Mermaid block with
Mermaid CLI 11.17.0/headless Chrome and inspected the result; independent review
resolved candidate/default test-target wording and cutover sequencing.
No shell code changed, so unrelated behavior tests were not rerun.

Verified all 39 GitHub issue bodies and states against the ticket files (allowing
source links to retain published revision snapshots), all 25 native parent/child
relationships, and `not_planned` closure reasons for CSH-002/014/015. CSH-039
remains open; retirement is future implementation work, not a completed result.


Integrated into `main` on 2026-09-23 as the prerequisite of
[pull request #45](https://github.com/melliott18/cshell/pull/45), merge commit
`0e527c3`. GitHub also marked [pull request #42](https://github.com/melliott18/cshell/pull/42)
merged because its `6118669` head is included. The CSH-017 harness/CI and CSH-036
conformance work already on `main` were preserved during that integration.
CSH-039 remains the owner of the future runtime retirement.
