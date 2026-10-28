# Selected file provider (CSH-103/104)

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
CSH-104 supplies 360 portable numeric magic cases / 1440 assertions for dC/dS/dI/dL and uC/uS/uI/uL, their explicit byte-count forms, signed extrema, unsigned high-bit ranges, comparisons, hexadecimal/octal masks and constants, bit tests and incomplete fields. Native C ABI widths and independently authored integer bytes supply the oracle; exact channels/status and unchanged inputs are required. The pinned file provider repairs native long type selection, rejection of truncated eight-byte values and signed-minimum parsing without overflow.

Default d/u widths, the long keyword alias, further numeric/message combinations, cross-database -m/-M/-d precedence, default classification, encodings/locales and utility resource failures remain unqualified. These residuals belong to CSH-105.

The CSH-104 changes map dL/uL to sizeof(long) and check that native and
explicit-endian eight-byte numeric fields fit the input before comparison.
The historical long keyword remains outside this qualification.

All previous selected assertions remain mandatory. Stock Apple/Linux file and
unpatched file 5.46 failures are retained separately; no output is translated by
a wrapper and no selected-profile allowances are introduced.
