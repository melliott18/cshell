# CSH-071: Qualify host predicates, permissions and identities

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-052, CSH-056
- Branch: test/CSH-071-host-permissions-identities
- Issue: [#143](https://github.com/melliott18/cshell/issues/143)

## Goal

Qualify host predicates, permissions and identities for the selected POSIX.1-2024 base profile. This is an
individual-contract transfer from [CSH-068](CSH-068-host-system-contract-inventory.md),
not a new platform milestone. The contracts below remain open.

## Scope

Supply disposable controlled credentials, privileged Darwin ACLs, and measured filesystem/namespace implementations; require actual read/write/execute controls alongside predicates. Preserve false grants, rejected grants, socket stat EINVAL and non-owner chmod failures independently.

Each row owns the complete applicable normative page (all behavior sections),
including [U-034](../posix-utilities.md#u-034) exec accessibility and
[U-040](../posix-utilities.md#u-040) common defaults. Optional shading retains
the decisions in the [inventory](../host-system-inventory.md); executable
presence and selected passing witnesses do not qualify a complete contract.

| Utility / normative page | Provider identities and missing contracts |
| --- | --- |
| [`test`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) | `/bin/test` / `/bin/test`; [retained provider/contract row](../host-system-inventory.md#utility-test). Full applicable behavior remains unqualified. |
| [`[`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html) | `/bin/[` / `/bin/[`; [retained provider/contract row](../host-system-inventory.md#utility-bracket). Full applicable behavior remains unqualified. |
| [`chmod`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html) | `/bin/chmod` / `/bin/chmod`; [retained provider/contract row](../host-system-inventory.md#utility-chmod). Full applicable behavior remains unqualified. |
| [`chgrp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chgrp.html) | `/usr/bin/chgrp` / `/bin/chgrp`; [retained provider/contract row](../host-system-inventory.md#utility-chgrp). Full applicable behavior remains unqualified. |
| [`chown`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chown.html) | `/usr/sbin/chown` / `/bin/chown`; [retained provider/contract row](../host-system-inventory.md#utility-chown). Full applicable behavior remains unqualified. |
| [`id`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/id.html) | `/usr/bin/id` / `/bin/id`; [retained provider/contract row](../host-system-inventory.md#utility-id). Full applicable behavior remains unqualified. |
| [`logname`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/logname.html) | `/usr/bin/logname` / `/bin/logname`; [retained provider/contract row](../host-system-inventory.md#utility-logname). Full applicable behavior remains unqualified. |
| [`newgrp`](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/newgrp.html) | `/usr/bin/newgrp` / `/bin/newgrp`; [retained provider/contract row](../host-system-inventory.md#utility-newgrp). Full applicable behavior remains unqualified. |

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
| `U-037/ACLs` | A changed test/bracket/libc vendor implementation or an additional ACL-capable filesystem, followed by strict predicates and independent read/write/execute controls. |
| `U-037/Darwin-ACLs` | A supplied disposable root-controlled Darwin environment for ordered allow/deny ACL entries, inheritance and controlled identities. |
| `U-037/unequal-identities` | A further credential mapping or changed vendor implementation; retain false and rejected grants under the supplied 0:0:1,1:20001:65535 maps. |
| `U-037/fakeowner-socket-type` | A changed fakeowner/filesystem implementation with successful socket stat metadata and strict test/bracket predicates plus actual AF_UNIX transfer. |
| `U-040/fakeowner-chmod` | A changed fakeowner/filesystem implementation enforcing non-owner chmod denial under measured IDs and capabilities, for syscall and selected utility. |
| `U-037/device-namespaces` | A disposable namespace allowed to create private device nodes, or an explicitly supplied stat-only witness. No real device I/O. |
| `U-040/chmod-ACL-identity-filesystem` | Additional ACL/identity/filesystem permission semantics with expected metadata and independently observed effects. |

Conditional prerequisite reports also owned here: `U-037/controlled-environment`, `U-037/permission-denial`, `U-037/block-device`.

## Acceptance criteria

- [ ] Select each required exec-accessible provider, supply missing packages/services,
  and retain exact PATH, realpath, executable hash, package and environment identity.
- [ ] Map every applicable page section and common default to clause-derived
  assertions or an individually justified disposition; repair required-contract
  failures. Selected examples alone do not complete a utility contract.
- [ ] Resolve each assigned retained condition with its required capability and
  strict evidence, or transfer that individual condition to a concrete open owner.
  Preserve vendor ownership, setup failures and failed assertions separately.
- [ ] Verify public cshell dispatch and direct exec access, exact output/status and
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

## Initial implementation snapshot

Implemented the bounded [predicate, permission and identity suite](../host-permissions-identities.md)
and [retained evidence](../evidence/csh-071/README.md) on the branch above in a
separate managed worktree. The suite inventories all eight providers, tests direct
exec and all three public cshell input modes, and independently observes modes,
ownership, credentials, actual permission operations and session state.

The opt-in profile now supplies an Issue 8 test/bracket adapter for locale-aware
`<` and `>`; other primaries continue to use the inventoried GNU provider.
`make test-host-permissions` is part of `make test-host-profile`. Linux controlled
credential tests are wired into the existing CI profile. Clause maps and the
current manifest record partial qualification; no residual is marked resolved.

Controlled Debian passes 1,072 new and 2,281 existing host assertions. The final
native selected run has 968 passes and 12 process timeout/cleanup failures and is
not qualified. Strict extra reproducers retain GNU chmod original-X failures and
newgrp numeric-group/failure-before-shell failures. The adapter passes 44 focused
ASan/UBSan assertions; final Linux harness controls pass. See the evidence ledger
for exact snapshots, commands, packages, effects, failed attempts and integration
results.

Status remains **in-progress**. The user confirmed that no disposable privileged
Darwin environment is available. Full page contracts, all original residual
conditions, and the new vendor failures retain this concrete open owner; no
completion is inferred from selected passing assertions. CSH-064 remains done
for its original bounded capability work and cleanup repair.

## Predicate, ACL, credential and ownership follow-up

[Follow-up evidence](../evidence/csh-071-acl-qualification/README.md) qualifies the
changed adapter's effective-ID r/w/x checks. Native owner ACL ordering/inheritance
and independent operations pass 496 assertions, also under ASan/UBSan. A fresh
native profile passes 980 permission assertions and 1,162 existing host assertions.
Hosted Linux passes all 2,260 strict unequal-ID ACL/host assertions, 22 focused
credential/non-owner assertions and 16 ordinary ownership assertions. No failed
grant/denial is allowed in these declared subsets.

The CI workflow supplies a traversable disposable source tree and existing
accounts rather than modifying any account database. Its privileged Darwin job
remains queued, so that boundary is still unqualified. Earlier local Docker and
process-cleanup failures and vendor profiles remain unchanged in the original
evidence directory. The full ticket remains open for its individually recorded
page, alternate namespace/filesystem, fakeowner and session/vendor obligations.

## Reproduced failure resolutions

[Resolution evidence](../evidence/csh-071-resolutions/README.md) records the
selected chmod replacement (124 checks on native and Linux; native ASan/UBSan),
newgrp numeric/unknown-name dispatch repairs (24 Linux session checks, also with
adapter ASan/UBSan), and all 2,281 strict host assertions passing in the original
remapped namespace with parent-supplied stat-only device nodes. The namespace's
own mknod denial remains measured and is not relabeled as success.

The hosted Darwin controlled run failed its Python account-membership oracle;
the child now reads libc process groups separately. Its corrected hosted rerun
is queued, so privileged Darwin is not yet qualified. Native runtime passes
3,950 checks; Linux runtime/PTY passes 4,015 summarized assertions. A fresh native
permission profile has 979 passes and one timeout/reaping failure, retained as
failed. Fakeowner implementation repairs, authentication/login-service fixtures,
and the remaining individually listed full-page obligations stay open here.
