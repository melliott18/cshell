# Continued CSH-070 contract qualification

This record extends [initial CSH-070 evidence](../csh-070/README.md) without
rewriting its failures or claiming that local Docker/native cleanup recovered.
[The section map](../../host-formatted-output.md#continued-format-policy-and-failure-qualification)
identifies the added contracts; [CSH-079](../../tickets/CSH-079-formatted-output-residuals.md)
retains the remaining environments and failure observations.

## Assertions and controls

- Numbered reuse through operand nine, gaps/repetition, sign/base/width/precision
  interactions, binary NUL/stop/reuse, decimal/hexadecimal optional floats,
  locale radix, multiple diagnostics and continued accumulated-value output.
- Literal echo's n/e/E combinations, quote/percent/backslash, empty operands
  and embedded newline/tab/carriage-return bytes.
- NLSPATH language/full-locale/catalog-name substitutions, ordered search after
  a missing entry, absent-set fallback, and malformed catalog policies. Every
  ordinary case runs directly and through public cshell exec/string/file/stdin.
- Default and ignored SIGPIPE/SIGXFSZ through actual direct and replacing exec.
  Printf literal, `%s`, `%b` and echo each have success controls, broken pipes
  with no readers, and a child-only 1024-byte file limit. Exact signal/status,
  diagnostics and partial-file bytes are required. No reference utility supplies
  expected output. These are 40 bounded I/O assertions.
- Workspace realloc, numeric-format realloc and `%b` strdup faults selected by
  `CSH_PRINTF_FAIL_SITE`, each with a nonmatching-site success control in direct
  and replacing-exec modes: 12 assertions. Local interposition is distinguished
  from the original Linux libc RLIMIT_AS probe.
- The I/O supervisor owns one non-forking process, uses a five-second deadline,
  three-second CPU limit, zero core size and bounded file output, then enforces
  a separate two-second kill/reap deadline. Four harness regressions collectively
  check wrong utility status, timeout/reaping, unrelated-child survival and
  setup failure. This scoped supervisor does not bypass or replace general
  smoke/PTY descendant cleanup.

LeakSanitizer is disabled in these scoped runs. The I/O supervisor also disables
symbolizer/stacktrace subprocesses to preserve its one-PID ownership contract,
including when CI builds ordinary providers with sanitizers. ASan/UBSan error
detection remains enabled; these results do not qualify leak scanning.

No provider implementation changes were necessary for these added cases.
The modified C is a test-only allocation selector. `--scope contracts` explicitly
omits the original stack/memory and exec-capacity probes; the normal full profile
still includes them and these new assertions.

## Native results and exact inputs

```sh
make test-host-formatted-contracts
make test-host-formatted-sanitize
make test-host-inventory
python3 docs/evidence/csh-070-contracts/audit.py
```

| Record | Result |
| --- | --- |
| `native-contracts.json.gz` | 588 contract assertions plus one input-stability assertion pass; zero failed assertions. One explicit unsafe-Darwin capability remains unqualified; capacity probes are explicitly not run in this scope. |
| `native-sanitize.json.gz` | 536 ordinary assertions plus one input-stability assertion pass with ASan/UBSan; zero failed assertions. Normal-helper resource/I/O/allocation probes remain separate. |
| `sanitized-io.json.gz` | All 40 I/O assertions also pass with the ASan/UBSan provider binaries; every owned process is reaped. |
| `inventory.log.gz` | Exhaustive ownership and ten accounting regressions pass. |

Both final native records have the build/test input digest
`e2df54fbb2a6bbb706dd3bb9f0554f93fece5a4b28906ac218fd24ffd1cf968b`.
The runner now captures source and executable/helper/catalog hashes before
execution and checks them again afterward. A changed input fails qualification.
Actual invocations, selected policies, outputs/statuses, process cleanup,
provider/libc/compiler/platform identities and hashes remain in the JSON.
Documentation/evidence changes outside that input set do not alter the tested
sources or binaries.

## Failed oracle and vendor policy

`native-attempt-1.json.gz` retains 523 passes and 30 failures: the original oracle
expected silent fallback for empty, non-catalog and directory inputs on Darwin.
The selected Apple libc emits an additional catalog-system diagnostic. This is
permitted diagnostic output, not a required-contract provider failure.

The correction is independently grounded in Apple's
[Libc-1592.100.35 catalog loader](https://github.com/apple-oss-distributions/Libc/blob/Libc-1592.100.35/nls/FreeBSD/msgcat.c),
whose CORRUPT branch prints a diagnostic and returns an error before the utility
uses its fallback. `catalog-policy-source.json` retains the fetched source hash.
The source reference establishes the declared policy; the actual selected
binary identity is independently retained, without assuming an upstream tag
uniquely identifies an installed binary. Glibc's selected policy remains silent
fallback. Expectations are chosen before execution, never derived from observed
utility output or accepted as a generic stderr allowance.

`native-attempt-2` (553 passes), `native-expanded` (588 passes) and
`native-sanitize-intermediate` (536 passes) are intermediate scopes preceding
the final input-stability guard. They are retained separately; the final records
above are authoritative for the completed native validation. The separately
retained `*-before-sanitizer-controls` records preserve the preceding successful
runs before disabling sanitizer helper subprocesses. `commands.json`
records the sequence and actual failures.

## Hosted Linux evidence at the initial PR source

The retained `baseline-ci-linux.log.gz` and `baseline-ci-docker.log.gz` are
successful jobs for source `d376bce3d1da77c5ef1fed3d2a1165e49f4210f2`:

- [Ubuntu/GCC job](https://github.com/melliott18/cshell/actions/runs/36630289274/job/109617499611)
- [Docker/Linux job](https://github.com/melliott18/cshell/actions/runs/36630289274/job/109617499313)

The logs include passing 1162-assertion host profiles, 3950 runtime assertions,
33 runtime PTY cases and sanitizer stages (plus other project suites).
They supply positive Linux integration evidence that local Docker could not
complete. They do **not** validate the new assertions in this follow-up revision,
repair the local engine, establish disappearance of stuck native processes,
or resolve the prior native ps/PTY cleanup failures. The job/run metadata files
preserve their exact source and individual job outcomes; a still-queued macOS
job is not counted as passing.
