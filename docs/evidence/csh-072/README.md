# CSH-072 filesystem qualification evidence

Qualification is limited to the exact selected assertions in the
[clause map](../../../tests/host_filesystem_contracts.json). No complete utility
page or full-system requirement is promoted. Remaining sections and the four
original conditions belong to [CSH-079](../../tickets/CSH-079-filesystem-remaining-contracts.md).

The [subsequent five-area extension](extended/README.md) retains additional
traversal, links, metadata, archive and I/O evidence. The records below remain
immutable evidence for the original 402-assertion scope.

## Results

| Run | Retained result | Decision |
| --- | --- | --- |
| Final native macOS selected filesystem profile | [native-filesystem.json.gz](native-filesystem.json.gz): **402 pass, 0 fail**, every private tree cleaned | Qualifies the declared case set on the recorded providers/environment. |
| Final native pathname providers with ASan/UBSan | [native-sanitized.json.gz](native-sanitized.json.gz): **402 pass, 0 fail** | The new standalone C pathname providers are instrumented; cshell and system utilities are ordinary builds. |
| Native stock audit | [native-stock-audit.json.gz](native-stock-audit.json.gz): **362 pass, 40 fail** | Strict diagnostic, output-error and Issue-8 option failures; this profile is not qualified. |
| Docker Debian 12 arm64 selected filesystem profile | [linux-filesystem-410.json.gz](linux-filesystem-410.json.gz): **410 pass, 0 fail** | Earlier superset, including eight subsequently removed missing-operand policy controls. All final 402 cases have identical authored expectations and passed in this run. |
| Final-scope Linux crosscheck | [linux-final-case-crosscheck.json](linux-final-case-crosscheck.json) | Checks all 402 IDs/modes and complete expectations against that retained run. This is not a rerun. The runner and C provider sources are unchanged; only the case removals, clause map and profile README differ. |
| Docker complete host profile | [linux-host-profile.json.gz](linux-host-profile.json.gz), [profile log](linux-profile.log.gz): **1162 pass, 0 fail, 0 gaps**, plus the 410 filesystem assertions | Strict selected subset, with other individually recorded capability limitations. |
| Docker selected-PATH runtime/PTY integration | [linux-runtime-pty.log.gz](linux-runtime-pty.log.gz): **3950 runtime passes**; terminal suites **1 + 30 + 1 + 33 passes**, no failures/skips | Passed before the Docker service stopped answering successfully. |
| Docker pathname ASan/UBSan | [linux-sanitizer-summary.log.gz](linux-sanitizer-summary.log.gz): **410 pass, 0 fail** reported | The command completed, but Docker API failures prevented retrieval of its detailed JSON; do not substitute this summary for the retained native sanitizer identities/results. |
| Ownership and harness regressions | [inventory.log.gz](inventory.log.gz): inventory accounting, **10 ownership + 9 filesystem harness tests pass** | Accounting, missing-provider, timeout/reaping, corrupted archive, unavailable terminal and independent-oracle checks. |

Provider inventories record exact PATH, realpath and SHA-256. Linux includes
package owners and the installed package/version list; macOS includes its OS
build. Each detailed run hashes cshell and the build/test inputs, records the
actual fixture filesystem, identity, locale, environment and protection limits,
and retains every invocation, expectation, output/status, effect and cleanup
result. [environment.json](environment.json) records the native compiler and
qualified Docker image ID. [normative-sources.json](normative-sources.json)
records the retrieved Issue-8 page hashes and headings, not copied page content.

## Reproduction

From the ticket worktree:

```sh
make -j8
make test-host-inventory
make test-host-profile
make test-host-filesystem-audit  # nonzero stock result is expected and retained
```

The profile adds only opt-in readlink/realpath executables; system binaries are
unchanged. Docker and Linux CI install file/pax in the controlled environment.
Native provisioning uses the already-installed Homebrew test/bracket providers.

The final focused native command was:

```sh
python3 tests/host_filesystem.py ./cshell --audit \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-profile.json
```

The native instrumented provider build and run were:

```sh
mkdir -p build/csh-072-sanitized/bin
cc -std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  tools/host-profile/paths.c -o build/csh-072-sanitized/paths
ln -sf ../paths build/csh-072-sanitized/bin/readlink
ln -sf ../paths build/csh-072-sanitized/bin/realpath
python3 tests/host_filesystem.py ./cshell --audit --sanitizer \
  --path "$PWD/build/csh-072-sanitized/bin:$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-sanitized.json
```

The completed Docker image was
`sha256:d75dc3f00d93f45a9d33217e41040a7a2fe0539ec0639b44bbbc0fbfa6ef899b`
(linux/arm64, default Debian bookworm Dockerfile). Its commands were:

```sh
docker build -t cshell:csh-072 .
docker run --name csh-072-final cshell:csh-072 sh -c '
  make test-host-profile &&
  CSH_TEST_PATH="/work/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty'
```

A separate `csh-072-audit` container ran the strict stock audit and compiled the
same provider source with the sanitizer flags above into `build/sanitized/paths`,
using symlinks in `build/sanitized/bin`. Its final command used `--audit
--sanitizer`, the sanitized prefix followed by `/work/build/host-profile/bin`
and `getconf PATH`, and wrote `build/tests/host-filesystem-sanitized.json`.

## Preserved failures and limits

- The initial native integration run passed the old host profile (1162), an
  intermediate 418-case filesystem profile and all 3950 runtime assertions.
  An existing `execute_faults --jobs-terminal` fixture then timed out and its
  terminal cleanup failed. [native-initial-integration.log.gz](native-initial-integration.log.gz)
  and [native-intermediate-profile.json.gz](native-intermediate-profile.json.gz)
  retain that run; it is not an all-green integration claim.
- A focused native job-PTY retry had 28 passes and two `/bin/ps` cleanup timeouts:
  [native-pty-retry.log.gz](native-pty-retry.log.gz). A later full host-profile
  run had 1161 passes and one stty PTY cleanup failure:
  [native-host-profile-cleanup-failure.json.gz](native-host-profile-cleanup-failure.json.gz).
  An initial sanitizer run similarly had 409 passes and one rm PTY cleanup
  timeout: [native-initial-sanitized.json.gz](native-initial-sanitized.json.gz).
  These failures remain failures; the final focused 402-case records supersede
  only the filesystem/sanitizer result, not the broader integration failures.
- The owned native helper PID 60832 was observed in state `UE`, parent 1, after
  SIGKILL. The recorded process command identifies this worktree's unchanged
  `build/tests/execute_faults --jobs-terminal`. It had not disappeared at evidence
  collection. No unrelated process was signalled and no host restart attempted.
- Initial Linux direct-rm prompt expectations omitted argv[0]'s absolute path.
  [linux-initial-prompt-mismatch.json.gz](linux-initial-prompt-mismatch.json.gz)
  retains those two harness failures; the corrected expectation is based on the
  actual authored invocation, not copied utility output. An earlier stock run
  also used an incorrect pax mode expectation without `-p p`:
  [linux-initial-stock.log.gz](linux-initial-stock.log.gz). Those are superseded
  harness oracles, not vendor defects.
- Excess-operand and then missing-operand adapter-policy controls were removed
  from the normative audit: implementation extensions outside the prescribed
  synopsis must not become false POSIX failures. This reduced 418 to 410 to 402
  assertions without relaxing any retained normative expectation. Intermediate
  passing native records are retained under `native-integration-*-410.json.gz`.
- Docker returned Internal Server Error during detailed sanitizer/stock result
  retrieval and the final 402-case image rebuild/recheck. The bounded version
  query is retained in [docker-api-failure.txt](docker-api-failure.txt). The owned
  build client was terminated; the daemon was not restarted because other work
  may use it. Stopped evidence containers remain available for recovery when the
  daemon responds. The failed final recheck is not reported as a pass.

All current filesystem records have verified private-tree cleanup. Timeout and
corrupt-output harness tests also verify cleanup, and the timeout test checks
that its owned process disappeared. That does not erase the separate older
job-PTY helper cleanup failure. Quotas, ENOSPC/EIO, inaccessible-ancestor/total
path boundaries, additional collation and remaining archive/metadata contracts
are explicitly unqualified in CSH-079. No protected mounts or physical-device
contents were accessed.
