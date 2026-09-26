# CSH-037 independent evidence review

This review was performed separately from the CSH-037 implementation and the
CSH-044/045 fixes on 2026-09-26 UTC. The reviewed source and matrix revision is
`58ca5c3dd1cea8d3af41a0ca83000c571327bca3`. The independent build used an archive
of that revision in a temporary directory, so concurrent worktree changes and
build flags could not alter its result.

The review checks the audit's evidence and ownership, and independently
reproduces selected implementation evidence. It does not certify POSIX
conformance or independently prove every clause of the standard. The
[CSH-037 ticket](tickets/CSH-037-portability-audit.md) records the final audit
disposition and subsequent validation of the integrated fixes.

## Findings and closure conditions

The two requirement tables contain 131 distinct rows: 65 language/invocation
rows and 66 utility/option rows. Sixteen utility/option rows explicitly exclude
UP or XSI behavior under the [selected base profile](posix.md#selected-profile):
U-018, U-021, U-022, U-025, U-028, O-003, O-008, O-010, O-011, O-015,
O-020–O-025. The other 115 rows remain applicable or contain applicable portions.
In particular, mixed rows such as ENV-005, O-018, U-015 and U-026 must retain
their base portions. Terminal/job conditions remain explicit in JOB-001–JOB-003.

At the reviewed revision, no complete requirement family was marked verified.
Most rows linked selected module/runtime evidence or a completed implementation
ticket, but lacked a complete mapping from normative clauses to actual passing
assertions. A completed implementation owner does not own that remaining
evidence work automatically. The following explicit open limitation/evidence
tickets now cover all 115 applicable rows, with no omissions or duplicate
primary allocations. Existing concrete defects retain their separate owners.

| Open evidence owner | Applicable rows | Remaining limitation |
| --- | --- | --- |
| [CSH-046: invocation and syntax](tickets/CSH-046-invocation-syntax-evidence.md) | SH-001–SH-008; LEX-001–LEX-006; GRAM-001–GRAM-005; U-017, U-031 (21) | Complete input/invocation, token/grammar and alias clause mapping; PATH-only negative, identity, nonblocking-terminal/post-completion and documented boundary witnesses. |
| [CSH-047: expansion](tickets/CSH-047-expansion-evidence.md) | ENV-002, ENV-004; EXP-001–EXP-011 (13) | Expansion context/order, parameters, patterns, numeric/encoding choices and supported locale breadth require reviewed assertions beyond selected witnesses. |
| [CSH-048: state and builtins](tickets/CSH-048-state-builtin-evidence.md) | ENV-001, ENV-003, ENV-005, ENV-006; U-001, U-002, U-005–U-007, U-009–U-014, U-016, U-019, U-020, U-023, U-024, U-027, U-029, U-030, U-033 (24) | Startup, utility options/errors, special-builtin effects, evaluation/lookup and environment interactions need complete case-level evidence; mixed profile portions need precise applicability. |
| [CSH-049: execution](tickets/CSH-049-execution-evidence.md) | SH-009; RED-001–RED-006; EXEC-001–EXEC-008, EXEC-010–EXEC-016; U-003, U-004; O-026 (25) | Ordering, descriptors, search, pipelines/status, control flow and error consequences lack complete family evidence; descriptor/offset and permitted execution choices need explicit boundary records. |
| [CSH-050: jobs and signals](tickets/CSH-050-jobs-signals-evidence.md) | EXEC-009; JOB-001–JOB-003; SIG-001–SIG-003; U-008, U-015, U-026, U-032 (11) | Base asynchronous/signal/wait rules and conditional terminal behavior need a complete runtime/PTY assertion map. Fixing intermittent failures alone does not verify the families. |
| [CSH-051: shell options](tickets/CSH-051-shell-option-evidence.md) | O-001, O-002, O-004–O-007, O-009, O-012–O-014, O-016–O-018 (13) | Each applicable option needs explicit invocation/set, enable/disable, defaults/reports and affected-environment coverage; common links to the option suite are insufficient. |
| [CSH-052: host utilities](tickets/CSH-052-host-utility-evidence.md) | U-034–U-041 (8) | Host allocation/availability is not utility semantic or shell-dispatch evidence. Required integration scope, helper identities, syntax exceptions and intrinsic-set policy need exact assertions. |

[CSH-042](tickets/CSH-042-locale-semantics.md) retains ENV-004, EXP-004,
EXP-007, EXP-008, EXP-010 and EXEC-012 locale findings.
[CSH-043](tickets/CSH-043-redirection-offset.md) retains SH-009/O-026 offset
maximum and boundary findings. [CSH-044](tickets/CSH-044-intermittent-bg-prompt.md)
and [CSH-045](tickets/CSH-045-jobs-fixture-timeout.md) retain the two observed
jobs/PTY failures. These are concrete findings, while CSH-046–CSH-052 own
unestablished family evidence, not presumed defects in every listed feature.

The initial reverse-owner table also omitted CSH-041's EXP-005/EXP-006 entries,
although prose named the owner. This must be reconciled alongside the new
ticket links. All other original owner/table pairs matched in the reviewed
snapshot. Merely checking that Markdown links resolve does not establish the
meaning or completeness of their evidence.

## Independently reproduced sample

The following commands use a clean source archive and do not modify the shared
worktree build. A new directory path will produce a different generated suite
hash because helper executable paths are embedded in its scripts.

```sh
review_dir=$(mktemp -d /tmp/csh037-review.XXXXXX)
git archive 58ca5c3dd1cea8d3af41a0ca83000c571327bca3 | tar -x -C "$review_dir"
make -C "$review_dir" -j2
make -C "$review_dir" test-portability test-runtime
```

Completed by **2026-09-26 04:10:45 UTC** on macOS 14.8.7 (23J520), Darwin
23.6.0 arm64, Apple clang 15.0.0 (`clang-1500.3.9.4`), Python 3.12.2 and
libSystem.B.dylib 1345.120.2. The build used the default
`-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2` and
`-D_POSIX_C_SOURCE=200809L -Iinclude`, with no sanitizer or linker override.
Archive extraction emitted a host-locale warning; it completed and the build
and both test commands returned zero. Test child locales are set explicitly.

| Artifact / result | Identity or observation |
| --- | --- |
| Shell path / realpath | `/tmp/csh037-review.tzMD2B/cshell` / `/private/tmp/csh037-review.tzMD2B/cshell` |
| Shell SHA-256 | `9c7e581699863965d2c0e5c4446908ceaf40e9b5358c53bac81d4c2330bff795` |
| Generated `build/tests/runtime.json` SHA-256 | `9e4d8c3583a7ee1435ef9b8a919a2318650a20d0ba19c50bee14380615039f81` |
| `tests/smoke.py` SHA-256 | `72c9b619c7fa337b80f8d296d1fe7b5ef774d8c65ece85ce3b85c8c6fe3de79f` |
| `tests/portability.py` SHA-256 | `1130527d1a907378c7bd3dcc0234c88c3c120efaae96bf60f53308ba92392caf` |
| `build/tests/execute_helper` SHA-256 | `21fd248da4225cd19a6eded32dc9b3863c0f2b7cf4161f02424110a3947015cd` |
| Portability suite | **60 passed, 0 failed, 0 skipped**; selected locale `en_US.UTF-8`. |
| Public runtime suite | **1,318 passed, 0 failed, 0 skipped**. |

The runner gives each case a fresh temporary directory, child session and pipes,
umask `077`, `PATH=/bin:/usr/bin`, `LANG=C`, `LC_ALL=C`, per-case `.home` and
`.tmp` paths, plus explicit case overrides. `MallocNanoZone=0` was forwarded;
no other ambient variables were forwarded, and TZ was absent. Default bounds
are five seconds and 65,536 combined output bytes, with CPU, file-size,
descriptor and core limits from [the runner](../tests/smoke.py). The sparse-file
case raises only its file-size bound. A pass includes the runner's completion,
exact stream/status, relevant filesystem and process-group cleanup checks.

Examples independently exercised within the passing runtime suite:

| Actual case name, with ` (string)`, ` (file)` and ` (stdin)` suffixes unless stated | Actual asserted result | Narrow evidence |
| --- | --- | --- |
| `evaluation: alias complete line timing` | stdout `hello\n1\n`, empty stderr, status 0 | Subsequent complete-command alias definition/removal in [evaluation cases](../tests/evaluation_cases.py); selected LEX-006/U-017/U-031 behavior. |
| `lazy parameter operands` | stdout `[set]\n[]\n`, empty stderr, status 0; both forbidden files absent | Unselected default/alternate words do not execute substitutions in [substitution cases](../tests/substitution_cases.py); selected EXP-003/EXP-005 behavior. |
| `control: case fallthrough skips patterns` | stdout `[first]\n[second]\n`, empty stderr, status 0; the later error-producing pattern is not expanded | Issue 8 fall-through in [control cases](../tests/control_flow_cases.py); selected GRAM-004/EXEC-012 behavior. |
| `ordered redirections` | stdout `[restored]\n`, empty stderr, status 0; `captured` contains `out\nerr\n` | Ordered descriptor redirection and restoration in [runtime cases](../tests/runtime_cases.py); selected RED-001/RED-005 behavior. |
| `quoted heredoc and following command` | stdout `$literal\n[after]\n`, empty stderr, status 0 | Quoted delimiter/body and subsequent input in [runtime cases](../tests/runtime_cases.py); selected GRAM-003/RED-004 behavior. |
| `stdin has no command read-ahead` (one stdin case) | stdout `payload\n`, empty stderr, status 0 | Utility receives remaining stdin bytes in [runtime cases](../tests/runtime_cases.py); selected SH-006 behavior. |

These reproduce implementation assertions, including project choices where
present. They do not turn all of their parent families into verified rows. This
independent sample did not rerun Docker, PTY or sanitizer suites; their integrated
results belong in the main audit ticket. No new reference-shell comparison is
claimed here; the versioned reference observations remain in that ticket.

## Choice-register reconciliation

The D-001–D-008 register mixes selected policies with incomplete evidence.
Retain that distinction and give every unfinished part an open evidence owner.

| Choice | What is already documented | What remains open |
| --- | --- | --- |
| D-001 | [Direct script opening](input-and-invocation.md#invocation-contract), no PATH fallback; `-i` requests interactivity. | PATH-only negative and unequal-identity runtime witnesses: CSH-046. |
| D-002 | [Parser contract](parser-and-ast.md) explicitly omits optional `{name}` descriptor allocation; selected numeric redirections and sparse append already run. | Descriptor policy/boundaries: CSH-046/049; exact per-open-file offset maximum/error behavior: CSH-043. |
| D-003 | [Dollar-single-quote choices](value-expansions.md#dollar-single-quote-decoding) specify escape encodings, NUL handling and supported encoding assumptions. | Complete IFS/encoding/locale evidence and required versus unspecified classification: CSH-042/047. |
| D-004 | [Alias timing](aliases.md#parser-eligibility-and-timing) and permitted alias choices are explicit. CSH-026 describes eager dollar-form versus deferred backquote parsing and NUL rejection; CSH-041 adds arithmetic-first replay. | Replace `missing; open` with those selected policies; full case-to-clause evidence remains CSH-046/047. |
| D-005 | [Signed-long model](value-expansions.md#arithmetic-and-parser-cooperation), overflow policy, unsupported extensions and recursion guard are explicit. | Exact platform boundaries, extension classification and full runtime coverage: CSH-047. |
| D-006 | [Assignment policies](execution.md#assignment-categories-and-resolved-dispatch), shell-name function syntax and special-builtin-name rejection are explicit. | Declaration recognition, export/lifetime, function/error interactions and permitted-alternative classification: CSH-047/048/049. |
| D-007 | [Signal status](traps-and-signals.md#delivery-and-environments) uses `128 + signal`; [multi-stage pipelines](execution.md#pipeline-lifecycle-and-stage-results) place each stage in a child. | Remove the stale assertion that pipeline-stage policy is unchosen; retain full signal/pipeline/terminal-stop evidence under CSH-049/050. |
| D-008 | Reader preserves source bytes; retired legacy operators are not a compatibility obligation. | Explicit shebang/operator/expansion-extension policy and public boundary fixtures: CSH-046/047. |

The initial portability case called `startup LC_CTYPE survives assignment`
sets `LC_ALL` to UTF-8, then assigns `LC_CTYPE=C`. This only witnesses LC_ALL
precedence. It does not establish the initial lexical-interpretation rule, and
pathname matching itself is not lexical processing. Rename and describe that
case accordingly; CSH-042/047 retain lexical and later locale-update review.

## Stale evidence descriptions to correct

The following are documentation findings at the reviewed revision, not reasons
to mark the broad rows verified:

- LEX-006 and GRAM-004 say `missing` despite alias and compound runtime cases.
  GRAM-001–GRAM-003 still describe later grammar/runtime integration as future
  work. Link the alias/control/runtime/substitution cases and their run record,
  with CSH-046/049 retaining the complete-family gap.
- ENV-001/ENV-003 still describe variable builtins/startup consumers as future;
  EXP-007/EXP-009/EXP-010, RED-003/RED-005/RED-006, EXEC-006/EXEC-010 similarly
  omit existing fields, execution, pipeline and context witnesses. Record
  selected evidence and the new gap owners without equating implementation with
  full verification.
- The API evidence introductions and CSH-026 integration paragraph refer to
  runtime aliases, options, control-flow consumers and locale startup as future.
  Keep historical results dated, and link later integration rather than
  presenting old boundaries as the current runtime.
- U-035–U-041 must distinguish existing host/intrinsic allocation from missing
  semantic/integration evidence. CSH-052 owns the incomplete evidence; the
  Docker image's absent `ed` remains a concrete image limitation.
- The reference-only null-default example in [evidence conventions](posix-evidence.md)
  is historical. Its original reference observation must remain separate from
  later cshell expansion/runtime evidence; remove statements that imply no
  corresponding runtime work exists today.
- The option-profile introduction must describe the current base selection
  consistently. Future UP/XSI selection can reopen excluded rows; it is not an
  unresolved choice blocking the already documented narrower target.

## Scope of normative review

The normative anchors remain the Open Group's
[Issue 8 Shell Command Language](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html),
[`sh`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html), and
[utility introduction](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html).
Direct page retrieval returned HTTP 403 during this review. Indexed excerpts
from the official Issue 8 Chapter 2 page were available for assignment choices,
job-control conditions, signal/wait behavior and environment isolation. These
support retaining explicit applicability and permitted-choice distinctions;
they do not justify claiming a fresh full-page or sentence-by-sentence audit.
The new evidence owners must inspect the full linked clauses before declaring
their families verified, and must not use older reference-shell behavior to
weaken Issue 8 requirements.

## Audit completion versus conformance

CSH-037 can record a completed audit outcome after the concrete failures have
regression coverage and a resolved or explicit open disposition, final source
and CI results are recorded, all 115 applicable rows have the reciprocal open
owners above, and the documentation findings are reconciled. The independent
reproduction requirement has a passing sample in this report. The final
review/integration lifecycle still follows [Contributing](../CONTRIBUTING.md).

CSH-046–CSH-052 remain explicit evidence limitations and CSH-042/043 retain
concrete unresolved boundaries. They do not become passing requirements when
the audit closes. [CSH-012](tickets/CSH-012-conformance-and-portability.md) needs
its own completion review, and any conformance statement remains withheld while
applicable requirements are unmet.

### Final matrix and ownership reconciliation

A read-only follow-up check on 2026-09-26 at 04:21 UTC confirmed 131 unique,
structurally valid requirement rows, all 115 applicable rows linked to their
intended open CSH-046–CSH-052 evidence owner in both owner and evidence cells,
and exact agreement across all 378 row/reverse-owner pairs. CSH-041's two
missing reverse entries are restored. Each of the seven new tickets lists its
complete allocated scope, an explicit limitation, open acceptance criteria and
a GitHub issue. All local file and heading links in the reviewed matrix,
utilities, owners, evidence, profile, review, index and new tickets resolved.
The 16 profile exclusions remain explicit, broad families remain unverified,
and the renamed LC_ALL probe no longer claims lexical-startup coverage. The
API/integration paragraphs, selected stale evidence rows, historical reference
example and choice register now distinguish implemented policies and selected
witnesses from incomplete verification. SH-002–SH-004 and GRAM-005 explicitly
describe remaining evidence breadth rather than implying absent runtime
integration or an unimplemented nesting guard. This
documentation check does not change the source identity or results of the
independent sample above; final integrated runtime/CI and defect dispositions
remain the main audit ticket's responsibility.
