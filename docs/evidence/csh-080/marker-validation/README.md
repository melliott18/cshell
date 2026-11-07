# Fault-marker reader hardening

Review on 2026-10-08 found that both kernel and allocation markers were read with
unbounded `Path.read_text()` after child capture finished. A child-created FIFO
could block the parent outside the capture watchdog. A symlink to a valid marker
could also be accepted, and non-object JSON in a kernel marker raised an uncaught
attribute error instead of producing a failed case record.

The shared reader opens with `O_NONBLOCK | O_NOFOLLOW`, validates the opened
file descriptor as a regular file of at most 4096 bytes, and limits the read to
4097 bytes to detect growth. JSON must be an object. Failure becomes a recorded
assertion error and the fixture is cleaned. A `finally` block closes the descriptor
on every path. This bounds marker types and bytes on the supplied fixture
filesystem; it is not a claim about stalled filesystem or kernel I/O.

One regression exercises five invalid marker forms for each of the two marker
protocols: FIFO, symlink, directory, oversized JSON and non-object JSON. The
symlink target and oversized document contain otherwise valid matching markers,
so they cannot be rejected merely for incorrect protocol values. Each helper
executes under an independent five-second watchdog, and each case must fail
with a marker error and successful fixture cleanup.

## Validation

- Native and Linux `make test-host-inventory`: accounting checks, 10 inventory
  tests and **18 filesystem harness tests** pass (10 new invalid-marker subcases).
- Native `make test-host-profile`: **1162 host, 810 filesystem, 240 allocation**
  assertions pass, with no gaps. All filesystem/allocation cleanups succeed.
- Fresh Debian/arm64 Docker `make test-host-profile`: **1162 host, 826 filesystem,
  200 allocation** assertions pass, with no gaps. All cleanups succeed.
- The final stronger symlink/oversize regression was rerun with the native
  inventory target and the Linux inventory target using the final tests mounted
  read-only into the built image. The earlier full-profile reports preserve
  their exact source hashes; the provider reader code is identical. No utility
  provider or shell runtime source changed.

The JSON reports and logs here are distinct from the original implementation's
[hosted CI completion](../hosted-1ecae53/README.md). New hosted checks run when
this hardening is pushed; original green checks do not certify this revision.

## Reproduction

```sh
make test-host-inventory
make test-host-profile
# Supply gfind/gdd/gtest/g[ for native provisioning as documented previously.
docker build -t cshell-test:csh080-markers .
docker run --rm cshell-test:csh080-markers make test-host-profile
```

No previous stock failure expectation or residual owner changed. Historical
CSH-072 and initial CSH-080 result artifacts remain intact.
