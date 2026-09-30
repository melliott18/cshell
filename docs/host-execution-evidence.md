# Host execution and process qualification (CSH-075)

CSH-075 adds strict, bounded evidence for 14 execution/process utilities. It does
**not** qualify their complete normative pages. The [section ledger](../tests/host_execution_contracts.json)
accounts for every utility-page heading, lists authored assertions, and records
remaining requirements and selected-profile exclusions. All whole-page contracts
and six retained conditions stay open under CSH-075 in the
[current ownership manifest](../tests/host_contracts.json).

## Providers and reproduction

`make test-host-execution` measures the stock system PATH. Missing providers fail
in a separate `provider` phase. `make test-host-execution-profile` supplies the
existing opt-in profile plus GNU `gtimeout` on macOS. The Docker image now installs
Debian's `time` package. No system executable or developer account is changed.
The macOS prerequisite is the same installed Homebrew coreutils used by CSH-056;
provisioning fails if `gtimeout` is absent. This provider is selected for measured
behavior, not claimed to implement all of Issue 8.

Each JSON record retains PATH, provider path/realpath/hash, OS identity, package
versions, source hashes, shell/helper hashes, invocation, streams, status and
observable effects. `/bin/sh` is inventoried separately from PATH `sh`: the
runtime's ENOEXEC branch in `src/execute.c` explicitly executes `/bin/sh`.
A no-shebang script succeeds while a shadow PATH `sh` would exit 93.

```sh
make test-host-inventory
make test-host-execution                    # stock; required missing providers fail
make test-host-execution-profile            # all authored assertions; known failures remain fatal
make test-host-profile HOST_EXECUTION_SUBSET=tests/host_execution_subset_darwin.json
# Inside the supplied Docker image:
make test-host-profile HOST_EXECUTION_SUBSET=tests/host_execution_subset_linux.json
make build/tests/host_execution_clock.so
# Disposable Linux root only; credentials apply to owned children, not accounts:
python3 tests/host_execution.py ./cshell build/tests/host_execution_helper \
  --clock-library build/tests/host_execution_clock.so --controlled-identities \
  --record build/tests/host-execution-controls.json
```

The last command runs the full assertion set, including failures. Add the explicit
Linux subset file with `--subset` to qualify only that declared subset. A subset
is a checked-in list of case IDs, never a run-time pass filter. Every omitted ID
is copied into the result. The macOS list excludes `getconf/issue8-environment`,
`timeout/foreground`, and `timeout/preserve`; Linux also excludes
`renice/relative-increment`. Whole-page obligations remain open even on success.
The historical `make test-host-profile` behavior is retained unless
`HOST_EXECUTION_SUBSET` is supplied. Its results and the new execution results are
separate files; both must pass when the extension is selected.

## Assertions and independent controls

Ordinary cases execute the selected external pathname directly and run utility
names through public cshell command-string, file and stdin modes. Named `kill`
uses cshell's intrinsic; direct mode tests the selected external implementation.
`command time` avoids the standard's unspecified unquoted-time/redirection case.
Input for an invoked utility is separate from the shell's stdin command stream.

| Utility / normative page | Authored scope and oracle |
| --- | --- |
| [env](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/env.html) | Empty/exact environments, unordered listing, inherited/replaced/removed variables, operand PATH lookup, preserved arguments, child status and 126/127 errors. A compiled helper inspects argv/environment directly. |
| [true](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/true.html), [false](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/false.html) | Empty streams, 0 or 1–125 status; no assumption that false must return 1. Aggregate exec thresholds are measured separately. |
| [getconf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/getconf.html) | ARG_MAX, PATH and NAME_MAX against Python's independent sysconf/confstr/pathconf; invalid names require failure/diagnostic. A required Issue 8 compilation-environment name is a strict failing probe. |
| [kill](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/kill.html) | Signal-number listing, signal zero and case-insensitive TERM; wait status proves delivery to an owned, ready child. Linux root controls check equal-ID success and different-ID denial with measured IDs/groups/capabilities. |
| [nice](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nice.html) | Positive increment measured by getpriority, child arguments/status and execution errors. |
| [nohup](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nohup.html) | Nonterminal SIGHUP disposition inspected using sigaction; no nohup.out side effect; arguments/status/errors. Terminal file behavior remains open. |
| [ps](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ps.html) | Explicit owned PID, `-o pid=` and no header; whitespace is validated under the page's column-format rules. Other selection/format fields remain open. |
| [renice](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/renice.html) | Owned process begins with nonzero niceness; `-n 1` must add one, measured independently with getpriority. Empty stdout is required. |
| [sh](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html) | Command/file/stdin parameters, noexec side-effect denial, syntax errors; separate ENOEXEC/PATH witness. This is not Chapter 2 qualification for the external shell. |
| [sleep](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sleep.html) | Zero, invalid duration and at least one monotonic second. Linux-only interposition checks exact total requested duration at 1, 2147483647, 2147483648 and 4294967295 seconds, permitting multiple normalized timespecs. |
| [time](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/time.html) | Child arguments/status/errors; `-p` field order, nonnegative decimal values and precision sufficient for SC_CLK_TCK. Measured timing accuracy remains open. |
| [timeout](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/timeout.html) | Zero disables limit, child status/arguments, execution errors, expiry 124, case-insensitive TERM, KILL escalation, invalid duration 125. Required `-f` and `-p` are strict probes, not replaced by GNU long options. |
| [uname](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uname.html) | Default and each required individual selector plus output ordering, against uname(2) through Python. `-a` vendor-added fields remain open. |

## Controls, bounds and remaining retained conditions

The ordinary harness allows five seconds and 65,536 output bytes per invocation,
with the existing smoke resource protections. Timeout helpers become ready before
pausing; escalation ignores TERM explicitly. Linux subreaping owns the recorded
helper PID when timeout kills its own group; cleanup waits only for that PID.
Owned signal/priority targets are killed if needed and reaped in `finally`.
Regression tests verify cleanup leaves an unrelated child alive.

Aggregate exec probes use a fixed nine-byte `LC_ALL=C` environment and 4096-byte
argument strings. Successful and E2BIG observations bracket adjacent argument
counts, with a 16-MiB allocation ceiling and three-second waits. File-backed
capture is limited by child RLIMIT_FSIZE. Kernel E2BIG is distinguished from a
utility that entered and returned an error. These are thresholds for the recorded
vector/environment shape, not universal ARG_MAX values.

The descriptor-limit helper creates a close-on-exec error pipe, forks, sets only
the child's RLIMIT_NOFILE to zero, and calls execve. The pipe distinguishes kernel
rejection from a post-exec failure. Linux's loader diagnostic and macOS's signal
termination are recorded as observations; a precise Darwin loader stage, memory
exhaustion and universal process-resource behavior are not inferred.

The Linux clock library replaces only the selected invocation's relative sleep
calls. It records requested timespecs and returns immediately. The oracle sums
normalized durations using unbounded Python integers, accepting chunked requests
but rejecting overflow, missing interposition and malformed output. It never
changes a host clock. The ordinary one-second case independently checks actual
elapsed time. These finite checks do not establish a maximum duration.

| Retained condition | Added capability; remaining open work (owner CSH-075) |
| --- | --- |
| `U-040/true-exec-resources` | Aggregate exec threshold and post-exec descriptor-limit observations; memory faults and independently identified loader stages remain open. |
| `U-040/false-exec-resources` | Same separate probes, preserving false's normal nonzero result; memory/process/loader-stage coverage remains open. |
| `U-040/kill-identities-resources` | Disposable Linux credentials with zero capabilities, owned-PID permission checks, and a child-only RLIMIT_NPROC=0 fork-rejection control. Utility-specific resource failures and other identity/group combinations remain open. |
| `U-040/env-ARG_MAX` | Successful aggregate vectors and kernel E2BIG rejection measured independently; a controlled failure of env's internal exec still needs a dedicated stage oracle. |
| `U-040/sleep-duration` | Bounded Linux virtual-duration oracle across 32-bit boundaries; native conversion/overflow, larger ranges and actual maxima remain open. |
| `U-040/sh-host-semantics` | Separate external-shell invocation and fallback identities; complete parser/resource/locale qualification remains open. |

The original immutable inventories and failure evidence are unchanged.
[Retained runs](evidence/csh-075/README.md) separate stock, supplied profiles,
strict failures, and declared subset results. Neither U-034/U-040 nor CSH-012 is
promoted by this work.

## Fallback, resource and timing extension

`make test-host-execution-edges` runs 80 additional strict assertions. The selected
profile also runs them when `HOST_EXECUTION_SUBSET` is supplied. These assertions
are separate from the original case-ID subset and are never silently filtered.
The [extension records](evidence/csh-075/edges/README.md) preserve validation and
platform availability separately from the original evidence.

- Nine shell programs run directly through the separately inventoried `/bin/sh`
  and through cshell's no-shebang fallback in command-string, file and stdin modes.
  The programs check quoted parameters, environment inheritance, function
  parameters, trailing-newline removal in substitution, a quoted here-document,
  subshell isolation, ordered redirection, EXIT traps/status, and syntax errors.
  A shadow PATH `sh` exits 93; expectations are independently authored bytes and
  effects, rather than output copied from that shell.
- External `env`, `nice`, `nohup` and `time` must pass all 256 byte values from
  stdin to an invoked helper in all four modes. Each stream, status and absence
  of `nohup.out` is checked.
- A direct execve probe reports ENOENT, EACCES or ENOEXEC. Public cshell dispatch
  must produce 127, 126, or the fallback script's authored status 29 respectively.
  These records distinguish the kernel-return stage from shell dispatch; they
  do not infer that the invoked image entered its main function.
- A helper limits only its own descriptors to 32, opens private descriptors to
  `/dev/null` until EMFILE, closes every descriptor it opened, and proves that a
  subsequent open succeeds. This qualifies descriptor exhaustion and recovery
  in that supplied process, not memory exhaustion or a production loader stage.
- `time -p` is exercised with a wall-clock wait, CPU work, and a waited-for CPU
  child. The helper records monotonic elapsed time and getrusage values. Reported
  values must lie between those inner measurements and the runner's whole-call
  elapsed/child accounting, with a two-clock-tick allowance for quantization.
  Zero or fabricated large timing values fail; matching output labels is
  insufficient. This is finite workload evidence, not universal timing accuracy.

The original timeout expiry/preserve/signal cases now also require at least the
requested one second; the escalation case requires at least 1.2 seconds. The
five-second watchdog remains a harness bound and is not a utility maximum.

All six retained conditions remain explicitly listed as unqualified in the
extension JSON, with CSH-075 retaining qualification ownership. Exact memory
failure stages, env's internal-exec E2BIG, general duration limits and complete
external-shell semantics are not inferred from these passing witnesses.


## Provider repairs and required environments

The [repair evidence](evidence/csh-075/repairs/README.md) records subsequent
qualification separately from both original runs. The execution profile now
selects BusyBox renice on Linux. An explicit source-build target supplies GNU
coreutils 9.11 timeout with a one-condition signal-preservation patch, selected
only by `HOST_PROFILE_PROVISION_FLAGS='--timeout build/host-timeout'`. See the
[build and provenance instructions](../tools/host-profile/README.md#csh-075-repaired-execution-providers).
No expectation or original failure artifact is replaced.

New cases distinguish timeout's actual SIGTERM termination from normal exit 143,
both before expiry and after a handler receives the expiry signal. Combined
`-fp` also preserves signal termination. Renice tests cover relative zero and
positive clamping. The ceiling oracle calls setpriority/getpriority in a separate
owned helper; the measured Darwin ceiling is 20 and Linux ceiling is 19.

The repaired subset excludes only the unresolved getconf Issue 8 name. This
list is an explicit scope, not a waiver or whole-page qualification. The strict
full run continues to exercise that failing assertion.

| Remaining work | Environment or manual work needed |
| --- | --- |
| getconf Issue 8 variables | A provider tied to the actual Issue 8 compilation environment, or a reviewed provider implementation. Existing macOS and Debian libc utilities lack the queried name. Do not fabricate support values. |
| true/false memory and loader stages; env internal-exec E2BIG | Deterministic fault injection with an independent entry/syscall-stage observer. A disposable Linux container can host this work; the current descriptor and aggregate-size tests do not supply that observer. |
| Additional kill credentials and resource failures | Disposable Linux root for owned children; the engine is available again. Corresponding privileged Darwin checks require a disposable macOS VM with permission to change fixture identities. |
| Sleep conversion/overflow and broader timing | Automated bounded virtual clocks/instrumented providers; no years-long waits or manual stopwatch tests. Linux interposition does not qualify Darwin. |
| Full external sh grammar/resource/locale coverage | More independently authored fixtures and controlled locales/resources on each claimed platform, with `/bin/sh` recorded separately from PATH sh. |
| nohup terminal redirection and other remaining page sections | Automated PTYs and owned process groups can cover terminal behavior. No physical terminal is required for these CSH-075 cases. |

Routine validation is automated. Additional environment access may need human
provisioning, but manual observation cannot substitute for the missing stage
oracles. All six retained conditions and all 14 whole-page contracts remain
owned by CSH-075 until their complete scopes are qualified or explicitly
transferred to another open ticket.
