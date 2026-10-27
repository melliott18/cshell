# Selected file provider (CSH-103)

The unmodified file 5.46 release archive comes from
<https://astron.com/pub/file/file-5.46.tar.gz>, SHA-256
`c9cc77c7c560c543135edc555af609d5619dbef011997e988ce40a3d75d86088`.
The archive contains the corresponding libmagic source and licenses; COPYING
is reproduced here. The build verifies the archive and needs no network.

`../../build-file.sh` applies `message-formats.patch`, builds a static libmagic,
and installs its matching default magic database under `build/host-file-install`.
The executable is copied to `build/host-file`; the opt-in profile selects it.
System installations are untouched. CC, CPPFLAGS, CFLAGS, LDFLAGS and LIBS are
passed through; configure and build/install logs are retained. The manifest
records executable, source archive, patch, build script and magic database hashes.

The local repair lets one-byte regular files reach position-sensitive tests,
accepts the plus and space numeric flags and promoted short character arguments,
and excludes literal `%%` pairs from the one-argument conversion count.
Text databases also retain source rule order; compiled system databases keep
their vendor strength ranking. Type validation, the single argument limit and numeric width/precision caps
remain enforced. These are local source changes, not an upstream acceptance claim.
The new fixtures use only signed byte/short and string types and bounded
formats. Additional numeric types, arbitrary formatting, multiple databases,
locales, compression and resource limits remain unqualified under CSH-104.

All previous selected assertions remain mandatory. Stock Apple/Linux file and
unpatched file 5.46 failures are retained separately; no output is translated by
a wrapper and no selected-profile allowances are introduced.
