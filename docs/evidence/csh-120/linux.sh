#!/bin/sh
# Run from the repository root. Reuse the pinned predecessor's built providers;
# mount this checkout's tests and accounting without rebuilding historical layers.
set -eu
image=${CSH120_BASE_IMAGE:-cshell-test:csh-119}
mkdir -p build/csh120-linux build/csh120-validation
docker image inspect "$image" > build/csh120-validation/linux-image.json
docker run --name cshell-csh120-validation --init \
  --tmpfs /tmp:rw,exec,nosuid,size=512m \
  --tmpfs /work/build/tests:rw,exec,nosuid,size=256m,uid=10001,gid=10001 \
  --mount "type=bind,src=$PWD/tests,dst=/work/tests,readonly" \
  --mount "type=bind,src=$PWD/docs,dst=/work/docs,readonly" \
  --mount "type=bind,src=$PWD/Makefile,dst=/work/Makefile,readonly" \
  --mount "type=bind,src=$PWD/build/csh120-linux,dst=/work/build/csh120-validation" \
  "$image" python3 docs/evidence/csh-120/validate.py linux
