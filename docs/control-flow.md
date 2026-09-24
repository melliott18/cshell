# Control flow and shell functions

[CSH-028](tickets/CSH-028-control-flow-and-functions.md) executes the compound
payloads produced by [the parser](parser-and-ast.md#compound-and-function-payloads).
These commands work through `-c`, script files, stdin, substitutions, and pipeline
stages. They use the existing ordered redirection and assignment machinery.

## Selection, iteration, and status

- `if` evaluates conditions in order, then executes only the selected body.
  With no selected body it returns zero; otherwise it returns that body's status.
- `while` repeats while its condition succeeds; `until` repeats while it fails.
  Both return the last body's status, or zero if no body ran.
- `for name in words` expands all words once using ordinary argument expansion,
  including splitting and pathname generation, before assigning and iterating.
  An omitted `in` snapshots positional parameters, preserving empty arguments.
  An explicit empty list performs no assignment and returns zero. Assignments
  preserve attributes, honor readonly, and obey the stored allexport option.
- `case` expands its subject without splitting or pathname generation. Patterns
  retain quote protection for `fnmatch`. Patterns are evaluated left to right
  until a match; subsequent alternatives and clauses are not expanded. `;;`
  ends selection; `;&` runs the next body's commands without testing its patterns.
  The result is the last executed command's status, or zero if none ran.

Compound redirections apply before condition/list/subject expansion and remain
active for the entire construct, including all loop iterations. Every normal,
control-transfer, and failure path restores descriptors. File creation or
truncation cannot be undone by restoration.

## Functions and ownership

A reached function definition installs its name without executing its body or
expanding its redirections. Names use the parser's shell-name syntax. Special
builtin names, including not-yet-implemented special builtins, are rejected at
definition time. Function lookup precedes regular builtins and external lookup.
Functions and variables have separate namespaces. `unset -f name` removes a
function; plain `unset` and `unset -v` remove variables only.

Definitions retain immutable AST nodes. Parser cleanup releases its ownership;
state keeps definitions across complete-command reads. State clones and
checkpoints copy the function name table and share reference-counted immutable
payloads. Redefinition/removal releases the table's old reference. An active call
holds its own reference, so a body can redefine or remove itself safely. Final
release uses the existing allocation-free iterative AST destructor.

Calls replace positional parameters, leave `$0` unchanged, and restore the
caller's parameters without allocating, including after `shift`, `set`, errors,
and nested calls. Other state changes persist. Prefix assignments follow the
project's existing function policy: temporarily exported values with selective
restoration, while unrelated variable changes survive.

The call's redirections apply first; definition redirections then expand in the
call's parameter and assignment environment. Definition here-documents likewise
expand at invocation. A function returns its body's status or the status requested
by `return`. Calls are limited to 128 active function frames; that depth is
inherited by subshells and substitutions. Structural execution plans retain the
existing nesting limit of 256.

## Control transfer and project choices

Execution results carry `CSH_CONTROL_BREAK`, `CSH_CONTROL_CONTINUE`, or
`CSH_CONTROL_RETURN` separately from exit status and shell-exit requests. Lists,
AND/OR, conditionals, case commands, and singleton pipelines propagate transfer;
negation does not invert a pending transfer's status. Each loop consumes one
requested level. A function consumes its own `return`.

`break [--] [n]` and `continue [--] [n]` default to one loop, require a positive
decimal `long`, and clamp counts beyond the active loop depth to the outermost
loop. Function calls and child execution contexts establish fresh loop boundaries.
Calling a function cannot break or continue its caller's loop.

`return [--] [status]` defaults to the previous status. Like `exit`, a signed
decimal `long` is accepted and reduced to its low eight bits. Subshells inherit
whether they are executing within a function; a return in such a child ends only
that child's execution. A new function call consumes its own return normally.

Malformed/excess operands or control outside a valid context print a diagnostic
and return status 2. These special-builtin errors stop non-interactive execution;
interactive execution can resume at the next command. Behavior outside enclosing
loops/functions, non-lexical loop enclosure, and signed/out-of-range return
statuses are explicit project choices where the standard leaves latitude.
Dot-script returns and trap interaction belong to CSH-031 and CSH-035.

## Evidence

`make test-control` runs the shared runtime cases from
[`tests/control_flow_cases.py`](../tests/control_flow_cases.py) in all three input
modes, plus API and allocation-failure sweeps in
[`tests/execute_faults.c`](../tests/execute_faults.c). Those sweeps check caller
parameters, active depths, definition replacement, retained AST ownership,
descriptor counts, and allocation cleanup after each injected failure.
`make test` includes this target and the complete runtime suite. Docker and
sanitizer builds use the same tests. This evidence covers the implemented subset;
it is not a claim of full POSIX conformance.
