# CSH-072 extended filesystem evidence

This extension covers traversal, links, metadata, ustar archives and bounded
kernel I/O errors. Qualification is case-scoped; complete utility pages and
remaining contracts stay with CSH-079. See the
[contract description](../../../host-filesystem-evidence.md) and
[clause map](../../../../tests/host_filesystem_contracts.json).

## Results

| Recorded run | Result | Qualification |
| --- | --- | --- |
| [Native selected](native-selected.json.gz), [log](native-selected.log.gz) | **550 pass, 0 fail** | Original 402 plus 148 new assertions through direct exec and cshell string/file/stdin. |
| [Native instrumented pathname providers](native-sanitized.json.gz), [log](native-sanitized.log.gz) | **550 pass, 0 fail** | Only the local readlink/realpath providers are ASan/UBSan instrumented. System utilities and cshell remain ordinary builds. |
| [Native strict extension audit](native-provider-audit.json.gz), [log](native-provider-audit.log.gz) | **152 pass, 16 fail** | Four vendor contracts fail in each of four invocation modes; none qualify. |
| [Linux selected](linux-filesystem-selected.json.gz), [log](linux-filesystem-selected.log.gz) | **562 pass, 0 fail** | Adds 12 Linux virtual-device ENOSPC assertions for dd and the selected readlink/realpath. |
| [Linux strict extension audit](linux-filesystem-provider-audit.json.gz), [log](linux-filesystem-provider-audit.log.gz) | **176 pass, 8 fail** | Linux pax ustar modes and EFBIG each fail in four modes. find cycle, pax truncation/EPIPE and pax ENOSPC pass in this environment. |
| [Ownership/harness regression log](harness.log.gz) | **10 ownership + 13 filesystem tests pass** | Includes timeout/reaping, rejected missing fault markers, a success-under-EPIPE negative control, duplicate archive members and refusing to read a FIFO archive. |

All five final native/Linux records use source identity
`81c96dacf23ed35e0e547915ca38ca8d0df468df876b50141d028786f1df7aed`
from implementation commit `7e9bd6def8e0c50ce489d8a0108bca7e5ce1a797`.
The records retain exact provider and executable hashes, source-file hashes,
OS/filesystem identity, PATH, environment, expectations, observed status/output,
metadata, archive members, kernel-fault markers and verified private-tree cleanup.
The Linux records come from the Ubuntu 24.04 job in
[workflow run 36641568903](https://github.com/melliott18/cshell/actions/runs/36641568903),
using its recorded distribution pax package. The [job log](linux-ci-job.log.gz)
confirms explicit `bash -e -o pipefail` and exit code 1 for the strict audit. The macOS hosted job remains
queued at collection; the native results above come from the developer host.
No new full-system or complete-utility claim is made.

## Reproduction

From the separate CSH-072 worktree, with the selected PATH already provisioned:

```sh
make test-host-inventory
python3 tests/host_filesystem.py ./cshell --audit \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-expanded.json
python3 tests/host_filesystem.py ./cshell --extended-only --provider-audit \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-provider-audit.json
python3 tests/host_filesystem.py ./cshell --audit --sanitizer \
  --path "$PWD/build/csh-072-sanitized/bin:$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-expanded-sanitized.json
```

The instrumented providers use the unchanged source and build command in the
[original evidence](../README.md). `make test-host-filesystem-provider-audit`
is the corresponding strict Make target and returns nonzero on any failed
assertion. `--extended-only` excludes the original 402 assertions;
`--provider-audit` adds the explicitly unqualified extension assertions without
allowing their failures. The default selected subset excludes those assertions.

## Preserved failures and boundaries

- Apple find `-L` returns zero without a diagnostic for the authored logical
  directory cycle. The expected positive exit and diagnostic remain required.
- Apple pax returns zero for a truncated member (with an end-of-volume warning),
  an EPIPE write (without a diagnostic), and an EFBIG partial archive write
  (with a warning). All are retained as strict failures owned by CSH-079.
- Linux pax encodes file-type bits in ustar mode values (for example, 0100640
  instead of 0640). The Issue-8 ustar mode field defines 12 mode bits separately
  from the typeflag. The independent decoder retains raw values and does not
  mask away the defect. The same strict type-graph archive assertion passes
  natively and stays in the provider audit on both platforms.
- [Initial Linux selected run](linux-initial-filesystem-selected.json.gz):
  **562 pass, 4 fail**; [strict audit](linux-initial-filesystem-provider-audit.json.gz):
  **176 pass, 8 fail**. The initial workflow's unspecified shell did not propagate
  the failing runner status through tee. Explicit Bash now supplies pipefail;
  the final run above excludes the still-strict ustar write assertion from the
  declared selected set and retains it in the diagnostic audit. The initially
  green job is not passing evidence. The earlier 554-pass native records are
  preserved in `native-*-before-linux-audit.*.gz`; removing this four-mode
  assertion from the portable selected set yields the final 550 native count.
- [Initial native strict run](native-initial.json.gz): **148 pass, 20 fail**.
  Sixteen failures are the vendor contracts above. Four were an incorrect
  harness assumption that dd creates an output before detecting closed stdin;
  the corrected fixture precreates an empty output and independently arms EBADF.
  No provider expectation was relaxed.
- Fault wrappers probe real EBADF/EPIPE/EFBIG before exec and retain action,
  provider, PID, phase and errno. Loader/setup failures cannot satisfy a utility
  positive-error assertion. EFBIG uses a 512-byte child limit; no disk is filled.
- Linux ENOSPC uses only `/dev/full`, opened without following links and checked
  by `fstat` for character device major 1/minor 7. This measures actual ENOSPC
  writes, not exhausted filesystem capacity, quotas or EIO. The capability is
  explicitly unavailable on macOS. pax ENOSPC remains in the strict audit.
- New fixtures retain the existing five-second/64-KiB/1-MiB bounds and verify
  cleanup, including error paths. No mounts, privileged accounts or physical
  device contents are used. Earlier broad job-PTY cleanup failures remain in
  the original evidence and are not superseded by these focused passes.
- The focused GitHub workflow has a required selected-profile step and a
  separate diagnostic provider audit. The latter uses `continue-on-error` only
  at workflow level; its command still fails and artifacts retain every strict
  failure. A green workflow does not qualify these audited contracts.


`SHA256SUMS` identifies every compressed evidence file. No detailed result is
rewritten to change its status or expectation. The two Linux archive assertions
remain strict; future provider repairs must pass them before qualification.
