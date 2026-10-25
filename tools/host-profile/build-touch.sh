#!/bin/sh
# Link the pinned GNU touch to pinned IANA conversion code. No system mutation.
set -eu
root=$(pwd)
source_dir="$root/build/host-tzcode"
archive="$root/tools/host-profile/vendor/tzcode/tzcode2025b.tar.gz"
mkdir -p "$source_dir"
python3 - "$archive" <<'PY'
import hashlib, sys
from pathlib import Path
expected = '05f8fedb3525ee70d49c87d3fae78a8a0dbae4fe87aa565c65cda9948ae135ec'
if hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() != expected:
    raise SystemExit('IANA tzcode source archive checksum mismatch')
PY
tar -xzf "$archive" -C "$source_dir"
make -C "$source_dir" tzdir.h TOPDIR= TZDIR=/usr/share/zoneinfo TZDEFAULT=/etc/localtime
# Disable the optional *_z API, which gnulib already supplies. Retain the
# standard conversion and timezone globals used by GNU touch/gnulib.
${CC:-cc} ${CPPFLAGS:-} ${CFLAGS:-} -DHAVE_TZNAME=1 -DUSG_COMPAT=1 -DNETBSD_INSPIRED=0 \
    -c "$source_dir/localtime.c" -o "$source_dir/localtime.o"
# build/host-cp has completed the shared configure/generated-header build.
# Link the object directly (before the gnulib archives) to select its symbols.
# Build the object before -W: pretending a missing object is current would
# skip its compilation on a fresh checkout. Then force the final relink.
make -C "$root/build/host-coreutils-build" src/touch.o V=1
make -C "$root/build/host-coreutils-build" -W src/touch.o src/touch \
    'src_touch_LDADD=../host-tzcode/localtime.o $(LDADD) $(CLOCK_TIME_LIB)' V=1
cp "$root/build/host-coreutils-build/src/touch" "$root/build/host-touch"
