# Execution, redirection and control flow: CSH-049 evidence

This is the clause/condition map for [CSH-049](tickets/CSH-049-execution-evidence.md),
reviewed against POSIX.1-2024 on 2026-09-26. Parent requirements remain
**implemented subsets**. The assertions below are narrower than the full
families; the [run record](tickets/CSH-049-execution-evidence.md#validation-record)
identifies the actual revisions and environments. No reference shell supplies
an oracle. [Residual obligations](#remaining-obligations) keep CSH-012 closed.

## Sources and policies

Normative sources reviewed together: Shell Command Language
[2.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07),
[2.8](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08),
[2.9](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09),
[break](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_16),
[continue](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_18),
and [sh DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_03).
The base shell profile makes these obligations applicable; absence of a locale,
PTY capability or native Linux runner is not an exclusion.

| Choice | Classification and selected behavior |
| --- | --- |
| D-002 descriptor numbers | Implementation-defined maximum: numeric operands through `INT_MAX` are representable, but successful allocation is bounded by the process descriptor limit and available descriptors (including private backups). Descriptors 0–9 must be supported. Optional `{location}` allocation is unsupported; CSH-046 owns the syntax probes. |
| D-002 offsets | The native signed `off_t` maximum is 2^63−1 on recorded hosts. Filesystem and resource limits can be lower; CSH-043 measures these separately. A shell redirection does not guarantee a successful write at every representable offset. |
| RED-005 direction | POSIX permits a redirection error for duplicating a descriptor in the wrong direction. cshell chooses `EBADF`. A nondigit, non-`-` operand is unspecified, so its rejection is a policy/robustness witness. |
| EXEC-001 order | Runtime performs argument expansion, redirection, then prefix expansion. Empty/special commands are permitted to exchange the last two steps; the prepared-command API does so. Tests do not claim one order is universally required for those categories. |
| D-006 prefixes | No-name/special assignments persist. External/regular/function prefixes are exported temporarily and restored, including attributes. Special prefixes preserve export attributes unless allexport applies. Function persistence/export, sequential prefix visibility and unrelated expansion side effects include unspecified choices; see [assignment policy](execution.md#assignment-categories-and-resolved-dispatch). |
| D-006 functions | Only shell names, excluding special-builtin names, are accepted. No optional extra-name-character extension is selected. Non-lexical loop transfer across a function or without a loop is policy evidence, not a portable requirement. |
| D-007 pipelines/status | Every multi-stage pipeline stage uses a child; cshell waits for all stages (permitted). Singletons retain ordinary command environments. Child signals map to `128 + signal_number`; tests derive host signal numbers. Pipefail is sampled at launch and selects the rightmost nonzero stage, then `!` negates. |
| EXEC-003/005 | No-name redirection state is disposable. POSIX does not require here-documents to be seekable and permits reopening closed standard descriptors. Closed-descriptor helper tests exercise the selected implementation, not arbitrary host utility behavior in a nonconforming environment. |
| EXEC-004 fallback | `ENOEXEC` invokes host `/bin/sh`. The simple fallback witness covers argument/status passing; host Issue 8 language completeness remains an external dependency, owned by CSH-052. Unset PATH defaults to `/bin:/usr/bin`; empty components search the current directory. |

## Fixture identities and conditions

The following abbreviations identify actual source fixtures, not intended IDs:

- **E**: [execution_cases.py](../tests/execution_cases.py), prefix `execution: `.
- **R**: [runtime_cases.py](../tests/runtime_cases.py), no added prefix.
- **C**: [control_flow_cases.py](../tests/control_flow_cases.py), prefix `control: `.
- **S**: [substitution_cases.py](../tests/substitution_cases.py), no added prefix.
- **V**: [evaluation_cases.py](../tests/evaluation_cases.py), prefix `evaluation: `.
- **O**: [option_cases.py](../tests/option_cases.py), prefix `options: `.
- **P**: `terminal_cases()` in R; exact PTY names have no invocation suffix.

Except the explicit interactive errors, these generators materialize identical
assertions in `(string)`, `(file)` and `(stdin)` modes. Interactive error-table
cases use `-ic` or `-i script` without a terminal; P separately checks terminal
recovery. [smoke.py](../tests/smoke.py) asserts every stdout/stderr byte, status,
requested file content/absence and a five-second default deadline with a 65,536
byte combined output limit. Its fresh directory, explicit C locale,
`PATH=os.defpath` (`/bin:/usr/bin` on these hosts), HOME/TMPDIR and umask 077 are authoritative.
TZ is absent; PTY startup supplies the shell’s default prompts. The environment
does not inherit arbitrary user shell variables. The helper
is [execute_helper.c](../tests/execute_helper.c); its absolute path is recorded
in generated JSON. Host errno wording is generated with `os.strerror`; exact
wording is a regression assertion, not wording prescribed by POSIX.

Older API suites are explicitly identified below by their literal scripts or
C assertion blocks because they do not have individually named cases. They
use separate bounded runners and sometimes only require a nonempty diagnostic;
that evidence is not silently strengthened to an exact diagnostic assertion.
No full family is promoted to verified by an API pass or a single boundary.

<a id="sh-009"></a><a id="o-026"></a>

## SH-009 / O-026 — large files and offset maximum

Source: sh DESCRIPTION and [2.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07).
Implementation: [pathname.c](../src/pathname.c), [redirect.c](../src/redirect.c).

| Condition | Exact assertions | Limit/owner |
| --- | --- | --- |
| File size must not cause glob failure | [portability.py](../tests/portability.py) `sparse file pathname expansion` matches a sparse file above 2 GiB; name bytes and status are checked | A representative large file, not all filesystem capabilities |
| Native offset maximum, duplication and boundary errors | [redirection_offsets.py](../tests/redirection_offsets.py), all 36 mode-specific cases: positioned last-byte success, EFBIG and unchanged tail, partial write, SIGXFSZ, builtin failure/restoration, shared offsets, truncation recovery | [CSH-043](tickets/CSH-043-redirection-offset.md#validation-record) supplies exact helper statuses and native/Linux differences; current runs retain them |
| Filesystem seek limit vs RLIMIT_FSIZE | Native syscall probe separates native off_t maximum, actual seek boundary and controlled file-size limit; shell append is compared with a direct syscall under the same conditions | APFS append behavior is host-qualified, not inferred to be portable. Absolute writable limits of every filesystem are unverified, CSH-049 |

<a id="red-001"></a>

## RED-001 — ordered descriptors and target expansion (2.7)

Implementation: `runtime_redirects` in [execute.c](../src/execute.c),
`csh_command_redirect` in [prepare.c](../src/prepare.c), `csh_redirect_apply/restore`
in [redirect.c](../src/redirect.c).

| Condition | Exact assertions | Limit/owner |
| --- | --- | --- |
| Left-to-right open/dup and restore | R `ordered redirections`: file `out\nerr\n`, later stdout `[restored]\n`; E `EXEC-006 pipe connected before output redirection`: stdout `err\n`, file `out\n` | Different descriptor order has different destinations |
| At least 0–9, not argv | E `RED-001 numeric descriptor 0` through `9`: helper writes `fd\n` into each target; subsequent stdout restored | Source/API validates larger integers; descriptor exhaustion stays an error, not an exclusion |
| Failure stops later redirects but preserves earlier file effects | E `RED-001 rollback retains file effects`: first file truncated, last file absent, status 1 then restored stdout | No filesystem rollback is promised |
| Expansion context and timing | S `redirection operands do not split or glob`, `redirection expansion observes previous redirection`; literal filename `two words *` and ordered target contents | Interactive optional globbing is not selected; exhaustive target-expansion combinations remain CSH-047/049 |
| Restore flags, closures and no private-fd exposure | [execute_fixture.c](../tests/execute_fixture.c) assertions for fd 40/41 preserve FD_CLOEXEC/count after success and failure; S `private group descriptor cannot become expanded dup source 3` through generated descriptors | API assertions, plus selected runtime witnesses; CSH-055 adds [public-runtime descriptor masks and inherited flags](execution-contracts.md#descriptor-and-command-read-witnesses); arbitrary layouts are not inferred |

<a id="red-002"></a>

## RED-002 — input/output/noclobber (2.7.1–2.7.2)

Implementation: `apply_one`, `open_noclobber` in redirect.c.
E `RED-002 default input and truncation` asserts `<` uses fd 0, `>` uses fd 1,
input unchanged and a longer output file replaced with `new\n`. O `O-004 refuse
and override` preserves an existing file on `>`, permits `>|`, and appends;
`O-004 create and dev null`, `O-004 symlink and dangling`, `O-004 fifo is writable`
cover creation and nonregular targets. Dangling-link rejection is permitted.
`O-004 concurrent exclusive creation` requires exactly one successful creator
among eight contenders and one winner record. It is evidence for the selected
atomic-creation case, not an exhaustive adversarial symlink-race proof.
Special versus regular error consequences are in EXEC-015.

<a id="red-003"></a>

## RED-003 — append (2.7.3)

Implementation: `apply_one` opens `O_WRONLY|O_CREAT|O_APPEND`.
E `RED-003 append ignores seek` invokes two independent writers which each seek
to zero before writing: final file must be `XYXY`, proving creation and append
semantics rather than just one initial seek to EOF. O `O-004 refuse and override`
also appends to an existing file with noclobber set. CSH-043 covers selected
large-file/resource-limit failures; host/filesystem differences remain scoped.

<a id="red-004"></a>

## RED-004 — here-documents (2.7.4)

Implementation: [parser.c](../src/parser.c) delimiter collection,
prepare.c expansion, redirect.c temporary descriptor delivery.

| Condition | Exact assertions | Limit/owner |
| --- | --- | --- |
| Quoted or partially quoted delimiter | S `quoted heredoc suppresses expansion`, `partially quoted heredoc suppresses expansion`, `dollar quoted delimiter suppresses expansion`: literal bytes and no substitution side-effect files | Other delimiter expansions are unspecified; no reference-derived oracle |
| Unquoted expansions and backslash rules | S `unquoted heredoc body rules`, `heredoc continuations and tab stripping`: exact quote/backslash/tab/result bytes | No seekability requirement on the delivered descriptor |
| Multiple documents and evaluation timing | S `ordered expanded heredocs`, `skipped heredoc does not parse or expand body`; C `function definition heredoc invocation` prints call-time `hello world\n` | Delimiter collection is distinct from deferred expansion |
| Large body and failures | S `large expanded heredoc`, `heredoc expansion error prevents execution`, `heredoc diagnostic follows earlier redirects` | Fault runner covers cleanup, not every host write error |
| Interactive PS2 | P `terminal heredoc prompts`: each input line synchronized to `> `; exact combined terminal transcript | Prompt expansion ownership remains CSH-048; supported PTY capability required |

<a id="red-005"></a>

## RED-005 — descriptor duplication/closure (2.7.5–2.7.6)

Implementation: redirect.c `apply_one` and `duplicate_to`.
E `RED-005 shared input offset` reads one byte through fd 0 then requires `bcd`
through its duplicate fd 3, proving a shared open-file offset. `close twice <&`
and `close twice >&` both succeed; `closed source <&` and `closed source >&`
require a diagnostic/status 1 and recovery. The two `direction policy` cases
require the selected EBADF error; POSIX also permits duplication in these
wrong-direction cases. [execute.py](../tests/execute.py) literal `<&-`/`>&-`
checks use the external `closed` helper for default fds 0 and 1. Error operands
that are neither digits nor `-` remain unspecified. API saves/closures are
mapped under RED-001; numeric representability is D-002.

<a id="red-006"></a>

## RED-006 — read/write (2.7.7)

Implementation: redirect.c `O_RDWR|O_CREAT` with no truncation.
E `RED-006 default read write preserves tail` opens fd 0, reads `a`, writes `X`
at the shared current position, and requires stdout `a\n` and file `aXcd`.
`RED-006 default read write creates` requires `fd\n` in the newly created file.
CSH-043 additionally covers positioned reads/writes and offsets beyond 2 GiB.
These checks do not infer writable behavior on every nonregular object.

<a id="exec-001"></a><a id="exec-002"></a><a id="exec-003"></a>

## EXEC-001–003 — preparation, assignments and no-name commands

Sources: [2.9.1.1–2.9.1.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_01).
Implementation: prepare.c `csh_command_arguments/assignments`, execute.c
`runtime_simple`, `assignments_apply`, state.c selective variable saves.

| Stable scope | Condition and exact assertions | Qualification |
| --- | --- | --- |
| EXEC-001/order | E `EXEC-001 expansion redirection assignment phases` sees `old` in argv and redirect target despite prefix `new`; parent remains `old`. `argument failure precedes redirection` leaves effect absent, status 2 | Regular command order required; permitted alternatives for empty/special commands documented above |
| EXEC-001/assignment-context | S `assignment expansion is scalar and sequential`, `assignment tilde sites`, `declaration operands use assignment context` compare scalar spaces/globs and sequential visibility; `assignment substitution sees preceding redirects` captures stderr in file | Sequential visibility includes D-006 policy; expanded declaration recognition remains CSH-047 |
| EXEC-002/no-name | E `EXEC-003 vanished command keeps assignments`: unset expansion yields no command, value persists, status 0 | Same category after expansion as a syntactically empty command |
| EXEC-002/external | E `external export and restore`: child `v=child`, next child unset, shell unset | Prefix exported only for command; [assignment_fixture.c](../tests/assignment_fixture.c) also asserts restored attributes/repeated names/rollback |
| EXEC-002/regular | E `regular builtin restores prefix only`: `read` restores `v=old`, preserves unrelated `answer=kept` | Regular standard utility assignment scope |
| EXEC-002/special | E `special builtin keeps further changes`: `eval` mutation to `changed` persists | Persistent required value; export policy separately documented |
| EXEC-002/function | E `function export policy`: child sees prefix, parent old/unexported restored; C `function state and prefix lifetime` retains unrelated mutation | D-006 unspecified persistence/export choices |
| EXEC-002/readonly | E `readonly category empty`, `:`, `read answer`, helper `status 0`, `f`: status 1, diagnostic, no body/later files | All five categories, noninteractive; interactive recovery under EXEC-015 |
| EXEC-003/last-status | E `last substitution status`: statuses 7 (last assignment substitution), 9 (redirection substitution), 0 (no substitution), exact created files | Last status obtained, not assumed first or rightmost textual nesting |
| EXEC-003/environment | S `empty command redirection environment isolated`: `${made:=created}` creates file but does not set parent variable | Disposal covers this mutation; [CSH-055](execution-contracts.md) adds no-name trap/substitution combinations; full environment combinations remain CSH-048 |

<a id="exec-004"></a><a id="exec-005"></a>

## EXEC-004–005 — lookup and external execution

Sources: [2.9.1.4–2.9.1.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_04).
Implementation: execute.c `command_category`, `path_builtin_category`,
`lookup_path`, `launch_prepare/replace`; state.c exported environment.

| Stable scope | Exact assertions | Limit/owner |
| --- | --- | --- |
| EXEC-004/precedence | C `function lookup before regular builtin`; V `command bypass function`, `command intrinsic without PATH`; special names rejected by C `function special name rejected` | Invalid special function names are outside portable application guarantees; reserved unspecified utility names are not treated as required search behavior |
| EXEC-004/path | E `PATH refresh after assignment`: `one\ntwo\n`; execute.py literal PATH search with first nonexecutable and second executable directory, empty component, and missing interpreter (126) | Fixed by [CSH-055](execution-contracts.md): expanded last-prefix PATH controls builtin selection; the strict regression now joins default suites |
| EXEC-004/pathname-fallback | E `pathname bypass and format fallback` ignores a same-name function, passes spaced argument and script `$0`, returns 17 | Host `/bin/sh` dependency; CSH-052 owns host Issue 8 gaps |
| EXEC-005/argv-environment | R `literal quoting` preserves empty/spaced/literal arguments; E `external export and restore` checks environment; execute.py prefixed PATH/VISIBLE/PRIVATE scripts assert exported vs unexported values | [CSH-055](execution-contracts.md) adds exact direct/PATH argv[0] and invalid imported-name policy assertions |
| EXEC-005/open-descriptors | E numeric 0–9 and shared-offset witnesses inspect descriptors after exec; [pipeline_fixture.c](../tests/pipeline_fixture.c) loops through all seven originally closed standard-fd masks and asserts restored closures/no fd growth | CSH-055 adds all public-runtime standard-fd masks in string/file modes and inherited fd flags; POSIX permits reopening closed standard fds |

<a id="exec-006"></a><a id="exec-007"></a>

## EXEC-006–007 — pipeline concurrency and status (2.9.2)

Implementation: execute.c `context_pipeline`, `context_job`, `pipeline_connect`,
`stage_wait`; [jobs.c](../src/jobs.c) status collection.

| Stable scope | Exact assertions | Qualification |
| --- | --- | --- |
| EXEC-006/concurrency | R `high volume pipeline` and [pipeline.py](../tests/pipeline.py) 8 MiB generation through multiple copying stages require exact byte count within bounds; early-closing reader completes | Serial launch-and-wait would deadlock. API gate uses blocked children to assert all started/reaped; partial pipe/fork failures assert cleanup in execute_faults.c |
| EXEC-006/redirection | E `pipe connected before output redirection`: stderr through pipe, stdout file; `pipe connected before input redirection`: explicit input wins | Both required connection-before-redirection directions |
| EXEC-006/isolation | R `pipeline builtin state is isolated`, `pipeline builtin assignment is isolated`; pipeline.py `exit`/`cd` in both stage positions | All children and wait-all are selected permitted policies; singleton stateful commands remain in caller |
| EXEC-007/status-table | E `pipefail=False/True negate=False/True statuses=(...)`: 16 combinations select last or rightmost nonzero, then invert; empty stderr/stdout and exact process statuses | No inference from completion order; earlier pipeline.py API stage-status checks preserve ordered statuses |
| EXEC-007/option-snapshot | E `option sampled before launch`: changing pipefail inside the final stage leaves results 0 then 9 | Setting at pipeline launch controls status |
| EXEC-007/signal | E `EXEC-016 signal selected by pipefail`: 128+TERM, empty output; R `negated pipeline` and pipeline.py final-signal negation | Host TERM mapping; exhaustive signal cases remain CSH-054 |

<a id="exec-008"></a><a id="exec-010"></a>

## EXEC-008 / EXEC-010 — lists and groups

Sources: [2.9.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_03),
[2.9.4.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04_01).
Implementation: execute.c `execute_plan`, `context_fork`.
EXEC-008: [contexts.py](../tests/contexts.py) crosses both statuses for both
AND/OR operators and asserts selected final status; R `AND OR equal precedence`
prints `[yes]\n`, R `list final status` returns 19. E `skipped branch has no
expansions` requires `end` and no effect file or expansion diagnostic.
EXEC-010: R `brace state persists`, `subshell state isolated`, `subshell exit
isolated`, `brace exit stops list` distinguish the environments and exit scope.
contexts.py literal nested-group redirects assert exact files and restored
stdout; cwd tests assert parent persistence versus isolation. This is not the
full ENV-006 inventory (umask, traps, options, aliases, IDs), owned by CSH-048/054.

<a id="exec-011"></a><a id="exec-012"></a><a id="exec-013"></a>

## EXEC-011–013 — loops, case and conditionals

Sources: [2.9.4.2–2.9.4.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04_03).
Implementation: execute.c `compound_body`, `execute_test`, fields/pathname pattern
matching. All C fixtures are runtime cases in three input modes.

| Stable scope | Exact assertions | Limit/owner |
| --- | --- | --- |
| EXEC-011/list and default | C `for expansion snapshot`, `for implicit parameter snapshot`, `for list expanded once` assert ordered expanded fields and independence of later parameter/value mutations | Required one-time word-list expansion; no empty-field loss |
| EXEC-011/zero and final | C `for explicit empty leaves variable`, `for last status`; E `implicit empty for status` requires 0 and unchanged variable, no body file | Explicit and implicit zero iteration; readonly loop variable failure is separately asserted |
| EXEC-012/pattern semantics | C `case quoted and unquoted patterns`, `case subject scalar and pattern substitution`, `case bracket slash dot`; E `subject once and later clauses skipped` | No field splitting of subject; subject once, first matching clause, no evaluation of later clauses |
| EXEC-012/status and fallthrough | C `case no match and empty body` yields 0/0; `case selected status` returns 21; `case fallthrough skips patterns` prints first/second; empty fallthrough retains 19 | Required `;;` termination and Issue 8 `;&` behavior |
| EXEC-012/unspecified ordering | C `case alternatives lazy expansion` selects the first matching alternative in cshell | Within-clause pattern evaluation order is unspecified; this fixture is policy evidence |
| EXEC-012/locales | [locale_cases.py](../tests/locale_cases.py) `locale UTF-8 case classes and quoted patterns` and host-qualified collation cases | CSH-042 results retained; [CSH-053](tickets/CSH-053-multibyte-lexical-boundaries.md) owns lexical non-UTF-8 gaps. Locale skips name installed-data conditions |
| EXEC-013/if | C `if elif else selection`, `unselected expansions`, `if no branch status`, `selected branch status`: selected branch only, absent side effects, zero or 17 | Required selection/status conditions |
| EXEC-013/while-until | C `zero loops`, `while until arithmetic`, `loop body status`; E `until body status and condition visibility`: failed condition visible as 1, final body status 19 | Required last-body/zero-iteration status; no claim about unbounded nesting |

<a id="exec-014"></a>

## EXEC-014 — functions (2.9.5)

Implementation: execute.c `define_function`, `flow_handler`, state.c function
and parameter frames. C `function definitions defer redirection` leaves its
file absent; `function definition redirect uses parameters` creates distinct
call-time files; `call and definition redirect order` asserts definition wins
and outer stdout restores. C `function nested parameters and return`, `return
implicit status`, `failed function redirect restores parameters`, `return
restores enclosing redirects` assert parameters/status/descriptor restoration.
E `zero unchanged and empty parameters restored` verifies `$0`, empty call
arguments and caller empty arguments; `variable and function namespaces`
asserts successful definition status and that `unset -f` retains variable `f`.
C recursive/redefined/unset-active-body cases retain owned AST lifetime.
Function-prefix export/lifetime is D-006, not an extra POSIX requirement.
The explicit recursion ceiling remains a documented size limitation under
CSH-046. [CSH-055](execution-contracts.md) adds nested function return, syntax
recovery/unwind and allocation-failure restoration witnesses.

<a id="exec-015"></a>

## EXEC-015 — error consequences (2.8.1)

Implementation: execute.c `runtime_simple`, `expansion_failed`, `execute_plan`,
`evaluate_input`; [main.c](../src/main.c) input loop and final exit.
E `EXEC-015 noninteractive ...` covers ten error categories in all three modes;
`EXEC-015 interactive ...` covers each in string/file `-i` mode. Every case
requires exact diagnostic and either no subsequent output or
`continued:<failing-status>\n`:

| Error category | Noninteractive | Interactive | Status before continuation |
| --- | --- | --- | --- |
| Special utility (`shift 99`) | Exit | Continue | 1 |
| Regular utility (`read -z`) | Continue | Continue | 2 |
| Special redirection | Exit | Continue | 1 |
| Compound redirection | Continue | Continue | 1 |
| Function redirection | Continue | Continue | 1 |
| External redirection | Continue | Continue | 1 |
| Readonly assignment | Exit | Continue | 1 |
| Expansion | Exit | Continue | 2 |
| Not found | Continue (permitted) | Continue | 127 |
| Special via `command` | Continue (required exception) | Continue | 1 |

Syntax: R `syntax error prevents execution`, V `eval parse failure`,
P `terminal eval syntax error recovers`; expansion and special errors also have
P `terminal expansion error recovers`, `terminal exit redirection error continues`,
`terminal control operand error recovers`. These assert combined terminal bytes
and subsequent commands, not just process survival. contexts.py readonly and
special errors in subshells assert parent survival. [input.py](../tests/input.py)
and trap/input-interruption tests cover input APIs and EINTR.
[CSH-055](execution-contracts.md#descriptor-and-command-read-witnesses) adds
public-main EIO injection for buffered commands, interactive input, pending
non-EXIT traps and dot/`command .` exceptions. These are distinct from EOF
and recoverable interruption.

<a id="exec-016"></a>

## EXEC-016 — statuses (2.8.2)

Implementation: execute.c `child_status`, jobs.c wait statuses, main.c final
status. R `nonzero completion`, `failure followed by blank lines`, `unknown
command`, `found but unexecutable`, and `signal retained ...` assert 37, retained
37, 127, 126 and 128+TERM in all modes. `unknown command parent continues` and
`signal parent continues` assert one subsequent output. E `signal selected by
pipefail` connects the D-007 status choice with Issue 8 pipeline selection.
A command deliberately returning 126/127 is not itself proof of a lookup error;
these two error cases also require the corresponding diagnostic. Complete
signal and wait/kill mapping remains CSH-054/052, especially platform-specific
signal numbers. Exit values outside portable 0–255 are separate policy cases.

<a id="u-003"></a><a id="u-004"></a>

## U-003 / U-004 — break and continue

Sources: break/continue DESCRIPTION, OPERANDS, EXIT STATUS and errors.
Implementation: execute.c `flow_handler`, `loop_transfer`, `compound_body`.
C `break nested levels` and `continue nested levels` assert depth 2 transfer
and no skipped-body output. E `U-003 default break status` checks innermost
transfer and status 0; C `loop count clamps` exits the outermost loop for 999.
E `U-004 default continue and success status` and `U-004 clamp to outermost
lexical loop` assert next for assignment, skipped files, and success status.
C `control through condition lists` and `control through negation and and-or`
cover lexical control from conditions/compound lists. Invalid counts, no-loop
commands, `break cannot cross function boundary`, and `break in subshell isolated`
are project robustness/policy witnesses: positive operands and same-environment
lexical enclosure are application preconditions, and non-lexical enclosure is
unspecified. `eval loop transfer` is therefore not a mandatory oracle for every
shell. [CSH-055](execution-contracts.md) adds while/until condition continues, nested
lexical transfers and explicit nonlexical policies. Signal interruption remains
CSH-054.

## Remaining obligations

[CSH-055](execution-contracts.md) fixes the prefix PATH/builtin lookup defect
and supplies assertions for its named execution conditions. CSH-047
owns expansion/declaration combinations; CSH-048 owns full environment/utility
state; CSH-053 owns multibyte lexical boundaries; CSH-054 owns residual signal,
job and loaded-PTY cleanup failures; CSH-052 owns host utilities and fallback
shell provisioning. CSH-049 retains cross-platform reruns and the evidence map.
These are applicable open obligations. Neither CSH-042 nor CSH-043's completed
narrow scope verifies the entire execution/case/redirection family.
