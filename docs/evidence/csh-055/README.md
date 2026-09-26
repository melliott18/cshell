# CSH-055 run artifacts

The [contract map](../../execution-contracts.md) defines the oracle, cases,
controlled environments and bounds. The [ticket](../../tickets/CSH-055-execution-contract-gaps.md#validation-record)
records outcomes and remaining platform limitations.

Identity JSON files record compiler/flags, OS/libc/Python, binary hashes,
test-executable and generated-suite hashes, and a per-file source manifest.
`source_revision` is the integration base; the source manifest identifies the
uncommitted implementation tested before the evidence commit. Initial identities
have source digest `a6b1b54ef172b710be3b8d704b676911ace0d3a6fcf1c7e967979302de64ce48`.
The final version additionally preserves shell status when API validation fails
and tests that a malformed pwd assignment vector is rejected before lookup.
The final source hashes are recorded separately; no other runtime behavior or
fixture limits changed between these versions.

`identity.py` is the collector. Docker's build does not copy Dockerfile, so the
identical build input was mounted for collection. The initial normal Docker
identity was collected from a snapshot of the completed test container: its
binaries and generated suites are the actual retained test outputs. Docker
sanitizer and final normal identities were collected before their containers
exited. Native sanitizer sources live in a separate ignored `build/asan` copy.

Logs are compressed verbatim (`gzip -dc NAME.log.gz`). Initial native harness
and Docker sanitizer failures are retained and are not counted as passing runs.
The native harness retry changes no code, expectations, or limits. Final Docker
sanitizer validation uses `-j1`; every individual test deadline remains unchanged.
Native and Docker normal runs include the pre-existing CSH-052/056 host gaps
and named locale/privilege capability skips; these do not become passing cases.

Normal commands: `make -j4 test test-execution-evidence` (final Docker `-j2`),
`make test-pty`, and `make test-harness`. The separately requested focused targets
also ran through the native focused command recorded in the ticket.

Sanitizer targets: `test-execution-evidence test-execute test-pipeline
 test-context test-control test-runtime-pty`, with
`CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`
and `LDFLAGS='-fsanitize=address,undefined'`.
API runners inherit `ASAN_OPTIONS=halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1`
and native `MallocNanoZone=0`; the runtime harness supplies its controlled
environment. External descriptor observers are deliberately uninstrumented so
sanitizer startup does not hide shell descriptor behavior.

`hosted-ubuntu.log.gz` and `hosted-ubuntu-job.json` retain the successful native
Ubuntu 24.04 job for implementation commit `814cd0a`. Both full normal and full
ASan/UBSan runs passed. The log includes runner image, Python/setup, commands,
and individual results; CI does not publish binary hashes. This supplements the
local identities and does not silently replace any failed local attempt.

`hosted-docker.log.gz` and `hosted-docker-job.json` similarly retain the passing
full normal/sanitizer Linux Docker job for the same implementation head. Hosted
results are separate from the local arm64 Docker attempts and their identities.

`docker-final-sanitizer.log.gz` records the completed passing local serial retry.
Its source digest agrees with the final native normal/sanitizer and Docker normal
manifests. `artifacts.json` hashes every retained artifact except itself.
