# CSH-031: Complete evaluation, lookup, and remaining utility builtins

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-008, CSH-009, CSH-029, CSH-030
- Branch: `feature/CSH-031-evaluation-builtins`
- Issue: [#32](https://github.com/melliott18/cshell/issues/32)

## Goal

Complete command evaluation and the remaining non-option utility inventory using
the parser, expansion, execution, and shell-state interfaces.

## Scope

- Implement `.`, `eval`, `exec`, `command`, command-search behavior, and `type`
  where selected by the profile; finish inventoried non-option utilities.
- Own `read`, `getopts`, `hash`, `umask`, and `times`, plus any unallocated required
  utility identified by CSH-029; record host utility dependencies explicitly.
- Verify state/special-builtin interactions across full scripts and integrate
  the alias handlers from CSH-030.

## Acceptance criteria

- [x] Sourced/evaluated text executes in the required environment with correct
  input ownership, positional parameters, control transfer, and error behavior.
- [x] `exec` and lookup utilities obey command search, descriptor, and failure
  rules, including specified special-builtin precedence and assignment lifetime.
- [x] Every assigned utility has operand, normal, error, and status fixtures;
  `read` covers EOF/backslashes/IFS, and `getopts` covers state and option errors.
- [x] Each applicable remaining inventory entry has implementation and passing
  evidence, or a named owning ticket for the separate options/aliases/jobs scope.
- [x] Special-builtin failures and nested evaluation follow interactive versus
  non-interactive rules without losing shell-state or descriptor ownership.
- [x] Dot/eval and command lookup have passing cross-feature alias fixtures;
  these checks are complete before this ticket closes.

## Validation

Run table-driven native and Docker scripts per utility plus nested dot/eval,
lookup, redirection, and assignment cases. Record expected stdout, stderr, status,
and state effects; review standard requirements when reference shells disagree.

## Implementation notes/evidence

The implementation is in `src/execute.c`, `src/utility.c`, and shell state,
with ownership contracts and profile choices in
[Evaluation builtins](../evaluation-builtins.md).

- Dot/eval use the complete-command parser in the current environment, restore
  temporary dot arguments, honor return/loop/exit transfers, and distinguish an
  evaluated command's nonzero result from a special-builtin error.
- Runtime, nested evaluation, and backquotes share state-owned aliases;
  substitutions and subshells isolate mutation. Function definitions retain the
  aliases applied at parse time.
- `command` suppresses functions and immediate special-builtin properties,
  preserves declaration expansion, obtains `-p` search from `_CS_PATH`, and
  dispatches external targets through the existing job manager. Lookup reports
  absolute paths; hash caching invalidates on PATH changes and directory changes.
- Exec replaces the calling PID with exported prefix assignments, or commits
  descriptors without a command. Failure restores interactive signal actions.
  Nested parser/job descriptors are relocated away from all enclosing and
  expanded descriptor operands; outer redirections still restore normally.
- Read/getopts cover state, EOF, backslashes, IFS, Issue 8 delimiters, option
  cursors/reset, diagnostics and error statuses. Umask, times and the previously
  inventoried base ulimit resources are internal; type and CPU-time limits are
  supported extensions without selecting full XSI.
- Host utilities and remaining options, traps, job semantics, locale startup,
  and profile audits retain their named owners in the utility inventory.
  CSH-032 owns subsequent option interactions; CSH-035 owns signal/trap policy.

The existing state allocation fixture caught a borrowed-name lifetime bug in
PATH/OPTIND invalidation under ASan; invalidation now uses the variable's owned
name. The existing private-descriptor PTY fixture also verifies that nested
parser and job-manager relocations cannot expose each other's descriptors.

## Validation record (2026-09-24)

- Separate worktree from `main` at `ee10314`, branch
  `feature/CSH-031-evaluation-builtins`.
- Merged by [PR #70](https://github.com/melliott18/cshell/pull/70) as
  `d7f1ba9`; [issue #32](https://github.com/melliott18/cshell/issues/32) closed.
- Native macOS arm64, Apple Clang 15: `make -j4 test test-pty` passed during
  implementation. The final full ASan/UBSan run below passed all module/API and
  allocation-failure suites, 979 runtime fixtures (including 304 evaluation
  cases), 15 runtime PTY cases, 12 job PTY cases and the job-failure PTY fixture.
- Local Linux Docker: full native test/PTY targets passed during implementation;
  the final `make test-evaluation test-runtime-pty` passed 304 + 15 cases.
- [Ubuntu/GCC PR CI](https://github.com/melliott18/cshell/actions/runs/36033620095/job/107748206011)
  and [Docker PR CI](https://github.com/melliott18/cshell/actions/runs/36033620095/job/107748205709)
  passed the full native, PTY, harness, and ASan/UBSan suites on implementation
  commit `cc3d2f1`. Both hosted workflows on the documentation-only evidence
  update passed on Ubuntu, macOS, and Docker after retrying transient macOS
  sanitizer timeouts in unchanged context/job fixtures.
- An earlier push-triggered run timed out in existing Ubuntu stop/resume and
  macOS job API fixtures. The separate PR Linux runs and the full local macOS
  sanitizer run passed those checks without weakening their expectations.
- `git diff --check` passed. The original `main` checkout remains unchanged.

Final native sanitizer command:

```sh
make -j4 test test-pty \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Full shell options, traps/signals, and locale/profile conformance retain their
existing owners and do not block this completed ticket.
