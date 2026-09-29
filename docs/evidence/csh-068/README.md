# CSH-068 contract ownership completion

CSH-068 satisfies its final criterion through explicit individual transfers,
not by declaring the full host qualified. The [current manifest](../../../tests/host_contracts.json)
assigns 101 external utility contracts to [CSH-070–078](../../host-system-inventory.md#current-contract-ownership),
30 stable residual IDs to the same narrower owners and eight conditional
prerequisite reports individually. [Published issues](issues.json) provide open
implementation owners. The utility/vendor implementation owners are unchanged.

## Validation

- `make test-host-inventory`: complete inventory/Markdown ownership check and
  10 regression tests pass. Negative tests cover dropped and duplicated utility
  contracts/residuals, omitted prerequisites, closed owners and stale Markdown.
  Report tests verify evidence preservation and strict setup-failure attribution.
- `make -j4 test-host-profile`: native macOS 14.8.7 arm64 passes **1162 assertions,
  zero failures, zero gaps**. [Full JSON](native-profile.json.gz) and
  [log](native-profile.log.gz) retain identities, selected PATH, capabilities,
  limits, 30 stable conditions and conditional prerequisites.
- `docker build -t cshell-csh068-test .`, then
  `docker run --rm --init cshell-csh068-test make -j4 test-host-profile`:
  Debian bookworm arm64, ordinary UID 10001, passes **1162 assertions, zero
  failures, zero gaps**. [Full JSON](docker-profile.json.gz) and
  [log](docker-profile.log.gz) retain the exact identities and source input hashes.
  The actual evidence-capture run also mounted this directory at `/evidence`
  and copied the resulting JSON and provider inventory out of the container.
- [Normative review](normative-review.json): freshly retrieved official utility
  index has exactly the retained 155 pages and identical index hash; independent
  §1.6/§1.7 review agrees with all base exec exemptions, including the kill
  exception. The existing per-page applicability decisions retain 111 base
  names, 45 conditional names, 101 exec-required names and 15 special builtins.
  No list was derived from the harness's selected HOSTS subset.
- [Requirement ownership audit](ownership-audit.json): forward/reverse
  requirement links agree; 797 historical artifact entries checked with no
  unexplained drift. `git diff --check` passes.
- `python3 docs/evidence/csh-068/verify.py` checks retained hashes, profile totals,
  emitted owners, complete ownership and all local links in changed Markdown.

The first Docker attempt failed before qualification because the existing image
excluded the documentation needed by the new inventory test. Its
[diagnostic log](docker-missing-docs.log.gz) is retained as a failed development
attempt. Dockerfile and `.dockerignore` now include only the required ledger,
tickets and immutable inventory/prerequisite inputs. The rebuilt image passes;
no failed attempt is relabeled as passing.

The native profile precedes the Docker-input adjustment and a checker-only
missing-file guard; its embedded source hashes identify that exact snapshot.
The final inventory regression check passes after those edits. Docker's passing
profile includes the guard and Docker-input repair. Later ticket issue links and
validation prose do not change utility behavior. No production C changed and no
new sanitizer, privileged ACL, physical-terminal or full runtime result is claimed.

## Provider inventory and reproduction

[Native providers](providers-native.json) and [Docker providers](providers-docker.json)
are fresh read-only observations from the retained `provider-inventory.py`:

```sh
python3 docs/evidence/csh-012/closure-5b56328/provider-inventory.py \
  "$PWD/build/host-profile/bin"
```

Run the same command in the built container with `/work/build/host-profile/bin`.
Each record contains standard `getconf PATH` and the selected qualified PATH,
path/realpath/hash for every indexed utility and `[`, platform, credentials and
package observations. Presence does not establish behavior; the old provider
ledger retains its original measured snapshots. No scheduling, mail, print or
account-changing utility was invoked by the inventory.

CSH-064 remains done for its bounded work and repaired probe cleanup. Its
[exact prerequisites](../../evidence/csh-064/prerequisites.json), strict failed
profiles, missing capabilities and vendor identities are retained without edits.
The full utility contracts remain open in CSH-070–078; the selected profile
results above do not qualify those contracts or the complete host system.
