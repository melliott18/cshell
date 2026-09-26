# Base shell-option clause evidence

[CSH-051](tickets/CSH-051-shell-option-evidence.md) refines O-001, O-002,
O-004–O-007, O-009, O-012–O-014 and O-016–O-018. The
[run records](evidence/csh-051/README.md) identify the tested source, binaries,
platforms, complete fixtures and results. This is evidence for the assertions
below, not a complete shell conformance claim. CSH-012 remains gated by the
other applicable open requirements. The existing UP/XSI exclusions remain.

## Sources and interpretation

Reviewed against POSIX.1-2024, Issue 8, on 2026-09-26:

- [set, DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_26_03): option syntax, effects and defaults.
- [sh, OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_04): the same option forms at invocation.
- [2.7.2, output redirection](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_02): regular files, symlinks, exclusive creation and override.
- [2.9.2, pipelines](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_02): pipeline-start pipefail state and negation after status selection.
- [2.12, execution environments](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_12): shared environments and subshell isolation.
- [2.6.2, parameter expansion](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_02) and [2.8.1, errors](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01): nounset exceptions and environment-specific consequences.
- [2.5.3, PS4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03): trace prefix expansion and default.

Required option effects and status/error relations determine the oracles.
Exact diagnostic wording, report order/spacing, letter inventory order and
trace quoting are additional cshell regression assertions, not POSIX mandates.
No reference shell was used to generate expectations.

| Choice | Classification and tested policy |
| --- | --- |
| `set -o` report | Format unspecified; existing readable report is a project assertion. `set +o` must be reusable; both all-off and individually enabled states are actually reinput with `eval`. |
| Invocation `-o` / `+o` without a name | Unspecified; status 2 and a diagnostic are the documented project choice. A missing-name witness is not a standard-required rejection. |
| Attached `-oname`, `set -` | Attached names are accepted; lone runtime `-` is unspecified and retains the documented disabling policy. |
| `-h` | Obsolescent but base. Default off is permitted; extra optimization is optional. Test lookup after PATH changes with either setting. The name `hashall` is an extension, not a required Issue 8 name. |
| `-n` in interactive shells and their recursive subshells | Ignoring it is permitted. cshell honors it. Once on, `set +n` cannot execute; runtime off cases test acceptance while off, and invocation cases test on then off before parsing. No fabricated runtime on-to-off witness is claimed. |
| Dangling symlink with noclobber | Failure is permitted; cshell rejects it. Atomic exclusive creation is required; file-type checks need not be atomic with creation. The finite race witness tests competing creators, not every possible adversarial type/symlink replacement schedule. |
| `set +x` | Whether the disabling command is traced is unspecified. Its stderr is redirected away in new disable/round-trip cases; the following command must have no trace. |
| `${#@}`, `${#*}` | Results unspecified. They are excluded from the nounset exemption oracle; scalar unset length and pattern-removal errors are tested instead. |
| Monitor, notify, ignoreeof, nolog, vi | Existing UP applicability remains. Terminal monitor defaults/overrides are recorded as implemented conditional behavior, not a claim to support the complete UP profile. |

## Entry point and effect grid

[option_evidence_cases.py](../tests/option_evidence_cases.py) generates exact
case names of the form:

`options: CSH-051 O-001 OPTION ENTRY SPELLING STATE (MODE)`

`OPTION` is each row below; `ENTRY` is `invocation` or `set`; `SPELLING` is
`letter` or `name` (only `name` for pipefail); `STATE` is `on` or `off`; `MODE`
is `string`, `file` or `stdin`. These are 228 distinct cases. The archived
`options.json.gz` files contain every expanded exact name, argument vector,
script/input byte string, setup file and expected output/status/file assertion.
`make test-options` and the full runtime suite execute the same cases.

| Requirement / option | Enabled assertion | Disabled assertion | Implementation |
| --- | --- | --- | --- |
| O-002 allexport / a | A syntax assignment reaches the external helper as `csh051=value` | Helper observes `csh051=<unset>` | [state.c](../src/state.c), [prepare.c](../src/prepare.c) |
| O-004 noclobber / C | Existing `out` remains `old\n`, diagnostic, redirection status 1 | File becomes `new\n`, status 0 | [redirect.c](../src/redirect.c) |
| O-005 errexit / e | `false` terminates with status 1; no following output | Following `survived\n`, final status 0 | [execute.c](../src/execute.c) |
| O-006 noglob / f | Literal `<*.txt>\n` | Matching `<a.txt>\n` | [fields.c](../src/fields.c), [pathname.c](../src/pathname.c) |
| O-007 hashall / h | Function resolves executable through changed PATH: `first\nsecond\n` | Same lookup result | [execute.c](../src/execute.c), [state.c](../src/state.c) |
| O-009 noexec / n | No output and `effect` absent | Output and file both `executed\n` | [execute.c](../src/execute.c), [main.c](../src/main.c) |
| O-012 nounset / u | Unset scalar expansion: diagnostic, status 2, no later output | Empty expansion followed by `survived\n` | [expand.c](../src/expand.c), [arithmetic.c](../src/arithmetic.c) |
| O-013 pipefail | `(exit 7)` piped to `true` has status 7 | Same pipeline has status 0 | [execute.c](../src/execute.c), [jobs.c](../src/jobs.c) |
| O-014 verbose / v | Literal comment and arithmetic-containing input on stderr; expanded `2\n` on stdout | Same stdout, empty stderr | [input.c](../src/input.c), [execute.c](../src/execute.c) |
| O-016 xtrace / x | Expanded `+ echo 2\n` on stderr, `2\n` on stdout | Same stdout, empty stderr | [execute.c](../src/execute.c) |

Option parsing and storage use [invocation.c](../src/invocation.c),
[builtin.c](../src/builtin.c), [options.h](../include/cshell/options.h) and
[state.c](../src/state.c). Off invocation cases first enable, then disable;
`set` cases do likewise except for the noexec restriction above. The grid
therefore checks effects as well as spelling acceptance.

## Additional clause assertions

Names below omit the common `options: ` prefix and three mode suffixes.
Within a row, abbreviated subsequent names inherit its `O-NNN` prefix.
Names beginning `invocation` are the exact single-case suffix, without a mode
suffix unless it appears in the fixture. The executable fixtures are in
[option_cases.py](../tests/option_cases.py), except the generated grid and
[terminal cases](../tests/runtime_cases.py). Existing witnesses are retained
with their original scope.

| Row | Clause/condition and exact witnesses |
| --- | --- |
| <a id="o-001"></a>O-001 | `O-001 grouped and named`, `keep and replace positionals`, `invalid option`, `invalid name`, `invalid preserves state`, `report with terminator`, `plus alone operand`: option parsing, parameter preservation/replacement, and error atomicity. `invocation mapping string/file/stdin`, `named valid attached`, `named attached`, `bad named`, `double dash source`, `double dash command`, `interactive error atomicity` cover startup syntax and source mapping. `O-001 defaults report`, `reusable report`, `round trip`, plus `CSH-051 O-001 OPTION enabled report round trip` for nine options cover reports and actual restoration from enabled state. Noexec cannot run its own report. `invocation missing name` records the unspecified policy. |
| <a id="o-002"></a>O-002 | `O-002 all assignment sources` checks syntax, parameter assignment, arithmetic assignment, read, getopts (including OPTIND/OPTARG) and cd (PWD/OLDPWD) via exported environment values. `disable and temporary` checks export attributes survive disabling and prefix assignments stay temporary; `loop and child assignments` checks loop exports and child isolation. The effect/lifetime grid covers shared and separate environments. |
| <a id="o-004"></a>O-004 | `O-004 refuse and override` checks refusal, `>\|` and append; `create and dev null` checks new and nonregular targets; `symlink and dangling` checks regular-file symlink refusal and chosen dangling policy. `special builtin fatal` and `ordered redirects` assert shell error consequence and diagnostic fd destination. `concurrent exclusive creation` requires exactly one successful creator and intact winning content; `fifo is writable` tests a synchronized reader/writer. |
| <a id="o-005"></a>O-005 | `O-005 plain failure`, `final AND failure`, `final OR failure`, `tested contexts`, `elif and loop tested functions` distinguish nonfinal AND/OR, negation and if/elif/while/until tests. `function stops`, `function tested`, `negated function`, `loop body`, `while body`, `until body fails`, `case body` cover body failures and inherited exception context. `compound exempt status`, `subshell exception`, `function status after exempt body`, `eval status after exempt body`, `dot status after exempt body`, `loop retains body exemption` distinguish compound, subshell and simple-command return consequences. `pipeline child environment`, `pipeline function child`, `negated pipeline descendants` assert child-local termination. `substitution argument`, `substitution assignment`, `substitution tested`, `substitution isolated toggle`, `last substitution status succeeds`, `last substitution status fails` assert utility versus assignment status and last-substitution selection. `eval and dot exempt`, `eval exit`, `dot exit`, `alias exit` cover indirect execution. `traps: EXIT runs after errexit` in [trap_cases.py](../tests/trap_cases.py) asserts exit-action execution and the failing status. |
| <a id="o-006"></a>O-006 | `O-006 splitting still active`, `patterns still active`, `other expansion stages` check toggling filename generation while retaining splitting, quoted fields, case/parameter patterns, tilde, arithmetic and substitution expansion. |
| <a id="o-007"></a>O-007 | The entry/effect grid tests PATH invalidation and function lookup under both h states; `O-007 hashall and O-011 nolog` retains acceptance/cache smoke evidence. No speed or particular caching algorithm is required. |
| <a id="o-009"></a>O-009 | `O-009 no effects on same line`, `async activation`, `loop activation`, `condition activation`, `eval no effects`, `child isolation`: no execution, expansion or file creation after activation at each boundary. `still parses later input` and `eval continues parsing` require syntax diagnostics despite suppression. `O-014 noexec still reads` proves continued input consumption. `terminal noexec honored`, `terminal recursive noexec` assert the selected interactive policy, including nested subshells with a surviving parent. |
| <a id="o-012"></a>O-012 | `O-012 nounset parameter`, `nounset positional`, `nounset arithmetic`, `unset length`, `unset pattern removal`: diagnostic and terminating expansion error. `exempt default and empty`, `braced positional exemptions` check unset @/*, default/alternate/assignment operators and set-but-empty values. `contexts`, `here document`, `glob and case errors` preserve fatal consequences even in tested commands and alternate expansion sites. `subshell error stays local`, `substitution error stays local` require parent continuation and status 2; terminal `nounset recovery` and `arithmetic nounset recovery` require another successful prompt/command. |
| <a id="o-013"></a>O-013 | `O-013 last rightmost nonzero` checks rightmost failure, all-success, and both negated outcomes. `start snapshot` changes the option within a pipeline stage; `background retained snapshot` changes it in the parent after launch and checks retained wait status in both directions. `errexit integration`, `tested integration`, `background immediate status`, `negated async descendants` combine failure selection, tested contexts, asynchronous immediate success and wait consequences. [pipeline_fixture.c](../tests/pipeline_fixture.c) additionally checks raw and converted signalled-stage status. |
| <a id="o-014"></a>O-014 | `O-014 input timing alias eval dot` distinguishes physical source from alias replacement and includes eval/dot read boundaries. `physical continuations and heredoc` asserts original physical lines, unexpanded here-document input and expanded output. `noexec still reads` and `invocation verbose` check parsing without execution and no added newline at EOF. |
| <a id="o-016"></a>O-016 | `O-016 expanded trace`, `stderr destination`, `substitution trace`, `eval alias trace`, `trace precedes execution`: expanded words, assignments, quoting, redirected stderr, child tracing, alias expansion and ordering before command output on the same descriptor. `PS4 expansions` checks parameter/arithmetic/command substitutions in the prefix without recursive tracing. `disabling has no later trace` avoids an oracle for the disabling command itself. `closed trace descriptor` is a project robustness check. |
| <a id="o-017"></a>O-017 | The environment grid below checks each option's effect and state lifetime. Existing `O-017 function shares options` and `eval dot alias state` remain complementary letter-state witnesses. Errexit tested-context behavior and noexec activation require the specialized cases above rather than a mere copied bit. |
| <a id="o-018"></a>O-018 | `O-001 defaults report` checks all settable options off in three noninteractive input modes, including the permitted h choice; the entry grid checks explicit startup overrides. `terminal monitor default` checks `mi`; `terminal invocation job defaults` starts with `+m -b` and checks `bi`, then `bmi` after enabling monitoring. UP remains unselected. |

## Environment grid

The exact generated effect names are
`options: CSH-051 O-017 OPTION CONTEXT effect (MODE)` for all ten options,
all three modes and each of `function`, `braces`, `subshell`, `substitution`,
`eval`, `dot`, `alias`, `pipeline`, `background` (270 cases).
Each executes the option's probe through a dot input inside the named context.
Options a/C/e/f/h/u/pipefail are enabled before entering the context; n/v/x
activation is inside it. For n this is necessary: activation in the parent
would prevent entering the context at all.

For v/x, separate names ending `inherited effect` repeat all nine contexts
with the option enabled in the parent (54 cases). Verbose includes the eval
input itself before dot source; alias replacement is not input read again.
Xtrace uses an explicit probe trace file so wrapper commands do not obscure
which trace proves inheritance. Command substitution removes trailing output
newlines. Ordinary pipeline status comes from the final `cat`, while each
stage still enforces its own nounset/errexit failure. Background probes wait
for the owned job and assert its status before reading captured output.

Names ending `lifetime` cover all nine inspectable options (everything except
noexec), three modes, and eight contexts: function/eval/dot/alias share changes;
subshell/substitution/pipeline/background retain changes locally (216 cases).
They assert complete reusable reports after returning to the caller. Both
verbose and xtrace are silenced only for the report/cleanup commands; this
avoids imposing a disable-command trace choice. For noexec, observable effects
and parent continuation in its child and PTY witnesses replace impossible
post-activation reporting. Braces share the current environment by construction
and their effects are covered above.

All generated pipe fixtures use the shared bounded runner, a fresh directory,
`LC_ALL=C`, `LANG=C`, controlled HOME/TMPDIR, `PATH=os.defpath` and the
runner's documented environment sanitization. There are no locale-dependent
skips in this option map. Terminal fixtures use the runner's controlling PTY,
non-echoing input, prompt synchronization, EOF control bytes and bounded cleanup.
Full PTY and harness results are recorded alongside the option suite.
