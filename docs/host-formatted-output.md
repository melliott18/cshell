# Selected formatted-output contracts (CSH-070)

This is finite qualification of two **exec-accessible, repository-built providers**:
patched FreeBSD printf and the new literal echo policy. It does not qualify
stock macOS/Debian utilities or a complete POSIX system. [Evidence](evidence/csh-070/README.md)
records separate native and Linux identities and every failed attempt.
[CSH-079](tickets/CSH-079-formatted-output-residuals.md) owns each remaining
full-page contract and all six retained condition IDs.

## Selected builds and environment

`build/host-printf` builds the checked-in FreeBSD source at upstream revision
`0b8224d1cc9dc6c9778ba04a75b2c8d47e5d7481` with the existing GNU getopt,
flush-error and binary `%b` patches. CSH-070 adds catalog messages, a heap
conversion workspace, libc-formatting failure propagation, and two numeric
operand corrections. FreeBSD retains upstream implementation ownership;
repository maintainers own these adapters, and the selected libc/platform
vendors own their implementation. Nothing is linked into the cshell runtime.

`build/host-echo-literal` is a separately selected base-profile provider.
All arguments are literal, including `--`, `-n`, `-e`, `-E`, combinations and
backslashes. Arguments are separated by one space and followed by a newline.
POSIXLY_CORRECT does not change this declared policy. It is not an XSI echo
selection. The ordinary qualified PATH still selects the stock Apple/GNU echo;
the focused runner creates a private PATH containing only these two overrides.

Builds are offline from checked-in sources. `gencat` compiles independently
written French/German diagnostic catalogs in an installed `en_US.UTF-8` locale.
Catalog generation uses a temporary output renamed only on success. Native
macOS supplies gencat and the tested locales; the existing Debian Dockerfile
supplies libc tooling/locales. No host installation is performed. `NLSPATH`
points to a private catalog in the tests; absent catalogs use English fallback.
The same catalogs include both utilities' messages with distinct IDs.

Each result records the complete selected PATH, realpaths, executable and
catalog hashes, all build/test input hashes, compiler, OS/kernel, libc and
Linux package versions. The private PATH is removed at completion; the build
artifacts remain reproducible using `make test-host-formatted`.

## Whole-page section accounting

Normative sources: [printf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html),
[echo](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html),
[common defaults](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html).
The table accounts for every behavior section, without treating a finite
assertion as proof of all inputs. NAME and SYNOPSIS are covered by invocation;
application usage, examples, rationale, future directions, see-also and change
history are informative, not additional normative assertions.

| Section / contract | Assertions or individual disposition |
| --- | --- |
| DESCRIPTION, OPERANDS, STDOUT | `host_formatted_cases.py` adds 24 conversion interactions, numbered gaps/repetition/reuse, missing operands, binary precision/padding, escapes, numeric limits and literal spacing. All 20 echo cases have independent byte expectations. Existing `host_utility_cases.py`, `host_boundary_cases.py` and `host_capability_cases.py` retain all-byte, standard escapes and bounded-size witnesses. Remaining valid-format combinations belong to CSH-079 `U-035/full-format`. |
| OPTIONS and utility syntax | printf's `--` and leading-hyphen format have a strict witness. Echo treats `--` as an operand and tests the declared implementation policy for n/e/E combinations and backslashes. Arbitrary malformed printf conversions, mixed numbered/unnumbered specifications, invalid n$ indices and argument-bearing formats with no consuming specification are outside the selected defined-input subset; no portable result is asserted for unspecified input. |
| STDIN | Shared-open-description fixtures prove both utilities leave input unread, followed by cshell `read` observing the original line. |
| INPUT FILES, OUTPUT FILES | Neither page specifies input or output file operands. Output is captured through pipes/private files; no utility-created output file contract is claimed. Catalog files are separately identified environment inputs. |
| ENVIRONMENT VARIABLES | French/German exact diagnostic messages and decimal-comma output under LANG, LC_MESSAGES/LC_NUMERIC and LC_ALL precedence; LC_ALL=C overrides conflicting locale settings. UTF-8 character constants and byte-limited `%s`/`%c` have authored results. Missing catalog fallback is explicit. Additional locale encodings and catalog failures remain CSH-079 `locale-catalogs`/`other-locales`. |
| NLSPATH and optional shading | NLSPATH catalog lookup is supplied as an extension; XSI is not selected. Echo XSI escape processing and LC_CTYPE-specific transformation are not applicable to this base-profile selection. Floating conversions are voluntarily supported and tested; no optional-family promotion follows. |
| ASYNCHRONOUS EVENTS | Neither provider installs signal handlers; default behavior is retained by source review. Exhaustive delivery/interrupted-write and signal-status integration witnesses remain CSH-079 (printf `full-format`, echo full-page contract); a closed descriptor is not a signal witness. |
| STDERR, EXIT STATUS, CONSEQUENCES OF ERRORS | Success requires empty stderr and exact status/output. Failed integer/float conversion requires diagnostic, nonzero status and continued processing. Closed stdout checks diagnostic failure. Echo error catalogs are exact. Linux libc ENOMEM has zero stdout, exact diagnostic/status; source review verifies failure propagation. Other write/interruption errors remain CSH-079. |
| printf EXTENDED DESCRIPTION | Individual rows above and fixture names cover bytes, no implicit padding, octal bases, binary decoding, numbering/reuse, missing arguments, character constants and conversion continuation. Empty `%c` and missing numbered operands select the source's allowed empty/default behavior. Unknown escapes and precision-truncated `\c` are not asserted as portable results. Other ranges/combinations remain CSH-079. Echo has no additional extended description. |
| U-034 exec accessibility | Every new ordinary oracle executes the selected pathname directly, through explicit cshell `exec`, and through public command-string, script-file and stdin dispatch. Selection is an actual executable/symlink, not a shell function or builtin. |
| U-040 common defaults | Exact streams/status, preserved input, no extra files, explicit environment/locale and bounded resource effects are checked. Existing host-profile checks retain lookup/shadow/environment/operand-order and error evidence. Signal/interruption/resource cases not covered here remain individually assigned above; no whole-family U-040 claim. |

## Resource controls and independent failure oracles

`host_printf_resources.c` includes the exact adapter/vendor source and lowers
limits **after startup**. A 262146-byte format with `%s` and 262144 literal bytes
under a measured 64 KiB stack must output exactly 262145 `x` bytes. The original
VLA faults on Linux; the heap workspace passes on native macOS and Linux.
This exercises formatting stack use, not the kernel's argv startup stack.

On Linux, a measured 16 MiB address-space limit plus `%.20000000f` causes libc
formatting allocation failure. The original adapter returned success without
output; the fixed adapter requires status 1, no stdout and the recorded ENOMEM
diagnostic. This is an actual libc resource failure, distinct from the retained
local strdup/realloc test injection. Other libc allocation sites and Darwin
allocation exhaustion remain unqualified. Resource helpers are deliberately
not sanitizer-instrumented, since ASan's virtual-address requirements invalidate
this limit; ordinary provider tests are separately sanitizer-checked.

`host_echo_threshold.py` fixes argv[0], environment and stack for each search.
Single-operand searches vary payload bytes; aggregate searches vary the count
of 1024-byte operands. Two padding sizes (0 and 4096 bytes) and selected stacks
are recorded. Each success checks all literal output bytes/status/stderr.
Binary search brackets E2BIG and repeats adjacent endpoints; a different error,
crash, unstable endpoint or missing rejecting bound fails qualification.

Trials cap payload allocation at 4 MiB, file output at that cap plus 64 KiB,
CPU at three seconds and execution at five seconds, with a separate two-second
kill/reap bound. These are harness protections, not advertised utility maxima.
The measured threshold applies only to the recorded kernel, executable path,
argv layout, environment and limits. Linux selects 1 and 8 MiB stacks; Darwin
selects 8 MiB. Darwin 1 MiB near-limit execs failed to terminate despite SIGKILL;
failed records and surviving owned PIDs are retained. CSH-079 requires a
disposable OS with reset capability for further investigation.

The threshold harness regressions reject a utility that returns failure and
check that an owned slow executable is killed/reaped while an unrelated owned
control process survives. Temporary fixture directories are removed and the
result records that check. The Darwin kernel-stuck attempt is explicitly a
cleanup failure, not covered up by passing ordinary timeout regression checks.

## Continued format, policy and failure qualification

[Additional evidence](evidence/csh-070-contracts/README.md) extends the selected
contract without replacing the initial records. `make test-host-formatted-contracts`
runs ordinary format/catalog assertions and the bounded failures below while
explicitly omitting the existing stack/memory and exec-capacity searches. This
allows contract work on a host where stress configurations remain unqualified.
The complete `test-host-formatted` target includes the new cases as well.

| Contract | Added independently authored assertions |
| --- | --- |
| Format numbering and reuse | Ninth-operand selection, gaps, repeated numbered integer/base conversions, highest-consumed-operand reuse, missing numbered operands under the selected default policy. |
| Required numeric and byte formats | Sign/base and width/precision reuse, zero-precision suppression, literal octal percent, binary NUL padding/precision and stop during format reuse. The selected optional floats cover decimal/hexadecimal strtod input and locale hexadecimal radix. |
| Conversion diagnostics | Multiple invalid operands continue with accumulated values, partial integers/floats, trailing quoted Unicode characters, and the provider's declared rejection of suffixed constants. Exact output/status/diagnostics in all five invocation modes. |
| Echo policy | Repeated n/e/E combinations, embedded newline/tab/carriage return, quote/percent/backslash and empty operands remain literal, including the final newline. |
| Catalog paths and failures | `%l`, `%L`, `%N` substitution, search past a missing first entry, and fallback from absent message sets. Empty, non-catalog and directory inputs have independently declared platform policies. |
| ASYNCHRONOUS EVENTS and output failures | Default SIGPIPE and SIGXFSZ terminate with the actual signal; inherited ignores instead produce status 1 and exact diagnostics. Broken pipes have no readers before exec. A child-only 1024-byte file limit requires exactly 1024 retained `x` bytes. Printf literal, `%s` and `%b` writers and literal echo all run directly and through public replacing `exec`. |
| Local allocation failures | `CSH_PRINTF_FAIL_SITE` selects conversion-workspace realloc, numeric-format realloc or `%b` strdup independently. Every failure has a nonmatching-site success control and exact diagnostic/status in direct and replacing-exec modes. This does not substitute for the separately retained Linux libc exhaustion probe. |

Apple's [published catalog loader](https://github.com/apple-oss-distributions/Libc/blob/Libc-1592.100.35/nls/FreeBSD/msgcat.c)
emits a corruption diagnostic before returning an error for malformed inputs;
the declared Darwin oracle includes it. The glibc policy expects silent loader
fallback. Neither policy is inferred from observed output during a test.
The initial quiet-fallback oracle failed on Darwin and remains in the evidence.
These are selected libc policies, not a portable diagnostic-wording requirement.

The I/O supervisor accepts only the selected non-forking C providers and the
shell's process-replacing exec path. It owns/reaps one PID, caps CPU/output/file
size, and enforces a five-second execution plus two-second reap deadline.
Leak scanning and symbolizer subprocesses are disabled for this supervisor,
including instrumented CI builds; ASan/UBSan error detection remains enabled.
Separate instrumented-provider I/O probes pass all 40 assertions.
Dedicated regressions check timeout reaping, preservation of an unrelated child,
and setup failures that must not be mistaken for signal termination. It does
not replace the general smoke/PTY descendant supervisor or qualify its retained
native cleanup failures. CSH-079 still owns other signals, interrupted writes,
Darwin libc allocation controls, broader locales and unsafe exec configurations.
