# CSH-136: Repair shared CI blockers and verify stacked ticket integration

- Status: in-progress
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: None
- Branch: `fix/CSH-136-shared-ci`
- Issue: [#284](https://github.com/melliott18/cshell/issues/284)

## Goal

Repair shared macOS permission-oracle and Linux harness/CI failures blocking the open PR stack, preserving strict behavior and cleanup assertions. Integrate only validated ready changes and synchronize completed ticket records.

## Acceptance criteria

- [ ] Diagnose shared failures from retained CI logs and add targeted regression coverage for demonstrated causes.
- [ ] Validate corrected native and Linux CI paths without weakening assertions or masking failures.
- [ ] Merge ready PRs in dependency order and record acceptance boundaries; leave unresolved work open.
- [ ] Synchronize completed Markdown and GitHub ticket statuses.

## Validation

Focused harness tests, ticket tests and live identity checks; hosted native macOS/Linux and Docker CI on corrected source. Preserve prior failures separately from new results.

## Repair implementation

Darwin selects pinned GNU coreutils 9.7 `id` to preserve the strict process-group oracle; stock Apple account-membership output remains failing evidence. Docker separates unprivileged filesystem qualification from root-only credential probes. Service harness tests isolate package discovery from injected failures. The Docker job budgets all stages at 90 minutes without changing case limits.

Original job logs and subsequent validation are retained in [CSH-136 evidence](../evidence/csh-136/README.md).
