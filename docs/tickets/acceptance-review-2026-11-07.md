# Ticket acceptance review — 2026-11-07

Reviewed 38 tickets marked `review` against their criteria, merged source history, retained platform records and current residual ownership. Accepted 35; CSH-073, CSH-074 and CSH-079 remain in review. This records scoped completion, not full utility or POSIX conformance.

The implementation merge is `13f57750b1bbd77c97396a75721c1486983f8b53`. Every accepted implementation head is an ancestor of main. Dependency integration is complete; historical pre-integration statements in the tickets and evidence are preserved.

## Accepted tickets

| Ticket | Evidence reviewed / native and Linux results |
| --- | --- |
| [CSH-070](CSH-070-host-formatted-output.md) | [Both retained host profiles: 1,162 assertions, zero failures or gaps; formatted-output remainders owned by CSH-079.](../evidence/csh-070/README.md) |
| [CSH-072](CSH-072-host-filesystem-paths.md) | [Final cleanup records: 570 / 586 filesystem assertions; passing runtime/PTY and cleanup harness records.](../evidence/csh-072/README.md) |
| [CSH-077](CSH-077-host-terminal-utilities.md) | [Retained normal/sanitizer terminal and controlled-session evidence; fresh native 665 profile and 90 effect assertions, plus ten harness tests. Remaining contracts belong to CSH-081.](../evidence/csh-077/README.md) |
| [CSH-080](CSH-080-filesystem-remaining-contracts.md) | [Retained full filesystem profiles: 810 / 826 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-080/README.md) |
| [CSH-082](CSH-082-container-readiness.md) | [Retained restricted ARM64/AMD64 JUnit suites and nine runtime checks; runtime packaging checks also passed during integration.](../evidence/csh-082/README.md) |
| [CSH-084](CSH-084-filesystem-residual-environments.md) | [Retained full filesystem profiles: 914 / 930 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-084/README.md) |
| [CSH-085](CSH-085-filesystem-isolated-contracts.md) | [Retained full filesystem profiles: 1026 / 1042 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-085/README.md) |
| [CSH-086](CSH-086-filesystem-unsupplied-contracts.md) | [Retained full filesystem profiles: 1065 / 1081 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-086/README.md) |
| [CSH-087](CSH-087-filesystem-environment-followup.md) | [Retained full filesystem profiles: 1133 / 1149 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-087/README.md) |
| [CSH-088](CSH-088-filesystem-remaining-environments.md) | [Retained full filesystem profiles: 1197 / 1213 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-088/README.md) |
| [CSH-089](CSH-089-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1227 / 1243 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-089/README.md) |
| [CSH-090](CSH-090-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1259 / 1275 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-090/README.md) |
| [CSH-091](CSH-091-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1291 / 1307 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-091/README.md) |
| [CSH-092](CSH-092-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1395 / 1411 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-092/README.md) |
| [CSH-093](CSH-093-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1427 / 1467 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-093/README.md) |
| [CSH-094](CSH-094-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1475 / 1515 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-094/README.md) |
| [CSH-095](CSH-095-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1659 / 1699 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-095/README.md) |
| [CSH-096](CSH-096-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1819 / 1859 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-096/README.md) |
| [CSH-097](CSH-097-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 1931 / 1971 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-097/README.md) |
| [CSH-098](CSH-098-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 2187 / 2227 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-098/README.md) |
| [CSH-099](CSH-099-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 2603 / 2643 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-099/README.md) |
| [CSH-100](CSH-100-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 3115 / 3155 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-100/README.md) |
| [CSH-101](CSH-101-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 3499 / 3539 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-101/README.md) |
| [CSH-102](CSH-102-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 3863 / 3903 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-102/README.md) |
| [CSH-103](CSH-103-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 4295 / 4335 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-103/README.md) |
| [CSH-104](CSH-104-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 5735 / 5775 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-104/README.md) |
| [CSH-105](CSH-105-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 6855 / 6895 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-105/README.md) |
| [CSH-106](CSH-106-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 11207 / 11247 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-106/README.md) |
| [CSH-107](CSH-107-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 11495 / 11535 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-107/README.md) |
| [CSH-108](CSH-108-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 11735 / 11775 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-108/README.md) |
| [CSH-109](CSH-109-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 11811 / 11851 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-109/README.md) |
| [CSH-110](CSH-110-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 11927 / 11967 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-110/README.md) |
| [CSH-111](CSH-111-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 12011 / 12051 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-111/README.md) |
| [CSH-112](CSH-112-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 12091 / 12131 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-112/README.md) |
| [CSH-113](CSH-113-filesystem-environment-residuals.md) | [Retained full filesystem profiles: 12331 / 12371 passing assertions; zero selected failures; successful fixture cleanup.](../evidence/csh-113/README.md) |

## Verification and limits

- Re-read all acceptance criteria and implementation/disposition records. Verified each accepted head is integrated and none remains a current open utility-contract owner. Filesystem residuals terminate at open CSH-114; terminal/session residuals remain with CSH-081; formatted-output residuals remain with CSH-079.
- Re-read the native and Linux raw filesystem profiles for CSH-080 and CSH-084–113: all declared cases pass, cleanup succeeds, providers have hashes, and source manifests agree across platforms. All manifest digests were recomputed. Thirty of the 31 source manifests match their original PR heads exactly. The CSH-080 marker-validation record differs only in the filesystem harness test file; its runner/provider inputs match, and the current integration harness passed all 160 filesystem tests. This does not claim the old record used the later test-file bytes.
- CSH-070/072/077 raw final profiles and CSH-082 restricted-container evidence were reviewed separately. CSH-077 meets the section-map criterion through explicit individual dispositions to CSH-081; its stale unchecked box is corrected without claiming full-page qualification.
- The same-session integration checks passed native/Linux `make test test-pty test-harness`, including 3,950 runtime cases on each platform, all 160 filesystem harness tests, provider builds and runtime-container checks. The fresh terminal rerun passed 665 profile assertions, 90 effect assertions and ten harness tests.
- Ownership validation (156 names, 101 external contracts, 30 retained conditions), all 13 ownership tests, all 24 ticket tests and live identity checks pass for this acceptance update. Historical stock failures, incomplete capabilities and earlier failed attempts are preserved. No fresh replay of every historical filesystem matrix or new sanitizer qualification is claimed.

## Not accepted

- [CSH-073](CSH-073-host-text-streams.md): Complete-page and common-default coverage, plus remaining retained text/byte conditions, are still owned here. The repaired finite audits do not complete these acceptance criteria.
- [CSH-074](CSH-074-host-languages-editors.md): Complete-page coverage remains open, including further patch prompts, locale/default behavior and additional language/editor contracts. This ticket still owns those remainders.
- [CSH-079](CSH-079-formatted-output-residuals.md): The checked criteria cover a bounded investigation and individual dispositions. The ticket explicitly retains Darwin libc-internal allocation, other locale/format/signal partitions and the unresolved original low-stack observation; it is not ready for whole-ticket closure.

CSH-073 is reopened because its automatic issue closure did not satisfy its remaining acceptance criteria. The other two remain open. No acceptance is inferred from a checked box alone.

## CSH-114 integration acceptance

Accepted CSH-114 after [PR #243](https://github.com/melliott18/cshell/pull/243)
merged as `a44c1047fed654dc78bf2fdf9d81e8e80f58b930`. The earlier open-ticket
review missed the isolated implementation `52ccffa`; main still had only its
backlog document. The implementation and original full evidence are now included.

The [integration review](../evidence/csh-114/integration/README.md) verifies the
original evidence, preserved source and oracle boundaries, and fresh macOS/Linux
results: 112 assertions and 166 harness tests per platform. Ownership, ticket
tests and live registry checks pass. CSH-115 / issue #242 is now the registered
open owner of all 21 remaining utility dispositions and four retained conditions.
Closure uses CSH-114's explicit individual-disposition acceptance criterion; it
does not promote remaining contracts to qualified. Broader hosted CI was still
running or queued at acceptance; ticket-integrity CI passed.
