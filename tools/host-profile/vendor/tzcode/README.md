# IANA timezone conversion provider (CSH-101)

Unmodified IANA tzcode 2025b is pinned from
<https://data.iana.org/time-zones/releases/tzcode2025b.tar.gz>, SHA-256
`05f8fedb3525ee70d49c87d3fae78a8a0dbae4fe87aa565c65cda9948ae135ec`.
The release archive includes its source and notices; LICENSE is reproduced here.
The linked localtime.c and supporting headers are public domain. No tzdata
release is bundled and no host timezone database is changed.

`../../build-touch.sh` checks and extracts the archive under `build/host-tzcode`,
generates tzdir.h for `/usr/share/zoneinfo` and `/etc/localtime`, and compiles
localtime.c with the caller's compiler/flags. It links that object directly into
GNU coreutils 9.7 touch, whose configure and gnulib prerequisites are supplied by
`build/host-cp`. The optional NetBSD *_z API is disabled to avoid conflicting
with gnulib's own implementation. Standard conversion functions and timezone
globals resolve to the pinned IANA implementation inside this executable.
GNU touch and IANA source files are not patched for this integration.

This supplies Issue 8 negative and greater-than-24-hour transition clocks that
macOS 14.8.7's host conversion does not handle in the authored fixtures. Both
Apple touch and the installed GNU touch reproduce that host behavior. Selecting
GNU touch alone is insufficient. This is a declared provider replacement, not a
wrapper translating operands, expected output, status, environment, or results.
Both native and Linux profiles use it; original stock failures remain separate.

The manifest records both archive hashes, the build script hash, configure
options, timezone compile options, and the selected executable hash. The build
log is retained under `build/host-tzcode/build.log`. Explicit TZ rules supply the
new tests; arbitrary geographical timezone files, ranges, ambiguous times,
locales and whole-utility correctness remain unqualified.
