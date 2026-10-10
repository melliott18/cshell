#!/bin/sh
# Offline reproducible GNU cp build; all mutations stay under ignored build/.
set -eu
root=$(pwd)
source_dir="$root/build/host-coreutils-src"
build_dir="$root/build/host-coreutils-build"
archive="$root/tools/host-profile/vendor/coreutils/coreutils-9.7.tar.xz"
mkdir -p "$source_dir" "$build_dir"
python3 - "$archive" <<'PY'
import hashlib, sys
from pathlib import Path
expected = 'e8bb26ad0293f9b5a1fc43fb42ba970e312c66ce92c1b0b16713d7500db251bf'
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() != expected:
    raise SystemExit('GNU coreutils source archive checksum mismatch')
PY
tar -xJf "$archive" -C "$source_dir" --strip-components=1
(cd "$source_dir" && patch -p1 < "$root/tools/host-profile/vendor/coreutils/cp-decline-status.patch")
cd "$build_dir"
"$source_dir/configure" --disable-nls --disable-acl --without-selinux --without-libgmp > configure.log 2>&1 || { tail -80 configure.log; exit 1; }
# Automake's direct program target omits generated gnulib headers. Build the
# declared prerequisites first without building every coreutils executable.
cat > csh-cp.mk <<'MAKE'
csh-cp-prerequisites: $(BUILT_SOURCES)
MAKE
make -j4 -f Makefile -f csh-cp.mk csh-cp-prerequisites > build.log 2>&1 || { tail -80 build.log; exit 1; }
make -j4 src/cp >> build.log 2>&1 || { tail -80 build.log; exit 1; }
cp src/cp "$root/build/host-cp"
