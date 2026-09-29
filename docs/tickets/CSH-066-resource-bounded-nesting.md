# CSH-066: Remove arbitrary shell nesting limits

- Status: done
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-005, CSH-028, CSH-041
- Branch: `fix/CSH-066-resource-bounded-nesting`
- Issue: [#135](https://github.com/melliott18/cshell/issues/135)

## Goal

Replace fixed recursive-depth rejection with storage and execution bounded by actual available resources.

## Scope

- XCU §2.9 and sh INPUT FILES/STDIN; SH-006, GRAM-002/004/005, EXP-001/005/006 and EXEC-014.
- Audit parser 128, executor tree 256, evaluation/function/substitution 128, expansion 128 and arithmetic 128 guards. The brace probe directly demonstrates only parser/tree rejection; other guards are source-inspected limitations.
- Prefer iterative owned work structures where needed. Raising a constant alone does not satisfy the contract.

## Acceptance criteria

- [x] Record all fixed guards and replace arbitrary limits with safe resource-aware handling, including partial-tree destruction and interruption.
- [x] Valid brace depths 127/128/129 execute in all input modes; add deeper and mixed construct witnesses without claiming finite samples prove unlimited capacity.
- [x] Allocation/resource exhaustion fails diagnostically without stack overflow, leaks, partial unintended effects or leaked children.
- [x] Update guard fixtures so known rejection is no longer presented as the required success oracle; run parser, expansion, execution, runtime and sanitizer checks.

## Validation

The original source-qualified probe retains six failures at depths 128/129 and
three passing depth-127 controls. Current `tests/invocation.py` requires all nine
brace cases to succeed. `make test-nesting` adds 42 finite runtime/resource
witnesses and API cleanup/rollback checks; no finite sample is an unlimited
capacity claim.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.


### Implementation

See the [complete guard audit and resource contract](../nesting-resources.md).
Execution-plan preparation/destruction now walk owned parent links iteratively,
including partial allocations and ancestor-cycle rejection. Existing iterative
AST and lexer destruction remain in place. Heap-backed expansion validation and
lexer arithmetic checkpoints no longer impose depth counts. Remaining recursive
paths check native stack bounds and the current soft `RLIMIT_STACK`, reserving
64 KiB for bounded calls, diagnostics, signals and cleanup. Fork descendants
retain the accounting for already-active native frames.

Arithmetic and expansion expose distinct resource results and preserve their
state rollback; arithmetic probe exhaustion cannot trigger substitution replay.
Runtime resource diagnostics use status 1. Tests cover reduced stack capacity,
a 12,000-level API plan, descriptor exhaustion, lazy effects, interrupted partial
parsing, and deep allocation failures alongside existing child/descriptor cleanup.
The test runner permits enough descriptors for successful dot recursion and its
parser JSON decoder permits the additional containers in deeper successful ASTs.

### Validation record (2026-09-29)

[Retained results and source/binary hashes](../evidence/csh-066/README.md).

| Environment | Checks | Result |
| --- | --- | --- |
| macOS 14.8.7 arm64, Apple Clang 15.0.0, Python 3.12.2 | `make -j4 test-parser test-expand test-execute test-runtime test-invocation test-control`, then `make test-evaluation test-substitution test-pipeline test-context test-options` | Pass; 238 parser checks, 3,905 runtime, 210 control, 304 evaluation and 1,101 option cases; allocation/field/child ownership suites passed |
| Debian bookworm Linux aarch64, GCC 12.2.0, Python 3.11.2 (Docker) | `make -j2 test-nesting test-parser test-expand test-execute test-runtime test-invocation test-control test-context test-substitution test-pipeline` | Pass; 42 nesting/resource witnesses, 238 parser checks and 3,905 runtime cases, plus focused API/control/ownership suites |
| Native ASan/UBSan | Same broad parser/expansion/execution/runtime/invocation/control/context/substitution/pipeline checks, plus `test-nesting` | Pass with `halt_on_error=1`, `detect_leaks=0`, `MallocNanoZone=0`; no sanitizer report |
| Final thread-local cache change, native | Optimized `make -j4 test-nesting test-context`; ASan/UBSan resource fixture and `tests/nesting.py` with the final stack object | Pass, including successive custom thread stacks and all 42 public resource witnesses |
| Final thread-local cache change, Linux | Optimized `make -j2 test-nesting`; clean ASan/UBSan/LSan `make -j2 test-nesting test-parser test-expand test-execute test-context` | Pass with `detect_leaks=1`; no sanitizer/leak report |

Sanitizer flags: `CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g
-O1 -fsanitize=address,undefined -fno-omit-frame-pointer'` and
`LDFLAGS='-fsanitize=address,undefined'`. Broad runs preceded the final change to
thread-local caching; the final-source repeats above verify that change. A
pre-cache-change broad Linux sanitizer run was stopped without a reported
failure in favor of the final-source focused sanitizer run; it is not counted
as a completed suite.

Two existing unequal-identity invocation cases require Linux root and were
skipped in unprivileged runs. Complete `make test`, PTY and unrelated host
qualification suites were not run. Changed Markdown links and `git diff --check`
pass. The optimized executable is retained in the implementation worktree.
