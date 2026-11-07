#!/bin/sh
# Offline pinned file/libmagic build for bounded POSIX message contracts.
set -eu
root=$(pwd)
source_dir="$root/build/host-file-src"
build_dir="$root/build/host-file-build"
archive="$root/tools/host-profile/vendor/file/file-5.46.tar.gz"
mkdir -p "$source_dir" "$build_dir"
python3 - "$archive" <<'CHECK'
import hashlib, sys
from pathlib import Path
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() != 'c9cc77c7c560c543135edc555af609d5619dbef011997e988ce40a3d75d86088':
    raise SystemExit('file source archive checksum mismatch')
CHECK
tar -xzf "$archive" -C "$source_dir" --strip-components=1
(cd "$source_dir" && patch -p1 < "$root/tools/host-profile/vendor/file/message-formats.patch")
cd "$build_dir"
"$source_dir/configure" --prefix="$root/build/host-file-install" --disable-shared --enable-static \
    --disable-zlib --disable-bzlib --disable-xzlib --disable-zstdlib --disable-lzlib \
    > configure.log 2>&1 || { tail -80 configure.log; exit 1; }
make -j4 > build.log 2>&1 || { tail -80 build.log; exit 1; }
make install >> build.log 2>&1 || { tail -80 build.log; exit 1; }
cp src/file "$root/build/host-file"
