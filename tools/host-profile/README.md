# Qualified host utility profile

CSH-056 supplies an **opt-in, bounded integration profile**, not a complete
POSIX utility distribution. It never installs over system binaries or changes
cshell's builtin allocation. All tools are real exec-accessible programs;
`kill` remains intrinsic unless addressed by pathname or through `exec`.

| Host | Selected replacements | Provisioning |
| --- | --- | --- |
| macOS | Standalone printf, test/bracket, chmod and newgrp adapters, and local readlink/realpath; Homebrew `gtest`, `g[` and `gfind`; GNU `gdd`; pinned local pax | `brew install coreutils findutils gettext`; prefixed binaries must be on the provisioning process's PATH |
| Debian/Ubuntu | Standalone printf, test/bracket, chmod and newgrp adapters, local readlink/realpath and pinned pax; BusyBox kill; GNU du in POSIX mode | `apt-get install build-essential python3 ed busybox locales acl file pax libbsd-dev ncurses-bin libncurses-dev bsdextrautils bc m4 gettext`; `host-locales` generates private locales |

Other scoped commands use `os.defpath` without additional symlinks, preserving
cshell's PATH-associated pwd builtin selection. In particular, echo remains the system
executable, with its explicitly recorded Apple/GNU policy. The Dockerfile
installs ed, BusyBox, curl and trusted CA certificates and generates the French locale. CI installs native
profile dependencies separately. macOS coreutils 9.3 and Debian coreutils 9.1 /
BusyBox 1.35.0 are the recorded package versions; future versions must pass the
same assertions, not acquire an automatic compatibility claim.

```sh
make test-host-profile
PATH="$PWD/build/host-profile/bin:$(getconf PATH)" ./cshell
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
```

The profile is recreated by `make host-profile`, and removed by `make clean`.
`build/host-profile/manifest.json` records every selected executable and hash; only replacements receive symlinks. The
runner independently inventories the actual selected paths and package owners,
then exercises lookup, explicit exec, argument preservation, environment, input,
status, and PATH shadows in string/file/stdin modes. `command -p` deliberately
continues to use the system default path. A changed profile requires re-running
both qualification and the existing utility-dependent runtime fixtures.

`tests/host_utilities.py --path PATH --echo-policy gnu` can qualify a deliberate
alternative GNU echo selection even on macOS. `--echo-policy darwin` selects the
Apple assertions. There is no generic assertion set for arbitrary echo
implementations: use a supported policy or add documented assertions first.
No selected utility ever generates the expected test bytes.

For positive block-device predicates, pass
`make test-host-profile HOST_PROFILE_FLAGS='--block-device /dev/disk0'` on a
Mac with that node. Only `stat` is performed; the device is never opened. The
Linux evidence uses a disposable block node created inside a container, then
runs the suite as UID 10001. Missing device access, root-only execution, and
missing French locales are individually recorded limitations owned by CSH-062;
these do not become passes. `--strict-gaps` concerns unmet assertions, not
universal capability coverage.

## Chmod and supplied device witnesses

The selected `chmod.c` uses BSD `setmode`/`getmode` (system libc on macOS,
`libbsd` on Linux) so `X` tests the file's original mode while permission copies
observe preceding actions. It supports the POSIX `-R`, octal and symbolic forms,
and `--`. Physical traversal follows command-line symlinks, skips encountered
symlinks, and updates directories after their children so removing search access
does not prevent descendant changes. It calls the kernel even for unchanged
modes, preserving authorization checks, ctime updates and filesystem ACL behavior.
The binary is never installed set-ID. GNU/BSD extension options are outside this
selected interface. `--vendor-residuals --case-prefix chmod/` checks original-X,
recursion, inaccessible final directory modes, symlinks and continued processing
after an invalid operand. Linux evidence records the installed libbsd version.

For mapped namespaces unable to create nodes, `host_utilities.py
--device-fixtures DIRECTORY` accepts private precreated `block` and `character`
nodes. It verifies their types and stable metadata identity, creates only a
fixture symlink, and records the supplied path/device/inode. Neither node is
opened; the parent environment owns their final removal. This qualifies stat
predicates in the supplied namespace, not permission to call `mknod` there.

## Newgrp dispatch adapter

The selected `newgrp.c` first checks literal group names, then resolves an
existing numeric GID to its canonical name before execing the absolute system
provider recorded in `build/host-newgrp-provider.h`. For an unknown nonnumeric
name it diagnoses the failed group assignment and execs the current user's
password-database shell with unchanged credentials, cwd, umask and environment.
It ignores the exported SHELL variable when choosing that fallback shell.
This adapter has no set-ID installation and implements no authentication or
credential changes. Known-group authorization/password handling and unsupported
argument forms still belong to the inventoried vendor; their broader contracts
remain open. `--session-controls` tests existing root/daemon and the `SUDO_USER`
account on CI (or the Docker image's `cshell` account), without changing accounts.

## Standalone printf provenance

`vendor/printf.c` is derived from FreeBSD source at commit
[`0b8224d1cc9dc6c9778ba04a75b2c8d47e5d7481`](https://github.com/freebsd/freebsd-src/blob/0b8224d1cc9dc6c9778ba04a75b2c8d47e5d7481/usr.bin/printf/printf.c).
Its BSD-3-Clause license is retained in the file. CSH-059 adds one local
`printb` function and replaces the `%b` libc `%s` call with it. This is a host executable,
never linked into cshell, and builds offline from the checked-in source.

`printf.c` contains two local adapters: GNU getopt must stop at the first
operand as BSD getopt does, and the standalone process must flush/check stdout
before returning success. The latter also addresses the newly reproduced
macOS system printf closed-stdout success. The CSH-059 local `%b` correction writes the decoded byte count instead of
passing it to libc `%s`, which truncated output at embedded NULs. Width and
precision count bytes, including NUL, and numbered reuse and `\c` retain their
upstream control flow. Literal `%b` width/precision above `INT_MAX` fail with a
diagnostic; this adapter limit is distinct from ARG_MAX and fixture limits.
Other formatting and argument conversion remain in the upstream implementation. The qualification scope does not
certify every extension or input accepted by that source. The underlying libc
implements numeric conversion (`intmax_t` is 64 bits on the recorded hosts),
locale behavior, and allocation limits.


## Extended boundary evidence

CSH-059 adds all 256 byte values through format octals and `%b`, binary
precision/padding/recycling, bounded 8192-byte format/operand/width checks,
256 arguments/conversions, and an independently detected UTF-8 locale. It also
checks finite files, edit buffers and trees for cat/sed/head/cmp/ed/find/ls/rm
and deleted-cwd failure in the explicitly selected external pwd.
See the [condition map](../../docs/host-contract-profile.md) and
[run evidence](../../docs/evidence/csh-059/README.md).

Each boundary run emits the residual conditions in
`tests/host_capability_limits.py` with the source page, actual host/executable,
reason and next owner (CSH-062). Missing French/UTF-8 locales, a root identity
and an absent explicit block-node witness remain separate limitations.
`host_limits` are parent system queries; `child_resources` are actual soft/hard
limits measured after the harness applies its protections (`-1` means infinity).
`filesystem_limits` query a temporary directory on the fixture filesystem.
None of these are per-utility capacity measurements. Successful bounded sizes
are recorded in the individual cases; they are not advertised maxima.

## CSH-060 environment qualification

`make test-host-profile` includes defined-format, error, locale, file-limit,
exec-size and explicit rm prompt witnesses. It builds `host_printf_faults`, a
test-only copy of the unchanged adapter/vendor source with local allocation
interposition; it never changes production printf or its provenance.

On a disposable Linux container, install `acl` and opt in to root-owned private
fixtures with `HOST_PROFILE_FLAGS=--controlled-identities`. The helper drops
supplementary groups and saved root credentials, records actual real/effective
UID/GID, and execs the inventoried utility. Private device nodes receive only
stat operations. Run ordinary non-root block qualification separately.

`--controlled-identities --unequal-acl` is a separate **strict failing reproducer**
for the recorded Debian 12 GNU test/bracket ACL grant with unequal IDs. Its
expected grant stays success; no known-gap allowance is added. The passing
controlled subset checks ACLs with equal IDs and unequal owner/group identities
separately. The combined condition remains owned by CSH-062.

For an alternative BusyBox echo profile, create a private directory containing
`echo -> /bin/busybox`, prepend it to the qualified PATH, and select
`--echo-policy busybox-fancy`. This explicitly selects FEATURE_FANCY_ECHO as
specified by the [1.35.0 source](https://git.busybox.net/busybox/tree/coreutils/echo.c?h=1_35_0).
It ignores POSIXLY_CORRECT; the expected bytes are authored independently.
Other BusyBox configurations require their own policy and do not inherit this
claim. Every run records the actual echo binary hash and policy source.

See [CSH-060 evidence and reproduction](../../docs/evidence/csh-060/README.md).


## CSH-061 ACL extension

The Linux-root `--controlled-identities` scope also checks access and inherited
(default) ACLs for read, write and execute, both named users and supplementary
group 10003. Each has grant, unrelated-identity and masked-denial witnesses for
test/bracket and actual read/append/exec operations. Defaults are applied to a
private parent before child creation; no child chmod rewrites its inherited
mask. Execute controls copy the test helper, never execute a shell script that
could change credentials. The helper verifies and prints actual supplementary
groups, real/effective IDs, and drops saved root credentials before exec.

Darwin's privileged ACL environment is unavailable in the retained native run
and is an individual limitation; Linux results do not qualify Darwin ACLs.
See [CSH-061 evidence](../../docs/evidence/csh-061/README.md) for the unequal-ID
libc investigation and unchanged strict failure expectations.


## CSH-062 supplied filesystem and credential combinations

`--controlled-identities` additionally checks multiple named-user ACL entries,
first/second supplementary-group grants (groups 10003 and 10004), named-user
precedence over group grants, unrelated groups and masked grants. Each has
read/write/execute operations and test/bracket predicates, for both access and
inherited ACLs. `--unequal-acl` changes these new combinations to unequal
real/effective UID/GID pairs and preserves every success expectation.

Use `--fixture-root /fixtures` only with an explicitly supplied disposable
filesystem directory. All private cases and filesystem queries use that root;
records include the actual device and Linux mount type/options. Setup errors
retain the command, status and diagnostic as failures and still write the
qualification JSON. An unsupported ACL filesystem is never qualified by a
partial run. Temporary files are cleaned up even on setup failure.

The Dockerfile accepts `--build-arg BASE_IMAGE=debian:trixie-slim` for an updated
vendor recheck; its default remains Debian 12. The [CSH-062 evidence](../../docs/evidence/csh-062/README.md)
records exact images, coreutils/libc identities, overlay and disposable-volume
results, and unsupported tmpfs ACLs. Every residual is individually retained
with its source, actual environment/executable identity, reason and next owner
[CSH-063](../../docs/tickets/CSH-063-host-platform-residual-qualification.md).
The privileged Darwin environment and physical terminal remain unavailable.


## CSH-063 ACL selection and creation modes

Controlled Linux cases additionally check owner precedence, owning-group grants,
matching-group denial without falling back to other, and owner/other permissions
outside the ACL mask. Default ACL creation with mode 0700 must suppress a named
user grant; mode 0777 retains it. All three permissions have test/bracket and
independent read/write/execute controls in string/file/stdin modes. Setup checks
the actual numeric ACL and file ownership before testing the selected utilities.
The optional unequal-ID run preserves both grants and denials as strict assertions.

Qualification JSON now embeds hashes of the build/test source inputs. Setup
errors and timeouts retain diagnostics as failures, with the actual fixture mount.
[CSH-063 evidence](../../docs/evidence/csh-063/README.md) compares Debian 13 and
newer Debian sid vendors and retains unsupported filesystem results separately.
[CSH-064](../../docs/tickets/CSH-064-host-platform-external-prerequisites.md)
owns every remaining condition; utility/libc/platform vendors own implementation.
No privileged Darwin environment or physical terminal has been supplied.


## CSH-064 namespace and bind prerequisites

The qualification record includes actual Linux user/mount namespace links,
UID/GID maps and the setgroups policy, separately from the helper's measured
credentials, system limit queries and per-case verdicts. All controlled ACL
fixtures validate numeric ACL metadata and ownership before predicates run;
malformed, duplicate or unexpected entries are setup failures.

A disposable root Linux container with util-linux `unshare` can supply an
additional credential namespace without creating or editing user accounts:

```sh
unshare --user --map-users=0:0:1 --map-users=1:20001:65535 \
  --map-groups=0:0:1 --map-groups=1:20001:65535 --setgroups=allow \
  python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" --strict-gaps --boundaries \
  --printf-faults build/tests/host_printf_faults --controlled-identities \
  --record /tmp/namespace.json
```

Repeat separately with `--unequal-acl` for strict grants and denials. Namespace
setup or private-node failures are failures, never an implicit permission to
skip a fixture. Keep the unshare command's status and diagnostics if it fails
before the harness starts. This mapping preserves namespace root but maps
fixture UID/GIDs 10001..10005 to outer 30001..30005; it does not establish every
namespace or filesystem contract.

For a separately supplied disposable directory, the focused diagnosis requires
Linux root and changes only private temporary fixtures:

```sh
python3 tests/host_platform_probe.py --fixture-root /fixtures \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" --record /tmp/platform.json
```

It compares socket stat/test/bracket predicates with a bounded AF_UNIX transfer,
and external chmod with Python's direct chmod under owner/non-owner credentials.
The child drops supplementary groups and all saved root IDs and records effective
capabilities. Status, diagnostics, metadata before/after and executable/source
hashes remain in JSON. A false grant returns failure even if the supplied mount
is `fakeowner`. The probe supplements the full runtime/PTY integration and does
not qualify a host by itself. See [CSH-064 evidence](../../docs/evidence/csh-064/README.md)
for results and unavailable external prerequisites. CSH-064 retains qualification
ownership; selected utility/libc/platform vendors retain implementation ownership.


## Probe timeout ownership

The focused Linux probe uses one five-second watchdog for the credential wrapper
and selected utility in an inherited process group. The privileged runner
becomes a child subreaper while the invocation runs, kills the owned group on
exit/timeout, and waits for its adopted descendants within a separate two-second
cleanup bound. It restores its prior subreaper setting and never waits for
unrelated children. Cleanup errors force a failure record. The inner credential
wrapper has no competing timeout or new process group.

In a disposable root Linux container, `make test-host-probe-timeout` exercises
the actual nested path with a slow utility, a forking slow utility, and an ordinary
control. It checks the deadline, strict timeout record, measured IDs, disappearance
of every owned PID (including zombies), and survival of an unrelated child.
Only private files and processes are used. See
[CSH-064 completion](../../docs/evidence/csh-064-completion/README.md) for validation.

## CSH-072 filesystem providers

`make host-profile` builds `paths.c` as standalone readlink and realpath programs
in the opt-in PATH. They repair stock diagnostic/Issue-8 option gaps and check
output errors. The provider manifest includes all 21 filesystem utilities; Linux
setup requires `file` and `pax`, supplied by Docker and CI.

`make test-host-profile` requires the strict filesystem audit with these providers.
`make test-host-filesystem-audit` retains stock-provider failures separately.
See [filesystem scope and limits](../../docs/host-filesystem-evidence.md), including
the 40-link missing-final fallback bound and remaining CSH-080 contracts. Neither
provider is installed over a system executable or linked into cshell.


## CSH-072 selected find and pax repairs

On Darwin the profile now requires GNU `gfind`, supplied by Homebrew findutils
(or an explicitly supplied prefixed executable on the provisioning PATH).
Linux continues to use its distribution find. This repairs Apple's silent
logical-cycle success without wrapping or changing system find.

Both platforms select a standalone pax built offline from checked-in
[MirCPIO 20240817 source and documented local changes](vendor/pax/CSHELL-CHANGES.md).
The fixes constrain ustar mode fields to their specified bits and drain final
partial writes or return failure. The selected profile now requires every
cycle/archive/I/O provider assertion via `--provider-audit`; none are diagnostic
allowances. Stock audit failures remain retained separately. CI still installs
stock pax so the diagnostic comparison remains reproducible.

`make host-profile` does not install host packages; missing gfind fails setup
with the same explicit provisioning error as missing gtest. The new provider
is never linked into cshell or installed over system pax. Record provider hashes
and repeat filesystem, host integration and selected-PATH runtime checks after
changing the profile.

CSH-080 also selects GNU `gdd` on macOS from the existing coreutils dependency.
Apple dd miscounts a short input block padded by `conv=sync` as a whole input
block. The selected provider must pass the unchanged whole/partial counts and
file-content assertions. Native provider paths/hashes, package version and the
stock failures are retained in [CSH-080 evidence](../../docs/evidence/csh-080/README.md).
`make test-host-filesystem-allocation` builds a separate test-only local pathname
provider with call-site ENOMEM controls; production PATH never selects it.

## CSH-085 Linux du configuration

Linux selects `build/host-du`, a standalone exec launcher for `/usr/bin/du`
that sets `POSIXLY_CORRECT=1` in the utility process. GNU documents this mode
as selecting the required 512-byte default when block-size overrides are absent:
[Block size](https://www.gnu.org/software/coreutils/manual/html_node/Block-size.html).
Explicit `-k` and user block-size settings remain GNU behavior. The launcher
passes the argument vector directly to `execv`; it neither reads nor changes
utility output or status. It cannot change the invoking shell's environment.
GNU retains all traversal, accounting and option handling. The manifest records
both launcher and backend hashes plus the exact environment configuration.

The stock Linux default reports 1024-byte units and fails the unchanged default
512-byte assertion in all four execution modes. Stock audit results retain this
failure. Native macOS uses its unchanged system du. No system executable is
replaced. See [CSH-085 evidence](../../docs/evidence/csh-085/README.md).

## CSH-086 owned-terminal overwrite decisions

Both platforms select `build/host-cp`, built offline from pinned GNU coreutils
9.7 with a local declined-copy status repair. The [vendored source notes](vendor/coreutils/README.md)
record its archive hash, patch, license and build configuration. Provisioning
records archive/patch/executable hashes. The C-locale build disables NLS, ACLs
and SELinux; those contracts remain open. Stock audits continue using the
system cp and retain decline-status failures. Run
`make test-host-filesystem-interactive` for the 39 new PTY assertions.

CSH-087 retains these exact provider builds and adds
`make test-host-filesystem-decisions`: 68 strict multi-operand, recursive prompt
and same-device directory assertions. The full host profile includes them.
No extra allowance or provider adapter is added; stock decline-status failures
remain in the separate audit. See [CSH-087 evidence](../../docs/evidence/csh-087/README.md).

CSH-088 adds `make test-host-filesystem-metadata`: 64 strict ls numeric metadata,
size/time ordering and find -newer assertions, including adjacent nanoseconds
and reference symlinks. No selected provider or build flags change. Every
private timestamp is read back exactly before exec; unsupported resolution is
a setup failure. See [CSH-088 evidence](../../docs/evidence/csh-088/README.md).

## CSH-089 recursive rm provider

The profile now selects `build/host-rm` on both platforms. The shared offline
GNU coreutils 9.7 build produces cp and rm; `rm-parent-prompt.patch` preserves
explicit final `-i` parent decisions after retained children. The manifest
records rm's archive, patch and executable SHA-256. The C-locale build disables
NLS, ACL, SELinux and GMP support, so it does not qualify those environments.
No system executable is replaced. `make test-host-filesystem-recursive` requires
all 30 new assertions; full stock audits preserve unpatched GNU prompt failures.
See [CSH-089 evidence](../../docs/evidence/csh-089/README.md).

CSH-090 adds `make test-host-filesystem-path-limits`: 32 assertions for measured
total pathname bytes and portable limits, including per-operand diagnostics.
The full profile includes them; selected provider sources and flags are unchanged.
See [CSH-090 evidence](../../docs/evidence/csh-090/README.md).

### Physical cwd namespace witnesses (CSH-091)

`make test-host-filesystem-cwd` qualifies external `pwd -P` and `pwd -L -P`
after private leaf/parent renames and removals, using direct exec and all three
cshell input modes. A child-only helper checks cwd inode identity and getcwd
resolution/ENOENT before exec; setup and exec failures cannot satisfy utility
error assertions. Exact stdout, diagnostics, status, effects and cleanup are
required. Six harness regressions cover corrupted markers/output/effects,
partial setup, wrong probes, exec failures and bounded timeout cleanup.
No mounts, host volume exhaustion, PWD edits or provider patches are involved.
Permission, total path limits, logical-mode namespace changes and libc/stdio
failures remain open under CSH-094.

### Creation masks and modes (CSH-092)

`make test-host-filesystem-creation` requires 104 final mkdir/mkfifo mode
assertions with child-only masks and independently measured directory/FIFO probes.
All four execution modes require exact effects, status and channels; setup and
cleanup errors fail. See [evidence](../../docs/evidence/csh-092/README.md).
Transient permissions, ACL inheritance, arbitrary mode/parent graphs and capacity
remain open under [CSH-094](../../docs/tickets/CSH-094-filesystem-environment-residuals.md).

### Output errors (CSH-093)

CSH-093 supplies 32 external pwd output-error assertions on macOS and 56 pathname utility assertions on Linux: closed stdout EBADF and readerless-pipe EPIPE for pwd -P, -L, -L -P and -P -L, plus Linux virtual-device ENOSPC for those forms and basename/dirname. PWD is unset, so logical forms fall back to the physical cwd. Child-only kernel probes precede exact provider exec. These cases do not supply libc-internal faults, actual filesystem exhaustion, logical namespace changes or arbitrary output failures.

`make test-host-filesystem-output` requires zero allowances. See
[CSH-093 evidence](../../docs/evidence/csh-093/README.md). All four original conditions remain open under CSH-094.

### Numeric magic boundary qualification (CSH-095)

`make test-host-filesystem-magic` requires 184 assertions against the inventoried
external `file` in direct and three cshell modes. The profile retains the stock
file provider: no replacement or allowance is introduced. Authored byte/short
boundaries and one-database first-match ordering do not qualify every magic
type or default database. See [CSH-095 evidence](../../docs/evidence/csh-095/README.md)
and [CSH-096 residuals](../../docs/tickets/CSH-096-filesystem-environment-residuals.md).

### Calendar timestamp qualification (CSH-096)

`make test-host-filesystem-calendar` runs 40 cases / 160 strict assertions against
the inventoried external touch provider directly and via cshell string/file/stdin.
The full selected profile includes these cases. Integer UTC calendar arithmetic
supplies exact expectations; target and unequal fractional baseline timestamps
must survive independent utime/stat probes before exec. The cases require empty
channels, status zero, exact selected and preserved timestamps, and unchanged
file content. Setup failure is a failure, never a skip.

This covers authored representable dates, not complete timestamp ranges,
unsupported-range errors, current clocks, DST or privileged filesystem behavior.
See [CSH-096 evidence](../../docs/evidence/csh-096/README.md) and
[CSH-098 residual ownership](../../docs/tickets/CSH-098-filesystem-environment-residuals.md).

### Reference timestamps and alias graphs (CSH-097)

`make test-host-filesystem-reference` runs 28 cases / 112 assertions through
direct exec and cshell string/file/stdin dispatch. The full selected profile
includes every case. Independent timestamp probes and stat/lstat measurements
prove the private graph before execution. All metadata is captured before
content reads can alter a hard-linked inode’s atime. Exact field selection,
unchanged reference files and links, and no-create continuation are required.
Four harness regressions cover corrupt effects/channels, setup failures and
failed-exec/timeout cleanup in all modes. Arbitrary graphs, live clocks,
unsupported timestamps, races and permission/ACL errors remain open.

See [CSH-097 evidence](../../docs/evidence/csh-097/README.md) and
[CSH-098 residual ownership](../../docs/tickets/CSH-098-filesystem-environment-residuals.md).

## Date syntax, fractional seconds and fixed TZ (CSH-098)

`make test-host-filesystem-datetime` adds 64 cases / 256 strict assertions to
the full selected profile. The existing touch provider must accept period/comma
fractions, T/space separators, local fixed TZ offsets and explicit Z, preserving
unselected fields and target identity/mode/content. Integer authored UTC fields
and fractions supply expectations; exact inode readback precedes execution.
No provider or allowance changes are made. DST, zoneinfo, arbitrary timestamp
precision/ranges, live clocks and other unsupplied environments remain under
[CSH-105](../../docs/tickets/CSH-105-filesystem-environment-residuals.md).

CSH-099 adds `make test-host-filesystem-timezone`: 104 cases / 416 assertions
for explicit POSIX daylight rules around unique local transition times.
It requires the unchanged selected touch provider and zero allowances.
Skipped/repeated times, other rules and timezone databases remain under CSH-105.

## CSH-100 Julian and numbered day rules

CSH-100 supplies 128 touch cases / 512 assertions for explicit POSIX Jn and zero-based n daylight-saving rules across common and leap years, including default 02:00 transitions and unique times before/after the authored changes. Independently authored UTC fields and exact target-inode timestamp probes supply the oracle for -d/-t and all four field selections. Skipped/repeated times, arbitrary rule values and transition times, timezone databases, timestamp ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

See [retained evidence](../../docs/evidence/csh-100/README.md). All remaining contracts and four original U-040 conditions
remain open under CSH-105; no whole-utility qualification is claimed.

## CSH-101 explicit transition clocks and offsets

CSH-101 supplies 96 touch cases / 384 assertions for explicit M/J/n transition clocks, minute/second standard and daylight offsets, 45-minute-10-second and 30-minute-15-second advances, and negative/next-day transition times. Independently authored UTC fields and exact target-inode probes supply the oracle for -d/-t and all four field selections. Skipped/repeated times, arbitrary rules and offsets, timezone databases, timestamp ranges, creation/current-time tolerances, races and permission/ACL errors remain unqualified.

See [retained evidence](../../docs/evidence/csh-101/README.md). All remaining contracts and
four original U-040 conditions remain open under CSH-105.

The CSH-101 profile selects GNU touch 9.7 linked with pinned IANA tzcode 2025b
on both platforms. Apple touch and the installed GNU touch on macOS return
incorrect timestamps for the authored negative and next-day transition rules;
those 64 stock assertions remain failures. See [provider provenance](vendor/tzcode/README.md).
The replacement changes only the opt-in profile; no system utility, timezone
file or shell runtime is modified. All older filesystem assertions remain required.

## CSH-102 string-magic qualification

CSH-102 supplies 91 file string-magic cases / 364 assertions for required backslash and control-character escapes, one/two/three-digit octal escapes including NUL and byte 255, decimal/octal/hexadecimal offsets, exact/trailing/mismatched/truncated fields and at/past-EOF boundaries. Independently authored bytes, exact channels/status and unchanged sample/database contents supply the oracle. Other types/widths, unsigned ranges, multiple databases, default classification, arbitrary encodings/locales and utility resource failures remain unqualified.

The selected file provider remains the inventoried host executable; no provider
replacement or output translation is introduced. See
[CSH-102 evidence](../../docs/evidence/csh-102/README.md).

## CSH-103 magic-message qualification

CSH-103 supplies 108 file magic-message cases / 432 assertions for native signed byte/short and string printf-style descriptions at top level and in continuations. Literal expected bytes cover signs, width, precision, zero padding, decimal/octal/hexadecimal output, alternate forms, characters and literal percent signs. Exact channels/status, pre-exec readback and unchanged sample/database contents supply the oracle. The pinned file 5.46 provider repairs one-byte magic dispatch, bounded format validation and textual rule order; original stock failures remain separately retained. Other types/widths, unsigned ranges, multiple databases, arbitrary formats/encodings/locales and utility resource failures remain unqualified.

All 21 residual utility contracts and four original U-040 conditions remain open in
[CSH-105](../../docs/tickets/CSH-105-filesystem-environment-residuals.md).
See [CSH-103 evidence](../../docs/evidence/csh-103/README.md) for provider provenance, strict results and stock failures.

## CSH-106 readlink byte qualification

Run `make test-host-filesystem-link-bytes` for the required opaque link byte suite.
CSH-106 supplies 1088 readlink cases / 4352 assertions: each non-NUL byte, authored valid and invalid UTF-8 sequences, embedded newlines and shell metacharacters, and mixed targets of 255/256/257/511/512/513/1023 bytes, in C and an installed UTF-8 locale, with and without -n. Authored output bytes are independent of the provider; pre-exec lstat/readlink probes establish stored bytes, and post-exec probes require unchanged inode, mode, size and contents. Exact channels/status and cleanup are mandatory.

Arbitrary byte sequences and locale repertoires, libc-internal allocation failures, true filesystem limits, namespace races and other error environments remain unqualified. No provider code changed.

## CSH-107 omitted-who creation modes

Run `make test-host-filesystem-omitted-who` for the 288 required assertions.
CSH-107 supplies 72 mkdir/mkfifo cases / 288 assertions for symbolic creation modes with omitted who under independently proved child-only masks 027, 077 and 777. Authored literal modes cover masked addition/removal, copy addition/removal/assignment, conditional execute, empty assignment and multiple actions, alongside explicit-who controls. Exact channels/status, final type/mode and cleanup are required. The selected pinned GNU coreutils 9.7 creation utilities replace Apple providers that retain masked group bits during copy assignment.

Further symbolic-mode and parent graphs, special-bit modes, transient permissions, ACL inheritance, other identities, path/depth limits and capacity exhaustion remain unqualified; FIFO transfer is outside creation. Apple stock failures are retained separately; no allowances are introduced.

### CSH-110 selected ln

The opt-in profile builds unmodified `ln` from the pinned GNU coreutils 9.7
archive, with the existing configure options, and records its source archive,
exact binary hash and `build/host-coreutils-build/ln.log`. Native Apple `ln -fs`
replaces a same-entry source instead of preserving it and diagnosing the error;
that failure remains required in the strict stock audit. The 29 link graph
cases require all earlier assertions and introduce no selected-profile allowance.
See [CSH-110 evidence](../../docs/evidence/csh-110/README.md). System executables
are untouched; only the opt-in PATH selects this provider.
## CSH-070 formatted-output profile

`make test-host-formatted` builds a catalog-capable printf and separately
selects the new literal echo build in a private PATH. It is also a prerequisite
of `make test-host-profile`; the latter retains its stock echo selection.
[Whole-page accounting and declared policies](../../docs/host-formatted-output.md)
explain the new exact locale/conversion cases, libc and stack controls, bounded
exec threshold searches and explicit remaining scope. French/German catalog
sources are checked in and compiled using `gencat` under `en_US.UTF-8`.

The new source fixes propagate libc formatting failure, move the input-sized
conversion workspace off the stack, diagnose trailing character-constant text,
and evaluate floating operands as `strtod` input. Catalog and conversion changes
apply only to the opt-in provider. [CSH-079](../../docs/tickets/CSH-079-formatted-output-residuals.md)
owns the six retained conditions and conditional allocation-helper prerequisite;
the original historical limitation reasons remain unchanged. Darwin 1 MiB stack
exec searches failed cleanup and are excluded from the selected profile.


## CSH-073 text stream subset

The [text/byte clause map](../../docs/host-text-contracts.md) and
[section ledger](../../tests/host_text_contracts.json) add bounded assertions for all 25 CSH-073 utilities,
sparse offsets, owned signal fixtures and explicitly supplied Linux ENOSPC.
The strict provider audit retains failed contracts separately; no full utility
page or common-default family is promoted. CSH-073 remains open for the listed
residuals, with CSH-074 sharing the ed signal requirement.


## CSH-073 pinned text repairs

`make test-host-text-repaired` builds and selects the [pinned text providers](text/README.md)
for the strict text audit. To select the same providers for the broader profile,
run `make test-host-profile HOST_TEXT_PROVIDER_BIN="$PWD/build/text-providers/bin"`
after `make host-text-providers`. Omitting the variable restores the original
profile selection. Only declared symlinks in `build/host-profile/bin` change;
stock PATH and system executables are unchanged. Download/source/compiler/patch
and executable identities are retained in the build manifest and text results.

## CSH-071 predicates and identities

`test.c` adds POSIX.1-2024 locale-aware `<`/`>` and effective-credential r/w/x
predicates, delegating remaining expressions to the absolute GNU test provider
selected during the build. Both adapter and
backend hashes are retained. `build/host-test-provider.h` records the provider;
`make host-profile` regenerates it when the selected path changes. No
system executable is replaced. The adapter now uses effective-credential
`faccessat` for r/w/x predicates; remaining expressions retain their vendor backend.

`make test-host-permissions` is included in `make test-host-profile`. Its
[clause map](../../docs/host-permissions-identities.md) records the exact subset,
Linux-root flags, strict vendor reproducers and still-open CSH-071 obligations.

## CSH-077 terminal adapters

The profile also builds `terminal.c` as standalone tabs/tput/mesg/who adapters
for the four reproduced contracts described in the
[terminal section map](../../docs/host-terminal-contracts.md). Each dispatches
to `/usr/bin/<name>`; no system executable is changed. The tput adapter exposes
clear/init/reset only, excluding terminfo query extensions.

Linux provisioning additionally installs `ncurses-bin` and `bsdextrautils` for
tic, tabs, tput and stock-provider write comparisons; libncurses-dev supplies
the adapter headers/library. `make test-host-profile` includes 755 strict
PTY/record/data witnesses and cleanup regressions. Records distinguish adapter/vendor hashes,
package versions and actual PATH. Native and container evidence remain separate.
Physical hardware and remaining full registered-session contracts stay with
[CSH-081](../../docs/tickets/CSH-081-host-terminal-residual-contracts.md); the strict
Linux delivery subset is described below.

## Standalone write provenance

`vendor/write.c` is derived from FreeBSD source at commit
[`a179e72489f8601f37b9039c86d3f224c73b3d51`](https://github.com/freebsd/freebsd-src/blob/a179e72489f8601f37b9039c86d3f224c73b3d51/usr.bin/write/write.c).
Its BSD-3-Clause license remains in the file. `build/host-write` is selected only
by this opt-in PATH profile; it is never installed setuid/setgid or over the
system provider. Kernel permissions still constrain terminal access.

Local changes remove FreeBSD-only Capsicum APIs and use portable POSIX calls;
they do not claim to reproduce the Capsicum sandbox. Session selection retains
the latest-access-time policy and self-session fallback. Fixed-width session
fields are bounded, recipient names cannot traverse out of /dev, symlinks and
non-terminal recipients are rejected, and message permission is rechecked on
the opened recipient descriptor. The sender terminal must also be writable.

The repaired provider emits the specified greeting structure (date format
`YYYY-MM-DD HH:MM:SS` in local time), alerts the sender exactly twice after a
successful greeting, preserves print/space/bell characters, and appends `EOT\n`
on EOF or SIGINT. Canonical erase/kill remain the terminal driver's job. Valid
nonprinting characters retain the FreeBSD hexadecimal `<0xX>` policy; invalid
multibyte input is an error. Locale/multibyte and additional IEXTEN combinations
are not yet qualified. Selection information goes to the original stdout.

Recipient stdio is unbuffered. The SIGINT handler uses only async-signal-safe
write/_exit, avoiding the upstream stdio/exit handler; ordinary input/output
errors fail. SIGHUP retains its default action. This is a local provider repair,
not a claim that upstream FreeBSD or the stock util-linux provider was fixed.
Linux registered sessions have 47 strict assertions; macOS currently verifies
build and error-path dispatch, with positive registered sessions still requiring
a supplied disposable environment.

The tput adapter now links ncurses (`libncurses-dev` on Linux; the system SDK on
macOS). It queries a known clear capability before dispatch, treating absence as
a successful no-op without normalizing possibly ambiguous vendor failure codes.
Attached/repeated -T options are supported. The mesg adapter diagnoses the lack
of any terminal on fd 0/1/2. All other unqualified contracts remain with CSH-081.

## CSH-081 terminal provider changes

The opt-in PATH additionally selects `stty` and `tty`. `stty` still uses the fixed
`/bin/stty` vendor for termios behavior; `-nl` explicitly appends `-inlcr -igncr`
to repair Darwin's combination, preserving operand order. Reports are copied
through a constant-size buffer and checked writes, so a vendor cannot silently
succeed after a real stdout failure. `tty` uses `isatty`/`ttyname` and checked
stdio, returning >1 for failed output on both terminal and nonterminal input.
Neither provider replaces a system file.

`tabs` now builds from `tools/host-profile/tabs.c` using ncurses capabilities,
instead of normalizing arguments and executing the vendor. It supports the base
interface, chooses the last `-T`, accepts ascending absolute/relative lists with
comma/space/tab separators, and clears/sets only positions within the terminal
width. It uses a nonzero ioctl width before the terminfo width and supports
widths 1–65,535. All generated bytes and final flush are checked. This repairs
Darwin's extra stop beyond the boundary for `tabs -1`. XSI presets and margins
are not part of this provider interface; newline is not a valid blank separator.

`tput clear` likewise checks its own capability output and flush, distinguishing
an absent operation (successful no-op) from an output error (status 5). `init` emits is1, is2 and is3 in order; `reset` emits rs1, rs2 and rs3,
with each absent reset phase falling back to the corresponding init phase.
Missing strings are successful no-ops and processing continues in operand order.
This is the profile's implementation-defined initialization/reset policy: it
emits terminfo strings through `tputs`, without changing termios modes, reading
initialization/reset files, executing initialization programs, or adding vendor
margin/tab sequences. These vendor extensions are outside the selected policy.
All operations check output and flush errors (status 5). Unknown terminal types
return 3; failure to locate a terminal database returns 5. Both tabs and tput choose `dumb` when TERM is
unset/null and no explicit type is supplied; the standard permits an unspecified
default. This policy does not promise every host has a database entry for it.

The [terminal section map](../../docs/host-terminal-contracts.md#csh-081-residual-implementation)
records strict new witnesses and outstanding partitions. The profile remains
opt-in, and selected repairs do not qualify every contract of these utilities.

The CSH-081 continuation adds strict three-phase initialization/reset ordering,
per-phase fallback, control/eight-bit capability bytes, unchanged terminal modes,
and missing-operation behavior even on read-only terminal output. The stock
`tput` identity is retained only for comparison. Full base `stty -a` fields are
compared with independent termios and window state (including changed controls
and flags); this does not qualify physical serial effects. Private `who -u`
records check current, two-hour and over-24-hour idle policy and process IDs.
The Linux session subset now has 28 cases in five paths (140 assertions), adding
default SIGHUP/SIGQUIT/SIGPIPE and actual distinct registered sender/recipient
users, with successful group access and denied recipient permissions. Recipient
peer closure after the verified greeting tests actual data and EOT output errors;
both require failure and diagnostics. The
original counts above describe the earlier CSH-077 increment.

## CSH-074 language/editor providers

The profile builds private ed, xargs, m4 and patch executables offline, alongside printf.
`vendor/ed` is GNU ed 1.22.6, GPL-2.0-or-later; its COPYING and complete compiled
sources are retained. `vendor/xargs` derives from FreeBSD commit
`16a79708d089423ec0c3d32f25e7ca97ae58e97b`; each source retains its license.
`vendor/m4` retains the complete GNU M4 1.4.20 source archive and GPL-3.0-or-later
COPYING, plus a reviewable patch for FIFO wrap processing and error status.
Each directory's `provenance.json` records upstream hashes and local changes. These are independent host processes, never linked into cshell.

The ed adapter emits the exact POSIX SIGINT stdout marker. The xargs adapter
preserves empty NUL arguments, implements empty-input invocation/`-r`, handles
strict byte limits and oversized `-s`, and uses a portable fork/error-pipe path.
A separate test-only ed build injects backing-store creation and write failures.
The production provider contains no fault-injection environment switches.

Linux explicitly supplies `bc`; stock m4 remains installed for historical
comparisons, while both platforms select the new private m4 executable.
M4/gnulib use the upstream build and warning policy: only `-Werror` is removed
from CFLAGS, retaining sanitizer instrumentation and all other flags. The
requested and effective flags are retained in `build/host-m4-build.json`.
The manifest records each real executable, including these overrides. No system
programs are overwritten.

`make test-host-languages` and `make test-host-profile` run the
[773 assertions](../../docs/host-languages-evidence.md), including SIGINT by
default. These qualify the declared operation subset only. Full pages remain
open. The six M4 provider regressions (including the three formerly failing
contracts) are now required by default and can be selected alone with
`--provider-regressions`. Historical failures remain preserved.


`vendor/patch` supplies GNU patch 2.8 with its complete source archive and
GPL-3.0-or-later license. It preserves the first backup across multiple patches
of one file; the local diff additionally backs up an existing `-o` output when
`-b` is used. `build_patch.py` authenticates the archive and builds offline with
the same upstream warning policy as M4. `build/host-patch-build.json` records
archive/diff/binary hashes and requested/effective build flags. The suite now
includes automated controlling-terminal editor and xargs prompt checks, and
patch conditional-output and backup interactions.

## CSH-076 locale and catalog subset

Dependent tracks can run `make host-locales` independently or
`make host-catalog-fixtures` for verified catalogs and byte inputs too. The
[shared interface](../../docs/host-locale-catalogs.md#shared-interface-for-dependent-tracks)
documents `fixtures.json`, the Python loader and retained generation lifetimes.

[Provider setup, independent assertions and exact unqualified contracts](../../docs/host-locale-catalogs.md)
cover gencat/gettext/iconv/locale/localedef/msgfmt/ngettext. `make test-host-profile`
includes the bounded strict subset; `make test-host-catalog-contracts` also runs
all retained reproducers without exclusions. Full utility contracts remain open.

CSH-076 now builds pinned standalone gencat providers and a private GNU libiconv
CLI for code-name conversions. Their strict retained reproducers pass with no
failure exclusions. First catalog setup downloads and checks the pinned GNU
archive; builds are private and reused after verification. See
[provider provenance and licenses](vendor/catalog-providers.md) for patches,
compiler policy, source hashes, charmap fallback and redistribution notices.

## CSH-078 codecs and services

Linux codec qualification additionally requires `sharutils` and `libbsd-dev`.
Both host profiles build a standalone Apple/FreeBSD `uudecode` with corrected
stdout cookies, output paths, symbolic permissions and MIME decoding; source commit, license and build adapters are documented in
[the service profile](../../docs/host-service-profile.md#selected-provider-repairs).
`make test-host-profile` now includes safe native codec/read-only date witnesses.

`make docker-test-host-services` separately provisions scheduler, local mail,
logging and CUPS services inside an owned disposable container. It never invokes
those services on the developer host. Exact commands, isolation, qualified
subsets and the full-contract exclusions are in the
[service profile](../../docs/host-service-profile.md) and
[retained results](../../docs/evidence/csh-078/README.md).
