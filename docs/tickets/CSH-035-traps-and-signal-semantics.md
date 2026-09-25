# CSH-035: Complete traps and shell signal semantics

- Status: review
- Type: feat
- Kind: implementation
- Parent: CSH-011
- Depends on: CSH-009, CSH-031, CSH-032, CSH-034
- Branch: `feat/CSH-035-traps-and-signal-semantics`
- Issue: [#36](https://github.com/melliott18/cshell/issues/36)

## Goal

Execute traps and handle signals at the specified points without unsafe signal
handlers or inconsistent child, terminal, and shell-state ownership.

## Scope

- Implement `trap`, pending-trap dispatch, signal inheritance/reset rules,
  interrupted input/waits, and required exit/hangup behavior.
- Preserve trap status/environment semantics across functions, evaluation,
  subshells, command substitutions, builtins, and external commands.
- Audit signal handlers for permitted operations; document selected POSIX option
  groups and implementation choices before closing the signals milestone.

## Acceptance criteria

- [x] Trap installation, listing, reset, ignored actions, invalid operands, and
  exit actions have specified output, environment, and exit-status behavior.
- [x] Pending traps execute at required safe points during command execution and
  waits, with tested ordering and status preservation where specified.
- [x] Children, subshells, and substitutions inherit/reset signals and traps as
  required; interactive interrupts leave the shell and terminal usable.
- [x] Signal handlers use only permitted operations, and rapid/coalesced signals
  cannot corrupt shell state or cause duplicate child reaping.
- [x] Exit, hangup, and interrupted input/wait policies are documented and tested
  for the selected profile, including cleanup after error paths.

## Validation

Run script cases and bounded CSH-033 PTY cases covering traps during waits,
subshells, functions, and shell exit. Exercise native and Docker builds, record
capability limits, and inspect cleanup after forced harness timeouts.

## Implementation notes/evidence

The executor now owns a trap table in each shell environment. Signal handlers
only set `sig_atomic_t` notification flags; the normal execution path copies
and runs actions at command and interrupted-input boundaries. Foreground jobs
defer parent actions until they complete, while trapped `wait` returns a
signal-derived status before dispatch. `EXIT` runs on shell shutdown, including
forked shell environments, and can replace the final status with `exit`.

Child setup resets caught actions and retains ignored dispositions; standalone
`trap` substitution can print its parent's saved actions. Launch masks protect
disposition changes across fork. A shell that ignores CHLD uses a no-op handler
until exec so the kernel does not auto-reap children before the job manager
collects them. External commands still receive ignored CHLD. Input interruption
resets the parser's partial command while ordinary input errors remain sticky.
See [Traps and signal behavior](../traps-and-signals.md) for the selected base
profile, status mapping, exit/hangup policies, and remaining XSI/UP scope.

Validation on 2026-09-25:

- Native macOS 14.8.7 (23J520), Darwin 23.6.0 arm64, libSystem.B 1345.120.2,
  Apple Clang 15.0.0, Python 3.12.2: `make test` and `make test-pty` passed.
  Debian 12 bookworm Linux Docker (engine 24.0.6, arm64, GCC 12.2.0,
  Python 3.11.2, glibc 2.36): `make docker-test` and `make docker-test-pty`
  passed. The final image was
  `sha256:34a72b2bb6e881097f88d8bd4233d1b541f3da78a38d4469aaa44ad66df219af`,
  built from `debian:bookworm-slim` at
  `sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251`.
  Both runtime suites had 1,318 strict cases across command strings, files,
  and stdin; both PTY suites had 27 cases. `make test-traps` passed three
  pre-ignored-signal cases, including inherited ignored CHLD with a working
  `wait`.
- `make test-harness` passed 64 bounded harness tests, including forced-timeout
  process and terminal cleanup. CSH-034's job ownership, rapid-completion,
  terminal-control, and interrupted-wait regressions pass in the combined runs.
- No PTY cases were skipped. Full POSIX conformance, XSI, and UP editing remain
  outside this ticket's claim; the matrix records implemented subsets and the
  remaining requirement-family audit.

The original [CSH-011](CSH-011-signals-and-job-control.md) criteria have combined
jobs/traps evidence. Its completion gate remains open until CSH-035 is merged
and the milestone prerequisites are checked.
