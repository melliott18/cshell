# Pinned text provider repairs

CSH-073 supplies an opt-in replacement profile for the strict audit failures.
The shell and system binaries are unchanged. Builds download checksum-pinned
sources into `build/text-providers/downloads`, retain extracted source, licenses
and logs, and publish executables only after successful builds. No `make install`
is used. `sources.json` is the source lock; changing versions requires repeating
qualification. Network access, a C compiler, make, curl, tar with xz/lzip support,
and the existing host-profile dependencies are needed.

```sh
make test-host-text-repaired
# Reuse the same providers for the broader profile:
make test-host-profile HOST_TEXT_PROVIDER_BIN="$PWD/build/text-providers/bin"
```

The explicit build target is `make host-text-providers`. Ordinary stock tests
and `make host-profile` keep their existing provider selection. The repaired
profile adds only the following overrides through `--text-bin`; provisioning
verifies the build manifest and each executable hash before changing any links.

| Provider | Repair and scope |
| --- | --- |
| GNU coreutils 9.11 `cat`, `head`, `cut`, `tsort` | Accept the bounded large head count, honor multibyte cut `-c`/`-b -n`, and support tsort `-w`. GNU tsort uses an implementation-defined cycle-status maximum of one; this is permitted by Issue 8, not an exact count of arbitrary cycles. |
| GNU sed 4.9 plus `sed-getdelim.patch` | Use GNU regex for native multibyte backreferences; diagnose getdelim allocation failure even when libc does not set ferror. |
| GNU diffutils 3.10 `cmp` | Source build allows attested read faults without modifying macOS protected system executables. GNU cat is likewise selected for test interposition. |
| GNU ed 1.22.6 plus `ed-sigint.patch` | Remove the extra newline preceding the specified SIGINT `?\n` stdout response. The patch changes only that write; upstream `make check`, strict INT buffer recovery and HUP saving are required. |
| Chimerautils/FreeBSD tail at `c480e578085becc3be9073696a6228e507a71c4a` (Linux) | Supply tail `-r`, including line limits and a larger reverse witness. Build the upstream Linux port and its `expand_number` dependency with its compatibility headers. No local tail algorithm or output rewriting. macOS retains its OS-provided tail. |

GNU source archives retain their GPL licenses; the tail source and compatibility
headers retain their BSD notices. They are separate host executables, never
linked into cshell. Tail's upstream Linux compatibility layer does not supply
FreeBSD Capsicum confinement; no sandbox claim is made. The ed and sed patches are local
changes and have not been submitted upstream.

`manifest.json` records archive hashes, patch/build-recipe hashes, compiler and
binary identities. Text result records include that metadata for selected local
builds. Stock provider failures and earlier qualification records remain intact.
No whole-page utility qualification follows from a passing repaired audit.

## Environment requirements

All known failing assertions can be tested automatically. Local macOS checks
Darwin regex/libc and signal behavior. Hosted Ubuntu and Debian check GNU/Linux
providers; Debian's private 1 MiB tmpfs supplies real ENOSPC. The repaired CI
jobs gate the full audit rather than accepting its failure.

The existing macOS environment supplies `/usr/bin/sample` for owned blocked-write
observation and `hdiutil` for a private 1.44 MiB FAT12 image. The wrapper verifies
its mount/size, runs real ENOSPC checks, detaches its own device and removes the
image. Failed detach retains the image and reports failure. No administrator
permission or manual terminal testing is required for these fixtures.

After provisioning the repaired profile:

```sh
make test-host-text-faults
make test-host-text-native-capacity # macOS only; includes full strict audit
```

The fault target loads a test-only shared library into source-built cat/head/cmp
and sed after shell exec. Each result must attest that the fault fired. It checks
read EINTR/EIO diagnostics, short-read bytes, cat short/EINTR-write bytes and sed
buffer-growth ENOMEM diagnostics, in direct and shell-exec modes. Linux cat's
zero-copy capabilities are deliberately disabled in that fixture to exercise
its read/write fallback. This does not establish arbitrary recovery or signal
restart semantics. Complete utility-page coverage remains open.
