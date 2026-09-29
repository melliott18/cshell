# CSH-012 closure evidence

This supplements the immutable [c8c1c91 review artifacts](../acceptance-c8c1c91/README.md).
The closure edits start at `5b56328143adc72f48f8af581b93fcb758af060e`; production,
fixture and workflow bytes remain identical to the passing c8c1c91 baseline.
[Audit decision](../../../conformance-closure.md).

| Record | Scope |
| --- | --- |
| `utility-sources.json` | Official Issue 8 index plus successful HTTPS retrieval metadata/hashes for all 155 utility pages. Certificate verification enabled. HTML remains outside the repository. Synopsis option codes are navigation aids; final classification also checks DESCRIPTION (notably ar). |
| `utility-inventory.json` | 155 indexed names plus `[`: 111 applicable names, 45 conditional names, 101 exec-required names. Fifteen special builtins are separately accounted by the linked existing clause maps. No executable presence is promoted to semantic qualification. |
| `provider-inventory.py`, `providers-native.json`, `providers-docker.json` | Read-only PATH/executable inventory, hashes and actual OS/compiler/libc/package/credential identities. Missing names are retained. No service or state-changing utility is invoked. |
| `docker-image.json` | Existing image ID, tags, creation time and architecture. This is availability inspection, not a fresh behavioral build. |
| `ci-36512726060.json`, `ci-36512740736.json`, `ci-job-*.log.gz` | Complete subsequent push/PR job snapshots at 5b56328 and raw logs. Push Docker fails context_fixture WNOWAIT; Ubuntu/macOS pass. PR Ubuntu/Docker pass; macOS is cancelled. Skipped later stages and cancellation are not passes. |
| `defect-dispositions.json` | Eleven observations, exact available records/hashes/identities, missing-detail declarations, strict regression paths/bounds and audit-only acceptance with CSH-069 recurrence ownership. |
| `verify.py`, `verification.json` | Inventory cardinality/classification, evidence hashes, source/fixture/workflow equality, Markdown link/anchor and ownership consistency checks. |
| `artifacts.json` | Byte/SHA-256 inventory of this new directory, excluding itself. Historical manifests are not rewritten. |

The native provider command was:

```sh
python3 docs/evidence/csh-012/closure-5b56328/provider-inventory.py /absolute/built-source/build/host-profile/bin
```

Docker used the immutable image ID in docker-image.json, `--rm --init --network
none --read-only`, a read-only mount of this directory at `/evidence`, entrypoint
`python3`, and `/evidence/provider-inventory.py /work/build/host-profile/bin`.
The existing Docker image and native build directory were inspected without
changing them. Native standard PATH is `/usr/bin:/bin:/usr/sbin:/sbin`; Linux is
`/bin:/usr/bin`. Qualified PATH prepends the recorded profile directory.
The provider collector performs filesystem lookup/hashing and harmless version
queries only; it does not execute the inventory utilities for their contracts.

The old all-green CI baseline and later failed/cancelled outcomes remain separate.
No retry-to-green or new runtime qualification is claimed by this closure.
CSH-012 records complete accounting while CSH-064–069 retain open work.
