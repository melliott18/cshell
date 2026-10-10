# Selected cp provider (CSH-086)

The unmodified release archive is GNU coreutils 9.7 from
<https://ftp.gnu.org/gnu/coreutils/coreutils-9.7.tar.xz>, SHA-256
`e8bb26ad0293f9b5a1fc43fb42ba970e312c66ce92c1b0b16713d7500db251bf`.
The archive contains the corresponding source and GPLv3-or-later notices;
COPYING is also reproduced beside it. No network access is needed to build.

`../../build-cp.sh` verifies and extracts this archive into
ignored build directories, applies `cp-decline-status.patch`, configures and
builds only `src/cp`, then installs the binary as `build/host-cp`. Make passes
CC, CPPFLAGS, CFLAGS, LDFLAGS and LIBS; configure/build logs remain under
`build/host-coreutils-build`. The profile manifest records the archive, patch
and selected executable hashes. All platforms select this same patched source.

The patch changes only cp's decision to skip an existing destination after a
negative interactive response. POSIX.1-2024 cp EXIT STATUS excludes declined
files from the requested copies. GNU's `--update=none-fail` extension retains
its failure result. No output or process exit status is translated externally.
Move behavior and all actual copy-error paths are unchanged. The patch is a
local provider repair; it does not claim an accepted upstream change.

The C-locale profile disables message catalogs, ACL support, SELinux and GMP.
Those environments remain unqualified in CSH-087. Existing ordinary ownership,
mode, timestamp, graph, EACCES and EFBIG assertions remain mandatory. Original
Apple and GNU stock-provider failures remain in separate evidence records.
