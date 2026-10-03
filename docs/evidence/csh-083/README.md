# CSH-083 ticket identity audit

Audit date: 2026-10-03. This is an identity/lifecycle audit, not shell-runtime
conformance evidence. [scope.json](scope.json) records the platform, Python
version, exact main/PR commits, registry tip and GitHub issue identities.

## Corrections

- Filesystem follow-up [#158](https://github.com/melliott18/cshell/issues/158)
  is CSH-080. Its title, body, ticket filename and current references were
  updated on its owning branch in commit `96b1a66`, included in
  [PR #165](https://github.com/melliott18/cshell/pull/165). The host inventory
  and ownership tests passed. Historical evidence retains its original labels.
- No other current naming collision was found across main and all 10 open
  implementation PRs. CSH-001 through CSH-082 each have one canonical issue.
  The allocator subsequently reserved CSH-083 for this governance work (#176).
- [status-sync.json](status-sync.json) records 45 closed issues whose body
  status was changed to `done`, matching their merged Markdown. Each issue
  was reread before mutation and the result was verified. Open issue states
  and in-flight review statuses were preserved.
- Closed [#171](https://github.com/melliott18/cshell/issues/171) is explicitly
  titled as a duplicate and is not another canonical allocation.
- CSH-044 and CSH-045 intentionally retain the historical branch
  `test/CSH-037-audit-follow-up`. Their ticket records identify commits
  `5421d2a` and `40583ad`, integrated through PR #85 (merge `c012aed`). These
  are historical shared-branch warnings, not current identity collisions.

## Prevention and validation

The shared data branch `chore/CSH-001-ticket-registry` was bootstrapped with
the audited 82 bindings at `32af285c66c7d66054bb078180cc14fd6e0d267a`.
Running `python3 tools/tickets.py reserve --issue 176` made its first new
reservation, CSH-083, and published the matching GitHub issue identity.
[registry-protection.json](registry-protection.json) records the applied
linear-history, no-force-push and no-deletion protections, including admins.
These protect Git history; the helper and review preserve append-only contents.

- `make test-tickets`: PASS, 17 tests and offline identity validation.
  Tests use a real bare remote and independent clones to force concurrent
  allocation, verify unique sequential IDs, recover idempotently after a lost
  response, and fail closed on denied pushes or a missing registry.
  Validation tests reject duplicate/unreserved IDs, malformed registries,
  inconsistent filenames/headings/index/issue links and wrong repository links.
- `python3 -Werror -m py_compile tools/tickets.py tests/test_ticket_registry.py`:
  PASS.
- `git diff --check`: PASS.
- Live checker: PASS for this worktree, `origin/main` and all 10 PR heads in
  [open-prs.json](open-prs.json), 12 snapshots total. Full findings and shared
  bindings are in [branch-audit.json](branch-audit.json). Only the two documented
  historical branch warnings remain in each snapshot.

The new Ticket integrity workflow uses read-only GitHub credentials and runs
the allocator tests, offline checks and live identity checks on pushes and PRs.
Its workflow and contributor/agent instructions need to merge before they apply
repository-wide. It is not yet configured as a required main-branch check.
No runtime code changed; shell behavior suites are not evidence for this task.
