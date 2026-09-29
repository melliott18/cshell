# Nesting and available resources

CSH-066 removes fixed nesting-count rejection. Valid commands at the former
127/128/129 brace boundary execute through `-c`, script files and stdin.
Recursive parser, expansion and execution paths can still exhaust the native
stack, just as owned syntax/checkpoint/plan storage can exhaust memory, sourced
files can exhaust descriptors, and substitutions can exhaust process resources.
The shell reports these failures instead of relying on a stack-overflow signal.

## Guard inventory and replacement

| Former guard | Replacement |
| --- | --- |
| Parser compound/function body and command substitution: 128 contexts | Check remaining native stack bytes before recursive grammar entry |
| Executor structural plan: 256 nodes along a path | Iterative preorder preparation with parent links/cursors; iterative allocation-free destruction, including partial child arrays; ancestor cycle detection |
| `eval`, dot and `command` wrappers: 128 calls | Check native stack at recursive evaluation/dispatch entry; retained source descriptors remain resource bounded |
| Function calls: 128 active frames | Check native stack; keep semantic function-depth bookkeeping and parameter restoration |
| Command substitutions: inherited 128 counter | Check native stack before pipe/fork; descendants inherit already-consumed stack space; existing owned-child cancellation/reaping remains |
| Expansion evaluation: 128 calls | Check native stack and return `CSH_EXPAND_RESOURCE`; state and intermediate output roll back |
| Expansion structural validation: 128 fragments along a path | Existing heap-backed fragment stack grows with the word; remove the redundant count guard |
| Arithmetic Pratt parser: 128 levels | Check native stack and return `CSH_ARITH_RESOURCE`; preserve scalar/state on failure |
| Lexer arithmetic checkpoints: 128 across command frames | Existing owned heap checkpoints and overflow checks bound storage; no count guard |

AST, lexer-child and arithmetic-checkpoint destruction were already iterative.
Those paths remain allocation-free with respect to traversal. Other limits such
as pathname components, job-status retention and signal numbers are outside
this shell-nesting ticket; they are not reclassified as nesting limits.

## Native stack contract

`src/stack.c` measures stack bounds using the current thread's pthread APIs:
[`pthread_getattr_np`](https://man7.org/linux/man-pages/man3/pthread_getattr_np.3.html) /
`pthread_attr_getstack` on Linux, and
[`pthread_get_stackaddr_np` / `pthread_get_stacksize_np`](https://github.com/apple-oss-distributions/libpthread/blob/main/include/pthread/pthread.h)
on macOS. The current
soft `RLIMIT_STACK` also constrains the calculation. Bounds are cached in thread-local storage and refresh when the soft limit
changes; reused thread IDs cannot retain another thread's stack bounds. The shell does not raise the user's resource
limits or create worker threads. Like the other stateful module APIs, access
must be serialized. Supported builds use Clang or GCC on Linux/macOS with
`-pthread`; another platform needs its own bounds implementation.

A native frame address is compared against those bounds. An ordinary local
variable's address is insufficient under ASan because it can live on a separate
fake stack. The helper reserves 64 KiB of byte headroom for bounded calls between
checks, libc diagnostics, signal delivery and error unwinding. This is not a
per-language-depth quota: attainable depth changes with actual stack limits,
compiler frame sizes, instrumentation and already active calls. There are no
input-sized automatic arrays on these recursive paths. Plan/AST/lexer cleanup
uses iterative ownership walks rather than consuming one C frame per node.

Resource errors from either arithmetic grammar probe propagate as errors;
they must never turn valid-but-resource-exhausted arithmetic into command
substitution replay. Expansion/arithmetic API callers get distinct resource
results; runtime resource failures use status 1 and a diagnostic. Parser errors
publish no partial AST. Execution-plan preparation finishes before any command
runs. Reached commands keep their ordinary effects: shell execution is not a
transaction across earlier commands, redirections or completed substitutions.
Word/arithmetic state checkpoints and reversible descriptor scopes retain their
existing rollback/cleanup contracts.

## Finite witnesses

`make test-invocation` requires successful brace depths 127/128/129 in every
input mode. `make test-nesting` adds 512 braces, 192 mixed compounds, 512 parameter
expansions, 1,024 arithmetic parentheses, 256 arithmetic checkpoints/unary
operators/command wrappers, 160 function/eval/dot calls and 129 command
substitutions, with exact output/status assertions. Lazy parameter operands
must leave their command substitution's `effect` file absent.

Controlled 256 KiB versus 8 MiB stack runs check that the same 192-brace input
fails before its file effect with the smaller resource budget and succeeds with
the larger one. API tests verify a 12,000-level plan under a 256 KiB stack,
iterative cleanup, runtime exhaustion for API-supplied trees, arithmetic and
word-state rollback, stack-limit refresh, successive thread stacks, and interrupted partial parsing beyond
128 contexts. Deep parser/plan allocation-fault samples complement the existing
complete allocation sweeps, descriptor restoration and child-cleanup tests.
These finite samples and platform runs do not prove unlimited capacity or full
POSIX conformance. Commands and results are recorded in the
[ticket](tickets/CSH-066-resource-bounded-nesting.md).
