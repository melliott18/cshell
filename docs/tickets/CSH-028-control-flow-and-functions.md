# CSH-028: Execute control flow and shell functions

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-009
- Depends on: CSH-027, CSH-006, CSH-007, CSH-008
- Branch: feature/CSH-028-control-flow-and-functions
- Issue: [#29](https://github.com/melliott18/cshell/issues/29)

## Goal

Execute compound-command AST nodes and reusable functions with correct control
transfer, variable/parameter lifetimes, redirections, and exit statuses.

## Scope

- Execute conditionals, loops, case selection, and function definitions/calls.
- Implement `break`, `continue`, and `return` as explicit control-transfer results,
  including operand validation and invalid-context behavior.
- Integrate function lookup/redefinition, positional-parameter restoration,
  compound redirections, and subshell isolation with existing module interfaces.

## Acceptance criteria

- [x] Nested compounds, zero-iteration loops, and case patterns execute with
  specified expansion behavior, command order, and resulting status.
- [x] Loop/function control handles operands and nesting levels without escaping
  unrelated execution contexts; invalid uses have tested diagnostics and statuses.
- [x] Function calls restore caller positional parameters and release replaced
  definitions while preserving the required function/variable environment.
- [x] Function and compound redirections have the required lifetime; subshell
  state changes do not escape to the parent shell.
- [x] Syntax/runtime/expansion failures unwind AST, state, and descriptor resources.

## Validation

Run native and Docker scripts combining functions, loops, lists, substitutions,
and pipelines; assert output, status, parameter restoration, and filesystem
effects. Cover failed redirections and resource cleanup with sanitizer builds.

## Implementation notes/evidence

The implementation and project choices are documented in
[Control flow and functions](../control-flow.md). The original
[CSH-009](CSH-009-compounds-and-functions.md) criteria are reviewed below.
CSH-031 and CSH-032 subsequently test
evaluation builtins and options against these control-transfer semantics.


### CSH-027 syntax handoff

The [compound payload contract](../parser-and-ast.md#compound-and-function-payloads)
and `include/cshell/ast.h` define the execution handoff: ordered condition/body
branches and optional else; distinct loop condition/body lists; for-list
`has_in` distinguishing omitted parameters from an explicit empty list; ordered
case patterns and bodies with `;;`, `;&`, or an omitted final terminator; and
function name/body ownership. Function redirections are stored on the function
node for application at invocation. Definition-time validation (including the
special-builtin name restriction), retained definition lifetimes, expansions,
control-transfer results, and execution are implemented by this ticket.

### Implementation record — 2026-09-24

- Implementation commit: `ccff0f9`.
- Review: [PR #69](https://github.com/melliott18/cshell/pull/69).

- The execution planner handles every parsed compound kind. Reached branches
  expand lazily; for lists snapshot fields/parameters; case patterns retain quote
  protection and support `;&` without expanding the next clause's patterns.
- Explicit execution-result transfers propagate through composition and unwind
  loop levels or the current function. Child contexts isolate transfers. Invalid
  operands/contexts have status-2 diagnostics; active function depth is bounded.
- State owns independently copied function-name tables with shared immutable
  payloads. Retained ASTs survive parser cleanup; active calls survive replacement
  and `unset -f`. Parameter push/pop restores callers without allocation.
- Function call redirects precede invocation-time definition redirects. Compound
  redirects enclose expansion and execution. Prefix assignments keep CSH-023's
  temporary/exported function policy and selective restoration.

### Validation record — 2026-09-24

- Native: macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2.
- Docker: Docker 24.0.6, Debian bookworm aarch64, GCC 12.2.0, Python 3.11.2.
- `make -j4 test test-pty`: passed the module/API/fault suites and 675 runtime
  cases, including 210 control-flow cases (70 scripts in three input modes).
- `make docker-test docker-test-pty`: passed all suites, including the final 12
  runtime PTY cases for prompts, recovery, and descriptor isolation.
- Native clean ASan/UBSan build with `-Werror`: `make -j4 test test-pty` passed.
  Final ownership/API checks and two new PTY cases also passed with
  `make -j4 test-control test-state test-runtime-pty` under the same sanitizers.
- `make test-harness`: all 62 native harness self-tests passed.
- Allocation sweeps cover retained definitions, replacement/removal during active
  calls, state copies, parameter push/pop, for-list storage, case expansion, and
  descriptor restoration. Every iteration checks allocation and descriptor
  counts, caller parameters, and active loop/function depths.
- Linux ASan/UBSan with `-Werror`: clean `make -j4 test-control test-runtime
  test-runtime-pty` passed all 210 control cases, allocation/API checks, 675
  runtime cases, and 12 runtime PTY cases without sanitizer reports.

### Original CSH-009 acceptance review

All six original criteria have corresponding evidence: nested selection and
expansion in the cross-mode control fixtures; nested transfer and invalid operands;
recursive calls and caller-parameter restoration; invocation and compound redirect
lifetimes; subshell/pipeline/substitution/background isolation; and parser fault
coverage plus executor allocation/redirection/expansion cleanup. The milestone
remains unclosed until CSH-028 is integrated. Evaluation builtins, shell options,
and trap interactions remain with CSH-031, CSH-032, and CSH-035.
