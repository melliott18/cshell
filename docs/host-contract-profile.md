# Qualified host contracts and remaining boundaries

Current residual qualification belongs to
[CSH-064](tickets/CSH-064-host-platform-external-prerequisites.md), after the
integrated CSH-063 work. The numbered sections below retain their historical
qualification scopes and handoffs. See [CSH-063 supplied platforms](#csh-063-supplied-platforms)
for the latest result and [CSH-012 reconciliation](evidence-reconciliation-current.md)
for milestone acceptance.

[CSH-056](tickets/CSH-056-host-contract-gaps.md) qualifies the
[opt-in profile](../tools/host-profile/README.md). Its
[retained evidence](evidence/csh-056/README.md) is separate from the CSH-052
stock-host observations. The original five failing requirements have unchanged
expected bytes/statuses. The ordinary system PATH still has its recorded
defects; only the named profile receives the narrower passing claim.

## Residual conditions

`tests/host_boundary_cases.py` supplies the following cases through all three
invocation modes. `make test-host-profile` enables them and strict-gap handling.

| Condition | Assertions / policy and source |
| --- | --- |
| U-035/locale-errors | `numbered missing` accepts either empty-string substitution with success or a diagnostic with nonzero status, as allowed by [printf OPERANDS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html). Stream/status alternatives are matched together. `conversion continuation` checks invalid, partially numeric, positive-overflow and negative-overflow operands followed by `after`; exact outputs are 0, 12, INTMAX_MAX and INTMAX_MIN. Diagnostics and nonzero status are mandatory. |
| U-035/non-C | French LC_NUMERIC produces `1,50`; French LC_MESSAGES is passed to the diagnostic continuation case. Diagnostics must be nonempty, but translated wording is not required: the selected standalone printf has no message catalog. Optional floating conversion is supported by this profile, not required of every base implementation. |
| U-036/host-environment | POSIXLY_CORRECT enables backslash processing for both recorded hosts. GNU retains an exact initial `-n` option; Apple treats it as an operand. `-e` is an operand in both tested forms. The assertions follow [GNU echo source](https://github.com/coreutils/coreutils/blob/v9.1/src/echo.c) and [Apple echo source](https://github.com/apple-oss-distributions/shell_cmds/blob/main/echo/echo.c), with independent hashes in each run. Arbitrary PATH alternatives need an explicitly selected supported policy and fresh qualification. |
| U-037/capabilities | Both test and bracket deny r/w/x on a mode-000 owned file under the recorded non-root EUID/EGID/groups. Both identify a supplied block node; the runner validates its type independently using stat. The macOS witness is `/dev/disk0`; Docker uses a disposable node, never device I/O. [test OPERANDS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) defines the predicates. |
| U-040/failures | `closed stdout` checks printf, echo, cat, head, sed, ls and find: a helper closes descriptor 1 and execs the actual selected utility. Nonzero status and a diagnostic are required. Missing operands/files or invalid duration exercise cat, head, sed, cmp, chmod, rm, find, ls, env, sh and sleep. Existing stty nonterminal and printf/test diagnostics remain applicable. |
| U-040/interruption | The helper forks an owned sleep, waits for the close-on-exec pipe handshake, sends TERM, reaps it and returns 143. The outer shell must propagate that status. This witnesses the helper's status handoff and sleep termination, not every utility's signal policy. Existing direct external kill delivery remains a separate witness. |
| U-040/locale-input | French LC_NUMERIC/LC_MESSAGES with empty LC_ALL preserve cat's ordered operands and all 256 input bytes. |
| U-040/limits | Each result records host ARG_MAX, OPEN_MAX, LINE_MAX and filesystem NAME_MAX, PATH_MAX, PIPE_BUF. These are system/path queries, not invented per-tool maxima. Cat and sed preserve an 8192-byte line. The child harness still caps descriptors at 64, file size at 1 MiB, output at 65536 bytes, and CPU at six seconds; those are test protections. |

## CSH-059 bounded extensions

[CSH-059](tickets/CSH-059-host-boundary-capabilities.md) extends the profile with
[case definitions](../tests/host_capability_cases.py) and
[retained native/Docker evidence](evidence/csh-059/README.md). Each ordinary
case runs through string, file and stdin invocation. Expectations are authored
independently; no selected utility supplies its own expected bytes.

| Stable condition / source | Bounded assertion; remaining scope |
| --- | --- |
| U-035/byte-format — [printf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html) | All 256 byte values from format octals and `%b`; embedded NUL with precision, left/right padding, numbered reuse and `\c`; UTF-8 precision is measured in bytes. CSH-059 found and corrected upstream `%b` truncation at NUL. This is not a whole-page claim. |
| U-035/format-allocation-limits — printf | 8192-byte format, `%b` operand and width; 256 conversions. Allocation failure, stack exhaustion and maximum format sizes remain limited. Literal `%b` width/precision above `INT_MAX` are rejected by the local adapter; that is a declared implementation limit, not a system ceiling. |
| U-035/locale-catalogs — printf | C, French numeric/messages and the recorded UTF-8 locale only. The standalone implementation has no message-catalog lookup; no translated diagnostic wording is required by these assertions. Other locales and full format combinations remain unqualified. |
| U-036/alternative-policies — [echo](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html) | Existing explicit Apple/GNU policies retained; 8192-byte operand, 256 arguments and UTF-8 operands checked. Other implementations and actual exec-size boundaries remain limited. |
| U-037/extended-permissions — [test/bracket](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) | Dedicated non-root mode-000 denial and stat-only block-node witnesses retained. ACLs, unequal real/effective identities and other device namespaces are separate limitations. Missing French/UTF-8 locale, root identity and absent block node are independently emitted per run. |
| U-040/host-boundaries — [§1.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_04), [§1.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_06) | Per-utility bounded operations and residual conditions below; no family promotion. |

## CSH-060 controlled environments

[CSH-060](tickets/CSH-060-extended-host-environments.md) adds
[environment cases](../tests/host_environment_cases.py) and
[retained evidence](evidence/csh-060/README.md). Expectations remain independent
of selected utility output. Ordinary cases run through string/file/stdin modes.

| Condition / source | Bounded assertion and remaining scope |
| --- | --- |
| U-035/format-allocation-limits, full-format — [printf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html) | 27 authored format combinations, four malformed/adapter-range cases, and test-only `strdup`/`realloc` ENOMEM injection with successful controls. The instrumented executable includes the exact production adapter/vendor source; it is never installed into the profile. libc failures, stack exhaustion and full format combinations remain unqualified. The CSH-059 binary regression and provenance are unchanged. |
| U-035/other-locales — printf | Independently probed German numeric locale produces `1,50`; available GB18030 preserves authored two/four-byte characters through `%b`. Catalog lookup is still absent. Missing German and GB18030 locales are separate limitations. |
| U-036/alternative-policies — [BusyBox source](https://git.busybox.net/busybox/tree/coreutils/echo.c?h=1_35_0) | Explicit `busybox-fancy` policy covers the configured `FEATURE_FANCY_ECHO` build, including ignored POSIXLY_CORRECT. `-e` enables escapes, `-n` suppresses newline, and default backslashes stay literal. Actual selected executable/hash and policy source are recorded. Other configurations remain unqualified. |
| U-036/argument-limits; U-040/true-exec-resources, false-exec-resources, env-ARG_MAX — [exec](https://pubs.opengroup.org/onlinepubs/9799919799/functions/exec.html) | Single and aggregate oversized vectors require kernel E2BIG before entering echo/env/true/false. The helper records child ARG_MAX, operand count/bytes and fixed environment bytes. It caps allocation independently at about 16 MiB. These are oversized rejection witnesses, not exact successful thresholds or utility limits. |
| U-037/ACLs, unequal-identities — [test](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) | Linux-root opt-in checks named ACL read grants/denials with equal IDs, and owner/group reads with unequal real/effective IDs in both directions. Actual IDs/empty supplementary groups, numeric ACL and stat metadata are recorded. The combined unequal-ID ACL grant fails for Debian 12 coreutils 9.1; `--unequal-acl` retains the strict failure with no allowance. Darwin, inherited ACLs and further credential combinations remain limited. |
| U-037/device-namespaces — test | Private Linux character/block nodes are created and stat'ed only. Dedicated non-root runs retain a separate supplied block node. No device is opened. Other namespaces remain limited. |
| U-040/cat-filesystem-limits, sed-space-limits — [cat](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cat.html), [sed](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sed.html) | Child-only 1024-byte RLIMIT_FSIZE and ignored SIGXFSZ require diagnostic failure and exactly 1024 bytes of retained output. UTF-8 and GB18030 character witnesses supplement finite spaces. Real filesystem I/O faults, maxima and broader locale expressions remain limited. |
| U-040/find-depth-locale-limits, chmod-ACL-identity-filesystem, rm-depth-mount-prompt — [find](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html), [chmod](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html), [rm](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | UTF-8 `?` matches one character; a non-owner chmod fails without changing metadata; explicit `rm -i` yes/no input requires a prompt and independently checked file state. Other filesystem/depth/terminal conditions remain limited. |

The remaining inventory retains all 27 stable residual rows with updated reasons,
actual platform/capabilities, source and next owner CSH-061. Root identity,
absent explicit block node, unavailable locales and absent controlled-environment
opt-in remain separate run-specific limitations. Root controlled runs do not
claim ordinary non-root mode-000 denial. Neither strict subset success nor an
allocation fault injection establishes universal host qualification.

## Explicit remaining capability limits

[CSH-062](tickets/CSH-062-host-contract-controlled-platforms.md) is the next owner for
residual conditions. The executable inventory and platform in **each run**
identify the environment to which its limitations apply. The machine-readable
[condition inventory](../tests/host_capability_limits.py) emits each source page,
reason, next owner and selected executable identity, including both test and
bracket. Conditions remain **unqualified**, never passes or inapplicability decisions. The unequal-ID ACL grant additionally has a retained failing reproducer.
The following table records the CSH-059 boundary snapshot; the later numbered sections extend it. Each linked page is its normative source. The current machine-readable inventory assigns residual qualification to CSH-064.

| Utility / source page | Evidence boundary and remaining capability |
| --- | --- |
| [true](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/true.html), [false](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/false.html) | Required status/no-output witnesses retained; system exec-resource failure untested. Neither utility has a claimed input/output maximum. |
| [pwd](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html) | Deleted cwd fails diagnostically using the inventoried external pathname. Inaccessible ancestors and pathname limits need controlled permissions/filesystems. |
| [kill](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/kill.html) | Owned-child delivery retained; cross-user failure and process exhaustion need additional identities/resources. |
| [cat](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cat.html) | All 256 values repeated in a 64-KiB file preserved; I/O faults and maximum file size untested. |
| [env](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/env.html) | Environment/exec-error witnesses retained; aggregate ARG_MAX and per-argument boundaries not reached. |
| [find](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) | File found under 32 nested `d` directories; descriptor/depth exhaustion and locale-sensitive matching untested. |
| [ls](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html) | 256 ordered C-locale entries and one UTF-8 filename; larger directories and locale collation untested. |
| [stty](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/stty.html) | Controlled PTY roundtrip retained; physical serial/terminal capabilities unavailable in a PTY. |
| [ed](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html) | 1024-line edit buffer printed exactly; maximum buffer/temp-file limits and signal recovery untested. |
| [sed](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sed.html) | 32768-byte line preserved through pattern/hold space; UTF-8 dot matches one character. Maximum space sizes and other multibyte expressions untested. |
| [head](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/head.html) | Count 2147483647 on two lines succeeds; maximum accepted count and interrupted input untested. |
| [cmp](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cmp.html) | Silent difference at byte 65537 returns 1; EOF difference requires status 1 and a diagnostic. Larger offsets and interrupted input untested. |
| [chmod](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html) | Mode update/error witnesses retained; ACL/cross-user/filesystem effects need controlled environments. |
| [rm](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | Owned 32-level tree removed; exhaustion, protected mounts and interactive prompts untested. |
| [sleep](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sleep.html) | Owned-child TERM retained; maximum duration cannot be established within a five-second fixture. |
| [sh](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html) | Invocation/status witnesses retained; host parser/resource/locale semantics need separate qualification. |

The sleep interruption witness does not establish interrupted I/O or signal
recovery for other utilities. No operation opens a real block device, reads real
disk contents, or signals unrelated processes. Trees and data files are private
fixtures removed by the harness.

`host_limits` records parent ARG_MAX/OPEN_MAX/LINE_MAX. `child_resources` records
actual soft/hard RLIMIT_CORE/CPU/FSIZE/NOFILE after the harness applies its bounds,
plus child ARG_MAX/OPEN_MAX. `filesystem_limits` queries the filesystem where
temporary fixtures run, not the source checkout. These are system queries and
harness protections; successful finite sizes above are not utility maxima.

Strict gaps remain fatal in the opt-in profile; stock-host failures remain
separate. Neither U-040 nor a parent utility family is promoted, and the CSH-012
gate stays closed.


## CSH-061 controlled ACL residuals

[Retained evidence](evidence/csh-061/README.md) adds access/default ACLs with
read/write/execute grants, unrelated-identity denials and mask denials for named
users and supplementary group 10003. Test and bracket predicates are checked
alongside independent actual read, append and private-helper execution.
Parent/child ACLs, metadata and actual real/effective IDs/groups are recorded.
This qualifies only the supplied Linux equal-ID fixtures and filesystem.

The unequal-ID strict reproducer retains six failures with success expectations
unchanged. Dynamic linkage and direct probes identify glibc 2.36's euidaccess
mode-bit path: the effective-ID ACL grant succeeds through faccessat and actual
open but fails through euidaccess. Utility/libc vendors own implementation.

The machine-readable inventory preserves all 27 existing conditions and adds
an independent unavailable privileged Darwin ACL condition. Missing root,
locales and explicit block witnesses remain separate. The next qualification
owner is [CSH-062](tickets/CSH-062-host-contract-controlled-platforms.md); bounded
passes do not promote any parent family or satisfy CSH-012.

## CSH-062 supplied platforms

[CSH-062](tickets/CSH-062-host-contract-controlled-platforms.md) adds 108
controlled ACL cases (324 string/file/stdin assertions) for multiple named
users, two supplementary groups, named-user precedence and masks, across
access/default ACL read/write/execute. The strict unequal-ID option applies
the same success expectations to the new combinations. Actual read bytes,
appended bytes and executable markers remain independent controls.

`--fixture-root` selects an explicitly supplied disposable filesystem for both
cases and queries. Records include device and Linux mount identity; setup
errors retain command/status/diagnostic failures instead of losing the result.
Debian 13 overlay and an ext4 Docker volume pass the equal-ID profile; tmpfs
ACL setup is unsupported on the recorded Docker kernel. The GNU 9.7/glibc 2.41
strict unequal-ID run still fails 114 grant assertions, with actual operations
passing. Native macOS does not supply a privileged Darwin ACL environment.

[Retained results and reproduction](evidence/csh-062/README.md) include vendor
identities, sanitizers and native/Docker/BusyBox runtime/PTY integration.
All 28 residual rows remain individually sourced; conditional missing-root,
locale and stat-only block witnesses remain separate and now also carry
selected executable identities. [CSH-063](tickets/CSH-063-host-platform-residual-qualification.md)
owns the remaining conditions. Utility families remain open and the CSH-012 gate stays closed.


## CSH-063 supplied platforms

[CSH-063 results](evidence/csh-063/README.md) add 144 controlled ACL cases for
owner precedence, owning-group/no-fallback rules and creation modes. Equal-ID
Debian 13 and sid overlay profiles pass 2,281 assertions. Each strict unequal-ID
run retains **204 failures** (132 rejected grants, 72 false grants), with actual
operations passing independently. These are utility/libc predicate failures.

Unsupported tmpfs retains 1,098 setup failures. The `fakeowner` bind profile
retains 1,110 setup failures and nine separate socket/chmod assertion failures;
it is not a qualified Linux filesystem profile. The 28 stable residual conditions
and conditional capability limits now belong to CSH-064. Privileged Darwin and
physical-terminal qualification remain absent. No parent utility family or
CSH-012 acceptance gate is promoted.

## CSH-064 external prerequisites and namespace evidence

[CSH-064 evidence](evidence/csh-064/README.md) supplies a disposable Linux user
namespace mapping fixture IDs 10001..10005 to outer IDs 30001..30005. The
qualification JSON records UID/GID maps, setgroups policy and namespace links,
separately from the actual helper credentials and system limit queries. ACL
metadata validation now applies to every controlled ACL fixture. Namespace
private-node creation failures remain setup failures; the bounded ACL result
does not qualify the complete namespace profile.

A focused independent probe diagnoses the supplied `fakeowner` bind mount:
stat on a bound AF_UNIX socket fails with EINVAL while a one-byte transfer works,
and both external and direct chmod permit a non-owner mode change with no
effective capabilities. Socket predicates and non-owner denial expectations
remain strict failures. These two conditions have individual residual rows.
The 204 unequal-ID test/bracket predicate failures remain separately retained.

[External prerequisite inventory](evidence/csh-064/prerequisites.json) records
the concrete capability required before revisiting each of the 30 residual
conditions. Each qualification record retains actual environment/executable
identities, source, reason, CSH-064 as qualification owner and selected
utility/libc/platform vendors as implementation owners. Privileged Darwin and
physical terminal environments remain unavailable; missing root, locale and
stat-only block witnesses remain separate. No parent utility family or CSH-012
gate is promoted.


The [CSH-064 acceptance reconciliation](evidence/csh-064-acceptance/README.md)
retains the passing evidence and the historical project-owned probe timeout
defect. [The completion record](evidence/csh-064-completion/README.md) validates
process-group cleanup and descendant reaping through the actual nested path.
The ticket records acceptance; this repair is independent of the external
capabilities required for vendor requalification.
