# CSH-074 native and Linux qualification evidence

These records qualify only the [bounded language/editor subset](../../host-languages-evidence.md).
Full utility contracts and remaining editor conditions stay open under CSH-074.
The branch is `test/CSH-074-host-languages-editors`. No shell production code or
system executable was changed, and no complete POSIX profile is claimed.

## Current results

| Check | macOS | Debian 12 Docker (before final readiness correction) |
| --- | --- | --- |
| Declared language/editor subset | 334 pass, 0 fail | 334 pass, 0 fail |
| New harness controls | 5 pass | 5 pass |
| Existing harness controls | 86 pass | 86 pass |
| Inventory/ownership checks | Pass | Pass |
| Existing full host profile | 1160 pass, **2 cleanup failures**, 0 gaps | 1162 pass, 0 fail, 0 gaps |
| Optional strict SIGINT transcript | **3 failures**, retained separately | **3 failures**, retained separately |

The complete native `make test-host-profile` invocation failed, so its selected
language stage did not run in that invocation. The 334 native passes above are
from the separately invoked focused target with the same selected PATH. Do not
combine them into a claim that the full native profile passed.

The final native default record is [native](native-final.json.gz).
The [Linux passing record](linux-final.json.gz) precedes the final readiness
correction; its later 332/2 result and current setup blocker are retained below. Each contains invocation, input/oracle, exact
actual bytes/status/effects, bounds, cleanup, source hashes and executable
identities. The [native package/toolchain identity](native-identity.json.gz)
adds compiler and Xcode build versions. [Docker image metadata](docker-image.json.gz)
identifies the tested image, not a claim about every Debian installation.

## Commands and environment

Native commands, from the separate worktree:

```sh
make -j4 cshell
make -j4 test-host-profile
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-host-languages
make test-host-inventory test-harness
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
```

The first full native profile exits 2; the focused target and harness checks
exit 0. The stock attempt used `os.defpath` (`/bin:/usr/bin`); final native
qualification uses the private profile plus the actual `getconf PATH`.
No locale other than C is qualified by the new cases. Existing profile locale
and privilege limitations remain in its own record.

Docker uses the repository Dockerfile with Debian bookworm-slim and explicit
bc/m4 packages, UID 10001, and its native Linux compiler. Image build and run
logs are retained. The first implementation image exercised the initial oracle;
a subsequent image contains the corrected fixtures and explicit subset boundary.
The attempted final focused Linux run is blocked before container creation. Linux
`make test-host-profile test-harness` exits 0 after the corrections; the
optional SIGINT reproducer exits 1 by design when its assertions fail.

```sh
docker build -t cshell-csh074:final .
docker run --init cshell-csh074:final make test-host-profile test-harness
python3 tests/host_languages.py ./cshell --path SELECTED_PATH \
  --ed-sigint --record build/tests/host-languages-sigint.json
```

`SELECTED_PATH` is expanded in the actual JSON invocation and logs. No expected
bytes are sourced from a selected utility. Compressed JSON preserves the exact
original record bytes; the [record index](records.json) lists uncompressed
SHA-256 values. Read a record with `gzip -dc NAME.json.gz`.

## Failed attempts and dispositions

1. [Initial native attempt](native-attempt1.json.gz): 317 pass, 20 fail. Four
   awk failures came from a literal newline mistakenly embedded in an awk string;
   the source fixture now supplies an escaped newline. Four ed filename failures
   omitted the filename printed by the `f file` command; both filename prints are
   now authored from the command definition. Four failed ed writes and three HOME
   recovery failures rejected implementation-dependent diagnostics; the required
   marker/status/file effects remain strict and actual diagnostics are retained.
   Three SIGINT checks waited on stdout, while macOS emitted to stderr. Two m4
   launcher invocations timed out after five seconds. The launcher timeout cause
   is **unknown**, not assigned to load or cache warming; the selected profile
   explicitly chooses and hashes the actual developer-tool m4 instead.
2. [Second native signal attempt](native-signals-attempt2.json.gz): two SIGHUP
   passes and one SIGINT timeout with PTY input/stdout. The
   [diagnostic attempt](native-signals-attempt3.json.gz) confirms that only the
   initial buffer print reached stdout. Later synchronization observes both
   streams and retains the actual macOS stderr marker; the normative assertion
   still requires stdout and fails.
3. [Initial Linux attempt](linux-attempt1.json.gz): 333 pass, four fail. One
   direct ed error case incorrectly required subsequent file effects to be absent;
   the normative default leaves those effects unspecified. The corrected case
   ends after the invalid address and requires the error marker and nonzero
   status. Three SIGINT transcripts contain an extra leading newline. These are
   retained as strict opt-in failures pending disposition, without a gap waiver.
4. [Native existing profile](native-existing-profile.json.gz): stty PTY cleanup
   and the false aggregate-E2BIG witness fail because `ps -axo pid=,stat=` exceeds
   the cleanup deadline (five seconds and one second respectively). Status and
   expected behavior bytes are otherwise present. These remain unexplained
   harness observations requiring triage; no retry-to-green or causal repair is
   claimed. The new code does not change the shared cleanup timeouts.
5. [Linux existing profile](linux-existing-profile.json.gz): 1162 pass, no
   failures/gaps in the first Linux attempt; new language fixtures then failed
   as described above. [Later full-profile record](linux-profile-final.json.gz)
   also passes. These are separate from the failing native profile.
6. [Intermediate native subset](native-subset-attempt2.json.gz): 334 pass after
   fixture corrections and the explicit SIGINT subset boundary. The
   [full optional native run](native-sigint-strict.json.gz) has 334 pass and three
   strict SIGINT failures. A final synchronization correction requires fresh
   output after each command, preventing reuse of the readiness print as the
   post-interrupt print. [Final native SIGINT records](native-sigint-final.json.gz)
   retain both buffer prints, the actual stderr marker and the saved bytes.
   Linux SIGINT failures remain in [its initial full record](linux-attempt1.json.gz);
   no final Linux SIGINT validation is claimed.

The SIGINT driver uses terminal input with echo/output processing disabled.
macOS recovery succeeds but writes `\n?\n` to stderr; the page specifies the
marker on stdout. GNU recovery succeeds but writes `\n?\n` to stdout, differing
from the strict `?\n` transcript. The latter still needs normative disposition;
this work does not establish that every additional terminal newline is a vendor
violation. Neither result is promoted into the passing subset.

## Readiness correction and broader regressions

A later [Linux run](linux-signal-sync-attempt.json.gz) exposed two SIGHUP
transcripts with a duplicated readiness print (332 pass, two fail). Waiting for
bytes alone allowed the signal to arrive before the print operation completed.
The driver now requires a subsequent ed shell-escape helper to create a private
readiness marker. This explicitly moves the fixture past the print command;
SIGHUP during a stdio operation remains outside the qualified timing boundary.
The [native gate check](native-signal-gate.json.gz) passes 18 additional cases
(three runs of both SIGHUP actions in each direct/string/file mode).
The final native subset also passes 334 assertions. Earlier passing snapshots
remain [native-before-ready](native-before-ready.json.gz) and the earlier Linux
records; they are not relabeled as validation of this last correction.

The [native runtime log](native-runtime.log.gz) records 3949 pass and one
process-cleanup timeout in the caught-action/subshell stdin fixture. The
subsequent `test-pty` stage did not run in that combined invocation. A
[separate native PTY run](native-pty.log.gz) fails the existing terminal handoff
failure-injection fixture: a five-second timeout, process-snapshot cleanup
deadline, and an EPERM group-kill diagnostic. The reported leader is absent on
a subsequent process query. These are retained observations, not diagnosed
production defects or passes. No new test relaxes the existing deadlines.

The first attempted final Linux container creation returned HTTP 500 before
any tests started ([daemon failure](docker-final-create-failure.log.gz)). This
is a setup failure, distinct from the utility assertions and earlier Linux
passes. Both ordinary Docker version negotiation and an explicit API 1.43 version query
also return HTTP 500. Final Linux validation is unavailable until the daemon is
healthy; no automatic daemon restart or retry-to-green is performed.

## Boundaries retained

SIGHUP cwd/HOME recovery supplies the requested bounded signal capability for
`U-040/ed-buffer-temp-signal`. It does not resolve temporary backing-store
allocation/write failures, buffer maxima, SIGINT streams or all recovery timing.
The current ownership overlay keeps the exact retained condition with CSH-074;
CSH-064 evidence is unchanged. Utility vendors retain implementation ownership.
Each normative heading has a witness list or explicit remaining disposition in
[the clause map](../../../tests/host_language_contracts.json). Full acceptance
of CSH-074 remains open; this implementation is ready for review as a bounded
qualification increment, not ticket closure.
