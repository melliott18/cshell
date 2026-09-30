# CSH-078 service and codec evidence

Base commit: `60295934db1c971a2b3aac582f88b0f766eccce2`.
Worktree branch: `test/CSH-078-host-service-utilities`.
Production cshell sources are unchanged. Each JSON retains its actual test/build
source hashes; later harness changes do not rewrite earlier results. Native
macOS 14.8.7 arm64 and Docker Debian 12/Linux aarch64 are separate environments.
Native Linux was not supplied.

The [profile](../../host-service-profile.md) describes assertions, identities,
limits and isolation. The [section map](../../../tests/host_service_contracts.json)
retains 20 named unqualified residuals under CSH-078 and explicitly sets
`full_contract_qualified: false`. Neither a passing subset nor a package's
presence closes the full utility contract. No developer-host job, mail,
logging, printing or clock-setting operation was performed.

## Attempts

All `.gz` files are gzip-compressed original records. `files.json` gives the
SHA-256 and size of the **decompressed** bytes, so they can be independently
verified without depending on compression metadata.

| Record | Result and interpretation |
| --- | --- |
| `native-stock.json.gz` | **380 pass, 110 fail.** Stock macOS uudecode treats `-` as a file instead of the Issue 8 stdout cookie. Both algorithms and explicit `-o` reproduce it through every dispatch mode. |
| `docker-guard-failure.json.gz` | **Setup failure; no utility witnesses ran.** The first guard incorrectly required exactly one interface. This Docker kernel exposes inactive `tunl0`/`ip6tnl0` interfaces even with `--network none`. The corrected guard requires no active non-loopback interface and excludes network administration capabilities. |
| `docker-interrupted-fixture.json.gz` | **Failed/incomplete fixture attempt.** libfaketime interfered with `date -u`; a synchronous syslog receiver also consumed PAM/runuser packets and filled its socket queue, causing timeouts. The run was interrupted. These are fixture defects, not vendor compliance findings. A clock-read-only shared object and an independently draining syslog process replace them. |
| `docker-provider-and-fixture-failures.json.gz` | **736 pass, 46 fail.** Debian stock batch omits completion mail for a silent job. Other failures were fixture expectations: absent-atd notices while intentionally staging jobs before daemon startup; Exim's unmet 1024-descriptor prerequisite; CUPS reporting zero named files for stdin; and assuming an out-of-range cron field (outside application requirements) must be rejected. The last assertion was replaced by an actual missing-file error and preservation check. |
| `docker-selected.json.gz`, `docker-selected-launcher.json.gz`, `docker-selected.log.gz` | **782 pass, 0 fail.** Independent scheduling/mail/logging/print-spool/clock and codec witnesses with the selected batch wrapper. Exact image/package/utility identities and command bytes are retained. Launcher records successful container removal. The complete CUPS printing contract remains unqualified because the backend is a byte sink. |
| `native-codecs.json.gz` | **490 pass, 0 fail.** Opt-in repaired macOS uudecode, system uuencode and read-only date. Service and controlled native-clock capabilities are explicitly unavailable. |
| `native-profile-initial.json.gz` | **1161 pass, 1 fail, 0 gap allowances.** The existing stty PTY behavior exited 0, but cleanup's `/bin/ps -axo pid=,stat=` query exceeded its five-second deadline. The entire profile attempt failed. |
| `native-profile.json.gz` | **1162 pass, 0 fail, 0 gaps.** Repeated existing host-profile assertions; no production or PTY-harness change between these two attempts. This does not erase the initial cleanup failure. |
| `native-regression.log.gz` | `make test-host-profile test-runtime test-pty`: codec/profile passes, **3950 runtime passes**, then 1 runtime PTY and 30 job PTY passes. The existing job-fault PTY fixture timed out before output; cleanup reported a process-snapshot deadline and an EPERM group-kill error. `make test-pty` failed; later prerequisites were not completed by that invocation. |
| `native-sanitized-codecs.json.gz`, `native-sanitized-codecs.log.gz` | **490 pass, 0 fail.** The new standalone uudecode was compiled with Clang ASan/UBSan, `-Werror`, and frame pointers; `ASAN_OPTIONS=halt_on_error=1:detect_leaks=0`, `UBSAN_OPTIONS=halt_on_error=1`. This instruments the adapter, not every host provider or cshell. |

The PTY timeout observations belong to the existing harness/job-control
investigation, not a waived service assertion. They are retained here because
this validation encountered them. No conclusion about their root cause is
inferred from a later pass.

## Earlier verification environment failure

The final image built successfully as
`sha256:73de8330899949faff4a1a42cd8dc9cc67d639a106298f832c6b3798785d7a9b`.
During its verification, the Docker daemon began returning HTTP 500 for version,
inspect, container-list and removal calls (including an explicit API 1.43 check).
The outer 300-second deadline fired; inspect and removal then failed. There is
**no passing qualification result for that final run**, and its container cleanup
could not be confirmed. `docker-final-launcher.json.gz`,
`docker-final-build-run.log.gz` and `docker-final-output.log.gz` retain this failed
attempt. The earlier 782-pass image has its own identity and successful cleanup;
it is not substituted for final-source validation.

The affected owned container is
`cshell-services-4d829919ca1f42cd846deb945479925e`. The three stopped development
containers `csh078-development`, `csh078-development-2`, and
`csh078-development-3` also required removal once the daemon became responsive.
At that checkpoint no unrelated container or Docker Desktop instance had been
stopped or restarted. That cleanup attempt remains in `final-cleanup.json.gz`;
the recovery below resolves the outstanding cleanup.

The final launcher additionally handles SIGTERM/interrupt cleanup and a create
response timing out after the daemon may have allocated the container. These
paths pass local failure-injection tests. The continuation below supplies a
passing live-Docker rerun. CSH-078 remains in progress for its unqualified
full-contract residuals.

## Disposable-service continuation (2026-09-30 UTC)

The [continuation records](continuation/files.json) retain decompressed SHA-256
and size for every new artifact. They were produced after checkpoint
`b1e2e2e`, on the same separate worktree branch. Each result records the exact
source and provider identities used for that attempt.

| Record under `continuation/` | Result and interpretation |
| --- | --- |
| `docker-restart-before.json.gz`, `docker-restart-after.json.gz` | Authorized Docker Desktop recovery after repeated HTTP 500 responses. The CSH-073 client had been waiting for 5h40m, but all three test stages had finished over five hours earlier. Their persisted statuses were 0, 0, 1; the audit had 552 passes and 18 failures. The stalled client ended during restart; no live test-stage termination was observed. Its command and logs/statuses are preserved for recovery, and no rerun was started. All four outstanding CSH-078 containers were subsequently removed successfully. |
| `expanded-initial.json.gz`, `expanded-initial-launcher.json.gz`, `expanded-initial.log.gz` | **852 pass, 20 fail**, with successful cleanup. Ten logging failures came from fixture assumptions: expecting no util-linux warning with `-f` plus operands, and assuming `-f -` means stdin. The provider logs operands correctly and treats dash as a literal filename. Ten scheduler failures incorrectly required a group distinct from the daemon rather than the submitting environment. The corrected assertions preserve the actual required effects. |
| `expanded-corrected.json.gz`, `expanded-corrected-launcher.json.gz`, `expanded-corrected.log.gz` | **872 pass, 0 fail**, successful container cleanup, after correcting the fixture assumptions. |
| `expanded-final.json.gz`, `expanded-final-launcher.json.gz`, `expanded-final.log.gz` | **872 pass, 0 fail**, successful container cleanup, using the final harness and narrowed contract map. |
| `native-final.json.gz`, `native-final.log.gz` | **490 native codec/date passes**, 12 inventory regression tests and 8 service/launcher harness tests pass. No native service invocation. |

New observations include a/c queue selection and filtering, multi-ID removal,
job UID/GID and absence of a controlling terminal, process groups distinct from
submission, mail address/date/message-ID headers and no-subject delivery,
logger operand precedence and literal-dash policy, and printing destination
precedence across two queues. The print copy test pauses the queue, submits
with `-c`, changes the source, then resumes the queue and checks the original
bytes. This avoids a race in which the backend could finish before mutation.
CUPS's byte sink still does not qualify hardcopy or completion notifications.

The restart did not erase the earlier Docker failure or establish an unseen
result for its old image. The fresh runs provide their own qualification and
cleanup evidence. There are still 20 residual IDs; their descriptions now
exclude the newly covered portions rather than claiming full-page closure.

## Reproduction

```sh
make test-host-inventory test-host-service-harness
make test-host-profile test-runtime test-pty
make docker-test-host-services
```

The inventory check passes for 156 names, 101 external contracts and 30 retained
conditions, with 12 accounting regression tests. The service and launcher harnesses have eight
passing checks for native safety refusal, missing providers, false successes,
owned timeout cleanup with an unrelated-process control, interrupted-profile
reporting, output bounds, an unavailable Docker executable and cleanup after a timed-out create response. The independent case-prefix check prevents a
missing declared witness from being called a passing profile.

For standalone decoder sanitizer reproduction:

```sh
cc -std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  tools/host-profile/uudecode.c -lresolv -o build/host-uudecode-sanitized
mkdir -p build/host-codec-sanitized
ln -sf ../host-uudecode-sanitized build/host-codec-sanitized/uudecode
ASAN_OPTIONS=halt_on_error=1:detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 \
  python3 tests/host_services.py ./cshell \
  --path "$PWD/build/host-codec-sanitized:/usr/bin:/bin" \
  --record build/tests/host-codec-sanitized.json
```
