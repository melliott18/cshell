# CSH-048 continuation evidence, 2026-09-28

The [ticket](../../../tickets/CSH-048-state-builtin-evidence.md) and
[clause map](../../../state-builtin-evidence.md#additional-runtime-partitions-2026-09-28)
identify exact assertions and limits. Source `47aae4e` adds read assignment and
remainder fixes, continuation PS2, checked builtin output, directory search
permissions, and runtime/fault witnesses. Source `7d50b61` additionally handles
logical parent, symlink and dot-component traversal beyond PATH_MAX. Source `4144945` fixes the additional hash/command output leak and diagnostics.
Broader sanitizer runs on `47aae4e` are retained with that filename prefix;
they do not stand in for the final source runs.

Each `*-identity.json` records the source/test manifest and its digest, binary
and fault-binary hashes, generated suites, compiler/flags, system library, OS,
architecture and Python. The manifest algorithm is unchanged from the parent
evidence README: Makefile and files under src/include/tests, excluding Python
caches; documentation and artifacts are outside that digest. Image/container
records retain immutable image IDs, layers, platform, invocation, environment
and process result. `sources.json` retains the normative source URLs and hashes
reviewed for the added conditions. No reference shell supplies an oracle.

`runs.json` records commands, outcomes and log hashes. Gzip logs contain the
complete output. Identity timestamps are collection times; log creation and
last-write times bound output collection, not individual case execution.
The pre-commit `development-fixture-errors.log.gz` retains three failures of an
incorrect dot-search test: its setup directories already existed, and it failed
to restore PATH before invoking host printf/chmod. The corrected fixture saves
PATH, captures dot's result, then restores PATH before observation. These were
fixture defects, not evidence of a shell defect or passing final validation.

Reproduce normal checks on the final source with:

```sh
make -j4
make test test-pty test-harness
make test-state-builtins
EVIDENCE_SOURCE_BASE=b1b6b15 python3 docs/evidence/csh-048/identity.py

docker build -t cshell-test:csh-048-output-final .
docker run --rm --init cshell-test:csh-048-output-final make test test-pty test-harness
```

Sanitizers use a separate source copy/build directory on native macOS and a
fresh container built from the same sources on Linux. Do not run `make clean`
in another active build. After cleaning that isolated build, run:

```sh
ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 MallocNanoZone=0 \
make test-state-builtins test-builtins test-state test-execute test-evaluation \
  test-control test-portability test-prompt test-runtime-pty \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

The first native sanitizer run uses `-j2`; Docker runs serially. Final directory and lookup-output changes additionally run focused builtin/edge,
execution and evaluation checks with both sanitizers.
The shared runner retains its five-second per-case deadline, output bound and
process-group cleanup. No sanitizer suppression or leak-detection disablement
is used. Linux containers run as the image's unprivileged user. The 102 CSH-048
edge checks have no skips on the recorded native/Docker hosts. Other suites'
unequal-ID, native catalog and non-UTF-8 pathname/locale skips retain
CSH-046, CSH-042 and CSH-053 ownership; runs.json preserves each reason.

`hash-output-leak.log.gz` retains the additional probe that failed under Linux
LSan on `47aae4e`: `hash cat; hash >&-; printf "status:%s\n" "$?"`. The shell
reported status 1 for hash, then LSan reported an 8,192-byte glibc dprintf leak at
exit. The final runtime cases exercise the corrected path without disabling
leak detection. This failed probe is separate from the earlier passing suites,
which did not yet contain that assertion.
