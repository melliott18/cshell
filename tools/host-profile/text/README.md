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
| GNU coreutils 9.11 `head`, `cut`, `tsort` | Accept the bounded large head count, honor multibyte cut `-c`/`-b -n`, and support tsort `-w`. GNU tsort uses an implementation-defined cycle-status maximum of one; this is permitted by Issue 8, not an exact count of arbitrary cycles. |
| GNU sed 4.9 | Use GNU's regex implementation for the native macOS multibyte backreference failure. |
| GNU ed 1.22.6 plus `ed-sigint.patch` | Remove the extra newline preceding the specified SIGINT `?\n` stdout response. The patch changes only that write; upstream `make check`, strict INT buffer recovery and HUP saving are required. |
| Chimerautils/FreeBSD tail at `c480e578085becc3be9073696a6228e507a71c4a` (Linux) | Supply tail `-r`, including line limits and a larger reverse witness. Build the upstream Linux port and its `expand_number` dependency with its compatibility headers. No local tail algorithm or output rewriting. macOS retains its OS-provided tail. |

GNU source archives retain their GPL licenses; the tail source and compatibility
headers retain their BSD notices. They are separate host executables, never
linked into cshell. Tail's upstream Linux compatibility layer does not supply
FreeBSD Capsicum confinement; no sandbox claim is made. The GNU ed patch is a
local change and has not been submitted upstream.

`manifest.json` records archive hashes, patch/build-recipe hashes, compiler and
binary identities. Text result records include that metadata for selected local
builds. Stock provider failures and earlier qualification records remain intact.
No whole-page utility qualification follows from a passing repaired audit.

## Environment requirements

All known failing assertions can be tested automatically. Local macOS checks
Darwin regex/libc and signal behavior. Hosted Ubuntu and Debian check GNU/Linux
providers; Debian's private 1 MiB tmpfs supplies real ENOSPC. The repaired CI
jobs gate the full audit rather than accepting its failure.

Native macOS capacity remains unavailable until a dedicated disposable small
filesystem is supplied. Observing an already-blocked native write still needs a
reliable Darwin observer; portable SIGPIPE and STOP/CONT tests do not prove it.
Actual EINTR-return/short-write and allocation-failure recovery need controlled
fault injection against the selected source builds. These are additional
automated qualification capabilities, not a requirement for manual testing.
Manual terminal testing is supplementary and cannot replace recorded PTY and
owned-process assertions. Complete utility-page coverage remains open.
