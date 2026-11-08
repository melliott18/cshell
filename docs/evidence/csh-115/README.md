# CSH-115: measured ls allocation

The separate `test/CSH-115-filesystem-environments` worktree starts at integration
commit `d175f9f`. This change adds 20 cases in direct execution and cshell
string/file/stdin modes (80 assertions). It selects unmodified GNU coreutils 9.7
`ls` from the existing checksum-pinned private build. No shell C source changes.

## Contract and oracle

The [Issue 8 ls specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html)
OPTIONS defines `-s` allocation reporting, explicit 1024-byte units with `-k`,
operand-link following with `-H`/`-L`, and physical operand treatment with `-d`.
STDOUT defines the count before each filename. The default `-s` unit is
implementation-defined. APPLICATION USAGE also describes filesystem-dependent
accounting. These cases qualify measured `st_blocks` accounting on the supplied
filesystems, not all conforming accounting implementations.

A fresh HTTPS retrieval of the normative HTML matched the existing section-map
SHA-256. The compressed source and URL/hash/section record are retained here.
The browser fetch returned 403; the successful retrieval used curl.

Each private fixture contains empty, regular, seek-created, hard-linked,
directory, FIFO and symlink objects. Two separate option orders (`-s -k` and
`-k -s`) cover each object, `-H`/`-L` symlink operands and a reverse-authored
multi-operand list that must appear in C order. Hard-link names each retain their
own displayed allocation; the oracle does not deduplicate inodes.

Before exec, Python lstat measures allocation in kernel 512-byte units and
independently checks types, sizes, a hard-link pair and a symlink referent.
Expected displayed counts use `(st_blocks + 1) // 2`. No utility generates the
expected output. The seek-created object's actual allocation is recorded; native
macOS allocates the full logical length, while Linux supplies a measured hole.
Neither behavior is assumed from the seek alone. Odd 512-byte counts are covered
only by a synthetic harness regression, not claimed as a physical boundary.

Every assertion requires exact count/name/order (allowing column spaces), empty
stderr, zero status, stable device/inode/mode/owner/group/size/link-count/allocation
and modification/status-change timestamps, preserved bytes and symlink text,
unchanged directory entries, and complete cleanup. Access times are excluded
because inspection can change them. FIFOs are never opened. Execution uses the
same inventoried PATH and direct-provider dispatch as the existing filesystem
suite; provider hashes and exact source inputs are retained in each report.

Five harness tests cover the case/mode matrix, incorrect counts/order/duplicates,
channels/status and object corruption, odd-count rounding, partial setup and
failed probes, failed exec, and bounded timeout with child reaping and cleanup.

## Provider defect and remaining scope

Apple stock `ls -H -d -s -k` reports the symlink allocation instead of the
referent allocation. Both option-order cases fail in all four dispatch modes.
The assertions stay mandatory; selected GNU ls passes them. The manifest records
its archive checksum, configure flags, build target/log and executable hash.

Default units, directory totals, other filesystem accounting policies, shared
extents, capacity limits, ACLs, other identities, arbitrary graphs, locales and
resource errors remain unqualified. All 21 utility rows and four original U-040
conditions remain individually open under [CSH-116](../../tickets/CSH-116-filesystem-environment-residuals.md),
[issue #244](https://github.com/melliott18/cshell/issues/244). Utility/libc/platform
vendors retain implementation ownership. U-034/U-040 remain partial.

## Reproduction

```sh
# Native: gfind and the documented GNU provisioning dependencies on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-115/validate.py native

docker build -f docs/evidence/csh-115/Dockerfile.linux -t cshell-test:csh-115 .
docker run --init --name cshell-csh115-validation cshell-test:csh-115 \
  python3 docs/evidence/csh-115/validate.py linux
docker cp cshell-csh115-validation:/work/build/csh115-validation ./build/csh115-linux-results
# Copy the two platform result directories here, then:
python3 docs/evidence/csh-115/verify.py
docker rm cshell-csh115-validation
```

The image layers current sources on the retained unprivileged integration image
`cshell-test:pr-integration-built` (base image ID
`sha256:e95256e8e72455de3769711ec46f7f51a3a8f6443d25bd65eea657678ad6f783`).
This is Linux/Docker evidence, not a separately hosted native-Linux run. Native
provisioning copies the same gfind used by CSH-114 into the ignored build tree.
No sanitizer or hosted-CI qualification is claimed.

## Development records

`development/` preserves the initial overly restrictive sparse-allocation setup
failure, the stock -H failures, an intermediate selected pass, and the first
provisioning attempt that lacked the new ls executable. These are not relabeled
as final-source passes. The setup was corrected to record allocation actually
measured on each filesystem, in line with the specification's accounting scope.
Final evidence uses the strengthened unchanged-metadata oracle as well.

## Final validation — 2026-11-08

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12523 pass, 0 fail | 12563 pass, 0 fail |
| New ls allocation assertions | 80 pass | 80 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 13 / 171 pass | 13 / 171 pass |
| Selected runtime | 3950 pass | 3950 pass |
| Selected PTY assertions | 65 pass | 65 pass |
| Stock full / provider failures | 757 / 16 retained | 578 / 8 retained |

Every ticket-listed selected target passed with zero allowances. Both complete
validation scripts exited zero with selected/stock-full/stock-provider command
statuses `[0, 2, 1]`. The native full audit adds exactly eight ls -H failures;
all prior native and Linux stock failures are preserved. The Linux task-owned
container was removed after collecting its results.

`python3 docs/evidence/csh-115/verify.py` passes the exact predecessor-expectation,
new-case, source/provider, stock-failure and cleanup comparisons. All 12443 native
and 12483 Linux predecessor expectations are unchanged. Checked-in source inputs
match across platforms; the recorded generated test/newgrp provider headers are
platform-specific and included in each independently reconstructed source hash.
`baseline-source.json` additionally fixes the unchanged shell C/header inputs.

`make test-tickets` and the live identity check passed: 24 registry tests and
116 shared reservations. `CSH_TEST_PATH` selected the qualified profile during
`make test-runtime test-pty` on each platform. No runtime or terminal skips.

Compressed reports preserve output, status, expected/observed effects, setup
measurements, cleanup, executable identities and source manifests. Build logs,
commands and timings are retained separately. [records.json](records.json)
checksums the retained compressed evidence. Historical evidence is unchanged.
This result is ready for review; it is not marked integrated or fully conforming.
