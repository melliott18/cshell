# CSH-012 integrated evidence reconciliation

Source: `07ee1cb26ffcec0470977d03789ce0ebb156603a`. Collected 2026-09-29 UTC;
see the [review and acceptance decisions](../../../evidence-reconciliation-current.md).
This directory supplements the older parent-directory snapshot without replacing
its artifacts. No runtime, fixture, deadline or expected result changed.

## Contents

- `runs.json` and six `*.log.gz` files: serial native commands, UTC start/end,
  archive path, environment overrides, return codes and raw combined output.
  Gzip uses mtime zero. All commands returned zero.
- `native-identity.json`: CSH-058's identity collector from the clean archive,
  augmented with hashes of built executables. It records source/binary/helper
  and generated-suite identities, normal flags, OS/compiler/Python and relevant
  inherited environment. No new sanitizer or reference-shell run is claimed.
- `native-host-profile.json.gz`: fresh native result, including exact utility
  identities, 1,162 passing assertions and 30 separately retained limitations.
- `case-selection.json`: the 883 execution and 207 trap/exit definitions have
  unique names and exactly equal their entries in the executed 3,905-case full
  runtime suite. These overlapping scopes must not be added as unique coverage.
- `reconciliation.json`: all 131 rows, 416 forward/reverse pairs, ticket statuses,
  primary allocations and 640 artifact entries from 21 historical inventories.
  638 entries match exactly; two current README versions differ as explained below.
- `document-drift.json`: exact old/current hashes, byte counts, historical Git
  revisions and diffs for the two changed READMEs. The CSH-056 link was corrected;
  the CSH-057-pty-fix loaded-run explanation was withdrawn. Neither old manifest
  is rewritten. `audit.py` validates these exact differences, not a blanket waiver.
- `host-artifact-audit.json`: output of CSH-063's existing auditor against the
  reviewed source. It validates source/result/owner accounting without rerunning
  the retained Linux strict failures or promoting them to passes.
- `hosted-current.json`, `hosted-green.json`, `hosted-cancelled.json`: GitHub
  job/step/source snapshots with retrieval times. Pending and cancelled jobs
  remain distinct from successful jobs. They do not supply executable hashes.
- `ci-source-comparison.json`: input differences from the separately identified
  older green run; unchanged runtime paths do not imply an identical host workload.
- `issues-before.json`, `issues-after.json`: lifecycle snapshots. CSH-046 #78
  is synchronized to its already-integrated `done` disposition; CSH-012 #13
  and CSH-050 #82 remain open, as does CSH-064 #127.
- `artifacts.json`: hashes of this directory's retained files, excluding itself.
- `validation.json`: changed-document link/anchor, Python/JSON syntax and diff
  checks; confirms no runtime, fixture, build or CI file changed.

The archive extraction emitted `tar: Failed to set default locale`, returned
zero and yielded a successful independent build. The raw test outputs retain
all actual outcomes; no output normalization or retry-to-green was used.

## Reproduce

From the repository, with Python 3 and the build requirements in the README:

```sh
python3 docs/evidence/csh-012/integrated-07ee1cb/run-native.py
python3 docs/evidence/csh-012/integrated-07ee1cb/audit.py
python3 docs/evidence/csh-063/audit.py
```

The native script archives the fixed source revision, creates a fresh build
directory and writes results to a new temporary output directory. An explicit
`--output /path/to/empty-directory` is also supported. It refuses a nonempty
output directory to preserve historical artifacts. It runs the same six command
groups as `runs.json`; normal fixture environments and limits remain unchanged.
Generated-suite hashes vary with absolute helper paths. The archive and results
are retained for inspection after completion.

The inventory auditor reads the checkout where it lives. Reproduce the recorded
ownership/lifecycle result from this reconciliation's documentation revision;
future ticket changes legitimately change that part of its output. It reads
Git history to verify the two old README blobs and checks retained bytes, not
fresh behavior or completeness against normative sources.
