# CSH-075 fallback, resource and timing extension

The [clause map](../../../host-execution-evidence.md#fallback-resource-and-timing-extension)
defines this extension's exact boundary. The parent evidence directory is unchanged.
This is additional native evidence; it does not close CSH-075 or waive its
required provider failures.

From the `test/CSH-075-host-execution-processes` worktree:

```sh
make test-host-inventory test-host-execution-edges
python3 -m unittest discover -s tests -p test_host_harness.py
make test-host-profile HOST_EXECUTION_SUBSET=tests/host_execution_subset_darwin.json
```

The combined profile exited 0 on macOS 14.8.7 arm64:

| Component | Passed | Failed / gaps |
| --- | ---: | --- |
| Existing host profile | 1162 | 0 / 0 |
| Declared execution subset | 242 | 0 |
| Fallback/resource/timing extension | 80 | 0 |

Inventory accounting and ten ownership tests passed, along with eleven execution
harness regressions and eighteen existing host-harness tests. Native Clang rebuilt
the helper without warnings. `runs.json` records each run's actual source digest;
the three profile records have the same digest. The JSON files contain exact
provider and helper identities, invocations or source-defined workload IDs,
stream bytes, statuses, effects, timing measurements and bounds. OS build identity
is retained in `package_environment`.

The extension comprises 36 external `/bin/sh` and fallback assertions, 16 binary
stdin handoff assertions, 12 bounded timing assertions, 12 exec-error/fallback
assertions and four descriptor-exhaustion/recovery assertions. Timing expectations
come from monotonic clocks and getrusage; a fabricated all-zero timing report
cannot satisfy a CPU-workload witness. The helper waits for its CPU child before
measuring accumulated usage. All temporary files and opened descriptors are owned
by the fixture and cleaned up.

`docker info` returned HTTP 500 from the configured engine. This is an unavailable
validation environment, not a passing Linux run. The previous Linux evidence
retains its prior boundary and does not validate the new extension. No Docker
restart or host package installation was performed. The exact capability boundary
remains in each result's `unqualified` condition map.

Memory exhaustion, production loader-stage identification, env internal-exec
E2BIG, universal duration limits and complete external-shell semantics remain
unqualified. The existing getconf, timeout short-option and Linux renice failures
are unchanged. All remain assigned to CSH-075 and the selected implementation
vendors as recorded in the ticket and current ownership manifest.
