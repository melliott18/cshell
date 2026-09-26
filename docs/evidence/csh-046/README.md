# CSH-046 run artifacts

See the [clause/condition map](../../invocation-syntax-evidence.md) and
[ticket validation record](../../tickets/CSH-046-invocation-syntax-evidence.md#validation-record).

`validation.json` identifies source/test revision, executable SHA-256, compiler
and flags, OS/system library, Python, generated suites and external helper
identities. It records the source fingerprint separately from generated suites:
absolute helper paths and errno text differ across platforms. The source
fingerprint is SHA-256 of `json.dumps(manifest, sort_keys=True).encode()`, where
manifest maps relative Makefile/src/include/tests file paths to SHA-256 and
excludes Python caches. The captured source fingerprints match across platforms.

The normal runs used the uncommitted implementation subsequently recorded in
`5e77577e892192567c091d0c20658ce4f01f6327`; that commit identifies all tested
source/test bytes. Later changes add evidence documentation and the CI command
for the already-tested root identity probes. `recorded_utc` is the post-run
identity collection time, not an inferred exact process-start time.

The `.log.gz` files retain complete output, including every named case, skip,
failure and summary. Read with `gzip -dc FILE.log.gz`. SHA-256 values in the
manifest refer to the compressed artifacts. Parallel make output can interleave
suite lines; suite-specific summary counts are retained in the ticket. A
successful shared-runner result asserts exact streams/status/files and bounded
cleanup, not merely that a process exited zero.

To reproduce normal checks from the source revision:

```sh
make clean
make -j4 test test-pty test-harness
make test-syntax
python3 docs/evidence/csh-046/identity.py

docker build -t cshell-test:csh-046 .
docker run --rm --init cshell-test:csh-046 make -j4 test test-pty test-harness
docker run --rm --init --user 0 cshell-test:csh-046 python3 tests/invocation.py ./cshell
```

For sanitizers, clean and build with the flags/targets in the ticket. Avoid
running multiple sanitizer suites concurrently on a CPU-constrained Docker
engine. The original parallel timeout is retained alongside the targeted
retry; it is not erased or reclassified as a pass. The retry uses unchanged
five-second case deadlines and the same instrumented binaries.

To capture Linux identity, bind-mount `identity.py` into the image and run it
with `python3` in `/work`; pass `EVIDENCE_CFLAGS` and `EVIDENCE_LDFLAGS` for
instrumented builds. The build does not copy documentation or Git metadata into
the image. Container/base image IDs and Dockerfile hash are recorded separately.
