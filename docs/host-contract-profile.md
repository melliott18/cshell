# Qualified host contracts and remaining boundaries

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

## Explicit remaining capability limits

[CSH-057](tickets/CSH-057-host-boundary-capabilities.md) owns the conditions
below. They are **unverified**, not known passing or inapplicable. Each utility
page is reachable from the [POSIX utility index](https://pubs.opengroup.org/onlinepubs/9799919799/idx/utilities.html);
XCU [§1.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_04)
and [§1.6](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_06)
continue to apply.

The following inventory applies to the recorded macOS 14.8.7 / Debian 12
profiles. Process argv/environment size is bounded by the recorded ARG_MAX;
pathname operands by the recorded filesystem limits. Neither value proves a
tool's complete maximum accepted input. Exhausting host memory/disk or changing
global terminal/device state is outside the bounded test environment.

| Scoped utility / source page | Evidence boundary and remaining capability, owned by CSH-057 |
| --- | --- |
| [printf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html) | 64-bit numeric saturation, French decimal point and descriptor failure checked; allocation/format-size exhaustion and all other locale catalogs unverified. |
| [echo](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html) | Named Apple/GNU environment policies and descriptor failure checked; arbitrary replacement policies and multibyte/large-argv boundaries unverified. |
| [test and bracket](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) | Basic mode permissions and stat-only block nodes checked; ACLs, unequal effective/real credentials and other device namespaces unverified. Both tools share this limitation. |
| [true](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/true.html), [false](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/false.html) | No required input or output; no utility-specific line/output maximum is claimed. System exec-resource failure remains unverified. |
| [pwd](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html) | Absolute output checked; deleted/inaccessible cwd and pathname-limit behavior require a separate environment. Shell prefix-PATH behavior remains CSH-055. |
| [kill](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/kill.html) | Number/status mapping and owned-child delivery checked; cross-user permission failures and process-limit exhaustion need additional identities. Internal kill remains CSH-054. |
| [cat](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cat.html) | Arbitrary-byte input, 8192-byte line, French environment and bad output fd checked; filesystem I/O faults and maximum file size remain unverified. |
| [env](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/env.html) | Environment clearing/argv and exec error checked; ARG_MAX boundary not reached. |
| [find](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) | Simple tree, absent path and write error checked; depth/descriptor exhaustion and locale ordering require dedicated trees. |
| [ls](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html) | Single entry, absent path and write error checked; large directories and locale collation remain unverified. |
| [stty](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/stty.html) | Controlled PTY roundtrip/nonterminal error checked; physical terminal capabilities are unavailable in the PTY environment. |
| [ed](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html) | Package availability and line-print operation checked; edit-buffer/temp-file limits and signal recovery require separate bounded scenarios. |
| [sed](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sed.html) | 8192-byte line, early seekable offset, absent file and write error checked; maximum pattern/hold-space size and multibyte expressions unverified. |
| [head](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/head.html) | One-line/seekable offset, option error, absent input and write error checked; very large count limits and interrupted input unverified. |
| [cmp](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cmp.html) | Equal files and absent input checked; large offsets, differing data diagnostics and interrupted input unverified. |
| [chmod](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html) | Mode update success and absent input checked; ACL/cross-user/filesystem capability boundaries unverified. |
| [rm](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | Removal and absent input checked; recursive-depth, protected mounts and interactive prompt boundaries unverified. |
| [sleep](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sleep.html) | Zero delay, invalid operand and owned-child TERM checked; maximum duration cannot be demonstrated by waiting within a five-second fixture budget. |
| [sh](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html) | Explicit exit and missing script checked; host sh's parser/resource/locale semantics are not cshell qualification and need separate host evidence. |

This inventory does not promote U-040 or any broad utility family to verified.
The CSH-012 gate stays closed.
