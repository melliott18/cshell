# CSH-072 selected provider repairs

Five reproduced contracts are repaired in the opt-in PATH: find logical-cycle
errors, pax truncated-input errors, EPIPE, final EFBIG/partial-write errors and
ustar mode encoding. The historical stock failures remain real and unchanged.
Complete utility pages and the broader environment-dependent contracts remain
open under [CSH-079](../../../tickets/CSH-083-filesystem-remaining-contracts.md).

## Results

| Run | Result | Boundary |
| --- | --- | --- |
| [Native selected filesystem](native-selected.json.gz) | **570 pass, 0 fail** | Includes all previously excluded provider assertions; every fixture cleanup passes. |
| [Native host profile](native-host-profile.json.gz), [combined log](native-integration.log.gz) | **1162 pass, 0 fail, 0 gaps**, then 570 filesystem passes | The complete bounded host profile with new providers. |
| [Native provider sanitizers](native-sanitized.json.gz), [log](native-sanitized.log.gz) | **570 pass, 0 fail** | Local pax and readlink/realpath instrumented with ASan/UBSan; GNU find, cshell and other system utilities are ordinary builds. |
| [Hosted Ubuntu selected filesystem](linux-selected.json.gz), [log](linux-selected.log.gz) | **586 pass, 0 fail** | Includes all Linux ENOSPC assertions and previously failing pax assertions; every fixture cleanup passes. |
| [Hosted Ubuntu stock audit](linux-stock-audit.json.gz), [log](linux-stock-audit.log.gz) | **176 pass, 8 fail** | Unmodified distribution pax still fails ustar type-graph writing and final EFBIG. The selected pax does not inherit those failures. |
| [Native selected-PATH runtime](native-runtime-initial.log.gz) | **3949 pass, 1 fail** | The stdin xtrace/dot case hit a one-second `/bin/ps` cleanup timeout. Preserve the failure. |
| [Isolated runtime retry](native-runtime-retry.log.gz) | **1 pass, 0 fail** | The same exact case passed alone; this does not rewrite the original full-run result. |
| [Native runtime PTY](native-runtime-pty.log.gz) | **33 pass, 0 fail** | Automated owned-terminal runtime checks with the selected PATH. |
| Ownership/harness regressions in the combined native log | **10 + 13 pass** | Inventory, independent oracles, armed I/O markers and cleanup controls. |

The detailed selected runs have identical source identity
`cf348b0758b24f6a3622a53d795f445f80ff9481bfc0e5e5e8cf49b294f8f2ea`,
corresponding to implementation commit
`11471e35d0fbc1b41137d85afe5290a2811a4da9`. Records contain source/provider hashes,
PATH, OS/package/filesystem identity, limits, every expectation and observed
status/output/effect, and cleanup. Native and Linux manifests are retained.
`SHA256SUMS` identifies the artifacts; later documentation does not alter them.

The Ubuntu records come from
[focused workflow 36663526005](https://github.com/melliott18/cshell/actions/runs/36663526005).
Full Linux/Docker jobs were still running and hosted macOS jobs were queued at
collection. Their current status must be checked separately. Earlier focused
hosted macOS results on commit 13b5441 completed: **550 selected passes** and
**152 pass/16 fail** in the original audit, now retained here as
`previous-hosted-macos-*.json.gz`. Those establish the earlier environment only.

## Provider provenance and repair scope

- macOS selects GNU find. This native run built GNU findutils 4.10.0 in the
  ignored worktree build directory and exposed its executable as `gfind` only
  to provisioning. [Build provenance](native-find-build.json) records source
  URL/hash, configure/build commands and executable hash. No host package was
  installed. CI provisions Homebrew findutils; Linux keeps its distribution find.
- Both platforms build pinned MirCPIO 20240817 pax offline from the checked-in
  source. [Upstream provenance and local changes](../../../../tools/host-profile/vendor/pax/CSHELL-CHANGES.md)
  preserve all license notices and the release checksum. Only `tar.c` and
  `buf_subs.c` differ from the original sources; [exact diff](pax-local.patch).
- The unpatched pinned pax already fixes Apple's truncated-member/EPIPE errors,
  but still fails ustar mode and final EFBIG assertions, as retained in
  [the direct native probe](upstream-pax-native.json.gz). Local changes mask the
  specified 12 mode bits and drain the final buffered record or propagate the
  flush failure. `memmove` handles overlapping pending bytes after a short write.
- No output filtering or status adapter is used. The original independent
  expectations are unchanged. The selected profile explicitly requires
  `--provider-audit`; that flag now includes mandatory provider regression
  contracts. The separate workflow diagnostic uses the stock PATH.

## Reproduction

```sh
# On macOS supply coreutils and findutils (gtest, g[, gfind) before provisioning.
make host-profile
make test-host-profile
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime-pty

# All selected filesystem contracts, independently of the broader host suite:
python3 tests/host_filesystem.py ./cshell --audit --provider-audit \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-repaired.json

# Stock comparison retains real failures and exits nonzero:
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --path "$(getconf PATH)" --record build/tests/host-filesystem-stock.json
```

Native instrumentation reused the original instrumented pathname build, then
built pax separately to avoid changing ordinary selected binaries:

```sh
mkdir -p build/csh-072-sanitized/pax
(cd build/csh-072-sanitized/pax &&
 CC=cc CFLAGS='-std=c99 -Wall -Wextra -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
 LDFLAGS='-fsanitize=address,undefined' \
 sh ../../../tools/host-profile/vendor/pax/Build.sh > build.log 2>&1)
ln -s ../pax/pax build/csh-072-sanitized/bin/pax
python3 tests/host_filesystem.py ./cshell --audit --provider-audit --sanitizer \
  --path "$PWD/build/csh-072-sanitized/bin:$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-repaired-sanitized.json
```

The broad hosted macOS job previously hit 45 minutes while actively progressing
in sanitizer runtime assertions. Its budget is now 90 minutes; per-case deadlines
remain unchanged. A larger budget is not a passing result. Native `/bin/ps`
cleanup timeouts remain an environmental limitation and are retained explicitly.
No unrelated process was stopped and no host restart was attempted.

## Additional environments and manual testing

All reproduced provider defects above are covered automatically by the existing
macOS/Linux environments. Ordinary options, traversal, formats and metadata
need more fixtures, not manual testing. Actual exhausted filesystems/quotas,
mount boundaries, cross-device moves and privileged ownership/ACLs need bounded
disposable filesystem and credential environments. Kernel EIO needs a controlled
fault mechanism. Linux cannot establish Darwin-specific behavior. These can
normally be automated after provisioning; a human operator is needed only for
a separately requested physical-terminal claim. The current terminal tests use
owned PTYs and require no manual interaction. See the exact capability table in
CSH-079 before claiming those broader contracts.
