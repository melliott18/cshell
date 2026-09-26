# CSH-047 run artifacts

The [clause/condition map](../../expansion-evidence.md) defines the exact scope;
the [ticket](../../tickets/CSH-047-expansion-evidence.md#validation-record) summarizes outcomes.

`validation.json` retains the tested source/suite revision, source manifest and
fingerprint, binary and generated-suite hashes, compiler/flags, OS/libc/CPU,
Python, host login data, long width, exact host-qualified locale oracles, Docker
identity, commands and results.
Collection timestamps are explicit; they are not claimed to be test-start
timestamps. All runs used the same source/test bytes, committed as `2153c39`.
Later evidence-documentation commits do not change the source fingerprint.

The compressed logs retain actual case names and outcomes, including skips:

- `native.log.gz`: `make -j4 test test-pty test-harness`.
- `docker.log.gz`: `make -j2 test test-pty test-harness test-expansion`.
- `native-sanitizer.log.gz`: clean build, then `make -j4 test-expand test-substitution test-expansion test-portability` with the sanitizer flags below.
- `docker-sanitizer.log.gz`: initial focused `-j2` run; retained timeout failures in one portability case and one field API case.
- `docker-sanitizer-retry.log.gz`: serial clean build with the same focused targets, flags, assertions and deadlines.
- `docker-build.log.gz`: base digest and Linux build output.
- `expansion-native.json.gz`: all 354 exact generated cases, including scripts,
  argv, expected fields/status/stderr, and filesystem assertions. Helper paths,
  login home and long width are qualified by the native identity. Regenerate
  the suite in Docker to obtain its `/work` helper path and host login home.

Normal CFLAGS: `-Wall -Wextra -Wpedantic -Wshadow -std=c99 -O2`.
CPPFLAGS: `-D_POSIX_C_SOURCE=200809L -Iinclude`; no extra linker flags/libraries.
Sanitizer CFLAGS:
`-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer`;
LDFLAGS: `-fsanitize=address,undefined`;
`ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`.
The existing descriptor-observer helper remains uninstrumented by Makefile
policy; shell and expansion/lifecycle/fault binaries are instrumented.

Reproduce from the source revision (or a later tree with the same source
fingerprint):

```sh
make clean
make -j4 test test-pty test-harness test-expansion
python3 docs/evidence/csh-047/identity.py > native-identity.json

docker build -t cshell-test:csh-047 .
docker run --rm --init cshell-test:csh-047 make -j2 test test-pty test-harness test-expansion

make clean
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 make -j4 \
  test-expand test-substitution test-expansion test-portability \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

For instrumented identities, pass those CFLAGS/LDFLAGS as
`EVIDENCE_CFLAGS`/`EVIDENCE_LDFLAGS` to `identity.py`. Docker has no Git checkout;
pass `EVIDENCE_REVISION` and mount the collector read-only. This run used
`/evidence/identity.py` and wrote identities to a separate `/results` mount.
Neither mount supplies shell source or compiled objects.

Native locale results include one translated-libc-catalog skip, owned by
CSH-042. Docker provides UTF-8 locales and French libc catalogs and executes
that branch. The full suites also report two unrelated Linux-root identity
skips owned by CSH-046. No new expansion or PTY case skips. The source map
retains untested encodings, pattern breadth and depth limits; passing these
runs does not establish complete POSIX conformance or native Linux outside
this Docker environment.

The serial Docker sanitizer retry passed all focused targets; its rebuilt
cshell hash equals the initial failed-run binary hash. The failed parallel log
is retained as a separate result. Neither timeout deadline nor assertion was
relaxed. Concurrent containers were observed, but contention is a hypothesis
rather than an established root cause.
