# Qualified host utility profile

CSH-056 supplies an **opt-in, bounded integration profile**, not a complete
POSIX utility distribution. It never installs over system binaries or changes
cshell's builtin allocation. All tools are real exec-accessible programs;
`kill` remains intrinsic unless addressed by pathname or through `exec`.

| Host | Selected replacements | Provisioning |
| --- | --- | --- |
| macOS | Standalone printf and local readlink/realpath; Homebrew `gtest`, `g[` and `gfind`; pinned local pax | `brew install coreutils findutils`; prefixed binaries must be on the provisioning process's PATH |
| Debian/Ubuntu | Standalone printf, local readlink/realpath and pinned pax; BusyBox kill | `apt-get install build-essential python3 ed busybox locales acl file pax`; generate `fr_FR.UTF-8` |

Other scoped commands use `os.defpath` without additional symlinks, preserving
cshell's PATH-associated pwd builtin selection. In particular, echo remains the system
executable, with its explicitly recorded Apple/GNU policy. The Dockerfile
installs ed and BusyBox and generates the French locale. CI installs native
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
the 40-link missing-final fallback bound and remaining CSH-083 contracts. Neither
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
