# Standalone catalog providers

These are opt-in external executables. None of their code is linked into cshell.
The [upstream manifest](catalog-provenance.json) pins source revisions and original
SHA-256 hashes; qualification records additionally hash all patched sources and
selected executables. Existing system executables are retained in the provider
manifest for comparison or the explicitly documented charmap fallback.

## gencat on Darwin

`gencat-darwin/genlib.c` and `gencat.h` come from Apple adv_cmds commit
`6bed8737a34dbb54782a18f47dccf933a9967a12`; `msgcat.h` comes from Apple Libc commit
`71bbe350ab79eef58113991d817ccc6165061a64`. Their Alfalfa permissive license is
retained in each file. The native catalog layout and parser remain from that
engine. Local changes remove the diagnostic for valid unknown escapes, initialize
serialized header padding, reset the default set for each input file, and repair
set deletion's freed-node traversal/current-set reference. Standalone compilation
also drops unused upstream bookkeeping and uses standard memory functions.

`../gencat_darwin.c` supplies POSIX stream operands, uses an anonymous seekable
file for the format's backpatched offsets, checks reads/writes/seeks/closes, and
checks closed standard descriptors before allocating that file. The latter keeps
an anonymous file from being mistaken for a closed stdout. The selected parser's
other extension/limit behavior is not promoted to full qualification.

## gencat on glibc Linux

`gencat-glibc/gencat.c` and `catgetsinfo.h` come from glibc release/2.36 commit
`e97cfe2293ed097eb3d0b4c18274d22855e65130`. The program is GPL-2.0-or-later;
the internal format header is LGPL-2.1-or-later. Full licenses are retained in
`gencat-glibc/COPYING` and `COPYING.LIB`. This standalone provider is separate from
the shell and the installed glibc utility.

Local changes honor `$delset` during old-catalog merging, discard earlier pending
messages when deleting a set, distinguish an empty message from deletion, and
reset the default set/quote state per source file. Stream output does not load a
literal file named `-`. `%zu` replaces the legacy GNU `%Zu` printf modifier.
`../gencat_glibc.c` supplies checked writes and a direct-file catalog loader that
checks table sizes and every referenced string before the upstream merge walks
it. It does not call a private glibc symbol or search NLSPATH. `version.h` and
`programs/xmalloc.h` provide standalone build identity/allocation plumbing.
Upstream-only GNU extensions and warnings are isolated by diagnostic pragmas;
project wrapper code retains the project's warning policy.

## iconv

`../build_iconv.py` downloads GNU libiconv 1.19 from the GNU release server and
requires SHA-256
`88dd96a8c0464eca144fc791ae60cd31cd8ee78321e67397e25fc095c4a19aa6` before extraction.
The complete archive is retained under `build/host-profile/`; no system library
or executable is installed. First setup requires HTTPS access, curl, trusted CA
certificates, make and a C compiler. Later runs reuse verified build generations.

The library and CLI are linked statically with shared libraries and NLS disabled.
The CLI is GPL-3.0-or-later and the library LGPL-2.1-or-later; the release's COPYING
and COPYING.LIB accompany each generated executable. Build manifests record source
and patched CLI hashes, effective compiler flags, compiler identity and commands.
Project sanitizer/optimization flags apply to the upstream build; upstream
warnings remain logged without promotion to errors. Project adapters still use
the requested strict warning flags. Publication and verified archive caching are
atomic, and older executable generations remain until `make clean`.

One patch emits the existing conversion diagnostic when `-c` first encounters
invalid input, unless `-s` was supplied. The upstream nonzero conversion status
and discard/recovery logic are preserved. Thus all four `-c`/`-s` combinations
retain the same error status, `-s` suppresses character diagnostics, and file or
stdout errors still diagnose. Tests also cover unmappable characters, incomplete
input, buffer boundaries and stateful encodings.

`../iconv_adapter.c` executes this CLI for code-name conversions. A slash in a
`-f` or `-t` argument selects the existing system utility for charmap-file joins;
that separate conversion path and its invalid-character policy remain explicitly
unqualified. `-l` lists GNU libiconv's code names. There is no stderr filtering,
and the native router does not alter inherited signal dispositions.
