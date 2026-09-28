# Qualified host utility profile

CSH-056 supplies an **opt-in, bounded integration profile**, not a complete
POSIX utility distribution. It never installs over system binaries or changes
cshell's builtin allocation. All tools are real exec-accessible programs;
`kill` remains intrinsic unless addressed by pathname or through `exec`.

| Host | Selected replacements | Provisioning |
| --- | --- | --- |
| macOS | Standalone FreeBSD printf with adapters; Homebrew `gtest` and `g[` | `brew install coreutils`; prefixed binaries must be on the provisioning process's PATH |
| Debian/Ubuntu | Standalone FreeBSD printf with adapters; BusyBox kill | `apt-get install build-essential python3 ed busybox locales`; generate `fr_FR.UTF-8` |

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
missing French locales are individually recorded limitations owned by CSH-059;
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
reason and next owner (CSH-060). Missing French/UTF-8 locales, a root identity
and an absent explicit block-node witness remain separate limitations.
`host_limits` are parent system queries; `child_resources` are actual soft/hard
limits measured after the harness applies its protections (`-1` means infinity).
`filesystem_limits` query a temporary directory on the fixture filesystem.
None of these are per-utility capacity measurements. Successful bounded sizes
are recorded in the individual cases; they are not advertised maxima.
