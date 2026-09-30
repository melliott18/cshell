# CSH-072 Darwin cleanup follow-up

Repeated `/bin/ps -axo pid=,stat=` timeouts made otherwise successful pipe
runtime checks fail during zombie-group verification. The shared Darwin session
snapshot now queries libproc PID enumeration and short BSD metadata directly.
It preserves session ownership, zombie exclusion, deadlines and the 1 MiB
snapshot cap. Final pipe cleanup also gives leader reaping its own one-second
budget after snapshot failure, matching the existing PTY approach.

## Validation

| Retained result | Outcome |
| --- | --- |
| [Native harness](native-harness.log.gz) | **93 tests pass**, including six libproc regressions and a real child reaped after an injected expired snapshot deadline. |
| [Native selected-PATH runtime and PTY](native-runtime-pty.log.gz) | **3950 runtime + 33 PTY passes**, zero failures/skips. This full rerun resolves the previous isolated ps-cleanup timeout. |
| [Native filesystem](native-filesystem.json.gz), [log](native-filesystem.log.gz) | **570 pass, 0 fail**; every fixture cleanup verified. |
| [Hosted Ubuntu filesystem](linux-filesystem.json.gz), [log](linux-filesystem.log.gz) | **586 pass, 0 fail**; every fixture cleanup verified. |
| [Previously completed hosted macOS filesystem](prior-hosted-macos-filesystem.json.gz) | **570 pass, 0 fail** on commit 2453082, confirming the preceding find/pax provider repairs on hosted macOS. This is not a libproc rerun. |

The final native and Linux filesystem records share source identity
`37440c8fee0ba58b1e9122796e8fec9fccee7adbb95efe93e6b97e07c9c115d4`, corresponding to implementation commit
`1a9a34970220a445a6635315a9be629e6f4c2f3a`. The exact source inventory is retained
in [source-identity.json](source-identity.json). Records retain provider hashes,
platform identity, all expected/actual outputs and effects, limits and cleanup.
`SHA256SUMS` identifies the evidence files.

Linux evidence comes from
[workflow 36676415195](https://github.com/melliott18/cshell/actions/runs/36676415195).
The current broader Linux/Docker jobs and hosted macOS jobs must be assessed
separately; at collection, the latter remained queued. The earlier hosted
macOS record came from workflow 36663876674. No green complete-matrix claim is
inferred from a focused result.

## Safety and independent controls

The ABI follows Apple's [libproc declarations](https://github.com/apple-oss-distributions/xnu/blob/main/libsyscall/wrappers/libproc/libproc.h)
and [short BSD process record](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/proc_info.h).
The native regression verifies PID, parent, process group and UID against an
actual owned child. It then kills but deliberately leaves that child unreaped,
confirms the PID still exists, and verifies it is excluded from live members.
The test forbids subprocess.run during discovery, so a hidden ps fallback
cannot satisfy it. All children are reaped by the test.

PID buffers that fill are retried within the shared deadline and memory bound;
a full or malformed result cannot be mistaken for an empty session. Session
membership is checked before status lookup and rechecked afterward. Permission
errors, invalid records and exhausted deadlines still fail cleanup. Only ESRCH
(disappearance) or zombie status excludes an owned process. No discovery query
signals a process; group signals retain the existing ownership rules.

The first native self-test incorrectly assumed libproc always returns a zombie
record. Darwin can return ESRCH while the unreaped PID remains present. The
[initial 92-test run](native-harness-initial.log.gz) retains that test error. The
corrected test independently checks kernel PID existence and excludes the exited
child; it does not weaken live-child, permission-error or incomplete-snapshot
checks. The final suite also tests a snapshot timeout advancing beyond its
budget while proving the real leader is still reaped with a separate bounded
wait, and that the original cleanup failure remains a failure.

## Reproduction and CI

```sh
make test-harness
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-runtime-pty
python3 tests/host_filesystem.py ./cshell --audit --provider-audit \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --record build/tests/host-filesystem-cleanup.json
```

The Tests and Filesystem qualification workflows now cancel superseded runs for
the same workflow/ref. Only older runs on this ticket branch were manually
cancelled during cleanup; successful earlier evidence is retained. Push and PR
refs retain their separate checks. The 90-minute macOS budget and per-case
limits remain unchanged. Historical stuck-helper and ps failures remain in the
older evidence; no unrelated process was stopped or host restarted.

This follow-up resolves reproduced harness failures. Broader missing utility
contracts and disposable filesystem/credential/EIO capabilities remain in
CSH-079; they are not silently declared qualified by these passes.
