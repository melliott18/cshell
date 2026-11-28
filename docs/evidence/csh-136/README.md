# CSH-136 shared CI repair and integration evidence

Original failures remain retained, including complete GitHub job output:

- `pr245-native.log.gz`: run 42504985060, job 128805568939, four `id/groups` failures. The invoking process has 16 supplementary groups while Apple id reports 17 directory memberships.
- `pr273-native.log.gz`: run 45049112240, job 137290080585, the same group-contract mismatch.
- `pr273-docker.log.gz`: run 45049112240, job 137290080637, the full filesystem harness is incorrectly invoked as root during controlled identity qualification (543 failures and 83 errors).
- `pr273-services.log.gz`: run 45049112240, job 137290080672, host package discovery times out before the intended simulated interruption.

The fixes preserve strict expected output, credential and cleanup checks. New validation and integration acceptance will be recorded separately from these historical failures.
