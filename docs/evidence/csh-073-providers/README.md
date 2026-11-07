# CSH-073 pinned provider repair evidence

The [provider recipe](../../../tools/host-profile/text/README.md) repairs the
known text audit failures through the existing opt-in PATH. It does not change
shell code, system providers or prior evidence. Source downloads are pinned by
SHA-256; build manifests retain source, compiler, patch and executable identities.

## Scope and reproduction

```sh
make test-host-inventory test-host-text-harness
make test-host-text-repaired
make test-host-profile HOST_TEXT_PROVIDER_BIN="$PWD/build/text-providers/bin"
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
```

The strict audit includes the former 194 extension assertions and seven new
cross-mode cases (28 assertions) for tail reverse limits and larger input,
acyclic tsort -w, and multibyte cut range endpoints. Expectations were not
relaxed. GNU ed's local patch removes its extra SIGINT newline; its upstream
`make check` and strict INT/HUP tests pass. Fourteen harness regressions include
corrupt source archives and changed/wrong-host provider rejection.

## Results

The first exploratory native audit passed 784 assertions, failed none, and
reported eight unavailable capabilities. The first hosted repaired audit at
`2a6abcb` passed 790 on Ubuntu (two capacity checks unavailable) and 792 on
Debian (no unavailable checks); their runtime and PTY regressions passed.
The exact initial run is
[36672254355](https://github.com/melliott18/cshell/actions/runs/36672254355).

Native broader host-profile validation passed all 1162 existing assertions,
then the 726-assertion text subset with eight unavailable conditions. Native
runtime and 30 public job-control PTY cases passed, but the subsequent
`execute_faults --jobs-terminal` module case timed out. An isolated retry and
a stock-PATH control reproduced the same timeout and ps cleanup deadline.
The separate runtime PTY target passed. No complete native `test-pty` pass is
claimed. The fault test exercises in-process job state and owned children,
not the selected text provider executables.

Three orphaned owned fault-test children remained in Darwin's `UE` state after
accepted SIGKILL requests. Their exact PIDs, states and cleanup attempts are
recorded in `text-provider-native-pty-cleanup.json.gz`. No clean native module
cleanup is claimed; no further repeats were attempted. This native job-control
failure needs separate diagnosis on a clean Darwin environment. It does not
prevent automated text qualification or require a manual terminal test.

Final validation uses `4f3de8e84a47f2867638ae12e5c434885b562571` and the
supported configure option. All three final audit source inventories exactly
match that commit's current build/test inputs.

| Final environment | Pass | Fail | Unavailable |
| --- | ---: | ---: | ---: |
| macOS 14.8.7 | 784 | 0 | 8 |
| Ubuntu 24.04 | 790 | 0 | 2 |
| Debian container with capacity | 792 | 0 | 0 |

Both final hosted jobs, including runtime and PTY regression steps, succeeded in
[36672619639](https://github.com/melliott18/cshell/actions/runs/36672619639).
macOS 15 remained queued at capture; completed native evidence is local
macOS 14.8.7. The 194 earlier extension assertions pass unchanged on all three
hosts. All 14 harness regressions and inventory checks pass. Native unavailable
rows are six blocked-write observations and two capacity probes; Ubuntu lacks
only the two explicit capacity probes. The final native build passes upstream
ed tests and the strict repaired audit.

[artifacts.json](artifacts.json) indexes checksums, source identity comparisons
and final results. Compressed JSON/logs preserve outputs and provider build
metadata. Initial, intermediate and final builds remain distinct; earlier
attempts are not overwritten with later successes.

## Attempts and limits

The initial direct coreutils program targets failed because gnulib generated
headers were absent; using the upstream `all` target supplies them. The first
build recipe used an unrecognized `--without-gmp` option; the final recipe uses
the supported `--without-libgmp`. Initial successful evidence is retained
separately from final recipe validation. Sources and logs remain available in
build directories during execution; compressed retained records preserve the
actual failures as well as final outcomes.

Stock provider failures remain visible in `make test-host-text-audit`.
Native capacity and blocked-write observation remain unavailable. Further
fault injection and full utility-page coverage remain open. A passing repaired
audit qualifies only its declared assertions. No macOS 15 CI result is claimed
while that runner is queued.
