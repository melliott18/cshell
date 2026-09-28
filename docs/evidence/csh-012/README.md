# CSH-012 reconciliation artifacts

These artifacts support the [post-integration review](../../evidence-reconciliation.md)
at `8ffb99e73cfd21bb1b5ad66829544350f78b69ae`.

- `runs.json`: exact native commands, UTC start/end times, return codes and logs.
- `build.log.gz`, `execution.log.gz`, `lookup.log.gz`, `jobs-signals.log.gz`,
  `harness.log.gz`: unmodified native command output, compressed with mtime 0.
- `native-identity.json`: CSH-058's identity collector run in the clean source
  archive, augmented with hashes of every built executable under `build/`.
  Source revision is explicitly supplied because the archive has no `.git`.
- `case-selection.json`: exact structural comparison of the 207 selected cases
  against the generated full runtime suite and original CSH-050 case names.
- `hosted-main.json`: GitHub metadata snapshot, not a claim that an in-progress
  job passed and not a substitute for executable identities.
- `reconciliation.json`: requirement/ownership and historical artifact checks.
- `artifacts.json`: hashes of this review's retained artifacts, excluding itself.

Reproduce the native scope in a clean archive of the revision above with
`make -j4`, `make test-execution-evidence`, the strict lookup command in
`runs.json`, `make test-jobs-signals` and `make test-harness`, in that order.
Generate `build/tests/runtime.json` for the structural comparison without
claiming that generation executes its 3,341 cases. Helper paths change generated
suite hashes between archive locations. No fixture, deadline or oracle changed.
