# Shell locale and pathname qualification (CSH-067)

This finite audit closes the evidence inventory assigned by
[CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). It adds strict
public-runtime witnesses and identifies external prerequisites individually.
It does not establish every locale, filesystem, or whole requirement family.
External utility locale/ACL contracts remain with CSH-064/068.

## Sources and applicability

The normative oracle is POSIX.1-2024, not another shell:

- [XBD §6.2 Character Encoding](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap06.html#tag_06_02)
  distinguishes single-shift from locking-shift encodings. A supplied
  single-shift encoding requires utility support. Locking-shift utility use is
  **implementation-defined**, not an unconditional obligation to implement
  ISO-2022. Cshell's supported encoding policy is ASCII-compatible, self-contained
  characters; locking-shift source/values are unsupported. The decoder resets
  its `mbstate_t` for each character. Do not use invalid-byte fallback as proof
  of support for a valid state-dependent encoding.
- [XCU §§2.2, 2.5.3, 2.6 and 2.14](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html)
  define source quoting, startup lexical context, runtime locale categories,
  splitting, removal and pathname matching. [XBD §9.3.5](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap09.html#tag_09_03_05)
  supplies the bracket-expression rules, including locale-defined collating
  elements and primary-weight equivalence. Expected values below come from
  the supplied locale definition; libc `fnmatch` is not used to generate them.
- [XCU §2.14.3](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_14_03)
  requires read permission for a pattern component and search permission for
  preceding literal components. Permission/content-related directory failures
  act as no matches; other errors permit either failure or no matches. EIO
  failure is the project's selected policy, not the only conforming result.
  [XBD §4.16 Pathname Resolution](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap04.html#tag_04_16)
  supplies symlink and trailing-slash resolution rules.
- [sh OPERANDS/EXIT STATUS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html)
  permits a non-executable readable source; inability to read is an error.
  Exact status 1 and diagnostic spelling in the unreadable-script regression
  are cshell policies within that requirement.
- [XBD §8.2 LC_MESSAGES](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html#tag_08_02)
  says unspecified-format diagnostics **should** follow the selected language.
  This is a recommendation, not a requirement to supply translations into
  every installed locale. XCU §2.5.3 likewise uses “should”.
  [alias](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/alias.html),
  [unalias](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unalias.html)
  and [read](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/read.html)
  still require their diagnostic destinations and error statuses.
  Cshell supplies English application messages and host `strerror` suffixes.
  Missing application catalogs alone are not classified as a demonstrated
  mandatory-contract defect. They remain a documented localization limitation;
  this does not exempt locale selection or the required error consequences.

## Finite condition map

Q names refer to [`tests/locale_pathname.py`](../tests/locale_pathname.py), run
through `-c`, script files and stdin unless stated. L is
[`locale_cases.py`](../tests/locale_cases.py); M is
[`multibyte_cases.py`](../tests/multibyte_cases.py). Names, raw script/output hex,
selected environments and exact actual/expected streams/statuses for Q are in
[the run records](evidence/csh-067/README.md). All fixtures use owned temporary
paths. Tests of source bytes do not require creating a filename with those bytes.

| Requirement / finite residual | Implementation and strict witness | Applicability / retained limit |
| --- | --- | --- |
| ENV-004: initial decoding, runtime categories; single-shift source | `character.c`, `state.c`, `lexer.c`; M startup mutation/eval/dot/alias/substitution cases; Q `single-shift source expansion read {8eb6,8fa2af}`; L category precedence/restoration | Required for supplied encodings. EUC-JP SS2/SS3 now exercised on both hosts. P1 covers missing candidate encodings; locking-shift policy above is separate. |
| LEX-002: escaping whole non-UTF character | `lexer.c`; M `quotes and escaped character`, startup-change cases; Q single-shift source case | Required §2.2.1; byte-exact escaped character, no dropped constituent bytes. |
| LEX-004: multibyte double-quote boundaries | `lexer.c`, `expand.c`; same M/Q cases, plus M nested/backquote/heredoc paths | Required §2.2.3; supports selected complete characters only. |
| LEX-005: dollar-quote source and generated escapes | `quote.c`; M dollar-quoted source; Q `single-shift dollar escape protection` emits `AA`, tab, literal `*` | Required §2.2.4 for these representable escapes; D-003 byte policy retained. Unspecified NUL, excess digits, unknown escapes and unrepresentable controls are not given normative output. |
| EXP-004: non-UTF length/removal; multicharacter/equivalent patterns | `expand.c`; Q single-shift length `1`/`#?`; Q `defined multicharacter element in case removal pathname` checks all four removal forms; Q `defined equivalence class and quoted bracket` | Required §§2.6.2/2.14; P2 for the supplied collation locale. No universal non-C ordering claim. |
| EXP-007: multibyte IFS boundaries | `fields.c`; Q splits `a<SS2/SS3>b` into exactly two fields; M constituent-byte IFS; L UTF-8 distinct characters sharing a byte | Required §2.6.5; only space/tab/newline are IFS whitespace (D-003). Invalid IFS bytes are unspecified. |
| EXP-008: public symlink/trailing slash and permissions | `pathname.c`; Q `symlink and trailing slash`, `quoted prefix and repeated slash`, `owned read versus search permissions` | Required §§2.6.6/2.14.3. Dangling final symlink retained; directory link followed; trailing slash excludes files/dangling links; loop/non-directory are nonmatches. Read-only directory can enumerate final names; search-only literal prefix can reach a nested wildcard. P3 for bypassing credentials. |
| EXP-008: partial directory read and I/O errors | `pathname.c`; Q `partial readdir {EACCES,ENOENT}`, `readdir EIO project failure policy` | Instrumented public main/parser/executor, **not an unmodified binary on a failing filesystem**. Content/permission error discards already collected matches for that directory, retains good siblings; EIO aborts before command/redirection effects. P4 retains actual-kernel failure qualification. API allocation/cleanup evidence remains separate. |
| EXP-008/010: raw non-UTF filenames | `pathname.c`; M `pathname components`, `pathname literal plus wildcard` | Linux GB18030 passes. Darwin APFS returns EILSEQ on these setup bytes: P5, not a decoder failure or a pass. |
| EXP-009: non-UTF quote removal | `lexer.c`, `quote.c`, `fields.c`; M four quoting forms and fixed startup; Q single-shift four forms/dollar escapes | Required §2.6.7; results preserve exact encoded bytes and protection. |
| EXP-010: multicharacter collating element and equivalence | `pathname.c`, `expand.c` call libc `fnmatch`; Q two `defined ...` cases | Required §2.14 with supplied definition: `[[.ch.]]` consumes `ch`, `[[=a=]]` admits `a` and `A`; quoted brackets remain literal. P2 applies on Darwin. |
| EXEC-012: non-C case pattern | `execute.c`; Q cases select `ch` element and `A` equivalence arms; M literal-pattern matching | Required §2.9.4.3; same P2, no reference-shell oracle. |
| U-017: non-UTF reusable alias output and messages | `alias.c`; Q `single-shift alias reusable output` saves a definition, removes aliases, reconstructs using `eval "alias $definition"`, invokes restored name; M multibyte replacement | Required alias STDOUT/§2.3.1 for supplied characters. Q `alias diagnostic language policy {C,fr_FR.UTF-8}` asserts empty stdout, exact stderr/status 1; English spelling is policy. |
| U-027: single-shift read/IFS | `utility.c`; Q source/expansion/read case distributes two fields from SS2/SS3 data; M escaped delimiter/raw read/current-context witnesses | Required read/§2.5.3 with supplied encodings. No additional external-utility read implementation claim. |
| U-031: removal and diagnostic locale | `alias.c`; Q reusable-output case removes and restores alias; Q `unalias diagnostic language policy {C,fr_FR.UTF-8}` | Required state/error behavior; application-message language classification above. |
| SH-003: unreadable script operands | `input.c`, `main.c`; Q `SH-003 unreadable {unreadable,./unreadable}` (file mode) | Required failure; status 1, exact diagnostic, empty stdout, and absent script effect. Non-executable readable positives remain CSH-046. P3 if owner mode denial is bypassed. |
| ENV-004 and utility diagnostic suffixes | `state.c`, libc; L `locale host-qualified diagnostic ...` and `locale runtime diagnostic language` | C destination/status witnesses always run; French libc precedence/runtime translation passes on Linux. P6 on Darwin. Application prefixes are tested separately, not mislabeled translated. |

## Supplied definitions and external prerequisites

[`tests/locales/csh_067`](../tests/locales/csh_067) composes the host's `cs_CZ`
LC_COLLATE with `en_US` other categories. The glibc definition supplies the
`ch` element and `a`/`A` primary-weight equivalence (secondary weights order
`a` before `A`). CI/Docker compile it with UTF-8 using `localedef`; they also
supply `ja_JP` with EUC-JP. The record fingerprints the definition and its host
source dependencies. This is a test locale, not a production runtime dependency.

| ID | Unmet prerequisite and owner | Run disposition |
| --- | --- | --- |
| P1 | CSH-067: installed usable Shift-JIS/Big5/GBK locales and libc decoders on Linux | Three CSH-053 capability groups skip in Debian; Darwin exercises source bytes for all four candidate encodings. Neither proves all other encodings. |
| P2 | CSH-067: supplied `csh_067.UTF-8` definition compiled for the target libc; on Darwin a compatible locale-definition compiler/data provider is needed | Linux executes six exact collation cases. Darwin skips that group; installing a locale with an unrelated name/unspecified collation is insufficient. A failure after locale selection is a failure, never a skip. |
| P3 | CSH-067: owned filesystem and credentials that enforce owner mode denial | Both non-root records exercise it. Root/bypassing credentials report a capability skip; requested mode bits alone are not treated as proof. |
| P4 | CSH-067: controlled filesystem/provider that makes an actual directory read fail after an entry | Deterministic instrumentation exercises runtime consequences on both hosts. Actual failing-mount behavior remains unexercised; module tests remain module evidence. |
| P5 | CSH-067: filesystem accepting the specific raw filename bytes | APFS rejects the M samples with EILSEQ while byte-source cases pass. Linux filesystem accepts GB18030 samples. Do not convert APFS unavailability to source-decoding failure. |
| P6 | CSH-067: translated libc ENOENT catalog selected by an installed locale | Linux French catalog passes; Darwin candidates return the C text and skip translation only. Shell-authored translated catalogs are an optional future localization capability, not a missing mandatory translation oracle. |

The explicit prerequisites remain attached to CSH-067 after this inventory is
reviewed; future qualification must supply and record them before widening the
claims. No skip is counted as a pass. The complete family maps remain scoped.
