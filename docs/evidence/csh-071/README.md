# CSH-071 qualification evidence

This is a partial implementation, not ticket closure or complete utility
qualification. [Clause dispositions](../../host-permissions-identities.md) keep
all eight full contracts and the original retained conditions with CSH-071.
The developer confirmed that no additional disposable privileged Darwin
environment is available. System binaries and account databases were not changed.

## Results

| Environment / selection | Result |
| --- | --- |
| [Debian ordinary profile](docker-permissions.json.gz) | **988/988** new permission assertions and **1,162/1,162** existing host assertions; zero failures/gap allowances. |
| [Debian controlled profile](docker-controlled-permissions.json.gz) | **1,072/1,072** new permission assertions; **2,281/2,281** existing host assertions; zero failures/gap allowances. |
| [chmod original-X strict reproducer](docker-chmod-X.json.gz) | **0 pass, 4 fail**, each invocation mode. GNU chmod 9.1 produces 0754 for initial 0644 and `u+x,g+X`; the authored original-mode oracle requires 0744. This remains open, not allowed in the qualified subset. |
| [newgrp strict session profile](docker-newgrp.json.gz) | **12 pass, 8 fail**. Default, named root and changed daemon group preserve measured GIDs, cwd, umask, exported variable and shell status. Numeric `0` and unknown-group failure return before creating a shell. Each fails in four modes; no authentication policy allowance masks the results. |
| Linux adapter ASan/UBSan | **44/44** assertions: comparison/negation/equality in test and bracket plus missing terminator. The adapter is instrumented; no sanitizer claim is made for vendor binaries or the cshell executable in this run. |
| [macOS final selected suite](native-final-permissions.json.gz) | **968 pass, 12 fail**. Every failure is a five-second no-output timeout with failed one-second leader reaping, not a semantic mismatch. This run is **failed**, not qualified. |
| [macOS existing host suite](native-existing-profile.json.gz) | **1,162/1,162**, zero failures or gaps, run independently because the new-suite prerequisite failed. |
| Runtime/PTY integration | Docker `make test-runtime test-pty` returns 0 with 4,015 summarized assertions passing. Native returns 2 in the terminal job failure-cleanup fixture; the exact assertion and per-suite summaries are retained. |
| Harness controls | Four final Linux regression tests pass, including actual timeout PID disappearance. Native attempts include failed controls and cleanup timeouts; retained separately. |

The JSON files retain raw output bytes, expected status/output/effects, invocation
mode, environment/provider/source identities and cleanup reports. Every selected
fixture directory was removed; the native reports still retain process-reaping
failures. Unknown root causes are not assigned to vendor logic or labeled passes.

## Reproduction

From this worktree:

```sh
make -j4 test-host-profile
make test-host-inventory
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty

docker build -t cshell-test:csh-071 .
docker run --rm --init cshell-test:csh-071 make -j4 test-host-profile
docker run --rm --init --user 0 cshell-test:csh-071 make -j4 test-host-profile \
  HOST_PROFILE_FLAGS=--controlled-identities HOST_PERMISSIONS_FLAGS=--controlled-identities
```

Capture `build/tests/host-permissions-results.json` and
`build/tests/host-profile-results.json` before removing the container. Evidence
runs mount this directory at `/evidence` and copy those outputs. The final ordinary
Linux run also mounts the final `tests/` read-only at `/work/tests`; this includes
a reporting-only change retaining identity before a failed session observation
and a stronger timeout regression that checks PID disappearance. The earlier
controlled run's embedded source hashes identify its exact snapshot.

In a disposable root container after `make host-profile`:

```sh
python3 tests/host_permissions.py ./cshell \
  --path "/work/build/host-profile/bin:$(getconf PATH)" \
  --vendor-residuals --case-prefix chmod/original-X --record /evidence/docker-chmod-X.json
python3 tests/host_permissions.py ./cshell \
  --path "/work/build/host-profile/bin:$(getconf PATH)" \
  --session-controls --case-prefix newgrp/ --record /evidence/docker-newgrp.json
```

Both strict residual commands return 1. They are additional failed qualification
attempts, not prerequisites silently bypassed by the selected passing profile.
GNU vendor ownership remains explicit. The existing strict unequal-ACL reproducer
and fakeowner prerequisite ledger remain unchanged; the adapter delegates those
predicates and does not purport to repair them.

For the sanitizer run, build `host-profile` with
`CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer'`
and `LDFLAGS='-fsanitize=address,undefined'`. Run the permission harness with
`--sanitizer` and prefixes `test/collation`, `[/collation`, `[/missing-bracket`,
each into its own record. Logs retain the compiler and exact selected arguments.

## Development failures and source identity

- `native-before`: 860 pass, 36 fail. Thirty-two are GNU 9.3 rejecting Issue 8
  string comparisons, repaired by the repository adapter. Four are an oracle
  transport defect: setting umask 0777 before writing the identity record made
  that record unreadable. The harness now records identity before applying the
  requested utility umask. This is not a chmod provider failure.
- `docker-before`: 988 pass, 4 fail. These isolate GNU chmod's original-X
  discrepancy. It is retained as an explicit strict residual, never redefined
  to expect the observed vendor behavior.
- `docker-traversal-oracle-before`: 1,048 pass, 24 fail. The initial -H oracle
  incorrectly required an encountered symlink's referent itself to remain
  unchanged. DESCRIPTION requires chown()-equivalent effects; -H prevents
  traversal of its children. The revised oracle distinguishes referent from
  descendant metadata. This is a test-authoring repair, not a vendor failure.
- `native-timeouts`: 978 pass, 6 fail in an earlier selected run. Native harness
  control/timeout logs preserve additional failed attempts. No native full-run
  success is inferred from smaller passing development selections.
- [Normative sources](sources.json) records hashes of the seven freshly retrieved
  official pages. No third-party implementation is used as the normative oracle.

All original CSH-064 evidence is immutable. CSH-071 remains `in-progress` because
privileged Darwin qualification, retained vendor/filesystem conditions, the new
strict vendor failures and the individually listed full-page branches are open.

`python3 docs/evidence/csh-071/verify.py` validates the retained verdicts,
provider identities, fixture removal and current open ownership.

## Outstanding execution-environment cleanup

After the final ordinary Linux reports were copied out, Docker's control API
returned HTTP 500 for scoped container listing twice. The `docker run --rm` client
remained attached, so final container teardown is unverified despite completed
passing assertion records. The [control error](container-cleanup.log.gz) is retained;
Docker was not restarted because other work uses it.

The failed native PTY fixture left owned `execute_faults --jobs-terminal` PID 53936
in macOS `UE` (uninterruptible/exiting) state, adopted by PID 1. It remained after
an explicit SIGKILL retry; [the observation](native-cleanup.log.gz) is retained.
This is an unresolved process-cleanup failure, not a passing cleanup assertion.
The worktree must remain available while that process may still refer to it.
