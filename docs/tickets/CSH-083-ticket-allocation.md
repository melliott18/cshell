# CSH-083: Prevent ticket identity collisions

- Status: review
- Type: chore
- Kind: implementation
- Parent: None
- Depends on: None
- Branch: `chore/CSH-083-ticket-allocation`
- Issue: [#176](https://github.com/melliott18/cshell/issues/176)

## Goal

Prevent concurrent branches from allocating the same sequential CSH ticket number, and audit existing issue/document identity.

## Scope

- Rename the filesystem follow-up to CSH-080 and audit main and open PR snapshots.
- Maintain a shared append-only Git reservation ledger with atomic fast-forward allocation and idempotent retries.
- Check filename, heading, issue mapping, index links and GitHub titles in CI.
- Document allocation, synchronization, failure recovery and historical evidence policy.

## Acceptance criteria

- [x] Concurrent independent clients receive distinct IDs without losing reservations.
- [x] Retrying the same issue recovers its reservation after publication failure.
- [x] Duplicate and unreserved identities fail validation.
- [x] Current tickets are audited and remaining non-identity differences are recorded separately.

## Validation

Run the registry race/failure tests, offline identity checks, and live checks against main and open PR heads. No shell-runtime behavior changes are involved.

## Implementation notes/evidence

The shared registry is active and protected against force pushes and deletion.
The first live allocation through the helper reserved this ticket as CSH-083
for issue #176 after the filesystem follow-up moved to CSH-080 (#158).

- `make test-tickets`: 17 tests pass, including a real race between independent
  Git clones, idempotent retries, lost responses and rejected pushes; offline
  identity validation passes.
- `python3 tools/tickets.py check --live --ref origin/main` plus all 10 open
  PR head refs: all 12 snapshots pass (including this worktree).
- No other current identity collision was found. Synchronized 45 closed issue
  body statuses to their merged Markdown status. Preserved two historical
  shared-branch records and historical evidence labels.
- [Audit record and scope](../evidence/csh-083/README.md).

The Ticket integrity workflow is proposed with this implementation; it becomes
available repository-wide after merge and is not yet a required main check.

## Continued verification (2026-10-08)

Closed two checker gaps found after the initial review: empty live GitHub issue
responses now fail for missing linked issues, and every `--ref` allocation
snapshot is checked for malformed data or conflicting reservations. Older refs
without a snapshot and stale snapshots that omit newer reservations remain valid.
Offline ref checks use the worktree snapshot as their authority.

- `make test-tickets`: all 24 tests and offline identity checks pass. Regression
  cases reproduced both false passes before the fixes.
- Live checks pass for the worktree, current `origin/main`, and all 13 open PR
  heads (15 snapshots), with only the two documented historical branch warnings.
- Strict Python compilation and `git diff --check` pass.
- [Retained logs, revision scope and source hashes](../evidence/csh-083/README.md#continued-verification-2026-10-08).

The ticket remains in review pending integration of PR #177.
