# Host utility and intrinsic lookup evidence

[CSH-052](tickets/CSH-052-host-utility-evidence.md) reviews POSIX.1-2024 XCU
§1.4, §1.6, §1.7 and the complete normative `printf`, `echo`, `test`, `true`,
`false`, and `kill` utility pages. This is a bounded integration profile, not
certification of the host's complete utility collection. The CSH-012 compliance
gate remains closed. [CSH-056](tickets/CSH-056-host-contract-gaps.md) owns the
specific host defects below. The [qualified profile and residual conditions](host-contract-profile.md)
record CSH-056's resolution; stock-host failures remain historical observations.

## Condition evidence states

These stable conditions split the broader matrix rows; a verified subset does
not promote its parent family. “Verified” refers only to the assertions and
platforms in the retained run record.

| Condition | State and scope |
| --- | --- |
| U-026/host-direct | Verified: external signal-number mapping and owned-child delivery |
| U-026/host-status-map | Verified in the CSH-056 qualified profile; Debian stock-host gap retained |
| U-034/scoped-access | Verified: listed exec/lookup operations and PTY stty, including provisioned ed in CSH-056 |
| U-034/host-ed | Verified in the CSH-056 qualified profile; Debian stock-host gap retained |
| U-035/core-format | Verified: named format/conversion/error witnesses below |
| U-035/numbered, U-035/b-precision | Verified in the CSH-056 qualified profile; Debian stock-host gap retained |
| U-035/locale-errors | Verified selected conversion/continuation and French-locale witnesses; broader catalogs/limits CSH-057 |
| U-036/base-operands | Verified: ordinary operands, newline and literal -- |
| U-036/selected-policy | Verified for the named C-locale host choices |
| U-036/host-environment | Verified named Apple/GNU POSIXLY_CORRECT policies and explicit policy selection; arbitrary alternatives CSH-057 |
| U-037/expressions | Verified: named base argument-count/primary/error witnesses |
| U-037/missing-timestamps | Verified in the CSH-056 qualified profile; macOS stock-host gap retained |
| U-037/capabilities | Verified positive block-node and non-root denial in dedicated native/Docker runs; extended identities/ACLs CSH-057 |
| U-038/base, U-039/base | Verified: no output, required status and unused stdin |
| U-040/dispatch-defaults | Verified: named argv/input/order/offset/environment/resource cases |
| U-040/host-boundaries | Selected failures/locales/system limits verified by CSH-056; individual remaining capabilities CSH-057 |
| U-041/selected-set | Verified: all 15 implemented names and named non-intrinsic controls |
| U-041/fc | Inapplicable: UP not selected; absent lookup is a profile witness |

## Assertions and implementation

Run `make test-host-utilities` (also in `make test`).
[Case definitions](../tests/host_utility_cases.py) contain the expected bytes,
status predicates and filesystem assertions. [The runner](../tests/host_utilities.py)
uses `smoke.capture`, with fresh directories, C locale, `os.defpath`, five-second
deadlines, a 65,536-byte combined output limit, process-group cleanup, and the
same CPU/file-size/descriptor/core limits as other fixtures. Every ordinary
name below has `(string)`, `(file)` and `(stdin)` variants; the terminal witness
has `(pty)`. The record includes input scripts, actual invocation, expectations,
actual bytes as hex, statuses, helper identities and setup source. No reference
shell supplies an oracle. A diagnostic predicate requires nonempty stderr;
its spelling is not a portable requirement. `nonzero` requires a positive shell
status; `error` requires status greater than one.

Host binaries supply utility semantics. [execute.c](../src/execute.c) owns
lookup, argv/environment handoff and status propagation; [redirect.c](../src/redirect.c)
owns shared descriptors. [builtin.c](../src/builtin.c), [utility.c](../src/utility.c)
and [jobs.c](../src/jobs.c) implement internal utilities. The small C observation
helper reads one environment variable or RLIMIT_FSIZE, or waits for a signal;
it supplies no utility-format oracle. Existing `evaluation: host utility
inventory` is a smoke witness only. The finer assertions here replace that
witness as the evidence for these rows.

A `GAP` is an unmet requirement, never a pass or an inapplicability decision.
The normal target reports the exact known host signatures separately from
passes; a changed failure signature fails the target. `--strict-gaps` makes
any gap fatal while preserving the normative expectations. An improved host
that satisfies the expectation becomes a pass. Missing `ed` on Linux is the
only recognized missing-tool gap; losing another dependency fails.

<a id="u-026"></a>
## U-026: external kill

Source: [kill OPTIONS, OPERANDS and EXIT STATUS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/kill.html).
`U-026 host kill signal number` requires `TERM\n`, empty stderr, status zero
for the actual SIGTERM number; `host kill exit status` requires the same for
128+SIGTERM. `host kill delivery` launches an owned helper, sends TERM through
the explicit host pathname, and requires `wait` to return 128+SIGTERM. The shell's
128+signal mapping is a documented implementation choice, not a mandated POSIX
encoding. No unrelated process is targeted.

`U-034 exec kill` separately proves exec accessibility. Native macOS passes;
Debian procps-ng 4.0.2 fails status-to-name conversion with status zero and a
stderr diagnostic. **U-026/host-status-map was missing on the CSH-052 stock host**; CSH-056 qualifies BusyBox kill;
no complete U-026 verification is claimed. Internal/job-aware kill stays with
[CSH-054](tickets/CSH-054-signal-contract-gaps.md).

<a id="u-034"></a>
## U-034: exact host scope

Source: [XCU §1.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_06).
The integration scope is `printf echo test [ true false pwd kill cat env find
ls stty ed sed head cmp chmod rm sleep sh`. All are inventoried with lookup
path, resolved path and SHA-256. Linux records installed package versions and
path ownership; macOS uses OS build plus executable hashes because these tools
have no common safe version flag. This list names dependencies of this suite;
it does not silently reduce the standard's system-wide utility requirements.
Python, the C compiler and Make are test infrastructure dependencies.

`U-034 lookup NAME` requires the independently resolved executable pathname
(except intrinsic `kill`). `U-034 exec NAME` invokes that pathname with `exec`
(except the `pwd` output check, which needs subsequent shell commands). Cases
assert a concrete operation: cat's two lines, env's isolated variable, find/ls's
single entry, sed/head's first line, cmp equality, chmod success, rm's file
absence, sleep success, sh's status 17, and the six core utility outcomes.
`pwd` requires an absolute result. The host inventory identifies its executable,
while U-033's existing evidence owns full logical/physical semantics.

`stty` on `/dev/null` must fail diagnostically. `U-034 stty terminal roundtrip`
uses the shared controlling-PTY harness, captures `stty -g`, enables echo,
restores the saved attributes, and compares a second capture byte-for-byte.
The terminal starts with canonical input, signals enabled, echo and output
newline translation disabled; all terminal output is compared as one stream.
The shared harness owns foreground process setup and session teardown.
`ed -s` must read the fixture's first line and exit successfully. Linux's absent
`ed` was **U-034/host-ed missing** in CSH-052; CSH-056 provisions ed in Docker and CI.
Other utility contracts, outside these declared integration operations, remain
host responsibility; this evidence never labels those complete pages verified.

<a id="u-035"></a>
## U-035: printf

Source: [printf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html),
especially OPERANDS, EXTENDED DESCRIPTION, EXIT STATUS and CONSEQUENCES OF ERRORS.
Every `U-035 printf …` invokes the external utility, with these exact suffixes:

| Condition | Case suffix / assertion |
| --- | --- |
| Format recycling and preserved empty/spaced operands | `reuse`: three angle-bracketed lines |
| Missing unnumbered arguments | `missing operands`: empty strings and numeric zero |
| Literal format and percent | `literal percent`: `a % b` plus newline |
| Decimal, base detection, unsigned, octal, hex | `integer conversions`: `-12 8 12 11 1f 1F` |
| Quoted character numeric operands and first-byte %c | `character constants`: `65 66 x` |
| String width/precision, left alignment, zero padding | `width precision`: exact bracketed fields |
| Specified format and %b escapes, octal byte | `format escapes`, `b escapes`: exact control bytes and `A` |
| %b early termination | `b stop`: only `one`, without trailing format/operands |
| %b precision | `b precision`: bracketed `ab` and tab; Linux host gap |
| Numbered argument selection and reuse | `numbered reuse`: `b:a` then `d:c`; Linux host gap |
| Utility syntax default | `end options`: leading `--` discarded, dash format preserved |
| Optional float conversion on these hosts | `C numeric optional float`: `1.50`; a selected host capability, not a base requirement to support floating conversions |
| Invalid/partial number | `invalid number`, `partial number`: output `0` / `12`, nonzero status and diagnostic |
| Overflow and missing format | `overflow`, `missing format`: nonzero and diagnostic; overflow's output value is not asserted |

Do not infer coverage for unspecified mixed numbered/unnumbered formats,
unknown escapes, or precision after `%b`'s `\c`. Numbered missing operands allow
alternatives and need a separate invariant witness, now supplied by CSH-056. **U-035/numbered** and
**U-035/b-precision** fail on GNU coreutils 9.1; native macOS passes. Locale
numeric formatting outside C, diagnostic catalogs, and conversion-error
continuation beyond these cases are now exercised by CSH-056; wider catalogs/limits remain CSH-057.

<a id="u-036"></a>
## U-036: echo

Source: [echo](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html).
`U-036 echo empty`, `ordinary` and `literal --` require newline/spacing,
preserved argument boundaries and literal `--`. No universal option terminator
rule is applied to echo. Base implementation-defined operands are delegated to
the selected host executable; changing PATH may select a different policy.
For the recorded system executables in C locale, `echo policy n/e/E/ne/backslash`
asserts the following documented choices:

| Input | macOS system echo | Debian GNU echo |
| --- | --- | --- |
| `-n value` | `value`, no newline | same |
| `-e 'a\nb'` | literal `-e a\nb` and newline | `a`, newline, `b`, newline |
| `-E 'a\nb'` | literal `-E a\nb` and newline | literal `a\nb` and newline |
| `-ne 'a\nb'` | literal `-ne a\nb` and newline | `a`, newline, `b`, no final newline |
| `'a\nb'` | literal backslash and final newline | same |

On macOS only an initial exact `-n` suppresses the newline; other e/E/n groups
remain operands, with backslashes literal. GNU echo processes initial groups
of e/E/n, defaults to literal backslashes, and `-e`/`-E` select escape processing.
These are host policies, not expansion oracles. XSI escape semantics are
inapplicable under the selected base profile. `POSIXLY_CORRECT` and arbitrary
replacement tools can change host behavior and are outside these C-locale
policy assertions; CSH-056 adds the named POSIXLY_CORRECT policies. Unqualified alternatives remain CSH-057.

<a id="u-037"></a>
## U-037: test and bracket

Source: [test](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html),
OPERANDS and the argument-count algorithm in EXTENDED DESCRIPTION.
Both `U-037 test …` and `U-037 [ …` exercise zero/one/two/three/four argument
forms defined by the base algorithm. Exact suffixes `zero`, `empty`, `one`,
`literal --`, `not empty`, `not word`, `nonempty`, `zero string`, `equal`,
`unequal`, `equal false`, `negated primary`, `negated binary` cover string
truth, negation and spaced argument boundaries. `integer eq/ne/gt/ge/lt/le`
requires each comparison's exact zero or one status.

`primary b/c/d/e/f/g/h/L/p/r/s/S/u/w/x/t` uses regular files, directory,
`/dev/null`, set-ID bits, regular/dangling links, FIFO, Unix socket, executable
and nonterminal stdin. `b` is a negative regular-file witness; it does not claim
access to a block device. `data -ef hardlink`, `new -nt old`, `old -ot new`,
`new -nt absent`, `absent -ot new`, `-e dangling`, `-e absent` add inode,
controlled timestamps and missing-file distinctions. All successful expressions
emit nothing and return 0/1 as specified. `bracket missing close` and
`invalid integer` require status >1 and a diagnostic. `--` is a nonempty
expression operand, not an option marker. Arbitrary >4 argument expressions,
`-a`/`-o` and historical parentheses are not base-profile oracles.

macOS fails the missing-file timestamp branches: **U-037/missing-timestamps**,
resolved by the CSH-056 GNU test/bracket selection. CSH-056 adds positive
block-node predicates and mode-000 denial under recorded non-root identities;
ACLs and unequal effective/real credentials remain CSH-057.

<a id="u-038"></a>
<a id="u-039"></a>
## U-038 and U-039: true and false

Sources: [true](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/true.html)
and [false](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/false.html).
`U-038 true` requires empty streams and zero; `U-039 false` requires empty
streams and any positive shell status. No particular nonzero value is normative.
`U-038 U-039 control` checks dispatch inside a conditional and OR list. The
exec, lookup, PATH override and unused-stdin witnesses identify the external
implementation and verify its integration. These scoped base outcomes are
verified by the recorded native/Docker runs; no options or operands are invented
for utilities whose base synopsis does not require them.

<a id="u-040"></a>
## U-040: defaults and exceptions

Source: [XCU §1.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_04).
`U-040 invalid option` (`cat -Z`) and `missing option argument` (`head -n`)
require empty stdout, diagnostics and nonzero. `operand order` requires cat to
concatenate second then first. `eight bit argv` transports bytes 128–255 through
a quoted substitution to external printf; `eight bit input` transports all
256 values through cat; both compare the resulting files byte-for-byte. NUL
is input data, not a shell argument. `environment scope` requires a two-word
prefix variable only in the child, then its original exported value; the env
exec case separately clears the environment.

`unused stdin COMMAND` leaves the first input line for `read` after each of
printf, echo, test, [, true and false. `seekable offset head -n 1` emits both
lines across head then cat; `seekable offset sed -n 1q` emits only the second
line from cat, confirming the shared input position after sed's silent early
exit. No seekability promise is made for pipes. `resource inheritance` verifies
that a 128-unit shell file-size limit is 65,536 bytes in the child. The suite's
CPU/output/descriptor limits are test protections, not proposed POSIX maxima.

`special syntax exception` confirms colon ignores apparent options. Existing
[state builtin evidence](state-builtin-evidence.md) owns the other special
builtin syntax rules; those are not overridden with a blanket `--` expectation.
Echo/test exceptions are tested above, printf's default separately. General
cross-utility locales, interruption/write failures, and documented host maxima
are split into CSH-056 passing witnesses and the explicit CSH-057 capability inventory. A selected test for each default is
not whole-family verification.

<a id="u-041"></a>
## U-041: intrinsic allocation and precedence

Source: [XCU §1.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_07)
and [§2.9.1.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_04).
The standard list has 16 names. The implemented set has 15: alias, bg, cd,
command, fg, getopts, hash, jobs, kill, read, type, ulimit, umask, unalias, wait.
UP-only `fc` is absent; `fc excluded UP` records that profile decision. bg/fg
are tested for lookup and the existing disabled-job-control diagnostic, not
for UP behavioral completeness.

For every implemented name, `intrinsic report NAME` succeeds with PATH missing;
`intrinsic execute NAME /missing` and `… shadow` execute its real handler despite
missing PATH or a same-name executable returning 73. `function precedence NAME`
requires the function's status 61. `command bypass NAME` suppresses that function
and invokes the real utility (except command itself, whose own function takes
precedence). `special reports` separately lists all 15 special builtins;
`assignment categories` checks special assignment persistence. Existing CSH-048
covers temporary intrinsic versus persistent special assignment scopes in depth.

`external PATH NAME` and `external missing NAME` cover printf, echo, test, [,
true, false and pwd: a replacement returns 73, a missing command returns 127
with a diagnostic. `pwd` therefore remains a PATH-associated regular builtin.
The category tables in builtin.c and execute.c contain no additional intrinsics;
this source inspection complements the finite name tests. U-041/selected-set
lookup is verified for this revision; it is not a claim about every string or
prefix-PATH selection (the known pwd prefix defect remains CSH-055).
