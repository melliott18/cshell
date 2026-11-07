# Selected pax source and local changes

Upstream: MirCPIO / paxmirabilis 20240817, the complete portable source release
from Debian's upstream-source archive:
<https://deb.debian.org/debian/pool/main/p/pax/pax_20240817.orig.tar.gz>

SHA-256: `e955d5d3af97aede0a3f463a9a59b83e8d1083aaf142eb6f388c549a7d182e6b`.
Verified against the SHA-256 in `pax_20240817-1.dsc` from the same repository.
No assertion of independent PGP verification is made. All upstream copyright
and license notices are retained in their files, including the `.linked`
portability headers. Nothing is downloaded during the build.

Local changes for CSH-072:

- `tar.c`: ustar mode output includes only the specified 12 mode bits (`07777`);
  file type already has its own typeflag field.
- `buf_subs.c`: final archive flush drains the buffer after a block-aligned short
  write, or preserves a fatal flush error. Previously an incomplete final write
  could return success. Move overlapping remaining bytes with `memmove`.

The upstream release already reports truncated members and EPIPE correctly on
Darwin; the older Apple system pax remains separately audited. The program is
standalone and selected only by the opt-in PATH. No executable is installed in
system directories. Its build runs upstream feature probes in `build/` and
preserves sanitizer flags, but omits the cshell-specific `-Werror`, `-Wpedantic`
and `-Wshadow` policy for upstream source. Qualification covers only asserted
contracts; multi-volume devices, privileged identities and complete pax/cpio
formats remain open under CSH-080.
