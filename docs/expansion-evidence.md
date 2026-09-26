# Expansion, parameter and locale evidence

[CSH-047](tickets/CSH-047-expansion-evidence.md) decomposes ENV-002, ENV-004 and
EXP-001–011 for the POSIX.1-2024 base profile. The inventory records selected
runtime assertions, API-only contracts, implementation policies and remaining
limits. No complete family is promoted to verified. The CSH-012 compliance
gate remains closed, including for the known non-UTF-8 lexical defect in
[CSH-053](tickets/CSH-053-multibyte-lexical-boundaries.md).

## Sources and execution contract

Reviewed on 2026-09-26: Issue 8 Shell Command Language
[quoting §2.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02),
[parameters and locale §2.5](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05),
[word expansion §2.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06),
[errors §2.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01),
[command processing §2.9.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_01),
[subshell environments §2.13](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_13),
[pattern matching §2.14](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_14),
and [command DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/command.html).
The dated `9799919799.2024edition` copy of the shell chapter was used when the
undated endpoint denied access. The normative parameter table supplies the
operator oracles; no reference-shell output was copied into expectations.

| Label | Fixture source and exact-name convention |
| --- | --- |
| N | New [`tests/expansion_cases.py`](../tests/expansion_cases.py): prepend `expansion: ` and append ` (string)`, ` (file)` or ` (stdin)` to each name below. All 118 scenarios run in all three modes: 354 cases. |
| X | Existing [`tests/substitution_cases.py`](../tests/substitution_cases.py): append the same input-mode suffixes, without a prefix. |
| L | Existing [`tests/locale_cases.py`](../tests/locale_cases.py) and [`tests/portability.py`](../tests/portability.py): append the same suffixes except the standalone sparse-file probe. |
| F | Existing [`tests/fields.py`](../tests/fields.py): exact API case names, no public input mode. |
| V/A/Q | [`expand.json`](../tests/fixtures/expand.json) `expand contracts`, [`arithmetic.json`](../tests/fixtures/arithmetic.json) `arithmetic contracts`, [`quote.json`](../tests/fixtures/quote.json) `quote contracts`; API assertions are in the associated C fixtures. |

A brace-enclosed set in a name below denotes its listed Cartesian product,
not an unspecified wildcard. The generated `build/tests/expansion.json` retains
every exact name, literal script, argument vector, setup file and expected byte
string. `make test-expansion` runs N alone; N is also included in the ordinary
`runtime.json` consumed by `make test`. Existing X/L/F/V/A/Q cases are reused
without relabeling them as new runtime evidence.

The shared [runner contract](testing.md#authoring-fixtures) applies: a fresh working
directory, isolated HOME/TMPDIR, `PATH=os.defpath`, `LANG=LC_ALL=C`, umask 077,
five-second deadline, 65,536-byte stream bound, resource limits and descendant
cleanup. N/X assert exact stdout, stderr and process status; named `files`
assertions check contents or absence. The `args` helper prints each field in
brackets, so empty and split fields are observable. It also returns success
with no output for zero fields. Status is zero and stderr empty unless the
fixture overrides them. N's `parameter` table redirects output to `result`,
asserting its exact contents; errors assert that `result` was never created.
Exact diagnostic wording and status 2 are cshell regression choices, while a
diagnostic/nonzero failure is the normative requirement.

L overrides the locale explicitly and probes host availability; host-derived
collation and strerror expectations are tied to that libc and locale, not
universal orderings/translations. F additionally compares selected cases with
`/bin/sh`; its independently specified `expected` arrays are the oracle, and
reference comparisons are secondary observations. The identities record the
reference binary hash; this audit makes no reference-shell conformance claim.
No new PTY behavior is introduced. The full existing PTY suite is still run.

## Clause and condition map

<a id="env-002"></a>
### ENV-002 — positional and special parameters

Source: [§§2.5.1–2.5.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_01).
Implementation: [`state.c`](../src/state.c), [`expand.c`](../src/expand.c),
[`jobs.c`](../src/jobs.c) and [`execute.c`](../src/execute.c).

| Condition | Exact witnesses and assertions | Boundary |
| --- | --- | --- |
| Decimal positional indices, braces, longest variable name, count | N `positional braces and longest name`: `$10` → `a0`, `${10}`/`${010}` → `ten`, `${008}` → `h`, separate `${v}x`/`$vx`, count 10. | Invocation `$0` mapping is additionally covered by [CSH-046 SH-002](invocation-syntax-evidence.md#sh-002); function save/restore is CSH-049. |
| `@`/`*`, zero parameters, embedded endpoints, IFS join vs splitting | N `positional at and star IFS variants`, `zero positional fields and embedded at`, `selected operator word preserves positional fields`; X `quoted positional expansion keeps empty arguments`. Assert exact fields, including null arguments and selected default/alternate `$@`. | Quoted `@` in scalar contexts and modified `@`/`*` are unspecified; V `positionals()` tests the documented join/rejection choices, not a portable oracle. Unquoted empty positional fields are discarded, a permitted choice. |
| `?`, `-`, `$`, `!`, `0` and subshell inheritance | N `initial and subshell status` asserts 0 at startup and 1 inherited in both subshell forms; `special PID status options and zero survive subshell` compares PID/name inheritance, observes `f`, checks positive background PID unequal to `$$`, and wait status 17. X `argument expansion retains prior pipeline status`. | No literal PID is hardcoded. Exact flag ordering is project policy; interactive `i`/resumed-job `$!` evidence is [CSH-050](jobs-signals-evidence.md), not inferred from this noninteractive witness. |

<a id="env-004"></a>
### ENV-004 — startup interpretation, runtime categories and diagnostics

Source: [§2.5.3 LC_CTYPE/LC_COLLATE/LC_MESSAGES/LANG/LC_ALL](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03).
Implementation: [`state.c`](../src/state.c) locale refresh,
[`lexer.c`](../src/lexer.c), [`fields.c`](../src/fields.c),
[`pathname.c`](../src/pathname.c) and [`expand.c`](../src/expand.c).

L `locale LANG fallback`, `locale empty LC_CTYPE fallback`, `locale LC_CTYPE
overrides LANG`, `locale LC_ALL overrides categories` assert the chosen C/UTF-8
filename match. `locale runtime CTYPE assignment and unset`, `locale runtime
LANG and LC_ALL precedence`, `locale temporary builtin assignment restores
categories`, `locale subshell and substitution changes stay local` assert
character lengths and state restoration. `locale lexical UTF-8 syntax stable
after CTYPE change` retains UTF-8 literal bytes across eval/subshell parsing.
`locale host-qualified collation {selected locale} {LANG,category,LC_ALL}` and
`locale host-qualified diagnostic {C,selected translated locale}
{LANG,category,LC_ALL}` assert host-qualified order and exact error bytes;
`locale runtime diagnostic language` checks a runtime update when available.
See [locale contract](locales.md) for the full original inventory.

These are conditional locale witnesses. Unavailable UTF-8, distinct collation
or translated libc catalogs remain reasoned skips owned by CSH-042. The
startup lexical requirement is **not established for all encodings**:
CSH-053 owns syntax-valued trailing bytes in Shift-JIS and related quotation
paths. Internal cshell diagnostics have no translated catalogs. Invalid-locale
C fallback is a project policy tested by L, not evidence for valid locale
semantics. Neither a missing locale nor an invalid-byte probe is inapplicability.

<a id="exp-001"></a>
### EXP-001 — expansion order and contexts

Source: [§2.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06).
Implementation: [`expand.c`](../src/expand.c), [`prepare.c`](../src/prepare.c),
[`fields.c`](../src/fields.c), [`pathname.c`](../src/pathname.c).

N `expansions execute beginning to end` observes `022end`, final `v=2` and one
`x` in `effect`. `pathname expansion results never split again` observes
sorted filenames containing spaces/IFS bytes, then only split patterns under
noglob. ENV-002's positional witnesses cover the multi-field exception.
X `assignment expansion is scalar and sequential`, `redirection operands do
not split or glob`, `unquoted heredoc body rules`, `quoted heredoc suppresses
expansion`, and `substitution output is never shell syntax` retain the context
partitions and absence of a forbidden side effect. F `{assignment,pattern}
suppresses splitting and globbing` is API-only supplemental evidence.

D-008: N `policy brace expansion absent` leaves both brace forms literal.
Expansion/arithmetical nesting still has a 128-level guard; selected cases do
not establish arbitrary nesting support. CSH-047 retains that expansion limit;
the parser/executor size guard is separately retained by CSH-046. Assignment
and redirection expansion environments include source-permitted alternatives;
X `empty command redirection environment isolated` tests cshell's clone policy.

<a id="exp-002"></a>
### EXP-002 — tilde prefixes

Source: [§2.6.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_01).
Implementation: [`expand.c`](../src/expand.c) tilde handling and `getpwnam()`.
N `tilde protection empty HOME and syntactic sites` preserves spaces/wildcards,
assignment colon sites and the empty HOME field; `tilde expansion is not
recursive` distinguishes literal/escaped/expansion-produced tildes and colons
from a leading operator-word tilde. `tilde known login` derives the root login
and home from the executing host's password database; that identity is recorded
and the generated suite contains the concrete expected path. X `assignment
tilde sites` supplies another exact colon-site witness. V `tilde_and_quotes()`
checks trailing-slash normalization and additional quote states.

N `policy unset HOME leaves tilde` is explicitly unspecified-source policy.
Unknown/nonportable login spellings, database failures and every NSS backend
are not required-output claims. The tested hosts have a root password entry;
this suite does not pretend to cover hosts without one or cross-ABI generation.

<a id="exp-003"></a>
### EXP-003 — parameter operators and lazy words

Source: [§2.6.2 operator table](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_02).
Implementation: [`expand.c`](../src/expand.c) parameter evaluation/checkpoints.

N `parameter {unset,null,value} {-,:-,=,:=,?,:?,+,:+} {word,omitted}` comprises
48 independently executed scenarios (144 input-mode cases). It checks both
substituted value and variable state, not merely output agreement. Required
errors prevent redirection/command execution; wording/status are policy.
`lazy operator {-,:-,=,:=,?,:?,+,:+}` asserts selected substitution effects
exactly once and no effect for unselected words. `nested default assignment`,
`assign default stores unsplit value`, and `assignment operator removes operand
quotes before splitting` distinguish storage from later argument splitting.
X `lazy parameter operands` includes both substitution syntaxes; `short circuit
does not expand skipped commands` protects unreachable errors.

V `parameters()` adds readonly rollback and invalid assignment targets. The
lifecycle probe in [`substitution_fixture.c`](../tests/substitution_fixture.c)
repeats failed-word rollback ten times, asserts no forbidden file, restores
variable state and checks descriptor/child counts; it is API evidence.
PTY recovery from every possible expansion failure and all interactions with
nounset/allexport are not established here (option/error partitions remain
CSH-051). Modified special parameters with unspecified results are excluded
from the required-output table, not counted as verified.

<a id="exp-004"></a>
### EXP-004 — length and pattern removal

Source: [§2.6.2 length/removal](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_02).
Implementation: [`expand.c`](../src/expand.c) character boundaries and fnmatch.
N `all four removal operators and empty patterns` distinguishes shortest/longest
prefix/suffix, empty pattern and character count; `pattern operand quote
provenance and nesting` distinguishes active variable patterns from quoted
ones. `patterns slash dot classes and nonmatches` checks ordinary slash/dot in
removal/case matching, a digit class and unchanged nonmatch.
X `pattern removal uses quote protection`, `quoted POSIX class name remains
literal in removal pattern`, `substitution in removal pattern` retain nested
substitution/class quotation. L `locale UTF-8 parameter removal character
boundaries` asserts length 3 and all four removals for `éaé`.

V `multibyte()` also checks invalid-byte fallback, a project choice, not a
portable expectation. Non-C multi-character collating elements and equivalence
classes remain unverified; special `#`/`@`/`*` forms have source-specific
unspecified conditions. CSH-042 owns unavailable locale capabilities and
CSH-053 the concrete encoding defect; CSH-047 retains pattern breadth.

<a id="exp-005"></a>
### EXP-005 — command substitution

Source: [§2.6.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_03),
[§2.13](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_13).
Implementation: [`lexer.c`](../src/lexer.c) replay, [`parser.c`](../src/parser.c)
ASTs, [`execute.c`](../src/execute.c) capture and [`prepare.c`](../src/prepare.c).
N `substitution {dollar,backquote} newline state and status` preserves internal
newline, strips trailing newlines, returns assignment status 7 and leaves
parent state intact. X `backquote execution and nesting`, `empty substitution
fields`, `substitution splitting and protection`, `nested substitutions and
embedded newline bytes`, `large capture drains before wait`, `substitution
pipeline capture`, `pipeline substitution reads pipeline input` and `command
status overrides substitution status` cover distinct integration boundaries.
X `arithmetic-first command replay`, `replayed substitutions execute exactly
once`, `replay preserves lazy operands` and `grammar-valid arithmetic error
stays arithmetic: {1/0,1<<999,999999999999999999999999999999999999}` retain CSH-041.

D-004 selects eager dollar-form AST parsing and deferred backquote parsing;
[alias parsing witnesses](invocation-syntax-evidence.md#lex-006) constrain the
selected behavior. NUL capture is unspecified by the standard; X `expansion
failure prevents command: NUL capture` asserts cshell's rejection policy.
Redirection-only substitutions and alias-produced closing delimiters are not
portable-result evidence. The API `substitution ownership checks passed`
asserts 30 repeated captures, no fd growth, only owned children reaped and an
unrelated child left waitable; `substitution fault checks passed` exercises
capture failures. The wrapper now also requires empty stderr so a diagnostic
cannot silently pass. No output-only test claims that resource contract.

<a id="exp-006"></a>
### EXP-006 — arithmetic

Source: [§2.6.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_04).
Implementation: [`arithmetic.c`](../src/arithmetic.c), [`expand.c`](../src/expand.c).
N `arithmetic {constants,unary,multiplicative,shifts,comparison,bitwise,logical,
conditional,short circuit}` uses bounded defined operands; `arithmetic compound
assignments` observes every compound assignment result and final value 15.
`arithmetic signed variable constants and nested expansion` covers equivalent
variable/expanded signed constants and nested evaluation. `arithmetic invalid
variable diagnostic` checks failure before side effects. A `operators()`,
`assignments_and_variables()`, `short_circuit_and_rollback()` and `boundaries()`
provide direct numeric/state/error assertions (function names in the C fixture).

D-005: signed `long` is 64 bits on both recorded platforms. N `arithmetic signed
long boundaries` checks LONG_MAX and LONG_MIN. N `policy arithmetic {addition
overflow,division overflow,negative shift count,width shift count}` checks
safe rejection; these out-of-range inputs do not establish portable C arithmetic
results. `policy arithmetic negative right shift and comma` retains cshell's
round-down shift selection and comma sequencing (comma is a C operator, not an
extra shell syntax claim). API boundaries assert unchanged result/storage after
failure. Recursive variable expressions, increment/decrement, suffixes,
`sizeof`, floating point and exponentiation are not supported extensions.
Nesting is bounded at 128; no ILP32 or different integer representation was run.

<a id="exp-007"></a>
### EXP-007 — IFS splitting

Source: [§2.6.5](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_05).
Implementation: [`fields.c`](../src/fields.c) span-aware splitting.
N `IFS {unset whitespace,empty IFS,nonwhite empties,mixed whitespace,literal
delimiter,leading quoted empty,trailing quoted empty,between expansions}`
checks precise ordered fields. Empty IFS still removes implicit null values;
syntactic literal delimiters never split. Quoted empties at span boundaries
follow Issue 8, even where older reference shells differ. F `arithmetic
eligible for splitting`, `adjacent expansion punctuation`, `multibyte IFS
expansion boundaries` cover API-only additional provenance boundaries.
L `locale UTF-8 IFS whole characters and empty fields` covers public multibyte
splitting and `$*` joining.

D-003: only space/tab/newline are IFS whitespace. N `IFS policy extra whitespace
is nonwhite` checks vertical-tab delimiters with empty fields. Invalid IFS byte
sequences have unspecified results; bytewise fallback is documented, not used
to verify valid-character behavior. F's multibyte capability may skip if neither
UTF-8 locale exists; CSH-042 owns the capability (the native/Docker runs here
execute it). All other encodings and boundary permutations remain unverified.

<a id="exp-008"></a>
### EXP-008 — pathname expansion

Source: [§2.6.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_06)
and [§2.14.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_14_03).
Implementation: [`pathname.c`](../src/pathname.c), [`fields.c`](../src/fields.c).
N `pathname order components dot and unmatched`, `pathname expansion results
never split again`, `quoted wildcard with unquoted suffix`, `non-directory
component is a nonmatch` check C-locale sort, literal initial dot, per-component
slash traversal, nonmatches, no resplitting and noglob. Ignoring dot/dot-dot
entries is a permitted project choice, not a mandatory interpretation of `.*`.
F `directory symlink traversal`, `dangling symlink is pathname match`, `trailing
slash filters files`, `allocation, I/O, interruption and ownership failures`
are API-only additional cases. L collation witnesses are host-qualified.
Permission/search-denial combinations and arbitrary file-system errors are not
fully mapped to public-runtime cases; CSH-047 retains this narrower gap.

<a id="exp-009"></a>
### EXP-009 — quote removal

Source: [§2.6.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_07).
Implementation: [`lexer.c`](../src/lexer.c), [`quote.c`](../src/quote.c),
[`expand.c`](../src/expand.c) and [`fields.c`](../src/fields.c).
N `quotes from values remain data` distinguishes syntactic quotes from quote
bytes produced by expansion, joins adjacent fragments and protects a decoded
asterisk. IFS empty-field witnesses above retain quote provenance until final
fields; X `substitution output is never shell syntax` asserts no reparse.
F `set f removes quote syntax` and `assignment removes protection syntax`
cover API contexts. Q `quote contracts` and [CSH-046 LEX-005](invocation-syntax-evidence.md#lex-005)
map required and policy escapes. ASCII-compatible C/UTF-8 witnesses do not
resolve CSH-053 or establish quote handling for every locale encoding.

<a id="exp-010"></a>
### EXP-010 — pattern notation

Source: [§§2.14.1–2.14.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_14).
Implementation: [`pathname.c`](../src/pathname.c) pattern encoding,
[`expand.c`](../src/expand.c) removal and [`execute.c`](../src/execute.c) case.
N `pattern portable bracket forms` covers C ranges, negation, literal `]`/`-`,
digit classes, a single-character collating element and equivalence class.
`pathname slash before bracket interpretation` asserts the literal slash split
before bracket interpretation. N removal and pathname witnesses distinguish
leading dots/slashes across contexts. F `quoted character class name is literal`
and `bracket dot cannot introduce dotfile` supplement runtime witnesses;
the latter is a selected result where explicit bracket-dot matching is
unspecified. L `locale UTF-8 case classes and quoted patterns` covers a UTF-8
character and quotation. Multi-character/non-C equivalence classes, ambiguous
invalid brackets, trailing pattern backslashes and source-unspecified `^`
negation are not assigned portable oracles; CSH-047 retains breadth and CSH-053
owns the known constituent-byte defect.

<a id="exp-011"></a>
### EXP-011 — declaration utility context

Source: [§2.9.1.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_01)
and [command DESCRIPTION](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/command.html).
Implementation: [`prepare.c`](../src/prepare.c) `csh_command_arguments()` selects
context after command-name fields are prepared; [`builtin.c`](../src/builtin.c)
and [`execute.c`](../src/execute.c) dispatch.
N `declaration {export,readonly,command export,command command readonly}` asserts
scalar assignment operands through nested command wrappers. `ordinary utility
has no assignment context` asserts ordinary splitting and literal `b=~`.
D-006 N `policy expanded declaration {$cmd,command $cmd,command -- export}`
asserts cshell's expanded-name/option recognition selection, preserving spaces
and applying tilde expansion; the standard leaves those recognition cases
unspecified. X `declaration operands use assignment context` supplies the
original witness. Assignment lifetime/export/readonly failure combinations
remain separately owned by CSH-048/049; these tests do not verify all special
builtin behavior or future declaration extensions.

## Run records and remaining claims

[Validation identities and compressed logs](evidence/csh-047/README.md) record
source/test fingerprints, generated suite and executable hashes, compiler flags,
OS/libc/architecture, host login/long width, commands, results and concrete
locale skips. The [ticket](tickets/CSH-047-expansion-evidence.md#validation-record)
summarizes those runs. Stable matrix IDs remain broad **implemented subsets**;
this document supplies their condition partitions without falsely converting
selected witnesses into whole-family verification. Remaining scope has explicit
owners above, and reference agreement never opens the compliance gate.
