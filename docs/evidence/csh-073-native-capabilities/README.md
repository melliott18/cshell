# CSH-073 native capabilities and attested faults

This follow-up repairs the concrete gaps left in the
[provider phase](../csh-073-providers/README.md). Earlier failures and evidence
remain unchanged. The opt-in PATH selects source-built GNU cat and diffutils
3.10 cmp in addition to the earlier providers. System binaries are unchanged.
The [recipe](../../../tools/host-profile/text/README.md) records archive,
patch, compiler and executable hashes.

## Reproduce

```sh
make test-host-text-repaired
make test-host-inventory test-host-text-harness
make test-host-text-faults
make test-host-text-native-capacity # macOS; includes the full audit
make test-host-profile HOST_TEXT_PROVIDER_BIN="$PWD/build/text-providers/bin"
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
```

Linux uses the workflow's owned 1 MiB tmpfs for capacity. Native macOS uses
`hdiutil` to create a private 1.44 MiB FAT12 filesystem. Its measured size,
attachment identity, real ENOSPC, detachment and removal are recorded. If an
attachment cannot be identified, the image is retained and cleanup fails;
there is no recursive removal of a potentially mounted directory.

Darwin blocked-write tests use `/usr/bin/sample` on the owned PID and require
repeated write syscall frames while the private pipe remains full with no drain.
Linux retains `/proc/PID/wchan`. The observer never changes signal disposition.
Negative controls reject the wrong PID, non-write frames, single samples and
summary-only output.

## Faults and fixes

The test-only shared library is loaded into the source provider after shell exec,
never into cshell. Each assertion requires a private trace proving injection:
cat/head/cmp read EINTR/EIO diagnostics and short reads, cat short/EINTR write
preservation, and sed growth realloc ENOMEM. There are 12 cases in direct and
shell-exec modes, with a five-second deadline and 65,536-byte capture ceiling.
No trace, signal death in place of an ordinary error, wrong bytes or failed
cleanup can pass. Linux cat's zero-copy capabilities are deliberately disabled
in this instrumented fixture. No arbitrary recovery or signal restart claim is
made.

Unpatched GNU sed 4.9 on Darwin returned success and no output after getdelim
allocation failure: libc set neither ferror nor EOF. The retained intermediate
suite has 22 passes and two failures. `sed-getdelim.patch` treats a negative
non-EOF result as an error, preserving the existing diagnostic and exit path.
Both repaired cases require a positive exit status, diagnostic and empty output.

A sample of an existing stuck jobs-test child localized the earlier native hang
to pending SIGQUIT delivery at sigprocmask, before the waitid race tests. The
harness now clears inherited Mach crash/corpse exception ports only in the
child deliberately receiving SIGQUIT. Default disposition, exact output and
wait-status expectations remain unchanged. The isolated module and complete
native runtime/PTY regression pass. No shell runtime source is changed.

## Results

Final qualification inputs are `c209012f4b7e87939647a27b28af650a6a37d478`.
The index compares every recorded build/test input hash against that revision;
initial and intermediate attempts intentionally retain their earlier identities.

| Environment | Strict audit | Attested faults | Capacity |
| --- | --- | --- | --- |
| macOS 14.8.7 | 792 pass, 0 fail, 0 unavailable | 24 pass, 0 fail | Private FAT12, detached and removed |
| Ubuntu 24.04 | 790 pass, 0 fail, 2 unavailable | 24 pass, 0 fail | Native runner has no dedicated filesystem |
| Debian container | 792 pass, 0 fail, 0 unavailable | 24 pass, 0 fail | Private 1 MiB tmpfs |

All 194 transformation/offset/large-input/interruption extension assertions remain
passing. All 17 harness regressions and inventory checks pass. Native broader
host-profile validation passes 1162 assertions, followed by 732 subset assertions
with two capacity checks unavailable in that separate non-capacity invocation;
the dedicated native audit above supplies and passes those checks.
Native runtime/PTY result groups are 3950, 1, 30, 1 and 33 passes with zero failures
or skips. The one-case groups are module assertions, not one syscall each.

Hosted evidence is from
[final run 36677573365](https://github.com/melliott18/cshell/actions/runs/36677573365),
[bounded-capture run 36677495595](https://github.com/melliott18/cshell/actions/runs/36677495595),
and [initial run 36677291846](https://github.com/melliott18/cshell/actions/runs/36677291846).
Both final Linux jobs pass their runtime and PTY regression steps.
macOS 15 remains queued at capture; no macOS 15 result is claimed.

## Attempts, cleanup and limits

The first image-create experiments used invalid hdiutil type/format arguments;
the successful command uses the default writable format. The first wrapper
attach under the system temporary directory timed out; exact-image querying
found no remaining attachment and cleanup removed the fixture. The later
build-directory fixture succeeded. This does not establish the timeout's root
cause. Intermediate and final source builds, the first failed sed fault cases,
observer samples and metadata are retained separately.

Three children from earlier jobs-module attempts (65644, 79039, 90790) remain
orphaned in Darwin UE state despite accepted SIGKILL. The corrected module
creates no such leftover. An optional upstream sed run additionally encountered
the installed Intel Valgrind under Rosetta stuck during `valgrind ... true`,
before its test could run. The owned run was killed; its Valgrind child 82376
also remained in UE state. Samples and final PID states are retained. Userspace
cleanup of those four old children did not complete; an OS restart may be needed.
No reboot, host binary modification or unrelated process termination was done.

The bounded upstream sed retry used a controlled system PATH with Valgrind
unavailable. It passed 59 sed tests plus 172 gnulib tests, with 29 capability
skips and no failures. Skipped Valgrind checks require a compatible Valgrind
runtime if that optional analysis is desired; they are not claimed as passing.
The required allocation and I/O faults are independently attested by the native
injector. No manual terminal test is required for this verified slice.

Full utility-page qualification and arbitrary allocation/I/O paths remain open
in CSH-073. The finite repaired audit does not promote whole utilities or the
U-034/U-040 families. [artifacts.json](artifacts.json) indexes the compressed
original bytes, SHA-256 hashes, totals and source comparisons.
