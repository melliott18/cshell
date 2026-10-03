# CSH-079 formatted-output environment qualification

This extends [CSH-070](../csh-070/README.md) and its
[continued contracts](../csh-070-contracts/README.md). The selected providers
remain patched FreeBSD printf and repository literal echo. No stock utility,
whole utility page, or POSIX system is newly qualified. CSH-079 stays open for
its individually identified unavailable environments.

## New independent assertions

`tests/host_formatted_environments.py` adds nine conversion/range scenarios,
three EUC-JP scenarios and one permission-denied catalog scenario. Each runs
directly and through cshell's replacing exec, command string, script file and
stdin. Expected bytes, status and diagnostics are authored independently of
provider output. Raw EUC-JP bytes survive every invocation path without a
UTF-8 transcode. No reference shell supplies an oracle.

The numeric cases cover ties-to-even on exactly representable binary inputs,
negative zero, precision wider than width, both quoted character constant
forms, numbered precision/reuse, standard binary escapes, signed over/underflow
and unsigned overflow with continued output. Optional floating behavior is a
selected libc policy. Integer limits apply to the recorded 64-bit intmax_t
providers, not every C data model.

EUC-JP bytes A4 A2 represent HIRAGANA LETTER A. Glibc's wide character value
is Unicode U+3042 (12354); Darwin's EUC implementation packs bytes, then applies
the locale mask/bits, yielding 0xA4A2 (42146). These are separate declared
policies, not a demand that every codeset use Unicode. Apple's
[EUC decoder](https://github.com/apple-oss-distributions/Libc/blob/Libc-1592.100.35/locale/FreeBSD/euc.c)
constructs the value by shifting and masking; the installed native LC_CTYPE
configuration is `1 0x0000 2 0x8080 2 0x0080 3 0x8000 0x8080`.
[Source and installed-definition hashes](source-provenance.json) retain the
reviewed identities. Locale availability is checked independently before
running cases. An unavailable definition remains unqualified.

The catalog fixture chmods only its private file to mode 000 and first requires
an independent open to fail with EACCES. If the test identity bypasses this
permission, that capability is explicitly unqualified. A supplied denial must
produce the exact English fallback, continued output and status 1. Earlier
French/German and malformed/search-path witnesses retain their own scopes.

### Interrupted output and libc API failures

`tests/host_formatted_interrupt.c` includes the production provider sources.
It creates a private pipe, fills it nonblocking until even a one-byte write
fails with EAGAIN, restores blocking mode and makes stdout unbuffered. The read
end remains open. A repeating timer delivers SIGALRM while actual libc output
is blocked. The caught handler has no SA_RESTART and only increments a
sig_atomic_t counter. The expected result is status 1, exact EINTR diagnostic,
a stream error, at least one delivered signal, and no utility bytes added to
the original pipe contents. The helper drains and verifies every prefill byte.
This is actual interrupted I/O, not an injected write return.

Printf literal, `%s`, `%b` and literal echo each run a normal-output control,
a caught-signal experiment and default SIGALRM termination, directly and via
replacing exec: 24 assertions. The source-including helper is identified
separately from ordinary provider binaries. Installing a caught handler is
experimental instrumentation; neither production utility installs one. Default
termination requires the actual negative signal status and a completed pipe
setup marker. A timeout or setup failure cannot pass as signal termination.
Partial transfers and SA_RESTART behavior are not covered by a full pipe.

Ten more assertions inject ENOMEM, EINTR, EOVERFLOW and a negative return with
zero errno at the vprintf API boundary, plus success controls, in both modes.
They require exact adapter diagnostics/status with no stdout, including EIO
fallback for zero errno. These validate propagation when ferror is clear;
**they do not establish an allocation failure inside Darwin libc**. Existing
Linux RLIMIT_AS and local realloc/strdup-site failures remain distinct evidence.

The one-PID supervisor owns only non-forking helpers/providers and replacing
exec, with five-second execution and two-second kill/reap deadlines. Every new
probe requires successful reap and a subsequent signal-0 ESRCH observation.
CPU, core and file-size bounds remain enabled. ASan/UBSan subprocess helpers
are disabled while memory/UB detection remains enabled. The general smoke/PTY
supervisor continues to own arbitrary shell descendants.

### Exec limits and historical cleanup

`threshold()` now rejects Darwin stacks below 8 MiB before fork. A regression
mocks the launcher and proves no launch occurred. Low-stack opt-in also requires GitHub-hosted macOS runner identity; the
disposable diagnostic is never enabled by the ordinary runner. Safe threshold
trials now retain PID, reap and disappearance evidence for every success.
Timeout regressions still require disappearance and unrelated-child survival.

The seven PIDs in the original native low-stack record remain **historically
unreaped**, not retroactively cleaned up. CSH-079 does not signal old numeric
PIDs, which may have been reused. Their record identifies Darwin 23.6.0 arm64,
the selected executable, 1 MiB child stacks and UEs states after SIGKILL. It
establishes a kernel/exec/cleanup observation, not its cause. The unsafe configuration was not repeated on the personal host. A dedicated
GitHub-hosted macOS diagnostic supplies an ephemeral OS; its separately
recorded result applies only to that runner kernel/architecture, and does not
establish a repair of the original kernel. The guard is a containment measure,
not a repair or completion of the required disposable-OS investigation.

Prior ps-inventory, runtime and PTY failures and the unavailable Docker attempt
remain in CSH-070 evidence. Current passing checks cannot erase them or prove
a common cause. The current main branch includes later CSH-057 cleanup work;
its independently documented scope does not by itself diagnose CSH-070.

The threshold supervisor now forks before exec and owns the child PID before
lowering its stack. Popen can wait internally for exec to finish before returning
its PID, so a later wait(timeout) alone did not bound the historical exec path.
The parent now polls waitpid against a monotonic deadline covering setup and
exec too, then applies the separate kill/reap deadline. A private close-on-exec
file distinguishes setup errors, exec E2BIG, provider failure and timeout.
This supervision repair does not claim it can kill a kernel-stuck process.

`tests/host_formatted_disposable.py` checkpoints runner/kernel/provider identity
before each configuration. It checks the 8 MiB controls before trying 1 MiB,
with both argv layouts and padding sizes. A failure stops further experiments;
retained PIDs/reap/disappearance are uploaded even if the job fails. The
15-minute job budget and ephemeral runner teardown provide the outer boundary.
No personal-host environment variables should be fabricated to run this probe.

## Individual dispositions and next capabilities

All open rows retain CSH-079 as evidence owner; selected utility/libc/platform
vendors retain implementation ownership. Historical CSH-064 IDs/reasons are
unchanged in the current ownership manifest.

| Condition | Supplied scope | Explicit remaining disposition |
| --- | --- | --- |
| U-035/locale-catalogs | Existing searches/malformed catalogs plus mode-000 denial/fallback | Other encodings, translated-message byte encodings, installation layouts and credential policies need authored fixtures; open. |
| U-035/other-locales | Existing UTF-8 plus EUC-JP character/byte and literal-policy assertions | Stateful encodings and additional locale families need independent mappings and installed definitions; open. |
| U-035/format-allocation-limits | Existing Linux libc exhaustion and local allocation faults; new vprintf error-return controls on both systems | Actual Darwin libc internal allocator exhaustion and other allocation sites need scoped allocator instrumentation; API-return injection does not satisfy this; open. |
| U-035/full-format | New precision/range/rounding plus actual full-pipe EINTR/default SIGALRM | Partial writes, SA_RESTART, remaining signals and conversion combinations need separate authored controls; open. |
| U-036/alternative-policies | Literal provider EUC-JP and caught/default SIGALRM | No additional stock/XSI provider policy selected. Qualifying another build requires its own declared expectations and identity; open. |
| U-036/argument-limits | Existing safe layouts rechecked with PID disappearance; Darwin low-stack exclusion enforced | Disposable Darwin OS/reset capability required for historical kernel-stuck reproduction, other stacks/layouts/kernels and disappearance after timeout; open. |
| Conditional U-035/allocation-injection | Normal targets supply the local allocation and API-result helpers | Runs that omit those helpers remain unqualified; sanitizer ordinary-provider results alone do not supply them. |
| Retained ps/PTY cleanup observations | Current regression/integration results recorded separately | Original cause and historical descendant disappearance remain unknown; need owned-process recurrence traces in a disposable environment. |

## Validation records

Results are recorded below after validation. JSON retains exact assertion IDs,
invocations, output hex/digests, environment, provider/helper/catalog hashes,
build/test input manifests and before/after input-stability checks. Missing
capabilities, failed assertions and setup failures are reported separately.

The first native contract attempt had 683 passes and five failures, all the
EUC-JP numeric-character case across five modes. The original oracle incorrectly
assumed Unicode on Darwin. The independently reviewed Apple decoder and locale
configuration above justify the corrected platform policy; no provider code
was changed. The failed JSON/log remain retained. The first inventory/full
attempt stopped before utility tests because an ownership regression still
expected CSH-070; its assertion now expects the deliberate CSH-079 update.
