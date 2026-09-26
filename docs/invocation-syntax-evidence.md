# Invocation, lexical, grammar and alias evidence

[CSH-046](tickets/CSH-046-invocation-syntax-evidence.md) audits 21 requirement
families at the POSIX.1-2024 base profile. This is a clause/condition inventory,
not a claim of complete shell conformance. Each row below distinguishes public
runtime assertions from module assertions. [Run identities](#run-records) apply
to the named fixtures, including the existing cases reused here.

## Sources, oracle and execution contract

Reviewed normative sources (Issue 8, fetched 2026-09-26):

- [sh OPTIONS, OPERANDS, STDIN, INPUT FILES, STDERR and EXIT STATUS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html).
- [Shell language §§2.1–2.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_01),
  [§2.7.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_04),
  [§2.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01),
  [§§2.9.4–2.9.5](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_04),
  [§2.10 lexical conventions and grammar](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_10),
  and [§2.13 environments](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_13).
- [alias](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/alias.html) and
  [unalias](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unalias.html),
  DESCRIPTION, OPTIONS, OPERANDS, STDOUT, STDERR and EXIT STATUS.

The standard supplies the semantic expectations. No reference shell was used
to generate them. Exact error wording, status 2 for syntax errors, sorted alias
listing and the particular reusable quote spelling are cshell regression
assertions; the normative error requirements generally prescribe only a
nonzero status and diagnostic. Permitted and unspecified cases below test
explicit project policies separately from required behavior.

Fixture abbreviations used in the inventory:

| Label | Source and execution |
| --- | --- |
| S | [`tests/syntax_cases.py`](../tests/syntax_cases.py); every name starts `syntax: ` and ends `(string)`, `(file)` or `(stdin)` in generated `syntax.json` and `runtime.json`. |
| I | [`tests/invocation.py`](../tests/invocation.py); names printed verbatim, executes the public binary with custom argv/descriptor/identity setup. |
| R | [`tests/runtime_cases.py`](../tests/runtime_cases.py), cross-mode cases have the same three suffixes as S. Terminal names have no suffix. |
| E | [`tests/evaluation_cases.py`](../tests/evaluation_cases.py), prefix `evaluation: ` and the three input-mode suffixes. |
| X | [`tests/substitution_cases.py`](../tests/substitution_cases.py), the three input-mode suffixes. |
| C | [`tests/control_flow_cases.py`](../tests/control_flow_cases.py), prefix `control: ` and the three input-mode suffixes. |
| API | [`input.py`](../tests/input.py), [`lexer.py`](../tests/lexer.py), [`parser.py`](../tests/parser.py), [`alias_parser.c`](../tests/alias_parser.c); these never establish public-runtime coverage. |

S/R/E/X/C retain literal scripts, arguments, setup contents and exact expected
stdout/stderr/status/file assertions in the generators. `smoke.py` executes
each in a temporary directory with isolated HOME/TMPDIR, `PATH=os.defpath`,
`LANG=LC_ALL=C`, umask 077, five-second deadline, 65,536-byte output bound,
resource limits and process-group cleanup. No prompt is stripped. File inputs
are non-executable. The helper's `args` operation prints each argument in square
brackets, preserving empty arguments and embedded newlines. Generated suites
are platform-specific only for absolute helper paths and errno strings.

I uses the same resource/cleanup helpers, five-second deadline and output
bound, an explicit C locale/PATH/HOME/TMPDIR/TZ/PS1/PS2 environment and a separate
session. PTYs disable echo and output postprocessing. Detection probes use
`+m`, with no controlling-terminal requirement; they measure `isatty` detection
and prompt placement, not foreground process groups. R's terminal fixtures use
the full controlling-PTY harness for foreground ownership and recovery.

## Invocation and input clauses

Implementation: [`src/invocation.c`](../src/invocation.c) selects sources,
arguments and interactivity; [`src/input.c`](../src/input.c) owns byte input and
normalizes descriptor flags; [`src/main.c`](../src/main.c) executes complete
commands and reports status/prompts. [`src/state.c`](../src/state.c) stores the
argument mappings used by expansion.

| Row / clause and condition | Exact runtime witnesses and asserted result | Module evidence and remaining scope |
| --- | --- | --- |
| <a id="sh-001"></a>[SH-001](posix-matrix.md#sh-001): sh OPTIONS/STDIN, three command sources, utility input remains independent for `-c`/file; shared input resumes correctly | R `command stdin independent of string source` / `command stdin independent of file source` assert payload plus following command; `stdin has no command read-ahead` asserts payload unchanged. I `SH-001/006 binary tail pipe` / `regular file` also assert a `read` consumes exactly its data line and parsing resumes at the next command. | API `descriptor ownership, CLOEXEC, blocking, and no read-ahead` asserts borrowed-fd ownership; runtime claims are limited to the named input types. |
| <a id="sh-002"></a>[SH-002](posix-matrix.md#sh-002): sh OPERANDS, default/custom/empty command name, positional order and empties, implicit/explicit `-s`, standalone `-` | I's 13 `SH-002` names enumerate `implicit stdin`, `standalone dash stdin`, `explicit stdin operands`, `stdin dash operand`, `command default name`, `command explicit name`, `command empty name`, `command standalone dash`, `slashless non-executable script`, `relative slash script`, `absolute slash script`, `standalone dash script`, `double dash script`. Each asserts `<$0>`, `<$#>` and every `<argument>`, status 0, empty stderr. | API `invocation: … with copied operands` also checks ownership. Mixed `-` and `--`, or `-` following another operand, are outside the source's guarantees and are not normative cases. |
| <a id="sh-003"></a>[SH-003](posix-matrix.md#sh-003): sh OPERANDS, slash path or cwd lookup; execute permission unnecessary; PATH fallback optional | I's three non-executable script-path mappings use mode 0600. `SH-003 PATH-only negative (D-001)` places an executable only in PATH, expects 127/stderr and absent `effect`. R `missing script` and `directory script` assert errors. | D-001 chooses direct path opening without fallback. Read permission denial remains API evidence (`unreadable script diagnostic` when non-root); filesystem/ACL breadth is not claimed. |
| <a id="sh-004"></a>[SH-004](posix-matrix.md#sh-004): sh OPTIONS, `-i` or stdin plus both terminal descriptors; identity exception permits rejecting `-i` | I `SH-004 {stdin,forced,string,file} stdin-tty={False,True} stderr-tty={False,True}` covers all 16 combinations, asserting `$-`, exact prompts on stderr/PTY, status 7. `SH-004 unequal uid accepts -i (D-001)` and `unequal gid` verify unequal IDs in child setup then assert interactive/status 7. R `missing command operand`, `unsupported option`, `conflicting modes` assert usage diagnostics and status 2. | D-001 accepts `-i` even with unequal IDs. Identity probes require Linux root with setresuid/setresgid; native non-root skip belongs to CSH-046 and is covered by a separate Docker root run. ENV/history are UP, excluded by the selected profile, not tested by these probes. |
| <a id="sh-005"></a>[SH-005](posix-matrix.md#sh-005): sh INPUT FILES/EXIT STATUS, empty/blank/comment-only sources and retained last status | R `empty input`, `blank and comment input` assert 0/empty streams; `nonzero completion`, `nonzero final unterminated line`, `failure followed by blank lines` assert 37; `failure followed by success` asserts 0/output. PTY `terminal EOF initially` and `terminal failure then EOF` assert 0 and 37 with exact prompts. | Existing witnesses suffice for this input/status partition; command-specific errors remain with their owners. |
| <a id="sh-006"></a>[SH-006](posix-matrix.md#sh-006): sh INPUT FILES/STDIN, NUL-free parsed prefix, arbitrary remaining bytes, unlimited physical line length | I `SH-001/006 binary tail pipe` / `regular file` asserts byte-exact `00 ff 70…0a` payload consumed by `/bin/cat`, and file offset at end. `SH-007 nonblocking {pipe,fifo,terminal} (stdin)` supplies additional input kinds. [`portability.py`](../tests/portability.py) `large input line (file)` / `(stdin)` retains a 256-KiB-plus-sentinel value; S `large sequential complete command` runs 5,000 commands then prints `complete`. | API `file: embedded NUL and high byte` is byte-storage evidence only: NUL in the parsed prefix is outside guarantees. Large samples do not prove unbounded storage; the known recursive-size limit is tracked below. Interactive asynchronous competing readers are unspecified and excluded. |
| <a id="sh-007"></a>[SH-007](posix-matrix.md#sh-007): sh STDIN, nonblocking FIFO/terminal becomes blocking and stays so after completion, regardless of command source | I `SH-007 nonblocking {pipe,fifo,terminal} ({stdin,string,file})` asserts full flags during a utility read and after shell exit equal original flags with only O_NONBLOCK cleared; stdout `ready\npayload\n`, status 7, empty stderr. `SH-007 independent {string,file} stdin closed={False,True}` asserts regular-file flags unchanged and independent sources work with closed fd 0. | These nine positive and four exclusion cases found and fix the missing `-c`/file normalization. `csh_input_prepare_stdin()` now handles all modes. API checks retain allocation/read failure and borrowed-fd ownership coverage; fstat/fcntl failure injection is not claimed. |
| <a id="sh-008"></a>[SH-008](posix-matrix.md#sh-008): sh STDERR/EXIT STATUS and §2.8.1 diagnostic and continuation rules | R `syntax error prevents execution`, `incomplete final quote`, `special builtin error stops script`, `regular builtin redirection failure continues`, and `interactive special builtin error (string)/(file)` assert streams/status/continuation. All S/I noninteractive cases assert no unexpected prompts. PTY `terminal eval syntax error recovers` and `terminal invalid exit bad` assert recovery. | Syntax/usage/ordinary/special and interactive partitions are witnessed, not every utility's errors; utility and option completeness remain CSH-048–051. |

## Token and quoting clauses

Implementation: [`src/lexer.c`](../src/lexer.c) retains raw spelling/quote
context and recognizes tokens; [`src/parser.c`](../src/parser.c) classifies
context and nested substitutions; [`src/quote.c`](../src/quote.c) decodes dollar
quotes; [`src/expand.c`](../src/expand.c) consumes quote provenance.

| Row / clause and condition | Exact runtime witnesses and asserted result | Module evidence / policy boundary |
| --- | --- | --- |
| <a id="lex-001"></a>[LEX-001](posix-matrix.md#lex-001): §2.3 rules 1–10, EOF, longest operators, quotes, nested substitutions, blanks/comments, execution after complete command | S `comments and token boundaries` keeps embedded/quoted/escaped `#`, discards comment text and treats tabs as separators; `longest redirection operators` asserts append/clobber/dup/read-write behavior; `no expansion during token recognition` asserts no file or parameter mutation in skipped syntax. R `successful final unterminated line`; X `nested substitutions and embedded newline bytes`, `replay retains outer heredoc queue`; S alias timing below. | API `all POSIX operators and longest matches`, `adjacent operators` and nested-token cases inspect every token kind/spelling. These complement runtime, not replace it. D-008 S `shebang comment policy` treats `#!` as comment (unspecified §2.1); `reject \|&` and `reject >>&` reject unsupported operators before creating `effect`. |
| <a id="lex-002"></a>[LEX-002](posix-matrix.md#lex-002): §2.2.1 escaped literal character vs removed backslash-newline | S `escaped metacharacters` asserts each literal shell metacharacter and escaped space; `escaped newline joins word and operator` produces `onetwo\nyes\n` with a split `&&`. `alias quoting eligibility` includes a continued alias name. | API `longest match across physical continuations`, `escape context distinction` inspect raw spans/quote flags. |
| <a id="lex-003"></a>[LEX-003](posix-matrix.md#lex-003): §2.2.2 literal single-quoted characters, no embedded unescaped apostrophe, adjacency/empty fields | S `single quote adjacency` asserts empty word, joined fragments, literal dollar/backquote/backslash and embedded newline. R `literal quoting`, `multiline literal`. | API `all quote modes and empty adjacent quotes`, `multiline quoted word retains newlines`; unterminated quotes are syntax errors, not a mechanism for an apostrophe inside quotes. |
| <a id="lex-004"></a>[LEX-004](posix-matrix.md#lex-004): §2.2.3 literal context, special dollar/backquote/backslash, recursive command and parameter contexts | S `double quote escapes` distinguishes escaped dollar/backquote/backslash/quote/newline from literal `\q` and literal `$'…'` inside double quotes; `nested quote contexts` asserts literal-pattern removal, quoted `)` in substitution and nested default substitution. X `backquote execution and nesting`, `quoted positional expansion keeps empty arguments`, `pattern removal uses quote protection`. | API `quoted parameter pattern resets quote context`, `quoted parameter default retains quote context`, `quoted parameter escaped brace stays inside expansion`. Unescaped double quotes in non-substring `${…}` and improperly crossed backquote quoting have unspecified/undefined rules; no reference-derived mandatory output is assigned. Expansion operator breadth remains CSH-047. |
| <a id="lex-005"></a>[LEX-005](posix-matrix.md#lex-005): §2.2.4 named, control, hex/octal escapes; termination and retained quoting | S `dollar quote required escapes` checks `\"`, `\'`, `\\`, a/b/e/f/n/r/t/v, control A/DEL/FS, octal and hex with non-digit termination. `dollar quote retains protection` asserts IFS, wildcard, dollar and backquote are literal, adjacency and empty words retained. X `dollar quoted delimiter suppresses expansion`. | Decoder API [`fixtures/quote.json`](../tests/fixtures/quote.json) covers further byte/control boundaries. D-003 uses ASCII-compatible bytes on tested C locales. Missing character encodings and non-C encoding breadth remain CSH-042/047; unknown escapes, NUL-producing escapes, excess hex digits and octal overflow are unspecified and are not normative runtime assertions. |
| <a id="lex-006"></a>[LEX-006](posix-matrix.md#lex-006): §2.3.1 eligibility, recursive rescanning/suppression, trailing blanks, timing and environments | S `alias quoting eligibility`, `alias assignment redirect and argument positions`, `alias direct recursion`, `alias recursion and independent reuse`, `alias empty replacement`, `alias trailing blank`, `alias introduces grammar`, `alias same complete command timing`. E `aliases in eval dot and substitutions`, `alias function definition timing`; I `LEX-006/U-017 aliases not inherited by new invocation`. | API `command position and quoting`, `trailing-blank continuation`, `recursion and finite chains`, `alias changes between complete commands`, `nested substitutions and heredoc ownership`. D-004 policy-only S `alias quoted trailing blank policy`, `alias reserved spelling policy`, `alias injected separator policy`; see policy register below. |

## Grammar and alias utility clauses

Implementation: [`src/parser.c`](../src/parser.c), [`src/ast.c`](../src/ast.c)
and [`src/execute.c`](../src/execute.c) parse/store/execute grammar;
[`src/alias.c`](../src/alias.c) stores aliases and implements both utilities.

| Row / clause and condition | Exact runtime witnesses and asserted result | Module evidence / remaining limitation |
| --- | --- | --- |
| <a id="gram-001"></a>[GRAM-001](posix-matrix.md#gram-001): §§2.4/2.10.1–2 lexical classification; reserved positions, IO_NUMBER, NAME, ASSIGNMENT_WORD | S `reserved words as arguments and quoted commands` keeps all reserved spellings as arguments and makes quoted `if` a command lookup; `assignment and descriptor token positions` keeps post-command `value=literal`/spaced `2` as arguments and restores prefix assignment. C `for implicit parameter snapshot`, `if elif else selection`, `case quoted and unquoted patterns`. | API `assignment classification …`, `descriptor adjacency …`, `reserved-word context …`, `for variable context and optional separator …` inspect lexical categories. Rule 7 invalid assignment names are implementation-defined: current parser returns ordinary words; full nonportable-name behavior remains outside this portable-name claim. Extra reserved words and colon-suffixed words have unspecified cases; no blanket rejection oracle. |
| <a id="gram-002"></a>[GRAM-002](posix-matrix.md#gram-002): §2.10.2 productions for pipeline, and_or, list, group, simple command and redirections | R `AND OR equal precedence`, `negated pipeline`, `list final status`, `brace state persists`, `subshell state isolated`, `compound pipeline`, `ordered redirections`; S `longest redirection operators`, `large sequential complete command`. [`contexts.py`](../tests/contexts.py) covers asynchronous lists separately. | API `pipeline AND/OR and list precedence`, `AND/OR associate left equally`, `ordered redirections preserve every operator`. D-002 does not select IO_LOCATION: S `optional IO_LOCATION is ordinary word` writes literal `{slot}` to `out`, allocates no named descriptor. Redirection semantics beyond grammar belong to CSH-049. |
| <a id="gram-003"></a>[GRAM-003](posix-matrix.md#gram-003): §§2.3/2.7.4 ordered io_here queue, literal/quoted delimiters, <<- tabs, continuation and incomplete input | X `ordered expanded heredocs`, `quoted heredoc suppresses expansion`, `partially quoted heredoc suppresses expansion`, `heredoc continuations and tab stripping`, `nested heredoc inside substitution`, `replay retains outer heredoc queue`; R `quoted heredoc and following command`, PTY `terminal heredoc prompts`. These assert exact bodies, expansion order and following-command execution. | API `multiple heredocs retain source order and quoting`, `nested substitution heredoc queue resumes outer queue`, `heredoc delimiter/body …`, `incomplete construct …`. Saved tokens containing newlines and a substitution closing before the heredoc's starting NEWLINE are unspecified; no exact portable oracle is claimed. |
| <a id="gram-004"></a>[GRAM-004](posix-matrix.md#gram-004): §§2.9.4–5/2.10.2 compounds and functions | C `if elif else selection`, `zero loops`, `while until arithmetic`, `for expansion snapshot`, `for implicit parameter snapshot`, `case alternatives lazy expansion`, `case no match and empty body`, `case fallthrough skips patterns`, `case fallthrough empty body retains status`, `function parser lifetime`, `function definitions defer redirection`, `function definition redirect uses parameters`; R group cases above. | API `nested functions and every compound production`, `function definition with … body and attached redirections`, `case patterns ordered arms and POSIX terminators` reconcile structural alternatives. Runtime cases establish named productions/behaviors, not every nesting combination; recursive depth remains open. |
| <a id="gram-005"></a>[GRAM-005](posix-matrix.md#gram-005): §§2.8.1/2.9/2.10 error vs incomplete, complete-command timing, growing storage | S `invalid complete command has no effects`, `prior complete command survives syntax error` assert absent `effect` and retained `prior`; `large sequential complete command` asserts 5,000-command progress. R `incomplete final quote`, PTY `terminal multiline and blank prompts`, `terminal eval syntax error recovers`. I `GRAM-005 parser guard depth {127,128,129}`: 127 executes, 128 fails executor validation, 129 fails parser, both before effects. | API `incomplete construct …`, `200KB command word`, `10000 command words`, `1000 pipeline members`, `2000 sequential commands`, `10000 AND/OR commands and iterative destruction`. The recursive parser/executor limit is a known unmet requirement, retained under CSH-046; this bounded guard regression is not a passing unrestricted-size claim. |
| <a id="u-017"></a>[U-017](posix-utilities.md#u-017): alias DESCRIPTION/OPERANDS/STDOUT/STATUS and §§2.3.1/2.13 | S `alias query and reusable quoting` queries and restores definitions containing spaces, newline, apostrophe and empty value, compares complete before/after listings and executes the restored alias; `alias mixed query and definition` asserts missing-name diagnostic/status 1 while another definition succeeds. E `alias listing`, `alias complete line timing`, `alias isolation`, `alias function definition timing`; I new-invocation exclusion above. | API storage/handler fixtures test ownership/failure and invalid names separately. Required reusable syntax does not mandate cshell's sorted order or particular single-quote representation. Utility LC_MESSAGES/non-C encoding breadth remains CSH-042; API-only failure injection is not public-runtime failure coverage. |
| <a id="u-031"></a>[U-031](posix-utilities.md#u-031): unalias DESCRIPTION/-a/OPERANDS/STDOUT/STATUS and future token reads | S `unalias subshell and named removal` asserts subshell removal does not affect parent, named removal preserves other entries, `-a` empties table, with no unalias stdout; `unalias mixed missing operand` asserts status 1/stderr while existing requested name is removed. `alias same complete command timing` keeps the already-parsed alias but uses function after the next newline. E `unalias operand error`. | API `alias changes between complete commands` independently checks tree timing. Exact status 1/message is project policy within required nonzero/diagnostic bounds. Non-C diagnostics remain CSH-042. |

## Resolved policies and retained limitations

- **D-001:** no PATH search for a missing slashless script. Explicit `-i` is
  accepted with unequal real/effective user or group IDs. This is a permitted
  choice, not an assumption that privilege dropping is implemented.
- **D-002 (syntax only):** `{name}` before a redirection is an ordinary word;
  optional IO_LOCATION descriptor allocation is not selected. Offset and
  descriptor limits remain CSH-043/049.
- **D-003 (dollar quotes only):** the tested C locales use ASCII-compatible
  control bytes. Runtime encoding conditions not present on these platforms
  remain open under CSH-042/047; no unavailable locale is labeled inapplicable.
- **D-004:** [alias policy](aliases.md#specified-choices-and-boundaries) excludes
  reserved spellings, inserts a separator after replacement text, permits a
  quoted trailing blank to trigger eligibility, and applies changes after the
  current complete command. Dollar substitutions parse eagerly; backquotes
  parse when expanded. These selected alternatives are tested as policies.
- **D-008 (syntax only):** a leading shebang is an ordinary comment when cshell
  reads the source; it does not invoke the named interpreter. `|&` and `>>&`
  are rejected by ordinary grammar before effects. Expansion extensions remain
  CSH-047. This does not describe kernel shebang dispatch when executing a file.

No broad family is promoted to `verified` by this audit. The tables replace
vague “runtime evidence missing” descriptions with actual cases and narrower
boundaries. CSH-046 retains the recursive-size limitation and unenumerated
combinations; CSH-042/047 own encoding and expansion breadth, CSH-048–051 the
utility/execution/option families. The CSH-012 compliance gate remains closed.

## Run records

Validation identities and results are recorded in the
[CSH-046 ticket](tickets/CSH-046-invocation-syntax-evidence.md#validation-record).
Source/suite hashes, compiler flags, binary hashes, OS/libc, timestamps, image
identity, commands and logs accompany that record. Native macOS skips only the
two privileged identity probes; an explicit Linux Docker root run supplies
those observations. Full PTY and harness tests remain separate from I's
non-controlling terminal descriptor probes.
