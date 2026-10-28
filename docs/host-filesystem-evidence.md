# Filesystem and pathname qualification

CSH-072 adds a **bounded selected profile** for 21 exec-accessible utilities.
It does not qualify complete utility pages, U-034/U-040 as a whole, or a complete
POSIX system. [CSH-105](tickets/CSH-105-filesystem-environment-residuals.md) owns each
remaining contract and the four original retained conditions. Implementation
ownership stays with the selected utility/libc/platform vendor.

The [machine-readable section map](../tests/host_filesystem_contracts.json)
records the Issue-8 source URL/hash, every normative page heading (including pax
subsections), concrete assertion IDs, and individual unqualified dispositions.
Sections after APPLICATION USAGE are informative and do not impose runtime
assertions. The map and [current ownership overlay](../tests/host_contracts.json)
are checked by `make test-host-inventory`.

## Running the profiles

```sh
make test-host-filesystem        # bounded stock subset, missing providers fail
make test-host-filesystem-audit  # also require Issue-8 pathname contracts
make test-host-profile           # provision the opt-in PATH, require declared assertions
make test-host-filesystem-provider-audit # strict extended vendor audit; failures remain failures
```

The stock audit is deliberately strict. A failure is not an allowance in the
selected profile. `HOST_FILESYSTEM_FLAGS` accepts `--path`, `--fixture-root` and
`--sanitizer`; the runner always records the PATH actually used. The profile
target selects its own PATH explicitly and includes the audit automatically.
The ordinary system PATH and shell builtin allocation are unchanged.

Docker and Linux CI install Debian/Ubuntu `file` and `pax` in addition to the
existing build/profile dependencies. No package is installed on the developer's
host by provisioning. Both native and Linux runs retain actual provider paths,
realpaths, hashes, OS/build identity, package versions, environment and limits.
The selected local providers are built from
[`tools/host-profile/paths.c`](../tools/host-profile/paths.c); the source and build
inputs are hashed in each run. They are standalone programs, not linked into
cshell. macOS still uses Homebrew coreutils for the pre-existing test/bracket
profile requirement.

## Assertions and independent oracles

[`host_filesystem_cases.py`](../tests/host_filesystem_cases.py) supplies ordinary
cases through direct exec and public cshell string, script-file and stdin modes.
Each invocation gets a new private tree. Python creates bytes, directories,
links and timestamps; Python/stat and a separate ustar reader check effects.
The selected utility never generates expected output for itself.

| Contract | Supplied bounded evidence |
| --- | --- |
| basename, dirname | Slash normalization, root, plain names, matching/nonmatching/whole-name suffixes. |
| cp, dd | All byte values, symlink following/physical recursive copy, mode/mtime preservation, block skip/count/swab; dd fails under a 512-byte child file-size limit and retains exactly 512 bytes. |
| df, du, file | Portable df fields and ceiling percentage, du KiB from independently measured st_blocks, empty/directory classification words. No free-space snapshot or vendor magic database is used as its own oracle. |
| find, ls | Authored file/link/prune/depth cases; UTF-8 `?` at 64 levels; 512 C-locale names in exact order and hidden-name handling. |
| ln, mkdir, mkfifo | Inode identity, dangling symlink text, replacement, explicit modes, parent creation and FIFO type. |
| mv, rm, rmdir | Byte/metadata/link preservation, replacement/removal, force-missing behavior, nonempty-directory errors, parent deletion. |
| pathchk, pwd | Portable-name rejection and measured filesystem component boundary; physical cwd with a NAME_MAX-length component. This is not a total PATH_MAX or inaccessible-ancestor qualification. |
| pax | Copy-tree bytes/link text; ustar output decoded independently; independently authored ustar input extracted with explicit mode preservation. Apple COPYFILE_DISABLE=1 suppresses its metadata extension for the declared archive profile. |
| readlink, realpath | Exact link bytes/newline suppression, missing-last-component resolution, strict existence, missing prefixes, dangling links, loops, directory requirements, last-option precedence and closed-output errors. |
| rm terminal | Owned controlling PTY, yes/no responses, exact Apple/GNU C-locale prompts and independently verified file state; direct exec and cshell string/script-file modes. |

Status and deterministic bytes are exact. POSIX's positive error classes and
unspecified diagnostics use positive/nonempty predicates; signal death never
satisfies a positive error predicate. df allows column spacing and dynamic live
counts while checking its normative header and percentage relationship. du uses
stat block counts. file permits unspecified description text around the required
classification. dd checks exact authored record counts plus a bounded vendor
transfer-statistics line. These policies are explicit in the runner and records.

## Selected provider repairs

The stock providers omit the required readlink nonlink diagnostic and differ in
realpath's Issue-8 option support. The selected readlink dynamically reads link
contents, diagnoses errors and checks output flushing. The selected realpath
uses libc resolution for existing paths, with a stat check that preserves
regular-file directory-component errors on Darwin. After ENOENT, `-E` resolves
components and symlinks before permitting only a missing final component;
`-e` requires existence and the last option wins. Missing-final fallback permits
at most 40 symlink expansions. Both providers diagnose invalid usage and output
errors. Stock-provider failures remain separately retained.

## Bounds and remaining work

The shared smoke/PTY harness owns and reaps each process/session. Cases cap
execution at five seconds, captured output at 64 KiB, ordinary file writes at
1 MiB, descriptors at 64 and CPU at six seconds; inherited lower resource limits
still apply. The dd fault deliberately lowers only the child file limit to 512
bytes and ignores SIGXFSZ so the provider must handle the write error. No actual
disk is filled. Cleanup is checked after success, failure and timeout; missing
providers, locales or fixture capabilities are failed setup, never passes.

The four retained condition IDs stay in the ownership ledger. CSH-072 supplies
larger-directory, deep UTF-8 and terminal-prompt capabilities; inaccessible
ancestors, total pathname limits, actual descriptor exhaustion, non-C collation,
mount boundaries, quotas, filesystem-capacity exhaustion/EIO, further archive formats and other individual page
contracts remain explicitly open in CSH-085. No protected mount or real disk
contents are used. [Retained results and commands](evidence/csh-072/README.md)
separate the stock audit, qualified subset and full-system limitations.

## Extended traversal, links, metadata, archives and I/O

[`host_filesystem_extended.py`](../tests/host_filesystem_extended.py) adds bounded
cases in all five areas, each through direct exec and cshell string/file/stdin:

- Traversal: distinguish `cp -RH/-RL/-RP` operand links from nested links;
  `find -H/-L`, physical operands, precedence and depth order; physical recursive
  removal of a symlink cycle and recursive FIFO copying.
- Links: `ln -L/-P` and last-option precedence, symlink-inode hard links,
  preserved existing targets, rename inode identity and decrementing link counts.
- Metadata: `cp -p` mode, source uid/gid and both timestamps; symbolic creation
  modes, parent/default umask behavior and isolated `touch -a/-m` updates.
- Archives: independently authored ustar directory/file/hard-link/symlink/FIFO
  graphs; list, selection, substitution, append and bad-checksum errors. The
  independent reader checks exact member sets, bytes, types, modes, times,
  link graphs and ustar headers without extracting provider output. It rejects
  duplicate entries and nonregular or oversized output before reading.
- I/O: EPIPE, EBADF, bounded EFBIG, directory reads and ENOTDIR. Linux adds real
  ENOSPC from its verified virtual `/dev/full` character device. Each descriptor
  or file-limit wrapper probes the expected kernel errno before executing the
  inventoried utility; missing, setup-failure or exec-failure markers fail the
  assertion. This does not supply a full filesystem, quota or EIO capability.

The selected profile now requires the previously failing provider contracts with
`--provider-audit`. It selects GNU find on macOS and a pinned locally built pax
on both platforms. The latter preserves 12-bit ustar modes and drains final
partial writes or returns failure. Its upstream source already handles truncated
members and EPIPE correctly. [Source provenance and exact patches](../tools/host-profile/vendor/pax/CSHELL-CHANGES.md)
are retained alongside the complete upstream release and license notices.

The stock Apple find/pax and Linux pax failures remain real, separately retained
failures. They are not repaired in the system installation. The focused workflow
requires all selected assertions and runs the stock extension audit as a
separate diagnostic step. Its passing selected step cannot be inferred from the
workflow status alone; detailed results and audit exit codes remain artifacts.

[Extended evidence](evidence/csh-072/extended/README.md) preserves the original
failures and intermediate fixture/CI corrections. The
[provider repair evidence](evidence/csh-072/repairs/README.md) records the new
selected scope and its integration checks. The
[remaining-environment table](tickets/CSH-080-filesystem-remaining-contracts.md#required-environments-and-manual-work)
distinguishes automated local work, disposable privileged environments and any
separate physical-terminal claim.

## CSH-080 ordinary contracts and provider faults

`host_filesystem_remaining.py` adds 60 cases (240 assertions in direct exec and
cshell string/file/stdin modes): empty/slash/UTF-8 pathname policies, dd
conversion and seek combinations, continuation after operand errors, symbolic
creation modes, pathchk -P combinations, find expressions/batched exec, C-locale
ls switches, pwd logical/physical precedence and touch date forms.

Apple dd incorrectly reports padded short input as a whole record. The opt-in
macOS profile selects GNU gdd from the existing coreutils prerequisite; the
stock audit retains the failure. No output/status filtering is used.
The exact counts remain required. `conv=ascii/ebcdic/ibm` is XSI-shaded and
outside the selected base profile; numeric touch timezone offsets are extensions.

`make test-host-filesystem-allocation` compiles the unchanged local pathname
provider with test-only call-site ENOMEM controls. It checks every allocation
reached by six successful scenarios in all four invocation modes, plus a
non-triggering end control. A checked marker distinguishes an injected failure
from loader/setup failure. Allocating libc calls can be made to return ENOMEM;
libc-internal allocation paths are not instrumented. These results do not
qualify kernel ENOMEM, quotas, filesystem ENOSPC or EIO.

[CSH-080 evidence](evidence/csh-080/README.md) separates selected, stock and
injected runs. The [residual ledger](../tests/host_filesystem_residuals.json)
retains every utility and all four original condition IDs under CSH-084,
including required environments and why current witnesses do not suffice.

## CSH-084 residual environments

`make test-host-filesystem-residual` runs 26 cases / 104 assertions on the
selected PATH. The same cases are mandatory in `make test-host-profile` and
remain strict in the separate stock audit. They add:

- Fourteen ordinary permission denials across thirteen utilities. A private
  directory loses all search bits, and Python independently requires EACCES
  from stat before dispatch. The record retains real/effective IDs, groups,
  mode and probe errno. Root or a filesystem ignoring these bits fails setup.
  Access is restored before independent file effects and in unconditional cleanup.
- Four `file -m` databases with authored string, continuation, hexadecimal
  offset and escaped-space rules and independent binary samples. Exact messages
  follow the normative magic rules; no installed database generates the oracle.
- Four readlink cases preserving `ff fe 80` bytes under C and UTF-8, with and
  without the final newline. These are selected bytes, not every repertoire.
- Four basename/dirname stdout EBADF/EPIPE cases using the existing independently
  probed kernel-fault wrapper; signal death cannot satisfy positive error status.

The selected providers require no additional repairs. The 24 harness regressions
include root/ineffective-denial rejection, altered effects/output, failed fixture
writes/symlinks, and deadline cleanup for permission, magic and byte-link fixtures.
Timeout helpers disable Python site initialization and allow two seconds to
start and report their PID; every owned PID must disappear after the deadline.
These synthetic setup failures test the harness, not real capacity exhaustion.

[CSH-084 evidence](evidence/csh-084/README.md) separates native, Linux and stock
results. [CSH-085](tickets/CSH-085-filesystem-isolated-contracts.md) retains every
remaining per-utility contract, environment and reason in the
[residual ledger](../tests/host_filesystem_residuals.json), including the five
utilities with no new CSH-084 witnesses. Existing four condition IDs and original
CSH-064 reasons remain unchanged. ACLs, privileged credentials, mount boundaries,
quotas, actual filesystem ENOSPC/EIO and libc-internal failures are not supplied.

## CSH-085 private graph, magic and subsecond environments

`make test-host-filesystem-isolated` runs 28 cases / 112 assertions through
direct exec and public string/file/stdin modes. The selected full profile also
requires them. Seven `du` cases cover recursive 512-byte totals, `-a -k`, `-s`
with a hard-link pair, operand `-H`, nested `-L`, and last-option precedence.
Pre-exec lstat measurements and a fixed authored graph supply the expected
records; a post-exec identity/allocation comparison rejects changed fixtures.
Output ordering is unspecified; duplicate, missing and extra records fail.

Sixteen `file -m` cases pair matching and nonmatching samples for byte equality,
less/greater comparisons, hexadecimal/octal masks, set/missing bits and native
short equality. Five `touch` cases check period/comma fractions, T/space date
separators, UTC/fixed-offset local time and separate access/modification changes
using exact nanosecond metadata. Setup independently proves both timestamps
representable; an unavailable capability is a setup failure, never a pass.

These are private directories under the runner's unprivileged identity, not
isolated mounted volumes. The [evidence](evidence/csh-085/README.md) separates
native/Linux selected runs, stock failures, provenance and cleanup. The
[current ledger](../tests/host_filesystem_residuals.json) and
[CSH-086](tickets/CSH-086-filesystem-unsupplied-contracts.md) retain every open
contract, required environment, reason and vendor owner. No privilege, actual
capacity, cross-device, shared-extent or full utility claim is added.

## CSH-086 owned-terminal overwrite decisions

CSH-086 adds 39 required assertions for C-locale `cp`/`mv` yes/no overwrite
responses, independent `cp -f/-i` behavior and last-option `mv -f/-i` precedence.
Each runs in an owned foreground PTY through direct provider exec and cshell
command-string/script dispatch. A test-only exec helper separates stdout from
terminal stderr and records the armed descriptor environment before exec.
Authored bytes prove source/destination preservation or replacement. Exact
vendor prompt text is checked separately from normative zero/nonzero status.
There is no shell-stdin-mode claim for these terminal interactions.

The selected profile builds pinned GNU coreutils 9.7 `cp` with a source repair
for declined-copy status; stock Apple cp and native GNU cp 9.3 declines remain failures.
The profile records the source archive, patch and executable SHA-256 identities.
Builds are offline from the vendored release and take longer than the shell
build. C-locale builds disable NLS, ACL and SELinux; those contracts stay open.
Run `make test-host-filesystem-interactive` for the focused subset; the full
`make test-host-profile` requires it automatically with zero allowances.

CSH-105 owns every unsupplied environment and the four immutable original
conditions. These bounded terminal decisions do not qualify a whole utility,
recursive/multiple-operand interaction, other locales, ACL/privileged ownership,
cross-device behavior, real filesystem exhaustion or libc-internal faults.
`ln -i` is a vendor extension absent from the selected base specification; it
is no longer mislabeled as an unqualified POSIX interactive requirement.
See `docs/evidence/csh-086/README.md` for native/Linux results and provenance.

## CSH-087 operand and recursive decisions

CSH-087 adds 68 strict assertions: all two-operand yes/no combinations for cp/mv,
continuation past a missing middle operand with a retained nonzero error,
one-child recursive cp overwrite acceptance/decline, rm descent rejection with
continuation, leaf removal followed by final directory acceptance/decline,
recursive symlink non-traversal, and last -f/-i precedence. Empty/nonempty
same-device mv destination directories have separate replacement/rejection cases.

Twenty terminal cases use direct exec and cshell string/file modes with the
existing descriptor/foreground marker; the two ordinary directory cases also
use shell stdin mode. Prompt sequence and filesystem effects are independent
oracles. Full stderr, stdout, status, setup, capture failures and cleanup remain
separate in each record. Provider selection/builds are unchanged; stock Apple
cp adds twelve decline-status failures while the selected repaired cp passes.

[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md) retains every
unsupplied environment and all four original conditions. These witnesses do
not qualify arbitrary recursive graphs, negative recursive-child responses,
non-C prompts, cross-device fallback, mounts, depth exhaustion, ACLs, quotas,
actual filesystem exhaustion or libc-internal faults. Original CSH-064 evidence
and earlier test assertions are unchanged. See [native/Linux evidence](evidence/csh-087/README.md).

## CSH-088 measured metadata and timestamp environments

CSH-088 adds 64 U-034/U-040 assertions through direct exec and cshell string,
file and stdin modes. Private lstat measurements check numeric ls listings
for regular files, hard links, directories, FIFOs and symlinks. Authored sizes
and independently read-back access/modification timestamps check sorting,
C-locale ties and reversal. Exact nanosecond readback precedes find -newer
comparisons before, equal to and after the reference, including -H/-L reference
symlinks. Setup and cleanup failures are failures, never profile allowances.

[CSH-088 evidence](evidence/csh-088/README.md) records both platforms and
separate stock failures. [CSH-105](tickets/CSH-105-filesystem-environment-residuals.md)
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
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md) owns every remaining
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
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md). See [CSH-090
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
original conditions under [CSH-105](tickets/CSH-105-filesystem-environment-residuals.md).
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
provider provenance. [CSH-105](tickets/CSH-105-filesystem-environment-residuals.md)
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
[CSH-093 evidence](evidence/csh-093/README.md). All four original conditions remain open under CSH-105.

### Logical cwd fallback (CSH-094)

CSH-094 supplies 48 external pwd assertions after leaf/parent rename/removal, with default options, -L and -P -L. The helper observes unchanged inherited PWD: absent for direct exec or naming the fixture root for shell modes, independently distinct from the cwd inode. It never sets or unsets PWD. Physical resolution or ENOENT is measured before exact provider exec. Valid logical symlink paths, arbitrary namespace races, inaccessible ancestors, path limits and allocation failures remain unqualified.

`make test-host-filesystem-cwd-logical` runs the focused cases. The full selected
profile requires them with zero allowances; all earlier assertions and provider
sources/build flags remain unchanged. Five harness regressions exercise immutable
specifications, corrupted markers and result channels, setup/exec failures,
inappropriate inherited PWD and timeout/reaping/cleanup. See
[CSH-094 evidence](evidence/csh-094/README.md). All unsupplied environments and
four original conditions remain open under
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md).

### Authored numeric magic boundaries (CSH-095)

CSH-095 supplies 46 authored file magic cases / 184 assertions for native signed byte/short minima and maxima, comparisons across zero, masks and bit tests on negative values, hexadecimal/octal short constants, complete/truncated numeric fields and first-match/continuation order within one database. Exact sample bytes, native ABI widths, channels, status and unchanged input effects are retained. Other types/widths, unsigned ranges, cross-database -m/-M/-d precedence, default classification, encodings and locales remain unqualified.

`make test-host-filesystem-magic` runs the focused cases. They are also mandatory
in the full selected profile with zero allowances. See [CSH-095 evidence](evidence/csh-095/README.md).
All four original U-040 conditions and every unsupplied environment remain open
under [CSH-105](tickets/CSH-105-filesystem-environment-residuals.md); utility/libc/platform
vendors retain implementation ownership. Historical evidence is unchanged.

## Calendar timestamps (CSH-096)

CSH-096 supplies 40 touch calendar cases / 160 assertions for the Epoch, two-digit years 70/99/00/68, omitted seconds, leap day, second-60 year rollover, the required January 2038 date and the signed-32-bit timestamp boundary. Integer UTC calendar arithmetic supplies expected timestamps; exact target and unequal fractional baselines are independently read back on the target inode before execution. Default, -a, -m and explicit -a -m selections require exact timestamps, empty channels, zero status and unchanged content. Other date/timezone forms, current-time tolerances, unsupported timestamp errors, arbitrary symlink graphs and permission/ACL boundaries remain unqualified.

See [CSH-096 evidence](evidence/csh-096/README.md). Every remaining contract and
all four retained U-040 conditions belong to [CSH-105](tickets/CSH-105-filesystem-environment-residuals.md).

## Reference timestamps and alias graphs (CSH-097)

CSH-097 supplies 28 touch reference cases / 112 assertions for distinct access/modification timestamps, regular and symlink-chain references, hard-linked and symlink-chain operands, all four field selections, and silent -c continuation past missing/dangling paths. Exact nanoseconds and inode relationships are independently probed before execution; post-exec metadata is captured before content reads. Reference files, link texts, inode identities and unselected fields must remain unchanged. Arbitrary graphs, creation/current-time tolerances, unsupported timestamps, races and permission/ACL errors remain unqualified.

See [CSH-097 evidence](evidence/csh-097/README.md). All 21 full utility contracts
and four original U-040 conditions remain open under
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md).

## CSH-098 date forms and fixed timezones

CSH-098 supplies 64 touch date-form cases / 256 assertions for period/comma fractional seconds down to one nanosecond, T/space separators, absent-zone fixed TZ interpretation, Z overriding nonzero TZ, and -t fixed-zone rollover. Independently authored UTC fields and integer fractions are exactly read back on the target inode before execution; all four field selections require exact timestamps, unchanged identity/mode/content and empty channels. DST transitions, timezone databases, arbitrary fractions/ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

The U-034 direct-exec and U-040 default contracts retain their existing evidence.
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md) owns all unsupplied
environments and the four original U-040 conditions. See [CSH-098 evidence](evidence/csh-098/README.md).

## CSH-099 explicit daylight-saving rules

CSH-099 supplies 104 touch cases / 416 assertions for unique local times around explicit northern and southern POSIX M-rule daylight-saving transitions, seasonal offsets, -d/-t forms and Z overriding daylight time. Independently authored UTC fields and exact inode timestamp probes supply the oracle; all four field selections require unchanged identity/mode/content and empty channels. Skipped/repeated times, other rule forms, timezone databases, arbitrary ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

The UTC expectations follow the Issue 8 touch OPTIONS/TZ contract and
[XBD TZ rules](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html#tag_08).
Both zones use explicit month/week/day rules; the southern rule ends earlier
in the year than it starts. Northern daylight offset defaults to one hour;
southern daylight offset is explicit. No local-time conversion library is an oracle.

See [CSH-099 evidence](evidence/csh-099/README.md). [CSH-105](tickets/CSH-105-filesystem-environment-residuals.md)
retains all 21 residual utilities and four original U-040 conditions.

## CSH-100 Julian and numbered day rules

CSH-100 supplies 128 touch cases / 512 assertions for explicit POSIX Jn and zero-based n daylight-saving rules across common and leap years, including default 02:00 transitions and unique times before/after the authored changes. Independently authored UTC fields and exact target-inode timestamp probes supply the oracle for -d/-t and all four field selections. Skipped/repeated times, arbitrary rule values and transition times, timezone databases, timestamp ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

See [retained evidence](evidence/csh-100/README.md). All remaining contracts and four original U-040 conditions
remain open under CSH-105; no whole-utility qualification is claimed.

## CSH-101 explicit transition clocks and offsets

CSH-101 supplies 96 touch cases / 384 assertions for explicit M/J/n transition clocks, minute/second standard and daylight offsets, 45-minute-10-second and 30-minute-15-second advances, and negative/next-day transition times. Independently authored UTC fields and exact target-inode probes supply the oracle for -d/-t and all four field selections. Skipped/repeated times, arbitrary rules and offsets, timezone databases, timestamp ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

See [retained evidence](evidence/csh-101/README.md). All remaining contracts and
four original U-040 conditions remain open under CSH-105.

The selected touch provider is GNU coreutils 9.7 linked with pinned IANA tzcode 2025b. Both Apple touch and the installed GNU touch using Darwin conversion return wrong timestamps for the authored previous-day start and next-day end boundaries (64 stock assertions). Preserve these failures separately and require all 384 new assertions without allowances for the selected provider. The replacement does not qualify arbitrary timezone rules or databases.

## CSH-102 string magic and offset boundaries

CSH-102 supplies 91 file string-magic cases / 364 assertions for required backslash and control-character escapes, one/two/three-digit octal escapes including NUL and byte 255, decimal/octal/hexadecimal offsets, exact/trailing/mismatched/truncated fields and at/past-EOF boundaries. Independently authored bytes, exact channels/status and unchanged sample/database contents supply the oracle. Other types/widths, unsigned ranges, multiple databases, default classification, arbitrary encodings/locales and utility resource failures remain unqualified.

See [retained evidence](evidence/csh-102/README.md). U-034/U-040 remain partial;
all 21 utility residuals and four original conditions remain owned by
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md).

## CSH-103 magic-message qualification

CSH-103 supplies 108 file magic-message cases / 432 assertions for native signed byte/short and string printf-style descriptions at top level and in continuations. Literal expected bytes cover signs, width, precision, zero padding, decimal/octal/hexadecimal output, alternate forms, characters and literal percent signs. Exact channels/status, pre-exec readback and unchanged sample/database contents supply the oracle. The pinned file 5.46 provider repairs one-byte magic dispatch, bounded format validation and textual rule order; original stock failures remain separately retained. Other types/widths, unsigned ranges, multiple databases, arbitrary formats/encodings/locales and utility resource failures remain unqualified.

All 21 residual utility contracts and four original U-040 conditions remain open in
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md).
See [CSH-103 evidence](evidence/csh-103/README.md) for provider provenance, strict results and stock failures.

## CSH-104 portable numeric magic types

CSH-104 supplies 360 portable numeric magic cases / 1440 assertions for dC/dS/dI/dL and uC/uS/uI/uL, their explicit byte-count forms, signed extrema, unsigned high-bit ranges, comparisons, hexadecimal/octal masks and constants, bit tests and incomplete fields. Native C ABI widths and independently authored integer bytes supply the oracle; exact channels/status and unchanged inputs are required. The pinned file provider repairs native long type selection, rejection of truncated eight-byte values and signed-minimum parsing without overflow. Default d/u widths, the long keyword alias, further numeric/message combinations, cross-database -m/-M/-d precedence, default classification, encodings/locales and utility resource failures remain unqualified.

All 21 utility dispositions and four original U-040 conditions remain open under
[CSH-105](tickets/CSH-105-filesystem-environment-residuals.md).
See [CSH-104 evidence](evidence/csh-104/README.md).
