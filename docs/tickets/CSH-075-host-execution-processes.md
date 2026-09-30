# CSH-075: Qualify host execution and process utilities

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-075-host-execution-processes
- Issue: [#147](https://github.com/melliott18/cshell/issues/147)

## Goal

Qualify host execution and process utilities for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Record the selected /bin/sh ENOEXEC provider independently of PATH sh; supply controlled processes, credentials, loader/resource failures and deterministic clock/timeout controls. Missing timeout remains a provider gap. Do not infer maximum sleep duration by waiting five seconds.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`env`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/env.html) | `/usr/bin/env` / `/bin/env`; [retained provider/contract row](../host-system-inventory.md#utility-env). Full applicable behavior remains unqualified. |
| [`false`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/false.html) | `/usr/bin/false` / `/bin/false`; [retained provider/contract row](../host-system-inventory.md#utility-false). Full applicable behavior remains unqualified. |
| [`getconf`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/getconf.html) | `/usr/bin/getconf` / `/bin/getconf`; [retained provider/contract row](../host-system-inventory.md#utility-getconf). Full applicable behavior remains unqualified. |
| [`kill`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/kill.html) | `/bin/kill` / `/bin/kill`; [retained provider/contract row](../host-system-inventory.md#utility-kill). Full applicable behavior remains unqualified. |
| [`nice`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nice.html) | `/usr/bin/nice` / `/bin/nice`; [retained provider/contract row](../host-system-inventory.md#utility-nice). Full applicable behavior remains unqualified. |
| [`nohup`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/nohup.html) | `/usr/bin/nohup` / `/bin/nohup`; [retained provider/contract row](../host-system-inventory.md#utility-nohup). Full applicable behavior remains unqualified. |
| [`ps`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ps.html) | `/bin/ps` / `/bin/ps`; [retained provider/contract row](../host-system-inventory.md#utility-ps). Full applicable behavior remains unqualified. |
| [`renice`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/renice.html) | `/usr/bin/renice` / `/bin/renice`; [retained provider/contract row](../host-system-inventory.md#utility-renice). Full applicable behavior remains unqualified. |
| [`sh`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html) | `/bin/sh` / `/bin/sh`; [retained provider/contract row](../host-system-inventory.md#utility-sh). Full applicable behavior remains unqualified. |
| [`sleep`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sleep.html) | `/bin/sleep` / `/bin/sleep`; [retained provider/contract row](../host-system-inventory.md#utility-sleep). Full applicable behavior remains unqualified. |
| [`time`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/time.html) | `/usr/bin/time` / **missing**; [retained provider/contract row](../host-system-inventory.md#utility-time). Full applicable behavior remains unqualified. |
| [`timeout`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/timeout.html) | **missing** / `/bin/timeout`; [retained provider/contract row](../host-system-inventory.md#utility-timeout). Full applicable behavior remains unqualified. |
| [`true`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/true.html) | `/usr/bin/true` / `/bin/true`; [retained provider/contract row](../host-system-inventory.md#utility-true). Full applicable behavior remains unqualified. |
| [`uname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uname.html) | `/usr/bin/uname` / `/bin/uname`; [retained provider/contract row](../host-system-inventory.md#utility-uname). Full applicable behavior remains unqualified. |

Providers above are the retained macOS / Debian standard-PATH observations,
not new measurements. Their hashes and qualified-PATH alternatives are in the
[immutable machine inventory](../evidence/csh-012/closure-5b56328/utility-inventory.json).
Select and record actual package/version/build identities before qualification;
missing providers require an explicit package/build choice and reproducible setup.
Selected utility/libc/platform vendors retain implementation ownership; this
ticket owns supplying and verifying the execution environment and reporting or
repairing the selected provider contract. No host installation is implied.

## Retained conditions

These exact condition IDs transfer from the [CSH-064 prerequisite ledger](../evidence/csh-064/prerequisites.json).
The [original evidence](../evidence/csh-064/README.md), including strict failed
profiles and executable/environment identities, remains unchanged.

| Condition | Required capability before further qualification |
| --- | --- |
| `U-040/true-exec-resources` | A disposable process/memory/loader fault environment for true with deterministic independently observed failure stages. |
| `U-040/false-exec-resources` | A disposable process/memory/loader fault environment for false with deterministic independently observed failure stages. |
| `U-040/kill-identities-resources` | Additional disposable credential/process-limit controls acting only on owned children. |
| `U-040/env-ARG_MAX` | A controlled environment and argv threshold/internal-exec fixture that distinguishes loader rejection from env entry. |
| `U-040/sleep-duration` | An independently bounded duration/overflow oracle that fits the fixture time budget. |
| `U-040/sh-host-semantics` | A separately scoped host shell parser/resource/locale qualification with independent oracles. |

## Acceptance criteria

- [x] Select each required exec-accessible provider, supply missing packages/services,
  and retain exact PATH, realpath, executable hash, package and environment identity.
- [ ] Map every applicable page section and common default to clause-derived
  assertions or an individually justified disposition; repair required-contract
  failures. Selected examples alone do not complete a utility contract.
- [ ] Resolve each assigned retained condition with its required capability and
  strict evidence, or transfer that individual condition to a concrete open owner.
  Preserve vendor ownership, setup failures and failed assertions separately.
- [x] Verify public cshell dispatch and direct exec access, exact output/status and
  relevant effects, with zero gap allowances for every declared qualified subset.
- [x] Update the inventory, current ownership manifest and clause maps with the
  exact qualification boundary; keep stock-host, qualified subset and full-system
  claims separate.

## Validation

Run `make test-host-inventory` to check exhaustive ownership and retained IDs.
Add focused bounded fixtures for the listed contracts, with independent normative
oracles, then run `make test-host-profile` for the supplied selected profile.
Retain native macOS and Docker/Linux results separately with commands, identities,
capabilities, limits and failures. If the needed capability is absent, report it
as unqualified; do not call an unavailable or failed profile passing. Use owned
processes and disposable files/services and verify cleanup after failure/timeout.

## Implementation notes/evidence

Implementation is in progress on `test/CSH-075-host-execution-processes` in the
separate `csh-075-host-execution` worktree. The [clause map](../host-execution-evidence.md)
and [retained runs](../evidence/csh-075/README.md) describe the delivered harness,
provider provisioning, exact subset lists, source identities and cleanup controls.

The new runner covers all 14 providers with direct exec and public cshell
string/file/stdin assertions. It independently inventories `/bin/sh`, measures
aggregate argv success/E2BIG boundaries, records post-exec descriptor-limit
failures, supplies Linux owned-process credential/limit controls, and checks
large sleep durations using a bounded, opt-in clock interposer. Linux timeout
cleanup explicitly adopts and reaps orphaned helpers. Tests protect status,
timing, duration, section accounting and unrelated-child cleanup.

Native macOS's declared execution subset passes 242 assertions; Docker/Linux's
passes 238. The existing host profiles pass 1,162 and 1,144 assertions respectively,
with zero failed assertions or gap allowances. The strict expanded profile still
fails 12 assertions on macOS and 16 on Linux: required getconf Issue 8 names,
timeout `-f`/`-p`, and Linux renice semantics. A native PTY cleanup timeout from
an earlier concurrent run is retained separately; the serial rerun passes.

**This ticket is not complete.** The two unchecked criteria remain unmet: required
provider failures are not repaired, and the six retained conditions have only the
bounded extensions listed in the clause map. No full-page or full-system claim
is made, no open contract is silently transferred, and no original failed
assertion is waived. All 14 page contracts and six conditions remain owned here;
selected utility/libc/platform vendors retain implementation ownership.


### Fallback/resource/timing extension

The [extension](../host-execution-evidence.md#fallback-resource-and-timing-extension)
adds 80 strict assertions for nine `/bin/sh` programs and their ENOEXEC dispatch,
256-byte stdin handoff through external process utilities, independently observed
exec error stages, child descriptor exhaustion/recovery, and wall/self/child CPU
timing bounds. Timeout assertions also reject completion before the requested
duration. Native results and current Linux availability are retained in the
[extension evidence](../evidence/csh-075/edges/README.md). The full-page criteria
and vendor failures above remain open; these checks do not change their scope.
