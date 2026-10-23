# POSIX target and tracking

Current audit disposition: [CSH-012 closure](conformance-closure.md),
[complete utility inventory](host-system-inventory.md), and [defect dispositions](defect-dispositions.md).

The [CSH-012 acceptance review](conformance-acceptance-review.md) at `c8c1c91`
records current requirement gaps, defect ownership, platform results and documentation corrections.

## Target

cshell targets the shell language and `sh` behavior in POSIX.1-2024 (Issue 8).
It currently implements a bootstrap subset. No complete conformance claim is made.

## Selected profile

The current target is the base Shell Command Language and `sh` utility. The
optional User Portability Utilities (UP) and XSI groups are not selected. cshell
already implements some job-control and XSI-associated commands, but those
features do not establish either complete option group. The conditional rows
remain in the [utility and option map](posix-utilities.md); selecting either
group later reopens its full linked set of requirements. This profile decision
does not exclude base requirements or make the current shell conforming.

Normative references:

- [Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html)
- [sh utility](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html)
- [Shell and Utilities introduction](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html)

Use the selected edition when evaluating behavior. Issue 8 includes
dollar-single-quote syntax and the `pipefail` option. Track optional facilities
and implementation-defined choices explicitly as coverage grows. A shell
implementation's compliance is separate from certification of an entire system.

## Requirements and evidence

The [requirements matrix](posix-matrix.md) inventories the shell language and
`sh` contract using stable IDs, precise Issue 8 sources, scope decisions,
implementation owners, planned fixtures and current evidence. Its companion
[utility and option map](posix-utilities.md) covers special/intrinsic utilities,
host dependencies and conditional profiles. Use [requirements by ticket](posix-owners.md)
to find a ticket's rows, or follow a row's owner and evidence links in the other
direction.

[Evidence conventions](posix-evidence.md) define missing, implemented, verified
and inapplicable states, exact smoke-test limits, and a reproducible differential
example. Unimplemented requirements and pending scope decisions remain open.
Reference-shell output does not establish expected results or cshell conformance.
Ticket lifecycle status continues to live in the [ticket files](tickets/README.md).
The [independent CSH-037 review](audit-review.md) accounts for all 131 rows:
115 applicable rows were allocated to evidence owners CSH-046–CSH-052,
and 16 rows retain the documented UP/XSI exclusions. Completing this audit does
not turn those open evidence limitations into passing conformance requirements.
The [current CSH-012 reconciliation](evidence-reconciliation-current.md) records
CSH-049 completion, CSH-050 platform acceptance, CSH-064 host ownership, and
current versus historical validation. The original audit allocation and
[earlier reconciliation](evidence-reconciliation.md) remain historical snapshots. CSH-057's later
[formal retention disposition](evidence/csh-057-retention-disposition/README.md)
allows its scoped completion while retaining an unknown-cause historical failure
and explicit reopening conditions. CSH-050 and CSH-012 keep their separate gates.

## Runtime baseline

This summary describes the public replacement runtime after CSH-039. The
requirement matrix retains its recorded historical baseline and detailed planning;
standalone module evidence does not establish runtime feature support.

| Area | Current evidence / gap | Owning tickets |
| --- | --- | --- |
| Build and source organization | One runtime; legacy sources and scanner dependencies removed | [CSH-039](tickets/CSH-039-legacy-retirement.md) |
| Memory and process safety | Module ownership, allocation failures, descriptor restoration, and child cleanup fixtures | [CSH-016](tickets/CSH-016-input-and-invocation.md), [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-020](tickets/CSH-020-pipeline-lifecycle.md) |
| Invocation and input | String/script/stdin, EOF, interactive detection, strict output, and final statuses | [CSH-018](tickets/CSH-018-status-and-cli-integration.md), [Runtime behavior](candidate-runtime.md) |
| Token recognition and quoting | Structured words, quote provenance, and integrated expansion | [CSH-004](tickets/CSH-004-lexer-and-words.md) |
| Grammar and command composition | Lists, groups, control flow and functions run through the replacement AST; full conformance audit remains open | [CSH-005](tickets/CSH-005-parser-and-ast.md), [CSH-021](tickets/CSH-021-lists-and-execution-contexts.md), [CSH-028](tickets/CSH-028-control-flow-and-functions.md) |
| Execution and redirections | Literal commands, external lookup/statuses, ordered redirections, concurrent pipelines | [CSH-019](tickets/CSH-019-simple-command-redirections.md), [CSH-020](tickets/CSH-020-pipeline-lifecycle.md) |
| Variables and execution state | Owned state, environment import, literal assignments, state builtins | [CSH-007](tickets/CSH-007-variables-and-parameters.md) |
| Word expansion | Integrated value/field expansion, substitutions, here-documents, and arithmetic-first replay; milestone complete | [CSH-008](tickets/CSH-008-word-expansion.md) |
| Compound commands and functions | Parsing and runtime control flow, function lifetimes, and control transfer fixtures | [CSH-009](tickets/CSH-009-compounds-and-functions.md) |
| Builtins, aliases, and options | State/evaluation builtins, aliases and [shell options](shell-options.md); full conformance audit remains open | [CSH-010](tickets/CSH-010-builtins-options-and-aliases.md) |
| Signals, interactive mode, and jobs | Process groups, terminal handoff, job builtins, traps, input interrupt recovery, and hangup policy; full conformance audit pending | [CSH-034](tickets/CSH-034-job-control.md), [CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) |
| Conformance evidence and portability | Native/Docker module and runtime fixtures, plus [locale, large-input and sparse-file probes](testing.md#portability-audit-probes); full requirement-level verification remains open | [CSH-037](tickets/CSH-037-portability-audit.md), [CSH-042](tickets/CSH-042-locale-semantics.md), [CSH-043](tickets/CSH-043-redirection-offset.md), [CSH-044](tickets/CSH-044-intermittent-bg-prompt.md), [CSH-045](tickets/CSH-045-jobs-fixture-timeout.md), [explicit coverage owners](audit-review.md) |

Legacy syntax such as `|&` and `>>&` must not be used as evidence of POSIX
coverage or retained as compatibility requirements. New modules take their
contracts from the standard. [CSH-039](tickets/CSH-039-legacy-retirement.md)
removes the old runtime without waiting for full POSIX coverage; unsupported
constructs must fail explicitly until their implementation tickets are complete.

## Replacement compound-syntax evidence

CSH-027 extends the [parser/AST API](parser-and-ast.md) to conditionals, loops,
case clauses (including POSIX.1-2024 `;&`), and function definitions. Structural
fixtures preserve words, redirections, source positions, and nested here-documents;
allocation-failure checks cover partial compound trees. CSH-028 adds
[execution evidence](control-flow.md) for control flow, function storage and
invocation, expansion, redirection lifetimes, and error cleanup. Full conformance
remains open; dot-script and trap integration subsequently landed in CSH-031/035,
with residual execution checks in CSH-055.

## Replacement value-expansion evidence

CSH-024 adds [module-level value expansion](value-expansions.md), with checked
parameter/tilde/arithmetic behavior, quote provenance, and dollar-single-quote
decoding. CSH-025 adds IFS field splitting, pathname generation, protected empty
fields, and explicit failure/interruption cleanup at the module level. CSH-026
integrates these APIs with substitutions, context-sensitive command preparation
and here-documents; [its evidence](tickets/CSH-026-substitution-and-heredoc-integration.md)
covers public runtime behavior and resource cleanup. CSH-041 adds arithmetic
ambiguity replay with lexer/parser fault sweeps and public cross-mode cases.
The [CSH-047 clause/condition map](expansion-evidence.md) reconciles exact
runtime/API witnesses, numeric/encoding policies and remaining limits.
Standalone API fixtures and selected integration cases do not establish shell
conformance.

## Replacement execution evidence

CSH-019 adds [module-level simple-command execution](execution.md), with
lookup/status conversion, owned children, ordered file/descriptor/here-document
redirections, and parent builtin restoration. CSH-026 replaces its initial literal
adapter with context-sensitive preparation. CSH-023 adds prefix
assignment categories, selective restoration, and readonly error handling, with
real external environment probes and resolved builtin/function dispatch fixtures.
CSH-029 adds the state builtin family and utility inventory. CSH-028/031 and
CSH-048/049 record integrated function and builtin semantics.
The public runtime uses integrated expansion and state builtins.

CSH-020 adds replacement pipeline API evidence through `make test-pipeline`:
concurrent multi-stage execution, default last-stage status and negation,
builtin subshell isolation, explicit redirection precedence, and partial-launch
child/descriptor cleanup. Every stage's raw and converted status is retained.
These API checks use `build/tests/execute_fixture`; CSH-018/CSH-039 also test
pipelines through the public `cshell` in all input modes. CSH-032 implements `pipefail`, with the CSH-051 option-context evidence; CSH-034 adds runtime process groups and job control. CSH-021 adds compound
stages as described below.

## Replacement context evidence

CSH-021 adds public-runtime and API evidence through `make test-context` for sequential and
AND/OR lists, brace/subshell state isolation, group redirection lifetimes,
compound pipeline stages, asynchronous return and background PID ownership.
Synchronization-based reaping checks and allocation/pipe/fork/wait injection
cover cleanup. Background PID storage and `$!` expansion are implemented and
covered by the expansion and jobs suites. CSH-034 adds retained wait statuses, idle SIGCHLD reaping and job
control through the optional runtime job manager. See [Execution contexts](execution.md#lists-groups-and-background-contexts).

## Replacement alias evidence

CSH-030 adds [alias storage, direct handlers, and token/AST substitution](aliases.md),
including recursive suppression and complete-command timing fixtures. CSH-031
adds [executed-script validation](evaluation-builtins.md) through the dispatcher,
nested dot/eval, functions, command lookup, and substitutions.

## Evidence required

As a feature is implemented, link its specific specification section and tests
from the owning ticket. Record the supported behavior, remaining cases, and any
implementation-defined decisions. A passing example is evidence for that case,
not every requirement in a section.

The test harness should compare observable output, exit status, filesystem
effects, and completion within a timeout. Fix the locale and environment when
needed for deterministic cases. Use pseudo-terminals for terminal behavior.

Differential tests against other shells help find discrepancies. Their output is
not the authority: use the standard to resolve differences and avoid asserting
one result where behavior is unspecified. Record reference-shell versions,
especially when testing Issue 8 additions.

Before claiming the target is covered, refine each matrix family into its full
fixture inventory, link passing results, close documented gaps, and validate on
the supported systems. Sanitizers and Linux/macOS builds are complementary safety and
portability checks, not substitutes for language conformance tests.

See [Testing](testing.md) for the current native and Docker entry points and
their intentionally limited smoke coverage.

## Job-control evidence

CSH-034 adds [job control](job-control.md) through the persistent runtime context.
Native and Docker script/PTY checks cover job builtins, process groups, terminal
signals, stopping/resuming, terminal modes, idle reaping, and failure cleanup.
CSH-035 adds [trap and signal evidence](traps-and-signals.md) for inheritance,
parser interruption, and exit/hangup policy. The combined tests do not by
themselves establish full conformance for the CSH-011 milestone.

## CSH-086 owned-terminal overwrite decisions

CSH-086 adds bounded C-locale owned-PTY cp/mv decisions to U-034/U-040.
The selected cp source repair and separate stock failures are recorded in
[evidence](evidence/csh-086/README.md). [CSH-091](tickets/CSH-091-filesystem-environment-residuals.md)
retains every unsupplied environment; no whole utility contract is qualified.

## CSH-087 operand and recursive decisions

CSH-087 extends U-034/U-040 with 68 bounded multi-operand, recursive terminal,
and same-device directory assertions. Exact provider provenance and the separate
stock failures remain required. [Evidence](evidence/csh-087/README.md) records
both platforms. [CSH-091](tickets/CSH-091-filesystem-environment-residuals.md)
retains every unsupplied contract, including all four original conditions.

## CSH-088 measured metadata and timestamp environments

CSH-088 adds 64 U-034/U-040 assertions through direct exec and cshell string,
file and stdin modes. Private lstat measurements check numeric ls listings
for regular files, hard links, directories, FIFOs and symlinks. Authored sizes
and independently read-back access/modification timestamps check sorting,
C-locale ties and reversal. Exact nanosecond readback precedes find -newer
comparisons before, equal to and after the reference, including -H/-L reference
symlinks. Setup and cleanup failures are failures, never profile allowances.

[CSH-088 evidence](evidence/csh-088/README.md) records both platforms and
separate stock failures. [CSH-091](tickets/CSH-091-filesystem-environment-residuals.md)
owns each remaining environment and all four original conditions. Whole
utility contracts, non-C collation, live-clock age boundaries, mount/depth
limits, ACLs, capacity exhaustion and libc-internal faults remain unqualified.

## CSH-089 declined children and nested recursive decisions

`make test-host-filesystem-recursive` adds ten cases / 30 U-034/U-040
assertions using direct provider exec and cshell command-string/script-file
modes on owned C-locale PTYs. Authored one-child chains cover declined regular
files and symlinks, declined nested descent, separate final parent decisions,
a nonempty-parent error after accepting removal of a still nonempty parent, and continuation
to a later operand. Exact transcripts, empty stdout, exit status, retained bytes,
link text and removed entries are checked independently. Five harness regressions
check bad transcripts/effects/status/channels, partial setup, timeout cleanup and provider-specific simple-prompt spelling.

The selected profile builds GNU rm 9.7 with a local source patch retaining the
mandatory final `-i` prompt after a declined nested descent (rm DESCRIPTION
2b-2e). Unpatched GNU skips the parent decision in that case. The patch changes
only the marked-ancestor shortcut under explicit `-i`; ordinary non-interactive
behavior remains unchanged. Original stock failures remain separate failures;
no output or status is translated and no selected allowance is added.

[CSH-089 evidence](evidence/csh-089/README.md) records native and Linux results.
[CSH-091](tickets/CSH-091-filesystem-environment-residuals.md) owns every remaining
utility environment and all four retained conditions. These cases do not
qualify arbitrary branching, depth/path exhaustion, mounts, races, non-C prompts,
ACLs, quotas, real filesystem exhaustion, libc-internal faults or whole utilities.

## CSH-090 total pathname boundaries

`make test-host-filesystem-path-limits` adds eight cases / 32 strict U-034/U-040
assertions in direct, string, file and stdin modes. CSH-090 supplies 32 total pathname
byte assertions: the selected filesystem PATH_MAX and portable 256-byte limit, operand
lengths limit-1, limit and limit+1 (the limit includes NUL), plus diagnostic
continuation across two invalid operands and a valid missing operand. Independent
pathconf and unnormalized stat probes distinguish kernel ENAMETOOLONG from the portable
policy. Components are at most two bytes; no deep tree or filesystem exhaustion is
exercised.

The full selected profile requires these assertions without allowances. No selected
provider or build configuration changes. All other individual environments and the four
original retained conditions remain open under
[CSH-091](tickets/CSH-091-filesystem-environment-residuals.md). See [CSH-090
evidence](evidence/csh-090/README.md) for native/Linux results.

## CSH-092 creation masks and final permissions

`make test-host-filesystem-creation` adds 26 cases / 104 strict U-034/U-040
assertions through direct exec and cshell string, file and stdin modes. A child
helper sets masks 027, 077 or 777, reads back the mask, and independently creates
a directory and FIFO to prove its effect before execing the inventoried provider.
The oracle checks final object types and modes, preserved existing data and parent
identity, output channels, status, and cleanup. Symbolic removal, sequential copies,
conditional execute, existing-middle continuation and two-level mkdir parents
are bounded witnesses. Six harness regressions check corrupted evidence, partial
setup, failed exec, wrong probes and timeout cleanup.

See [CSH-092 evidence](evidence/csh-092/README.md) for native/Linux results and
provider provenance. [CSH-100](tickets/CSH-100-filesystem-environment-residuals.md)
retains each unsupplied contract and all four original conditions. Final-state
checks do not observe transient permissions, qualify every symbolic mode, ACL
inheritance, privilege, arbitrary graphs, capacity or whole utilities.

### Output errors (CSH-093)

CSH-093 supplies 32 external pwd output-error assertions on macOS and 56 pathname
utility assertions on Linux: closed stdout EBADF and readerless-pipe EPIPE for pwd -P,
-L, -L -P and -P -L, plus Linux virtual-device ENOSPC for those forms and
basename/dirname. PWD is unset, so logical forms fall back to the physical cwd. Child-
only kernel probes precede exact provider exec. These cases do not supply libc-internal
faults, actual filesystem exhaustion, logical namespace changes or arbitrary output
failures.

`make test-host-filesystem-output` requires zero allowances. See
[CSH-093 evidence](evidence/csh-093/README.md). All four original conditions remain open under CSH-100.

### Logical cwd fallback (CSH-094)

CSH-094 supplies 48 external pwd assertions after leaf/parent rename/removal, with default options, -L and -P -L. The helper observes unchanged inherited PWD: absent for direct exec or naming the fixture root for shell modes, independently distinct from the cwd inode. It never sets or unsets PWD. Physical resolution or ENOENT is measured before exact provider exec. Valid logical symlink paths, arbitrary namespace races, inaccessible ancestors, path limits and allocation failures remain unqualified.

`make test-host-filesystem-cwd-logical` runs the focused cases. The full selected
profile requires them with zero allowances; all earlier assertions and provider
sources/build flags remain unchanged. Five harness regressions exercise immutable
specifications, corrupted markers and result channels, setup/exec failures,
inappropriate inherited PWD and timeout/reaping/cleanup. See
[CSH-094 evidence](evidence/csh-094/README.md). All unsupplied environments and
four original conditions remain open under
[CSH-100](tickets/CSH-100-filesystem-environment-residuals.md).

### Authored numeric magic boundaries (CSH-095)

CSH-095 supplies 46 authored file magic cases / 184 assertions for native signed byte/short minima and maxima, comparisons across zero, masks and bit tests on negative values, hexadecimal/octal short constants, complete/truncated numeric fields and first-match/continuation order within one database. Exact sample bytes, native ABI widths, channels, status and unchanged input effects are retained. Other types/widths, unsigned ranges, cross-database -m/-M/-d precedence, default classification, encodings and locales remain unqualified.

`make test-host-filesystem-magic` runs the focused cases. They are also mandatory
in the full selected profile with zero allowances. See [CSH-095 evidence](evidence/csh-095/README.md).
All four original U-040 conditions and every unsupplied environment remain open
under [CSH-100](tickets/CSH-100-filesystem-environment-residuals.md); utility/libc/platform
vendors retain implementation ownership. Historical evidence is unchanged.

## Calendar timestamps (CSH-096)

CSH-096 supplies 40 touch calendar cases / 160 assertions for the Epoch, two-digit years 70/99/00/68, omitted seconds, leap day, second-60 year rollover, the required January 2038 date and the signed-32-bit timestamp boundary. Integer UTC calendar arithmetic supplies expected timestamps; exact target and unequal fractional baselines are independently read back on the target inode before execution. Default, -a, -m and explicit -a -m selections require exact timestamps, empty channels, zero status and unchanged content. Other date/timezone forms, current-time tolerances, unsupported timestamp errors, arbitrary symlink graphs and permission/ACL boundaries remain unqualified.

See [CSH-096 evidence](evidence/csh-096/README.md). Every remaining contract and
all four retained U-040 conditions belong to [CSH-100](tickets/CSH-100-filesystem-environment-residuals.md).

## Reference timestamps and alias graphs (CSH-097)

CSH-097 supplies 28 touch reference cases / 112 assertions for distinct access/modification timestamps, regular and symlink-chain references, hard-linked and symlink-chain operands, all four field selections, and silent -c continuation past missing/dangling paths. Exact nanoseconds and inode relationships are independently probed before execution; post-exec metadata is captured before content reads. Reference files, link texts, inode identities and unselected fields must remain unchanged. Arbitrary graphs, creation/current-time tolerances, unsupported timestamps, races and permission/ACL errors remain unqualified.

See [CSH-097 evidence](evidence/csh-097/README.md). All 21 full utility contracts
and four original U-040 conditions remain open under
[CSH-100](tickets/CSH-100-filesystem-environment-residuals.md).

## CSH-098 date forms and fixed timezones

CSH-098 supplies 64 touch date-form cases / 256 assertions for period/comma fractional seconds down to one nanosecond, T/space separators, absent-zone fixed TZ interpretation, Z overriding nonzero TZ, and -t fixed-zone rollover. Independently authored UTC fields and integer fractions are exactly read back on the target inode before execution; all four field selections require exact timestamps, unchanged identity/mode/content and empty channels. DST transitions, timezone databases, arbitrary fractions/ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

The U-034 direct-exec and U-040 default contracts retain their existing evidence.
[CSH-100](tickets/CSH-100-filesystem-environment-residuals.md) owns all unsupplied
environments and the four original U-040 conditions. See [CSH-098 evidence](evidence/csh-098/README.md).

CSH-099 adds 104 touch cases / 416 assertions for explicit POSIX daylight-saving
rules, using unique local times around northern and southern transitions,
seasonal offsets, -d/-t forms and Z overrides. Exact UTC expectations, inode
probes and channel/status/effect checks are mapped in the current filesystem
section inventory. See [CSH-099 evidence](evidence/csh-099/README.md).
U-034 and U-040 remain partial; [CSH-100](tickets/CSH-100-filesystem-environment-residuals.md)
owns all unsupplied environments and the four retained conditions.
