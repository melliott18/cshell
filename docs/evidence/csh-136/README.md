# CSH-136 shared CI repair and integration evidence

Original failures remain retained, including complete GitHub job output:

- `pr245-native.log.gz`: run 42504985060, job 128805568939, four `id/groups` failures. The invoking process has 16 supplementary groups while Apple id reports 17 directory memberships.
- `pr273-native.log.gz`: run 45049112240, job 137290080585, the same group-contract mismatch.
- `pr273-docker.log.gz`: run 45049112240, job 137290080637, the full filesystem harness is incorrectly invoked as root during controlled identity qualification (543 failures and 83 errors).
- `pr273-services.log.gz`: run 45049112240, job 137290080672, host package discovery times out before the intended simulated interruption.

The fixes preserve strict expected output, credential and cleanup checks. New validation and integration acceptance will be recorded separately from these historical failures.

## Fresh combined native validation

Combined source `73c284a37f0d39c873c3aacb670a83f236a01ae5` includes the complete filesystem stack, CSH-129 ed capture fix and CSH-136 CI repairs. `combined-source.json` identifies changed source/build inputs, and each JSON report retains the full source identity. The native provider manifest records selected executable and source hashes.

`PATH="$PWD/build/prerequisites:$PATH" make test-host-profile test-host-languages` exits 0: 16,179 filesystem assertions, 1,162 general host assertions, 1,089 language assertions, 980 permission assertions, all zero failures; 268 filesystem and 13 ownership harness tests pass. The language regression suite and all three public/direct SIGINT witnesses also pass. Cleanup is checked in the retained records. Existing unavailable text-capacity partitions remain explicitly unavailable.

The initial local permission-harness attempt retained one control failure and one timeout error. These are preserved in `native-permissions-tests.log.gz`; the later complete native profile passes the same permission harness and all public permission cases. No historical failure is relabeled passing.

The unchanged CSH-134 evidence verifier was independently rerun at original revision `e22f8c832c68952c9edd59ccaedfac7b5f88b292` and passed both platform manifests, predecessor expectations and stock failure identities. Running it against changed integration inputs is not a valid historical source-identity check.
