# Complete utility obligation inventory

This expands [U-034/U-040](posix-utilities.md#u-034) for the CSH-012 audit.
It accounts for all **155 Issue 8 utility pages**, the second `test` spelling
`[` and **15 special builtins**: **171 names** total. Of the 156 ordinary/intrinsic
names, **111 have base obligations**, **45 are conditional**, and **101 require
an exec-accessible implementation** under XCU §1.6. The special builtins are
base obligations but are exempt from that exec-access requirement.

Sources: [official utility index](https://pubs.opengroup.org/onlinepubs/9799919799/idx/utilities.html),
[§1.6/§1.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap01.html#tag_18_06),
and each linked utility page. [Source hashes](evidence/csh-012/closure-5b56328/utility-sources.json)
cover all 155 pages. The [machine inventory](evidence/csh-012/closure-5b56328/utility-inventory.json)
and [provider snapshots](evidence/csh-012/closure-5b56328/README.md) retain actual
paths, realpaths, executable hashes, image/platform/package identities and lookup PATH.

## Scope and evidence rules

The selected profile remains base Shell Command Language/sh. UP and XSI are
unselected; CD (C development), SD (software development), FR (FORTRAN runtime)
and UU (UUCP utilities) are separate conditional options, not implicit claims
made by using a C compiler or Make to build cshell. Conditional entries are
retained with their source and applicability trigger. Selecting an option
reopens its complete contract. `ctags` is conditional on CD or SD; `vi` also
requires the option's terminal condition. `ar` is SD by its normative DESCRIPTION.

A partly shaded synopsis does **not** exclude the utility: `crontab`, `date`,
`df`, `kill`, `ls`, `mailx`, `od`, `pr`, `ps`, `sh`, `tabs`, `ulimit`, `who` and
`xargs` retain base obligations. In particular, mailx send mode is base even
without UP receive/editing features; its availability below is not a delivery test.
Obsolescent (`OB`) features are not automatically optional or excluded.

Every applicable external row below has an explicit **open contract** transferred
by CSH-068 to its named implementation owner in CSH-070–078: the linked utility's
normative DESCRIPTION, OPTIONS, OPERANDS, STDIN, INPUT FILES, ENVIRONMENT VARIABLES,
ASYNCHRONOUS EVENTS, STDOUT, STDERR, OUTPUT FILES, EXTENDED DESCRIPTION, EXIT STATUS
and CONSEQUENCES OF ERRORS, subject to its option shading and the common defaults
in XCU §§1.1–1.6. This is a finite per-utility assignment of unqualified behavior,
not a claim that every byte combination needs its own test. Explicitly named
passing witnesses in the linked maps carve out only their asserted conditions.

**Present** below means located executable, not conformance. **Missing** is a
measured provider gap for that PATH. An intrinsic is exempt from a separate
executable except `kill`; an OS wrapper for an intrinsic does not supply cshell's
state-changing semantics. Required intrinsic and special-builtin contracts link
the existing clause maps and their open residual owners.

## Provider and contract ledger

Paths show standard `getconf PATH` lookups: macOS 14.8.7 arm64 and the existing
Debian bookworm arm64 image `sha256:42e058b3ee3f92d31540bc667dc9059cb576e5a6b5783c655da59f89dcfe77e0`.
These read-only observations are new availability evidence; no new behavioral
qualification of that image is inferred. Qualified-PATH replacements and their
hashes are separate fields in the snapshots.

| Utility / normative page | Applicability | Exec obligation | macOS / Debian standard provider | Evidence and current owner |
| --- | --- | --- | --- | --- |
| <a id="utility-admin"></a>[`admin`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/admin.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-alias"></a>[`alias`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/alias.html) | base | Exempt (§1.6) | `/usr/bin/alias` / **missing** | [U-017](posix-utilities.md#u-017) clause map; cshell internal. Open shell-locale conditions: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| <a id="utility-ar"></a>[`ar`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ar.html) | conditional SD | Not selected | `/usr/bin/ar` / `/bin/ar` | Conditional SD not selected; re-evaluate complete page if selected. |
| <a id="utility-asa"></a>[`asa`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/asa.html) | conditional FR | Not selected | `/usr/bin/asa` / **missing** | Conditional FR not selected; re-evaluate complete page if selected. |
| <a id="utility-at"></a>[`at`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/at.html) | base | Required | `/usr/bin/at` / **missing** | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-awk"></a>[`awk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/awk.html) | base | Required | `/usr/bin/awk` / `/bin/awk` | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). Availability only; behavioral qualification not established. |
| <a id="utility-basename"></a>[`basename`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/basename.html) | base | Required | `/usr/bin/basename` / `/bin/basename` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-batch"></a>[`batch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/batch.html) | base | Required | `/usr/bin/batch` / **missing** | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-bc"></a>[`bc`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/bc.html) | base | Required | `/usr/bin/bc` / **missing** | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). Availability only; behavioral qualification not established. |
| <a id="utility-bg"></a>[`bg`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/bg.html) | conditional UP | Not selected | `/usr/bin/bg` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-c17"></a>[`c17`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/c17.html) | conditional CD | Not selected | **missing** / **missing** | Conditional CD not selected; re-evaluate complete page if selected. |
| <a id="utility-cal"></a>[`cal`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cal.html) | conditional XSI | Not selected | `/usr/bin/cal` / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-cat"></a>[`cat`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cat.html) | base | Required | `/bin/cat` / `/bin/cat` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-cd"></a>[`cd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cd.html) | base | Exempt (§1.6) | `/usr/bin/cd` / **missing** | [U-019](posix-utilities.md#u-019) clause map; cshell internal. Mapped bounded evidence retained. |
| <a id="utility-cflow"></a>[`cflow`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cflow.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-chgrp"></a>[`chgrp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chgrp.html) | base | Required | `/usr/bin/chgrp` / `/bin/chgrp` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). Availability only; behavioral qualification not established. |
| <a id="utility-chmod"></a>[`chmod`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html) | base | Required | `/bin/chmod` / `/bin/chmod` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-chown"></a>[`chown`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chown.html) | base | Required | `/usr/sbin/chown` / `/bin/chown` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). Availability only; behavioral qualification not established. |
| <a id="utility-cksum"></a>[`cksum`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cksum.html) | base | Required | `/usr/bin/cksum` / `/bin/cksum` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-cmp"></a>[`cmp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cmp.html) | base | Required | `/usr/bin/cmp` / `/bin/cmp` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-comm"></a>[`comm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/comm.html) | base | Required | `/usr/bin/comm` / `/bin/comm` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-command"></a>[`command`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/command.html) | base | Exempt (§1.6) | `/usr/bin/command` / **missing** | [U-020](posix-utilities.md#u-020) clause map; cshell internal. Mapped bounded evidence retained. |
| <a id="utility-compress"></a>[`compress`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/compress.html) | conditional XSI | Not selected | `/usr/bin/compress` / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-cp"></a>[`cp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cp.html) | base | Required | `/bin/cp` / `/bin/cp` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-crontab"></a>[`crontab`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/crontab.html) | base | Required | `/usr/bin/crontab` / **missing** | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-csplit"></a>[`csplit`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/csplit.html) | base | Required | `/usr/bin/csplit` / `/bin/csplit` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-ctags"></a>[`ctags`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ctags.html) | conditional CD or SD | Not selected | `/usr/bin/ctags` / **missing** | Conditional CD or SD not selected; re-evaluate complete page if selected. |
| <a id="utility-cut"></a>[`cut`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cut.html) | base | Required | `/usr/bin/cut` / `/bin/cut` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-cxref"></a>[`cxref`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cxref.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-date"></a>[`date`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/date.html) | base | Required | `/bin/date` / `/bin/date` | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-dd"></a>[`dd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dd.html) | base | Required | `/bin/dd` / `/bin/dd` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-delta"></a>[`delta`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/delta.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-df"></a>[`df`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/df.html) | base | Required | `/bin/df` / `/bin/df` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-diff"></a>[`diff`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/diff.html) | base | Required | `/usr/bin/diff` / `/bin/diff` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-dirname"></a>[`dirname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/dirname.html) | base | Required | `/usr/bin/dirname` / `/bin/dirname` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-du"></a>[`du`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/du.html) | base | Required | `/usr/bin/du` / `/bin/du` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-echo"></a>[`echo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html) | base | Required | `/bin/echo` / `/bin/echo` | Open full utility contract: [CSH-070](tickets/CSH-070-host-formatted-output.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-ed"></a>[`ed`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html) | base | Required | `/bin/ed` / `/bin/ed` | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-env"></a>[`env`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/env.html) | base | Required | `/usr/bin/env` / `/bin/env` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-ex"></a>[`ex`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ex.html) | conditional UP | Not selected | `/usr/bin/ex` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-expand"></a>[`expand`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/expand.html) | base | Required | `/usr/bin/expand` / `/bin/expand` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-expr"></a>[`expr`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/expr.html) | base | Required | `/bin/expr` / `/bin/expr` | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). Availability only; behavioral qualification not established. |
| <a id="utility-false"></a>[`false`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/false.html) | base | Required | `/usr/bin/false` / `/bin/false` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-fc"></a>[`fc`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/fc.html) | conditional UP | Not selected | `/usr/bin/fc` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-fg"></a>[`fg`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/fg.html) | conditional UP | Not selected | `/usr/bin/fg` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-file"></a>[`file`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html) | base | Required | `/usr/bin/file` / **missing** | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-find"></a>[`find`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/find.html) | base | Required | `/usr/bin/find` / `/bin/find` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-fold"></a>[`fold`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/fold.html) | base | Required | `/usr/bin/fold` / `/bin/fold` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-fuser"></a>[`fuser`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/fuser.html) | conditional XSI | Not selected | `/usr/bin/fuser` / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-gencat"></a>[`gencat`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/gencat.html) | base | Required | `/usr/bin/gencat` / `/bin/gencat` | Open full utility contract: [CSH-076](tickets/CSH-076-host-locale-catalogs.md). Availability only; behavioral qualification not established. |
| <a id="utility-get"></a>[`get`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/get.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-getconf"></a>[`getconf`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/getconf.html) | base | Required | `/usr/bin/getconf` / `/bin/getconf` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-getopts"></a>[`getopts`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/getopts.html) | base | Exempt (§1.6) | `/usr/bin/getopts` / **missing** | [U-023](posix-utilities.md#u-023) clause map; cshell internal. Mapped bounded evidence retained. |
| <a id="utility-gettext"></a>[`gettext`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/gettext.html) | base | Required | **missing** / **missing** | Open full utility contract: [CSH-076](tickets/CSH-076-host-locale-catalogs.md). Availability only; behavioral qualification not established. |
| <a id="utility-grep"></a>[`grep`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/grep.html) | base | Required | `/usr/bin/grep` / `/bin/grep` | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). Availability only; behavioral qualification not established. |
| <a id="utility-hash"></a>[`hash`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/hash.html) | base | Exempt (§1.6) | `/usr/bin/hash` / **missing** | [U-024](posix-utilities.md#u-024) clause map; cshell internal. Mapped bounded evidence retained. |
| <a id="utility-head"></a>[`head`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/head.html) | base | Required | `/usr/bin/head` / `/bin/head` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-iconv"></a>[`iconv`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/iconv.html) | base | Required | `/usr/bin/iconv` / `/bin/iconv` | Open full utility contract: [CSH-076](tickets/CSH-076-host-locale-catalogs.md). Availability only; behavioral qualification not established. |
| <a id="utility-id"></a>[`id`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/id.html) | base | Required | `/usr/bin/id` / `/bin/id` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). Availability only; behavioral qualification not established. |
| <a id="utility-ipcrm"></a>[`ipcrm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ipcrm.html) | conditional XSI | Not selected | `/usr/bin/ipcrm` / `/bin/ipcrm` | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-ipcs"></a>[`ipcs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ipcs.html) | conditional XSI | Not selected | `/usr/bin/ipcs` / `/bin/ipcs` | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-jobs"></a>[`jobs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/jobs.html) | conditional UP | Not selected | `/usr/bin/jobs` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-join"></a>[`join`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/join.html) | base | Required | `/usr/bin/join` / `/bin/join` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-kill"></a>[`kill`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/kill.html) | base | Required | `/bin/kill` / `/bin/kill` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-lex"></a>[`lex`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/lex.html) | conditional CD | Not selected | `/usr/bin/lex` / **missing** | Conditional CD not selected; re-evaluate complete page if selected. |
| <a id="utility-link"></a>[`link`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/link.html) | conditional XSI | Not selected | `/bin/link` / `/bin/link` | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-ln"></a>[`ln`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html) | base | Required | `/bin/ln` / `/bin/ln` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-locale"></a>[`locale`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/locale.html) | base | Required | `/usr/bin/locale` / `/bin/locale` | Open full utility contract: [CSH-076](tickets/CSH-076-host-locale-catalogs.md). Availability only; behavioral qualification not established. |
| <a id="utility-localedef"></a>[`localedef`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/localedef.html) | base | Required | `/usr/bin/localedef` / `/bin/localedef` | Open full utility contract: [CSH-076](tickets/CSH-076-host-locale-catalogs.md). Availability only; behavioral qualification not established. |
| <a id="utility-logger"></a>[`logger`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/logger.html) | base | Required | `/usr/bin/logger` / `/bin/logger` | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-logname"></a>[`logname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/logname.html) | base | Required | `/usr/bin/logname` / `/bin/logname` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). Availability only; behavioral qualification not established. |
| <a id="utility-lp"></a>[`lp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/lp.html) | base | Required | `/usr/bin/lp` / **missing** | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-ls"></a>[`ls`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html) | base | Required | `/bin/ls` / `/bin/ls` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-m4"></a>[`m4`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/m4.html) | base | Required | `/usr/bin/m4` / **missing** | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). Availability only; behavioral qualification not established. |
| <a id="utility-mailx"></a>[`mailx`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mailx.html) | base | Required | `/usr/bin/mailx` / **missing** | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-make"></a>[`make`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/make.html) | conditional SD | Not selected | `/usr/bin/make` / `/bin/make` | Conditional SD not selected; re-evaluate complete page if selected. |
| <a id="utility-man"></a>[`man`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/man.html) | conditional UP | Not selected | `/usr/bin/man` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-mesg"></a>[`mesg`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mesg.html) | base | Required | `/usr/bin/mesg` / `/bin/mesg` | Open full utility contract: [CSH-077](tickets/CSH-077-host-terminal-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-mkdir"></a>[`mkdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html) | base | Required | `/bin/mkdir` / `/bin/mkdir` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-mkfifo"></a>[`mkfifo`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkfifo.html) | base | Required | `/usr/bin/mkfifo` / `/bin/mkfifo` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-more"></a>[`more`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/more.html) | conditional UP | Not selected | `/usr/bin/more` / `/bin/more` | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-msgfmt"></a>[`msgfmt`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/msgfmt.html) | base | Required | **missing** / **missing** | Open full utility contract: [CSH-076](tickets/CSH-076-host-locale-catalogs.md). Availability only; behavioral qualification not established. |
| <a id="utility-mv"></a>[`mv`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html) | base | Required | `/bin/mv` / `/bin/mv` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-newgrp"></a>[`newgrp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/newgrp.html) | base | Required | `/usr/bin/newgrp` / `/bin/newgrp` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). Availability only; behavioral qualification not established. |
| <a id="utility-ngettext"></a>[`ngettext`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ngettext.html) | base | Required | **missing** / **missing** | Open full utility contract: [CSH-076](tickets/CSH-076-host-locale-catalogs.md). Availability only; behavioral qualification not established. |
| <a id="utility-nice"></a>[`nice`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nice.html) | base | Required | `/usr/bin/nice` / `/bin/nice` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-nl"></a>[`nl`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nl.html) | conditional XSI | Not selected | `/usr/bin/nl` / `/bin/nl` | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-nm"></a>[`nm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nm.html) | conditional SD | Not selected | `/usr/bin/nm` / `/bin/nm` | Conditional SD not selected; re-evaluate complete page if selected. |
| <a id="utility-nohup"></a>[`nohup`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nohup.html) | base | Required | `/usr/bin/nohup` / `/bin/nohup` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-od"></a>[`od`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/od.html) | base | Required | `/usr/bin/od` / `/bin/od` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-paste"></a>[`paste`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/paste.html) | base | Required | `/usr/bin/paste` / `/bin/paste` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-patch"></a>[`patch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/patch.html) | base | Required | `/usr/bin/patch` / `/bin/patch` | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). Availability only; behavioral qualification not established. |
| <a id="utility-pathchk"></a>[`pathchk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pathchk.html) | base | Required | `/usr/bin/pathchk` / `/bin/pathchk` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-pax"></a>[`pax`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pax.html) | base | Required | `/bin/pax` / **missing** | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-pr"></a>[`pr`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pr.html) | base | Required | `/usr/bin/pr` / `/bin/pr` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-printf"></a>[`printf`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html) | base | Required | `/usr/bin/printf` / `/bin/printf` | Open full utility contract: [CSH-070](tickets/CSH-070-host-formatted-output.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-prs"></a>[`prs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/prs.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-ps"></a>[`ps`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ps.html) | base | Required | `/bin/ps` / `/bin/ps` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-pwd"></a>[`pwd`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html) | base | Required | `/bin/pwd` / `/bin/pwd` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-read"></a>[`read`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/read.html) | base | Exempt (§1.6) | `/usr/bin/read` / **missing** | [U-027](posix-utilities.md#u-027) clause map; cshell internal. Open shell-locale conditions: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| <a id="utility-readlink"></a>[`readlink`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/readlink.html) | base | Required | `/usr/bin/readlink` / `/bin/readlink` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-realpath"></a>[`realpath`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/realpath.html) | base | Required | `/bin/realpath` / `/bin/realpath` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-renice"></a>[`renice`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/renice.html) | base | Required | `/usr/bin/renice` / `/bin/renice` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-rm"></a>[`rm`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html) | base | Required | `/bin/rm` / `/bin/rm` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-rmdel"></a>[`rmdel`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rmdel.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-rmdir"></a>[`rmdir`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rmdir.html) | base | Required | `/bin/rmdir` / `/bin/rmdir` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-sact"></a>[`sact`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sact.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-sccs"></a>[`sccs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sccs.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-sed"></a>[`sed`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sed.html) | base | Required | `/usr/bin/sed` / `/bin/sed` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-sh"></a>[`sh`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html) | base | Required | `/bin/sh` / `/bin/sh` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). cshell evidence: [language map](posix-matrix.md); /bin/sh remains a separate provider. |
| <a id="utility-sleep"></a>[`sleep`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sleep.html) | base | Required | `/bin/sleep` / `/bin/sleep` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-sort"></a>[`sort`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sort.html) | base | Required | `/usr/bin/sort` / `/bin/sort` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-split"></a>[`split`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/split.html) | base | Required | `/usr/bin/split` / `/bin/split` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-strings"></a>[`strings`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strings.html) | base | Required | `/usr/bin/strings` / `/bin/strings` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-strip"></a>[`strip`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/strip.html) | conditional SD | Not selected | `/usr/bin/strip` / `/bin/strip` | Conditional SD not selected; re-evaluate complete page if selected. |
| <a id="utility-stty"></a>[`stty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/stty.html) | base | Required | `/bin/stty` / `/bin/stty` | Open full utility contract: [CSH-077](tickets/CSH-077-host-terminal-utilities.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-tabs"></a>[`tabs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tabs.html) | base | Required | `/usr/bin/tabs` / `/bin/tabs` | Open full utility contract: [CSH-077](tickets/CSH-077-host-terminal-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-tail"></a>[`tail`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tail.html) | base | Required | `/usr/bin/tail` / `/bin/tail` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-talk"></a>[`talk`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/talk.html) | conditional UP | Not selected | `/usr/bin/talk` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-tee"></a>[`tee`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tee.html) | base | Required | `/usr/bin/tee` / `/bin/tee` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-test"></a>[`test`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) | base | Required | `/bin/test` / `/bin/test` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-time"></a>[`time`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/time.html) | base | Required | `/usr/bin/time` / **missing** | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-timeout"></a>[`timeout`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/timeout.html) | base | Required | **missing** / `/bin/timeout` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-touch"></a>[`touch`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/touch.html) | base | Required | `/usr/bin/touch` / `/bin/touch` | Open full utility contract: [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). Availability only; behavioral qualification not established. [CSH-072 bounded qualification and repaired profile](host-filesystem-evidence.md); full contract remains open. |
| <a id="utility-tput"></a>[`tput`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tput.html) | base | Required | `/usr/bin/tput` / `/bin/tput` | Open full utility contract: [CSH-077](tickets/CSH-077-host-terminal-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-tr"></a>[`tr`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tr.html) | base | Required | `/usr/bin/tr` / `/bin/tr` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-true"></a>[`true`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/true.html) | base | Required | `/usr/bin/true` / `/bin/true` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |
| <a id="utility-tsort"></a>[`tsort`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tsort.html) | base | Required | `/usr/bin/tsort` / `/bin/tsort` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-tty"></a>[`tty`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tty.html) | base | Required | `/usr/bin/tty` / `/bin/tty` | Open full utility contract: [CSH-077](tickets/CSH-077-host-terminal-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-type"></a>[`type`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/type.html) | conditional XSI | Not selected | `/usr/bin/type` / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-ulimit"></a>[`ulimit`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ulimit.html) | base | Exempt (§1.6) | `/usr/bin/ulimit` / **missing** | [U-029](posix-utilities.md#u-029) clause map; cshell internal. Mapped bounded evidence retained. |
| <a id="utility-umask"></a>[`umask`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/umask.html) | base | Exempt (§1.6) | `/usr/bin/umask` / **missing** | [U-030](posix-utilities.md#u-030) clause map; cshell internal. Mapped bounded evidence retained. |
| <a id="utility-unalias"></a>[`unalias`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unalias.html) | base | Exempt (§1.6) | `/usr/bin/unalias` / **missing** | [U-031](posix-utilities.md#u-031) clause map; cshell internal. Open shell-locale conditions: [CSH-067](tickets/CSH-067-shell-locale-pathname-qualification.md). |
| <a id="utility-uname"></a>[`uname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uname.html) | base | Required | `/usr/bin/uname` / `/bin/uname` | Open full utility contract: [CSH-075](tickets/CSH-075-host-execution-processes.md). Availability only; behavioral qualification not established. |
| <a id="utility-uncompress"></a>[`uncompress`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uncompress.html) | conditional XSI | Not selected | `/usr/bin/uncompress` / `/bin/uncompress` | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-unexpand"></a>[`unexpand`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unexpand.html) | base | Required | `/usr/bin/unexpand` / `/bin/unexpand` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-unget"></a>[`unget`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unget.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-uniq"></a>[`uniq`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uniq.html) | base | Required | `/usr/bin/uniq` / `/bin/uniq` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-unlink"></a>[`unlink`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/unlink.html) | conditional XSI | Not selected | `/bin/unlink` / `/bin/unlink` | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-uucp"></a>[`uucp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uucp.html) | conditional UU | Not selected | `/usr/bin/uucp` / **missing** | Conditional UU not selected; re-evaluate complete page if selected. |
| <a id="utility-uudecode"></a>[`uudecode`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uudecode.html) | base | Required | `/usr/bin/uudecode` / **missing** | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-uuencode"></a>[`uuencode`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uuencode.html) | base | Required | `/usr/bin/uuencode` / **missing** | Open full utility contract: [CSH-078](tickets/CSH-078-host-service-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-uustat"></a>[`uustat`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uustat.html) | conditional UU | Not selected | `/usr/bin/uustat` / **missing** | Conditional UU not selected; re-evaluate complete page if selected. |
| <a id="utility-uux"></a>[`uux`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uux.html) | conditional UU | Not selected | `/usr/bin/uux` / **missing** | Conditional UU not selected; re-evaluate complete page if selected. |
| <a id="utility-val"></a>[`val`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/val.html) | conditional XSI | Not selected | **missing** / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-vi"></a>[`vi`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/vi.html) | conditional UP | Not selected | `/usr/bin/vi` / **missing** | Conditional UP not selected; re-evaluate complete page if selected. |
| <a id="utility-wait"></a>[`wait`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/wait.html) | base | Exempt (§1.6) | `/usr/bin/wait` / **missing** | [U-032](posix-utilities.md#u-032) clause map; cshell internal. Mapped bounded evidence retained. |
| <a id="utility-wc"></a>[`wc`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/wc.html) | base | Required | `/usr/bin/wc` / `/bin/wc` | Open full utility contract: [CSH-073](tickets/CSH-073-host-text-streams.md). Availability only; behavioral qualification not established. |
| <a id="utility-what"></a>[`what`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/what.html) | conditional XSI | Not selected | `/usr/bin/what` / **missing** | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-who"></a>[`who`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/who.html) | base | Required | `/usr/bin/who` / `/bin/who` | Open full utility contract: [CSH-077](tickets/CSH-077-host-terminal-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-write"></a>[`write`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/write.html) | base | Required | `/usr/bin/write` / **missing** | Open full utility contract: [CSH-077](tickets/CSH-077-host-terminal-utilities.md). Availability only; behavioral qualification not established. |
| <a id="utility-xargs"></a>[`xargs`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/xargs.html) | base | Required | `/usr/bin/xargs` / `/bin/xargs` | Open full utility contract: [CSH-074](tickets/CSH-074-host-languages-editors.md). Availability only; behavioral qualification not established. |
| <a id="utility-xgettext"></a>[`xgettext`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/xgettext.html) | conditional CD | Not selected | **missing** / **missing** | Conditional CD not selected; re-evaluate complete page if selected. |
| <a id="utility-yacc"></a>[`yacc`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/yacc.html) | conditional CD | Not selected | `/usr/bin/yacc` / **missing** | Conditional CD not selected; re-evaluate complete page if selected. |
| <a id="utility-zcat"></a>[`zcat`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/zcat.html) | conditional XSI | Not selected | `/usr/bin/zcat` / `/bin/zcat` | Conditional XSI not selected; re-evaluate complete page if selected. |
| <a id="utility-bracket"></a>[`[`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) | base | Required | `/bin/[` / `/bin/[` | Open full utility contract: [CSH-071](tickets/CSH-071-host-permissions-identities.md). [Selected host assertions](host-utility-evidence.md), [retained CSH-064 evidence](tickets/CSH-064-host-platform-external-prerequisites.md). |

## Special builtins

These 15 names are accounted separately from the ordinary utility index.
All use [U-001 shared semantics](posix-utilities.md#u-001) and cshell's internal
implementation; none requires a separate exec provider. The linked maps cover
the page-specific conditions; parser/size/locale limitations retain CSH-065–067.

| Name | Clause/evidence | Residual linkage |
| --- | --- | --- |
| `:` | [U-002](posix-utilities.md#u-002) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `break` | [U-003](posix-utilities.md#u-003) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `continue` | [U-004](posix-utilities.md#u-004) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `.` | [U-005](posix-utilities.md#u-005) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `eval` | [U-006](posix-utilities.md#u-006) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `exec` | [U-007](posix-utilities.md#u-007) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `exit` | [U-008](posix-utilities.md#u-008) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `export` | [U-009](posix-utilities.md#u-009) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `readonly` | [U-010](posix-utilities.md#u-010) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `return` | [U-011](posix-utilities.md#u-011) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `set` | [U-012](posix-utilities.md#u-012) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `shift` | [U-013](posix-utilities.md#u-013) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `times` | [U-014](posix-utilities.md#u-014) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `trap` | [U-015](posix-utilities.md#u-015) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |
| `unset` | [U-016](posix-utilities.md#u-016) | [Current requirement ledger](requirement-review-ledger.md) and [defect dispositions](defect-dispositions.md); no unowned requirement inferred from scoped completion. |

## Execution environment and reproduction

`cshell` is a repository-local executable, with no install target. Inherited
PATH is used for normal execution; when absent, execution uses `confstr(_CS_PATH)`
and explicit command-prefix PATH remains effective. ENOEXEC fallback executes
`/bin/sh`; this is a separate unqualified host-shell dependency, not recursion
into the public cshell executable. Scripts with explicit slash paths are opened
directly under the documented invocation policy.

The default runner uses `os.defpath`; `CSH_TEST_PATH` selects the qualified
profile as `<build>/host-profile/bin:$(getconf PATH)`. The snapshots record
standard `getconf PATH` and that qualified path separately; these are not
assertions about arbitrary user PATHs. The existing profile supplies compatible
printf/echo/test/kill selections and ed as recorded in [host profile](host-contract-profile.md).

Dockerfile installs build-essential, python3, procps, locales, ed, busybox and
acl; supplies en_US/fr_FR/de_DE UTF-8 and zh_CN.GB18030; runs as uid 10001 by
default, with explicit root controlled-identity stages. Native CI supplies
coreutils on macOS and the Linux workflow supplies its listed packages/locales.
The snapshots retain OS, libc/toolchain/package identity and uid/gid. They do
not assume ACL semantics, raw pathname encodings, device privileges, physical
terminals, mail delivery, print services or at/cron daemons are supplied. Missing
or unqualified services remain part of the relevant open utility row;
existing controlled filesystem/credential limitations retain their CSH-064
source records and transfer to the owners below for further qualification. CSH-064's
bounded work and its project-owned probe timeout repair are integrated and done.

Reproduce read-only availability with `provider-inventory.py` in the linked
evidence directory, passing the qualified-bin directory as its argument. Run
documented `make test-host-profile` for the bounded strict profile; presence
alone never satisfies that test. No mail, print, scheduling or account-changing
utility was invoked by this inventory.

Audit completion records and assigns these obligations. It neither certifies
the host distribution nor requires all open provider/behavior contracts to be
implemented before CSH-012 can close.

## Current contract ownership

CSH-068 completes its remaining criterion by transferring each of the 101
external contracts and each of the 30 stable CSH-064 conditions to narrower
open implementation tickets. This is an ownership disposition, not behavioral
qualification. The immutable closure inventory above keeps its original owners
and provider hashes; [the current manifest](../tests/host_contracts.json) is the
machine-readable overlay. `make test-host-inventory` checks that no required
external name or retained condition is lost, duplicated or assigned to a closed
ticket, and that both directions of the Markdown utility ledger agree.

| Open owner | Individual external contracts | Stable conditions |
| --- | --- | --- |
| [CSH-070](tickets/CSH-070-host-formatted-output.md) | `printf`, `echo` | 6 |
| [CSH-071](tickets/CSH-071-host-permissions-identities.md) | `test`, `[`, `chmod`, `chgrp`, `chown`, `id`, `logname`, `newgrp` | 7 |
| [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md) | `basename`, `dirname`, `cp`, `dd`, `df`, `du`, `file`, `find`, `ln`, `ls`, `mkdir`, `mkfifo`, `mv`, `pathchk`, `pax`, `pwd`, `readlink`, `realpath`, `rm`, `rmdir`, `touch` | 4 |
| [CSH-073](tickets/CSH-073-host-text-streams.md) | `cat`, `cksum`, `cmp`, `comm`, `csplit`, `cut`, `diff`, `expand`, `fold`, `head`, `join`, `od`, `paste`, `pr`, `sed`, `sort`, `split`, `strings`, `tail`, `tee`, `tr`, `tsort`, `unexpand`, `uniq`, `wc` | 5 |
| [CSH-074](tickets/CSH-074-host-languages-editors.md) | `awk`, `bc`, `ed`, `expr`, `grep`, `m4`, `patch`, `xargs` | 1 |
| [CSH-075](tickets/CSH-075-host-execution-processes.md) | `env`, `false`, `getconf`, `kill`, `nice`, `nohup`, `ps`, `renice`, `sh`, `sleep`, `time`, `timeout`, `true`, `uname` | 6 |
| [CSH-076](tickets/CSH-076-host-locale-catalogs.md) | `gencat`, `gettext`, `iconv`, `locale`, `localedef`, `msgfmt`, `ngettext` | 0 |
| [CSH-077](tickets/CSH-077-host-terminal-utilities.md) | `stty`, `tabs`, `tput`, `tty`, `mesg`, `who`, `write` | 1 |
| [CSH-078](tickets/CSH-078-host-service-utilities.md) | `at`, `batch`, `crontab`, `date`, `logger`, `lp`, `mailx`, `uudecode`, `uuencode` | 0 |

All eight conditional prerequisite reports have explicit owners in the manifest.
Locale provisioning belongs to CSH-076, allocation injection to CSH-070 and
controlled credentials/devices to CSH-071. Full per-utility locale behavior stays
with that utility's owner. The shared interruption condition belongs to CSH-073,
including coordination of the ed witness with CSH-074. No new option profile is
selected; the 45 conditional names retain their applicability triggers.

The [CSH-064 prerequisite ledger](evidence/csh-064/prerequisites.json) supplies
an exact required capability for every stable condition, and its original
qualification records retain actual environment/executable identities and vendor
implementation owners. New reports use current qualification owners; historical
reports remain unchanged. CSH-064 is complete and is not reopened.

CSH-072 supplies the [filesystem subset](host-filesystem-evidence.md) and transfers
only its explicitly unqualified contracts and four retained conditions to CSH-080.
The stock provider observations above are historical; new provider hashes and
Docker file/pax package identities are retained in the CSH-072 evidence.

CSH-080 adds ordinary option/conversion/error-continuation witnesses and isolated
pathname allocation failures. [Individual residuals](../tests/host_filesystem_residuals.json)
transferred to CSH-084 with explicit environments and vendor ownership.

CSH-084 adds 26 private permission, magic, byte-link and output-error cases.
CSH-084 handed individual residual environments to CSH-085; the original
condition IDs and historical reasons are unchanged.

CSH-085 adds private recursive allocation graphs, paired numeric magic samples
and independently representable subsecond timestamps. CSH-086 then supplies
bounded terminal decisions; CSH-109 owns individual residuals and all four
original conditions. See the
[CSH-085 evidence](evidence/csh-085/README.md) for platform results and limits.

## CSH-086 owned-terminal overwrite decisions

CSH-086 qualifies bounded C-locale cp/mv terminal decisions and corrects the
ln -i entry: it is a vendor extension, not a base-profile requirement.
CSH-109 owns all remaining contracts and the four retained conditions. See
[filesystem evidence](host-filesystem-evidence.md) for source/provider identity
and the cp decline-status repair.

## CSH-087 operand and recursive decisions

CSH-087 qualifies the bounded cp/mv operand sequences, cp/rm recursive decisions
and same-device mv directory targets listed in the current section map. All
21 full utility contracts and four original conditions remain open under CSH-109,
with explicit environments, reasons and vendor implementation ownership. See
[CSH-087 evidence](evidence/csh-087/README.md) for provider identities, strict
selected results, unchanged historical evidence and additional stock failures.

## CSH-088 measured metadata and timestamp environments

CSH-088 adds 64 U-034/U-040 assertions through direct exec and cshell string,
file and stdin modes. Private lstat measurements check numeric ls listings
for regular files, hard links, directories, FIFOs and symlinks. Authored sizes
and independently read-back access/modification timestamps check sorting,
C-locale ties and reversal. Exact nanosecond readback precedes find -newer
comparisons before, equal to and after the reference, including -H/-L reference
symlinks. Setup and cleanup failures are failures, never profile allowances.

[CSH-088 evidence](evidence/csh-088/README.md) records both platforms and
separate stock failures. [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md)
owns each remaining environment and all four original conditions. Whole
utility contracts, non-C collation, live-clock age boundaries, mount/depth
limits, ACLs, capacity exhaustion and libc-internal faults remain unqualified.

## CSH-089 declined children and nested recursive decisions

`make test-host-filesystem-recursive` adds ten cases / 30 U-034/U-040
assertions using direct provider exec and cshell command-string/script-file
modes on owned C-locale PTYs. Authored one-child chains cover declined regular
files and symlinks, declined nested descent, separate final parent decisions,
a nonempty-parent error after accepting removal of a still nonempty parent, and continuation
to a later operand. Exact transcripts, empty stdout, exit status, retained bytes,
link text and removed entries are checked independently. Five harness regressions
check bad transcripts/effects/status/channels, partial setup, timeout cleanup and provider-specific simple-prompt spelling.

The selected profile builds GNU rm 9.7 with a local source patch retaining the
mandatory final `-i` prompt after a declined nested descent (rm DESCRIPTION
2b-2e). Unpatched GNU skips the parent decision in that case. The patch changes
only the marked-ancestor shortcut under explicit `-i`; ordinary non-interactive
behavior remains unchanged. Original stock failures remain separate failures;
no output or status is translated and no selected allowance is added.

[CSH-089 evidence](evidence/csh-089/README.md) records native and Linux results.
[CSH-109](tickets/CSH-109-filesystem-environment-residuals.md) owns every remaining
utility environment and all four retained conditions. These cases do not
qualify arbitrary branching, depth/path exhaustion, mounts, races, non-C prompts,
ACLs, quotas, real filesystem exhaustion, libc-internal faults or whole utilities.

## CSH-090 total pathname boundaries

`make test-host-filesystem-path-limits` adds eight cases / 32 strict U-034/U-040
assertions in direct, string, file and stdin modes. CSH-090 supplies 32 total pathname
byte assertions: the selected filesystem PATH_MAX and portable 256-byte limit, operand
lengths limit-1, limit and limit+1 (the limit includes NUL), plus diagnostic
continuation across two invalid operands and a valid missing operand. Independent
pathconf and unnormalized stat probes distinguish kernel ENAMETOOLONG from the portable
policy. Components are at most two bytes; no deep tree or filesystem exhaustion is
exercised.

The full selected profile requires these assertions without allowances. No selected
provider or build configuration changes. All other individual environments and the four
original retained conditions remain open under
[CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). See [CSH-090
evidence](evidence/csh-090/README.md) for native/Linux results.

## CSH-091 physical working-directory changes

`make test-host-filesystem-cwd` adds eight cases / 32 strict U-034/U-040
assertions. A child-only helper enters an owned directory and renames it or its
parent, or removes it alone or together with its parent. Pre-exec device/inode,
old-path ENOENT, and getcwd probes establish the environment independently of pwd.
Exact renamed paths, empty error stdout, diagnostics, status, effects and cleanup
are mandatory in direct exec and all three cshell input modes. These exercise the
external provider; they do not qualify the pwd builtin. Both option forms end in
-P; no PWD assignment or logical-mode namespace behavior is claimed.

The section map and residual ledger retain each other environment and all four
original conditions under [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md).
No provider source or selected-profile allowance changes. See
[CSH-091 evidence](evidence/csh-091/README.md) for native/Linux results, provenance,
harness failure checks and separate stock audits.

## CSH-092 creation masks and final permissions

`make test-host-filesystem-creation` adds 26 cases / 104 strict U-034/U-040
assertions through direct exec and cshell string, file and stdin modes. A child
helper sets masks 027, 077 or 777, reads back the mask, and independently creates
a directory and FIFO to prove its effect before execing the inventoried provider.
The oracle checks final object types and modes, preserved existing data and parent
identity, output channels, status, and cleanup. Symbolic removal, sequential copies,
conditional execute, existing-middle continuation and two-level mkdir parents
are bounded witnesses. Six harness regressions check corrupted evidence, partial
setup, failed exec, wrong probes and timeout cleanup.

See [CSH-092 evidence](evidence/csh-092/README.md) for native/Linux results and
provider provenance. [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md)
retains each unsupplied contract and all four original conditions. Final-state
checks do not observe transient permissions, qualify every symbolic mode, ACL
inheritance, privilege, arbitrary graphs, capacity or whole utilities.

### Output errors (CSH-093)

CSH-093 supplies 32 external pwd output-error assertions on macOS and 56 pathname
utility assertions on Linux: closed stdout EBADF and readerless-pipe EPIPE for pwd -P,
-L, -L -P and -P -L, plus Linux virtual-device ENOSPC for those forms and
basename/dirname. PWD is unset, so logical forms fall back to the physical cwd. Child-
only kernel probes precede exact provider exec. These cases do not supply libc-internal
faults, actual filesystem exhaustion, logical namespace changes or arbitrary output
failures.

`make test-host-filesystem-output` requires zero allowances. See
[CSH-093 evidence](evidence/csh-093/README.md). All four original conditions remain open under CSH-109.

### Logical cwd fallback (CSH-094)

CSH-094 supplies 48 external pwd assertions after leaf/parent rename/removal, with default options, -L and -P -L. The helper observes unchanged inherited PWD: absent for direct exec or naming the fixture root for shell modes, independently distinct from the cwd inode. It never sets or unsets PWD. Physical resolution or ENOENT is measured before exact provider exec. Valid logical symlink paths, arbitrary namespace races, inaccessible ancestors, path limits and allocation failures remain unqualified.

`make test-host-filesystem-cwd-logical` runs the focused cases. The full selected
profile requires them with zero allowances; all earlier assertions and provider
sources/build flags remain unchanged. Five harness regressions exercise immutable
specifications, corrupted markers and result channels, setup/exec failures,
inappropriate inherited PWD and timeout/reaping/cleanup. See
[CSH-094 evidence](evidence/csh-094/README.md). All unsupplied environments and
four original conditions remain open under
[CSH-109](tickets/CSH-109-filesystem-environment-residuals.md).

### Authored numeric magic boundaries (CSH-095)

CSH-095 supplies 46 authored file magic cases / 184 assertions for native signed byte/short minima and maxima, comparisons across zero, masks and bit tests on negative values, hexadecimal/octal short constants, complete/truncated numeric fields and first-match/continuation order within one database. Exact sample bytes, native ABI widths, channels, status and unchanged input effects are retained. Other types/widths, unsigned ranges, cross-database -m/-M/-d precedence, default classification, encodings and locales remain unqualified.

`make test-host-filesystem-magic` runs the focused cases. They are also mandatory
in the full selected profile with zero allowances. See [CSH-095 evidence](evidence/csh-095/README.md).
All four original U-040 conditions and every unsupplied environment remain open
under [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md); utility/libc/platform
vendors retain implementation ownership. Historical evidence is unchanged.

## Calendar timestamps (CSH-096)

CSH-096 supplies 40 touch calendar cases / 160 assertions for the Epoch, two-digit years 70/99/00/68, omitted seconds, leap day, second-60 year rollover, the required January 2038 date and the signed-32-bit timestamp boundary. Integer UTC calendar arithmetic supplies expected timestamps; exact target and unequal fractional baselines are independently read back on the target inode before execution. Default, -a, -m and explicit -a -m selections require exact timestamps, empty channels, zero status and unchanged content. Other date/timezone forms, current-time tolerances, unsupported timestamp errors, arbitrary symlink graphs and permission/ACL boundaries remain unqualified.

See [CSH-096 evidence](evidence/csh-096/README.md). Every remaining contract and
all four retained U-040 conditions belong to [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md).

## Reference timestamps and alias graphs (CSH-097)

CSH-097 supplies 28 touch reference cases / 112 assertions for distinct access/modification timestamps, regular and symlink-chain references, hard-linked and symlink-chain operands, all four field selections, and silent -c continuation past missing/dangling paths. Exact nanoseconds and inode relationships are independently probed before execution; post-exec metadata is captured before content reads. Reference files, link texts, inode identities and unselected fields must remain unchanged. Arbitrary graphs, creation/current-time tolerances, unsupported timestamps, races and permission/ACL errors remain unqualified.

See [CSH-097 evidence](evidence/csh-097/README.md). All 21 full utility contracts
and four original U-040 conditions remain open under
[CSH-109](tickets/CSH-109-filesystem-environment-residuals.md).

## CSH-098 date forms and fixed timezones

CSH-098 supplies 64 touch date-form cases / 256 assertions for period/comma fractional seconds down to one nanosecond, T/space separators, absent-zone fixed TZ interpretation, Z overriding nonzero TZ, and -t fixed-zone rollover. Independently authored UTC fields and integer fractions are exactly read back on the target inode before execution; all four field selections require exact timestamps, unchanged identity/mode/content and empty channels. DST transitions, timezone databases, arbitrary fractions/ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

The U-034 direct-exec and U-040 default contracts retain their existing evidence.
[CSH-109](tickets/CSH-109-filesystem-environment-residuals.md) owns all unsupplied
environments and the four original U-040 conditions. See [CSH-098 evidence](evidence/csh-098/README.md).

## CSH-100 Julian and numbered day rules

CSH-100 supplies 128 touch cases / 512 assertions for explicit POSIX Jn and zero-based n daylight-saving rules across common and leap years, including default 02:00 transitions and unique times before/after the authored changes. Independently authored UTC fields and exact target-inode timestamp probes supply the oracle for -d/-t and all four field selections. Skipped/repeated times, arbitrary rule values and transition times, timezone databases, timestamp ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

See [retained evidence](evidence/csh-100/README.md). All remaining contracts and four original U-040 conditions
remain open under CSH-109; no whole-utility qualification is claimed.

## CSH-102 string magic and offset boundaries

CSH-102 supplies 91 file string-magic cases / 364 assertions for required backslash and control-character escapes, one/two/three-digit octal escapes including NUL and byte 255, decimal/octal/hexadecimal offsets, exact/trailing/mismatched/truncated fields and at/past-EOF boundaries. Independently authored bytes, exact channels/status and unchanged sample/database contents supply the oracle. Other types/widths, unsigned ranges, multiple databases, default classification, arbitrary encodings/locales and utility resource failures remain unqualified.

See [retained evidence](evidence/csh-102/README.md). U-034/U-040 remain partial;
all 21 utility residuals and four original conditions remain owned by
[CSH-109](tickets/CSH-109-filesystem-environment-residuals.md).

## CSH-103 magic-message qualification

CSH-103 supplies 108 file magic-message cases / 432 assertions for native signed byte/short and string printf-style descriptions at top level and in continuations. Literal expected bytes cover signs, width, precision, zero padding, decimal/octal/hexadecimal output, alternate forms, characters and literal percent signs. Exact channels/status, pre-exec readback and unchanged sample/database contents supply the oracle. The pinned file 5.46 provider repairs one-byte magic dispatch, bounded format validation and textual rule order; original stock failures remain separately retained. Other types/widths, unsigned ranges, multiple databases, arbitrary formats/encodings/locales and utility resource failures remain unqualified.

All 21 residual utility contracts and four original U-040 conditions remain open in
[CSH-109](tickets/CSH-109-filesystem-environment-residuals.md).
See [CSH-103 evidence](evidence/csh-103/README.md) for provider provenance, strict results and stock failures.

## CSH-105 default numeric magic

CSH-105 supplies 280 file cases / 1120 assertions for default d/u (the selected provider uses native int/unsigned int) and byte/short/long aliases, at top level and in continuations. Native ABI widths and independent integer bytes cover signed extrema, unsigned high-bit comparisons, masks, bit tests, every truncated length and trailing bytes. The selected provider repairs textual long to mean native dL while retaining the vendor compiled-database encoding. Exact channels/status and unchanged inputs are required. Further numeric/message combinations, cross-database -m/-M/-d precedence, default classification, encodings/locales and utility resource failures remain unqualified. U-034/U-040 remain partial; [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md) owns the residuals. See [evidence](evidence/csh-105/README.md).

## CSH-107 omitted-who creation modes

CSH-107 supplies 72 mkdir/mkfifo cases / 288 assertions for symbolic creation modes with omitted who under independently proved child-only masks 027, 077 and 777. Authored literal modes cover masked addition/removal, copy addition/removal/assignment, conditional execute, empty assignment and multiple actions, alongside explicit-who controls. Exact channels/status, final type/mode and cleanup are required. The selected pinned GNU coreutils 9.7 creation utilities replace Apple providers that retain masked group bits during copy assignment.

Further symbolic-mode and parent graphs, special-bit modes, transient permissions, ACL inheritance, other identities, path/depth limits and capacity exhaustion remain unqualified; FIFO transfer is outside creation. U-034/U-040 remain partial; [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md) owns all residuals. See [retained evidence](evidence/csh-107/README.md).

## CSH-108 bounded parent graphs

CSH-108 supplies 60 mkdir -p cases / 240 assertions for shared parents, repeated operands, existing directory symlinks and continuation after regular-file or dangling-symlink prefix obstructions. Literal final and intermediate modes under independently proved child-only masks 027, 077 and 777 cover default, numeric, empty and copy-assignment modes. Existing directory, file and link identities/modes and contents are preserved; output, status, effects and cleanup are required.

Further mode/parent graphs, special bits, transient permissions, ACL inheritance, other identities, path/depth limits, namespace races and capacity exhaustion remain unqualified. All 21 utility dispositions and four original U-040 conditions remain open under [CSH-109](tickets/CSH-109-filesystem-environment-residuals.md). See [retained evidence](evidence/csh-108/README.md).
