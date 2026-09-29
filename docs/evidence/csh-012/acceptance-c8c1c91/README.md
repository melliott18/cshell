# CSH-012 acceptance-review evidence at c8c1c91

Source: `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`. Review and limitations:
[acceptance review](../../../conformance-acceptance-review.md).
No production changes, compliance claim or rerun-to-green classification.

| Artifact | Meaning |
| --- | --- |
| `runs.json`, `native-build.log.gz`, `native-full.log.gz` | Exact commands and intervals for a clean `git archive` build and complete normal native validation; both return 0. |
| `native-identity.json` | Existing CSH-058 identity collector run with EVIDENCE_REVISION set to the baseline; source/compiler/platform/binary/helper identities; unavailable libSystem file query retained. |
| `native-host-profile.json.gz` | Actual selected executable identities, per-case outcomes and capability limitations, separate from stock-host gap allowances. |
| `native-platform.json` | Supplementary libSystem load-command version and bash/sh/zsh versions; no new differential validation. |
| `review-checks.py`, `review-checks.json` | Reproducible changed-document link checks, unchanged source/diagram checks and exact-baseline CI assertions. |
| `probe-contracts.py`, `contracts.json` | Twenty-five bounded review cases; 15 pass, 10 fail. The script exits 1 while required behavior is unmet. Four main-parser recovery failures and six nesting failures are owned by CSH-065/066. |
| `sources.json` | Official Issue 8 source URLs, successful HTTPS retrieval hashes and timestamps; jobs source has a retained initial timeout plus successful retry. Sources were not copied into the repository. Local paths identify temporary review copies, not durable dependencies. |
| `ci.json`, `ci-job-*.log.gz` | Final success snapshot for all three jobs of run 36507732235, with complete logs. |
| `ownership-audit.json` | Reuses the retained `integrated-07ee1cb/audit.py` against this review tree; 131 families, 115 applicable, 443 matching ownership pairs. 731 existing artifact entries: 729 exact, two previously explained README corrections, zero unexplained differences. This inventory is not a conformance verifier. |
| `artifacts.json` | SHA-256/byte inventory of this directory after collection, excluding itself. |

Native execution used a separate temporary source archive with no user checkout
build outputs. `make -j4` followed by `make test test-pty test-host-profile
test-harness` ran without environment overrides. Identity collection occurred
after the build/test and before review probes; source files did not change.
Each pipe probe uses an owned temporary directory and the source's unchanged
`smoke.capture` runner with five-second/65,536-byte bounds and session cleanup.
The PTY probe uses the same terminal helper and stops on the premature close.
Expected diagnostics use a nonempty predicate in pipe cases and the exact
project diagnostic in the PTY transcript; status and subsequent output remain
strict. No probe is automatically added to a passing default suite.

To reproduce, build a clean archive of the baseline, then run:

```sh
python3 docs/evidence/csh-012/acceptance-c8c1c91/probe-contracts.py /absolute/built-source /absolute/contracts.json
python3 docs/evidence/csh-012/integrated-07ee1cb/audit.py
```

The first command is expected to **report failures**, not validate conformance.
The second reads the current review tree; its live artifact count can grow after
this snapshot and does not change the historical count above.
