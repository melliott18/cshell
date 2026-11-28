#!/bin/sh
# Run from the repository root. Reuse the pinned predecessor's built providers;
# mount this checkout's tests and accounting without rebuilding historical layers.
set -eu
image=${CSH132_BASE_IMAGE:-cshell-test:csh-119}
mkdir -p build/csh132-linux build/csh132-validation
docker image inspect "$image" > build/csh132-validation/linux-image.json
docker run --name cshell-csh132-validation --init \
  --tmpfs /tmp:rw,exec,nosuid,size=512m \
  --tmpfs /work/build/tests:rw,exec,nosuid,size=512m,uid=10001,gid=10001 \
  --mount "type=bind,src=$PWD/tests,dst=/work/tests,readonly" \
  --mount "type=bind,src=$PWD/docs,dst=/work/docs,readonly" \
  --mount "type=bind,src=$PWD/Makefile,dst=/work/Makefile,readonly" \
  --mount "type=bind,src=$PWD/build/csh132-linux,dst=/work/build/csh132-validation" \
  "$image" python3 "${CSH132_VALIDATION_SCRIPT:-docs/evidence/csh-132/validate.py}" linux
