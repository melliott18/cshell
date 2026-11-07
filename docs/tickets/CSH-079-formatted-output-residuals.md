# CSH-079: Qualify remaining formatted-output environments

- Status: blocked
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: `test/CSH-079-formatted-output-environments`
- Issue: [#157](https://github.com/melliott18/cshell/issues/157)
- Pull request: [#175](https://github.com/melliott18/cshell/pull/175)

## Acceptance review (2026-11-07)

Not accepted. The checked criteria cover a bounded investigation and individual dispositions. The ticket explicitly retains Darwin libc-internal allocation, other locale/format/signal partitions and the unresolved original low-stack observation; it is not ready for whole-ticket closure. See the [acceptance review](acceptance-review-2026-11-07.md) for validation and limitations.

## Goal

Own each full-page and environmental remainder after the bounded
[CSH-070](CSH-070-host-formatted-output.md) qualification. Utility/libc/platform
vendors retain implementation ownership. No stock host or entire utility page
is qualified by the selected profile's passing examples.

## Scope and concrete prerequisites

| Utility / normative page | Remaining contract and provider selection |
| --- | --- |
| [`printf`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html) | Continue the repository's patched FreeBSD provider and catalog identities in [CSH-070 evidence](../evidence/csh-070/README.md). Supply Darwin libc allocation controls, other locale/codeset expectations, default-signal and interrupted-output fixtures and further independently authored conversion combinations. |
| [`echo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html) | Continue the separate repository-built literal policy; Apple/GNU/BusyBox stock policies retain only prior scopes. Investigate the retained Darwin low-stack exec/cleanup failure in a disposable macOS environment before enabling that configuration again. |

| Retained condition | CSH-070 result; remaining prerequisite |
| --- | --- |
| `U-035/locale-catalogs` | French/German catgets catalogs supplied and strict diagnostic expectations added. Further catalog encodings, installation/search patterns and malformed/unreadable catalogs require supplied fixtures. NLSPATH is an explicitly selected extension, not a base-profile requirement. |
| `U-035/other-locales` | French/German LANG/category/LC_ALL precedence, decimal comma and UTF-8 character/byte semantics supplied. Other independently specified locales and stateful encodings remain unqualified. |
| `U-035/format-allocation-limits` | Linux 16 MiB RLIMIT_AS induces libc formatting ENOMEM; 64 KiB post-startup stack exercises a 256 KiB format. Darwin libc allocation failure and other libc allocation sites/limits require controlled instrumentation. |
| `U-035/full-format` | New flag/precision/base, numbered/binary/reuse and diagnostic-continuation combinations supplied, including repairs for quoted float and trailing character constants. Further valid combinations, precision/range edges, asynchronous/default signal and interrupted output behavior remain unqualified. |
| `U-036/alternative-policies` | Newly built literal policy has exact byte/status/catalog expectations and identity. Other vendor/build policies need separately declared oracles and identities; no universal policy claim. |
| `U-036/argument-limits` | Adjacent success/E2BIG searches for fixed single and 1024-byte aggregate operands, two environment sizes and recorded stacks. Darwin 1 MiB stack searches left stuck exec processes despite SIGKILL; reproduce only in a disposable OS with reset capability. Other layouts, stacks, environments and kernel versions remain unqualified. |

Conditional `U-035/allocation-injection` remains owned here for runs that do not
supply the test helper. Historical CSH-064 IDs/reasons stay immutable; the current
manifest links this boundary without rewriting the historical observations.

## Acceptance criteria

- [x] Account for each retained condition above separately with new supplied
  capabilities and strict assertions, or an explicit individual disposition.
- [x] Investigate the Darwin near-ARG_MAX low-stack exec failure with kernel/OS
  identity and owned-process disappearance, including timeout cleanup. Do not
  repeat it on a personal host merely to retry a failed run.
- [x] Supply independent libc/locale/conversion and signal/error oracles; keep
  setup failure, implementation failure and missing capability distinct.
- [x] Update the whole-page section map, ownership manifest and native/Linux
  evidence without promoting finite witnesses to complete POSIX conformance.

## Additional retained observation

The first native full host-profile attempt recorded a PTY cleanup inventory
timeout in `ps -axo pid=,stat=` after successful stty output/status. Its cause
is unknown; no causal connection to the low-stack exec failure is asserted.
CSH-079 owns recurrence diagnosis and actual process-disappearance evidence.
A later native runtime run also timed out in the same ps inventory operation
while checking pipe cleanup for `caught action resets in subshell` (string
mode); 3949 assertions passed and that one failed. Later passing runs do not
repair or erase either observation.

## Validation

Run `make test-host-inventory test-host-formatted test-host-profile` on separately
identified native and Docker/Linux profiles. Preserve every failed attempt and
actual cleanup outcome. Add focused controlled capabilities before repeating a
residual, and require zero allowances for each declared qualified subset.

A separate native PTY attempt passed the notification control and all 30 job
cases, then the terminal failure-injection fixture timed out without output.
Cleanup also recorded a ps-inventory timeout and EPERM killing its reported
group; a later direct ps lookup found no process with that group leader PID.
This observation is not causally attributed to the formatted-output changes.
Retain it for diagnosis alongside the other native cleanup failures.

The separately run native runtime-PTY stage also retains a failed cleanup
assertion; consult the CSH-070 evidence log for its exact diagnostic. It is
not converted to a passing result by unaffected cases.

The final Linux sanitizer run lost Docker API access before producing a result;
queued runtime/PTY integration was not observed to start. Complete these stages
and verify owned-container cleanup after the engine becomes usable. Native
ASan/UBSan and both completed host-profile suites remain separate positive
evidence; no diagnosis of the engine failure is inferred.

### Additional CSH-070 evidence

[Further contract assertions](../evidence/csh-070-contracts/README.md) now supply
catalog search/substitution and malformed-input policy witnesses; numbered
format reuse through operand nine; independently selected local allocation
failure sites; and default/ignored SIGPIPE/SIGXFSZ plus exact partial-file output
for literal/%s/%b printf and literal echo. Those finite paths are no longer
missing capabilities. Remaining signals/interruption combinations, permissions,
encodings, Darwin libc exhaustion and unsafe exec configurations stay open.
Passing hosted Linux CI at the original PR source additionally supplies runtime,
PTY and sanitizer integration; it does not repair the local Docker engine or
native cleanup failures. New assertion revisions retain separate validation.


## Implementation record

The [CSH-079 evidence and dispositions](../evidence/csh-079/README.md) add 99
strict assertions: 65 ordinary input-mode cases and 34 API-error/signal probes.
Selected native/Docker profiles pass with zero allowances. The supervisor now
owns threshold PIDs before exec so its timeout covers exec itself, and enforces
the personal-host Darwin low-stack exclusion. A separate disposable hosted
macOS diagnostic checkpoints the excluded configuration and stops on failure.

Internal Darwin libc allocation exhaustion is still unsupplied: the new
ENOMEM test injects the vprintf API return and is explicitly not an allocator
experiment. Other remaining environments have individual open dispositions.
Historical failures remain retained; this implementation does not close the
whole ticket or declare whole-page conformance.


The disposable investigation ran on GitHub-hosted Darwin 24.6.0 arm64: all
8 MiB controls passed; the first 1 MiB search produced SIGSEGV near the argument
limit, with successful reap and verified PID disappearance. Remaining low-stack
configurations were not run after this failure. The prior Darwin 23.6.0
unkillable-process observation remains unresolved; no root-cause or vendor-fix
claim follows. Timeout cleanup is independently exercised before and after
exec. Checked acceptance boxes refer to this scoped investigation and the
explicit individual dispositions, not universal qualification or ticket closure.


## Final validation

At assertion/provider revision `fd3cba6`, native formatted qualification passes
693 assertions; Docker/Linux normal and instrumented qualification each pass
698. Both complete host profiles pass 1,162 assertions with zero allowances.
Native ordinary-provider sanitizers pass 602 assertions; separately instrumented
new native helpers pass 34. Native and Linux runtime/PTY integrations pass
3,950 runtime cases and all PTY stages, with 95 harness self-tests. Hosted macOS
and Ubuntu each pass 688 contract assertions. The retained disposable Darwin
low-stack diagnostic fails with SIGSEGV and successful cleanup as described
above. Current ownership checks and the retained-evidence audit pass.

[Final identities, limitations and reproduction details](../evidence/csh-079/README.md#final-validation)
retain every failed, interrupted and successful attempt separately. All newly
owned local containers were stopped and removed. This is a reviewable bounded
implementation, with the individual unqualified contracts still open here.

## Contract continuation and acceptance blocker (2026-11-07)

Actual SA_RESTART and partial-write probes add 16 assertions. Native formatted
contracts pass 704 checks; the 40 interruption checks also pass ASan/UBSan.

The newly supplied Darwin libc allocator audit exposes a required-contract
failure: three allocations originating in `__Balloc_D2A` cause SIGSEGV when
returned ENOMEM during real `vprintf`. Direct and cshell exec paths both fail;
all six children are reaped with verified PID disappearance. This is controlled
allocator failure inside libc, not the previous API-return injection. The audit
returns nonzero and is retained as failing evidence.

Acceptance is blocked pending a repair or separately qualified replacement for
that Darwin libc path, plus the resettable Darwin 23.6 environment needed for the
historical low-stack investigation. Other locale/format remainders also remain
owned here. The [continuation evidence and review](../evidence/host-contract-continuation-2026-11-07/README.md)
provide the reproducer, traces, passing controls and remaining boundaries.
This ticket is not accepted or closed.
