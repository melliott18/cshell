# Host predicates, permissions and identities

CSH-071 adds strict, bounded qualification for eight external utility contracts.
**All eight full contracts remain open in CSH-071.** The default passing subset
is the authored case list in `tests/host_permission_cases.py`; it does not qualify
all credentials, ACL implementations, locales, session databases or filesystems.
The [run records](evidence/csh-071/README.md) distinguish vendor failures, harness
repairs, setup failures and unavailable capabilities.

## Reproduction and provider selection

```sh
make test-host-permissions
make test-host-profile
# Only in a disposable Linux root container:
make test-host-profile HOST_PROFILE_FLAGS=--controlled-identities HOST_PERMISSIONS_FLAGS=--controlled-identities
# Strict additional contracts, not allowances in the passing subset:
make test-host-permissions HOST_PERMISSIONS_FLAGS='--vendor-residuals --case-prefix chmod/original-X'
make test-host-permissions HOST_PERMISSIONS_FLAGS='--session-controls --case-prefix newgrp/'
```

Each selected case runs through direct `execv` (with the specified argv[0]) and
public cshell command-string, script-file and stdin dispatch. Unequal-ID `id`
cases deliberately use direct exec: shell invocation has its own privilege
normalization contract, so its resetting credentials must not become the id
oracle. Every operation has a fresh private directory, five-second process-group
watchdog, 64 KiB output bound and the existing smoke child resource limits.
Setup errors, missing providers, failed assertions and cleanup failures fail the
run. The regression harness checks lying metadata, missing providers and timeout
cleanup. No reference utility supplies expected values.

The opt-in profile now selects the repository's `host-test` adapter for `test`
and `[`. It implements Issue 8 `<` and `>` using `strcoll`, including equal operands
and four-argument negation. It checks r/w/x with effective-credential `faccessat`
and delegates remaining expressions to the selected GNU `test`. Darwin selects
Homebrew `gtest`; Linux selects `test` from `os.defpath`.
The build embeds its absolute path, and inventories record both adapter and
backend realpaths/hashes, generated header, source inputs, package observations
and OS identity. The adapter checks/removes the bracket terminator and delegates
with argv[0] `test`. Effective-credential permission checks are now supplied by
the adapter; the
[follow-up evidence](evidence/csh-071-acl-qualification/README.md) records the
strict Linux unequal-ID ACL qualification. The original vendor failures remain retained.
`command -p` and stock-host evidence continue to use the system search path.

Use `--path`, `--fixture-root`, and `--record` on `tests/host_permissions.py` for
an explicit provider/filesystem selection. `--case-prefix` records a focused
selection and rejects an empty match. `--controlled-identities` and
`--session-controls` require Linux root; the latter belongs only in disposable
containers. They never modify the developer host's account database.

## Clause map

The normative sources are the POSIX.1-2024 pages for
[test and bracket](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html),
[chmod](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html),
[chgrp](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chgrp.html),
[chown](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chown.html),
[id](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/id.html),
[logname](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/logname.html), and
[newgrp](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/newgrp.html).
The evidence source manifest records the retrieved page hashes. The following
maps cover every behavior section; an open disposition is not a passing assertion.

| Page section | Selected assertion or explicit disposition |
| --- | --- |
| NAME / SYNOPSIS | Eight provider identities and exec accessibility are inventoried. Seven utilities run by default. `newgrp` requires the separate session profile. Only listed argument forms qualify. |
| DESCRIPTION | Per-utility effects and open branches appear below. U-034 direct exec is separate from cshell dispatch. |
| OPTIONS | `test` treats `--` as a nonempty operand, with no option parsing. chmod tests `--` and `-R`; controlled chown/chgrp test `-h`, `-R`, `-H/-L/-P` and last-option precedence. id tests `-u/-g/-r/-n/-G`. `newgrp -l` remains open. logname has no options. |
| OPERANDS | Fixed strings, signed integers, owned paths, numeric/name ownership and current user names are tested. Numeric-name database precedence, group membership extremes and every pathname encoding remain open. Unspecified test argument forms and newgrp `-` are not assigned portable outcomes. |
| STDIN | No utility consumes stdin in the selected ordinary forms. Newgrp's *new shell* reads authored commands; this does not claim that newgrp reads stdin for authentication. A deliberately unread open pipe/interruption test remains open. |
| INPUT FILES | These pages specify none except newgrp's `/dev/tty` password input. Controlled password prompting and authentication remain open; no live account passwords are used. Files named by operands are verified separately. |
| ENVIRONMENT VARIABLES | C locale is explicit; LOGNAME/USER are poisoned for logname. A supplied `csh_067.UTF-8` locale tests `ch > h` to distinguish collation from byte ordering. Missing that locale leaves that branch unqualified. LANG/LC_ALL/category precedence, complete multibyte interpretation and translated diagnostics remain open for each utility. XSI NLSPATH is outside the selected base profile. |
| ASYNCHRONOUS EVENTS | Default handling is an open obligation per utility; harness timeout termination is cleanup evidence, not a signal-conformance claim. |
| STDOUT | Exact empty output, id's numeric/name formats, logname's getlogin-derived line and authored new-shell output are checked. Group order is unspecified: id -G must emit each distinct measured group exactly once with exact separators/newline. Default id formatting and untranslated/translated alternatives remain open. |
| STDERR | Success requires empty stderr. Errors require a diagnostic where specified; exact wording is not prescribed. Actual bytes are retained. Newgrp password prompts and localized messages remain open. |
| OUTPUT FILES | No page defines an output-file format. Changes to file mode/ownership and actual permission operations have independent metadata/byte checks below. Newgrp accounting effects remain provider-policy obligations. |
| EXTENDED DESCRIPTION | chmod's mode grammar is exercised below, with remaining branches explicit. Other pages specify none. |
| EXIT STATUS | test true/false/error use 0/1/>1; other errors require >0. Success is 0 except newgrp, which must propagate the authored shell's 23. Default id and all error branches are not exhaustively qualified. |
| CONSEQUENCES OF ERRORS | Individual diagnostic failures and continued parent harness execution are witnessed. Full default error behavior (including output-device failures and resource exhaustion) remains open for each utility. Newgrp may terminate the invoking shell; tests launch owned child shells. |

U-040 common defaults are accounted for above (locale, streams, signals, errors),
not inferred from ordinary successful invocations. U-034 provider existence alone
does not establish the behavioral page contract.

| Utility | Exact selected behavior | Individually open behavior (owner CSH-071) |
| --- | --- | --- |
| test / [ | Defined 0–4 argument branches, empty/nonempty, !, all six integer comparisons, equality/inequality, collation, file/directory/link/FIFO/socket/set-ID/size predicates, hard-link identity, timestamps including missing operands, pipe/closed descriptors. Equal-ID mode grants/denials have actual read/write/exec controls under the same child credentials. Existing controlled profile adds ACLs and stat-only private devices. | Full LC_COLLATE/LC_CTYPE coverage, positive terminal and every descriptor boundary, every type/error/race combination, retained ACL/identity/filesystem conditions below. No device I/O. |
| chmod | Octal and symbolic modes, u/g/o/a, +/−/=, empty perms, copies, clause/action ordering, basic X, set-ID executable files, omitted-who masks, directory X, recursion, multiple operands, symlink operand, invalid mode, absent file, controlled non-owner denial. Python stat checks effects independently. | Original-mode X interpretation is a strict GNU failure; metadata timestamp update, full grammar limits, set-ID implementation choices on non-regular files, traversal errors, ACL effects and alternate filesystems remain open. XSI sticky-bit semantics are excluded. |
| chgrp / chown | Existing numeric and named IDs, multiple operands, missing path, controlled real changes, -h symlink ownership, -R with H/L/P and last-option precedence for argument and encountered links. -H changes a nested link's referent via chown() without traversing its children; -P does not follow it. | Numeric-looking database names, nonprivileged set-ID clearing, every authorization/ID mapping, filesystem failures and full timestamp semantics remain open. No H/L/P default is asserted because it is unspecified. |
| id | Measured effective/real numeric IDs, names from independent pwd/grp APIs, current-user operand, distinct -G set, missing user, direct unequal real/effective IDs. Linux children record saved IDs and capabilities. | Default formatted identity line, unresolved names, complete supplementary-group/name/-G combinations, database membership boundaries and privilege-restricted user lookup remain open. |
| logname | Same-session child getlogin() supplies the normative oracle; poisoned environment names must not replace it. Exact success line or failure diagnostic/status are enforced. | Creating controlled successful and failing login databases on both OSes, session transitions and locale branches remain open. A successful native getlogin or container failure qualifies only that observed session. |
| newgrp | Separate disposable-root profile requests default/named/numeric and changed group; observes real/effective GIDs, cwd, umask, exported variable and returned shell status. Failed-group case strictly requires a new shell. | Provider rejection of numeric groups or failure-before-shell remains a strict failed assertion. -l, supplementary-list capacity/transitions, numeric-name precedence, password/PTY prompts, authentication/accounting policies and non-root membership remain open. |

## Retained condition ownership

The immutable CSH-064 ledger is unchanged. No earlier false grant, rejected grant,
socket stat EINVAL or non-owner chmod failure is erased by a passing mode-bit case.
The current manifest keeps all seven residual IDs and three conditional reports
with CSH-071 and utility/libc/filesystem vendors retain implementation ownership.

| Condition | Current disposition and required next evidence |
| --- | --- |
| U-037/ACLs | Selected adapter qualified on measured Linux ext4 and native Darwin owned ACL fixtures, including independent r/w/x operations. Additional filesystems and full utility contracts remain open. |
| U-037/Darwin-ACLs | Native owner ACL ordering/inheritance qualifies without root. A disposable hosted workflow now supplies the controlled-identity plan; its Darwin job is queued, so privileged Darwin qualification remains open. |
| U-037/unequal-identities | The changed adapter passes the strict swapped real/effective-ID ACL matrix on the measured Linux initial namespace. Original mapped-namespace failures remain retained; that additional mapping and all other credentials are not automatically qualified. |
| U-037/fakeowner-socket-type | Open: no changed fakeowner implementation supplied. Ordinary socket type assertions do not repair its retained EINVAL; successful metadata and actual AF_UNIX transfer are both required there. |
| U-040/fakeowner-chmod | Open: overlay non-owner denial cannot qualify fakeowner. Changed implementation must deny both syscall and selected utility under measured IDs/capabilities. |
| U-037/device-namespaces | Existing disposable Linux controlled-node profile is rerun, stat only. Additional namespaces remain unqualified. |
| U-040/chmod-ACL-identity-filesystem | Qualified selected non-owner chmod/chown/chgrp denials, set-ID clearing, group changes and ctime updates. Chmod interactions with every ACL/filesystem remain open. |
| U-037/controlled-environment | Available only in the explicitly selected Linux-root controlled run; unavailable natively. |
| U-037/permission-denial | Mode-000 native non-root and explicitly dropped Linux IDs supply bounded denial controls. Root baseline alone cannot demonstrate denial. |
| U-037/block-device | Linux controlled profile creates a private stat-only node; no additional native block witness supplied. |

No replacement platform milestone or fictitious completed owner is introduced.
The remaining contracts keep this implementation ticket open.

## Effective-credential and ACL qualification extension

The selected adapter now evaluates `-r`, `-w`, `-x`, and their defined negated
forms with `faccessat(AT_FDCWD, path, mode, AT_EACCESS)`. This uses effective IDs
and filesystem ACL decisions rather than the retained GNU `euidaccess` mode-bit
approximation under unequal IDs. Other predicates still delegate. The relevant
interface is [faccessat](https://pubs.opengroup.org/onlinepubs/9799919799/functions/access.html).
This implementation change does not by itself qualify an unavailable platform.

`--qualification-only` selects focused ownership and credential assertions.
`--darwin-acls` adds current-user named ACL grants, denials, ordered entries and
file inheritance, with exact ACL metadata and independent read/write/exec
controls. It needs no account modification or root for ordinary owned files.
All tests include test/bracket and negation. Binary execute fixtures use mode
0454, providing the global execute mode bit Darwin requires; the owner cannot
use the group bit, and a no-ACL control must fail. Controlled root-owned fixtures
exclude both dropped subjects from the owning group. Write effects are checked
by returned byte count and independent file size without requiring read access.

The separate `Permission qualification` workflow supplies disposable Linux and
macOS runners. Linux tests independently varied real/effective UID/GID and
supplementary groups, non-owner chmod/chown/chgrp denials, and the strict existing
unequal-ID ACL suite. Darwin's `--darwin-credentials` uses sudo only on that
runner, then drops to its existing runner/daemon accounts in both ID directions.
Each child verifies loss of saved-root access before invoking the selected
provider. No account database is modified. macOS may include the effective GID
in getgroups(); no other unsupplied supplementary groups are accepted.

Ordinary ownership checks include nonprivileged set-ID clearing, a real change
to a supplied supplementary group, and strict file-status timestamp updates.
Full user-namespace/fakeowner and remaining page contracts are still separate.

[Follow-up results and retained failures](evidence/csh-071-acl-qualification/README.md)
record native, sanitizer and hosted Linux qualification independently.
