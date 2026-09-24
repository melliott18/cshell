# CSH-029: Implement state builtins and allocate the utility inventory

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-010
- Depends on: CSH-019, CSH-022
- Branch: `feature/CSH-029-state-builtins`
- Issue: [#30](https://github.com/melliott18/cshell/issues/30)

## Goal

Provide builtins that inspect or change shell state, and make ownership of every
required builtin explicit before the remaining utility families are implemented.

## Scope

- Inventory required utilities against the selected POSIX profile; record internal
  versus host implementations and assign every remaining requirement to a ticket.
- Implement `:`, `cd`, `pwd`, `export`, `readonly`, `unset`, `shift`, and the state
  and positional-parameter portion of `set`, plus any inventoried state family.
- Allocate evaluation/lookup and remaining non-option utilities to CSH-031,
  aliases to CSH-030, options to CSH-032, control transfer to CSH-028, and
  signals/jobs to CSH-034/035; link existing `exit` work instead of duplicating it.

## Acceptance criteria

- [x] The inventory has an owner and evidence target for every applicable utility,
  including `read`, `getopts`, `hash`, `umask`, and `times` under CSH-031.
- [x] State builtins apply changes in the required environment and honor temporary
  redirection lifetimes; directory tests cover logical/physical state and errors.
- [x] Variable attributes, listing output, positional shifts, and invalid operands
  have table-driven fixtures with explicit expected state and exit status.
- [x] Special-builtin assignment persistence and failure behavior are represented
  in the interface and tested wherever current execution support permits.

## Validation

Run direct builtin/state fixtures plus available simple-command integration tests
under native and Docker builds. Record unsupported cross-feature cases as forward
checks owned by CSH-031/032, without waiving this ticket's scoped criteria.

## Implementation notes/evidence

Record inventory and validation here. Full special-builtin error interactions and
command syntax are milestone gates in [CSH-010](CSH-010-builtins-options-and-aliases.md);
module-level state coverage alone cannot close that milestone.


### Implementation (2026-09-23)

- Added the replacement [state builtin module](../state-builtins.md), owned
  variable-name snapshots, and executor dispatch for all eight scoped utilities.
- Prepared special-builtin assignments persist through later failures; execution
  exposes `special_builtin_error` for future context-dependent policy. Existing
  exit remains unchanged; syntax and general assignment lifetimes stay in CSH-023.
- Finalized internal/host allocation in the [utility inventory](../posix-utilities.md).
  The current profile is base Issue 8; conditional UP/XSI rows remain tracked,
  without a conformance claim. No extra intrinsic names are introduced.
- Forward checks: CSH-028 function removal; CSH-023 declaration-word expansion;
  CSH-031 command suppression, intrinsic/function precedence, nested evaluation
  and special-error runtime policy; CSH-032 option parsing and effects.

Validation on macOS (Apple Clang) and Docker Linux (GCC):

- `make -j4 test`: passed, including new state builtin API/behavior fixtures and
  the 69 existing execution behavior cases and failure checks.
- `make docker-test`: passed on Linux, including the new builtin target.
- `make test-pty test-harness`: passed (one prototype PTY fixture; 61 harness tests).
- Clean Clang AddressSanitizer/UndefinedBehaviorSanitizer build of
  `test-builtins test-execute test-state`: passed. State fault sweeps now cover
  variable-name snapshot allocation, cleanup and survival after state destruction.

These checks exercise replacement modules. They do not make the prototype
executable a replacement runtime or close the CSH-010 milestone.

Integrated into `main` through [pull request #57](https://github.com/melliott18/cshell/pull/57)
on 2026-09-23. Implementation commit: `de0d80f`; assignment-environment
integration commit: `1d830ed`; merge commit: `4a09ff9`. GitHub closed issue
#30 when the pull request merged. Both hosted workflows passed Ubuntu/GCC,
macOS/Clang, and Docker Linux.
