# CSH-064 cleanup repair and scoped acceptance

The [acceptance review](../csh-064-acceptance/README.md) correctly retained a P2
probe cleanup defect. This repair satisfies that added gate without erasing the
failure or weakening any utility assertion. The earlier four criteria retain
their original evidence; the [ticket](../../tickets/CSH-064-host-platform-external-prerequisites.md)
owns integration and final acceptance status.

## Repair

`tests/host_platform_probe.py:command` is now the single Linux watchdog for its
wrapper and selected utility. It starts an owned process group and temporarily
enables Linux child-subreaper mode. The credential wrapper inherits the group
and has no competing inner timeout. On completion or timeout, the privileged
runner kills the group, waits for the wrapper, and reaps adopted descendants by
that group ID. It never uses a wait-for-any-child operation. Cleanup has its own
two-second bound; errors force a failure record, and the prior subreaper setting
is restored. Timed-out commands still report status null and timeout_seconds 5.

The scope is the inherited process tree created by this probe, including the
nested selected utility and its ordinary forks. This is not a sandbox for
hostile programs that deliberately escape the probe's process group. Real
accounts, protected mounts and device contents are unchanged.

## Regression

`tests/host_probe_timeout.py` uses the actual `_chmod-child` entry point, drops
to UID/GID 10002 with empty groups, and runs only private selected executables:

| Case | Original source | Fixed source |
| --- | --- | --- |
| Slow selected utility | FAIL: utility remains after timeout | PASS: strict timeout and owned PID fully reaped |
| Slow utility with forked child | FAIL: both PIDs remain | PASS: strict timeout and both PIDs fully reaped |
| Ordinary completion | PASS | PASS: bytes/status preserved |

Each case checks a maximum eight-second return bound and keeps a separate owned
but unrelated child alive to ensure cleanup does not kill or reap other work.
The test checks `/proc/PID` absence, not only signalability or absence of live
states; a zombie is not counted as fully reaped. The before run explicitly kills
its survivors after recording failure. Exit 1 remains a failed regression run.

The exact same regression script is used before and after. The before source
is original PR head `c0e61ef` plus that regression, with source SHA-256
`e956e07faa039845f721651f149a7bed89839282e94e5a5b7a36270111704c18`.
The fixed source is based on `c8c1c91` and the reconciliation, with source SHA-256
`4e24b19eb1b088b6b8041a7f6e2a37bbb9f67f112d060ea6678581e939c3d694`.
The intervening CSH-050 fixture repair is independent; the nested timeout
regression calls only this probe. No C is changed by this repair.

## Validation

| Record | Result |
| --- | --- |
| `timeout-before.json` | One pass, two failures; original nested watchdog defect retained. |
| `timeout-after.json` | Three passes, no owned survivors or cleanup errors; unrelated child survives each case. |
| `timeout-python311.json` | The same three regression cases pass on the default Debian 12 / Python 3.11.2 runtime. |
| `overlay.json` | Eight passes with the selected qualified Linux PATH. |
| `bind.json` | Three passes and **five failures** on fakeowner, unchanged socket metadata and cross-user chmod semantics. |
| `native-integration.log.gz` | 3905 runtime assertions, 30 jobs PTY + 32 runtime PTY + notification/fault checks, and 86 harness tests pass. |
| `linux-integration.log.gz` | The same runtime/terminal/harness checks pass, followed by the three timeout regressions. |

The final regression, overlay and bind records share the final source digest.
Identity records name the OS, Python, compiler and source inputs. The container
uses the previously retained CSH-063 sid image, with this checkout's build files,
src, include, tests and tools copied into `/work` and built before testing.
`commands.json` preserves exit-status distinctions, including the failed baseline
and failed bind probe. The original CSH-064 qualification and review artifacts
are unchanged. Full qualification, mapped-namespace integration and sanitizer
results are not newly claimed here; their historical scopes remain identified.
No C changed, so this repair requires no new ASan/UBSan result.

The new explicit target is included in the existing root Docker CI job:

```sh
# Inside a disposable Linux root container:
make test-host-probe-timeout
# Writes build/tests/host-probe-timeout.json; no account modification.
```

The ordinary checks are:

```sh
make -j4 cshell host-profile
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty test-harness
python3 tests/host_platform_probe.py --fixture-root /tmp \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" --record /tmp/overlay.json
```

Run the focused probe only as disposable Linux root. An explicitly supplied
private fakeowner directory can replace `/tmp` to reproduce the retained
platform failures. `artifacts.json` hashes the evidence; `audit.py` verifies
identities, before/after assertions and integration summaries.

## Acceptance boundary

The ticket's original scope says to **qualify or individually retain** unavailable
external conditions. The supplied mapped namespace, independent fakeowner
investigation, complete retained records, prerequisite inventory and this cleanup
repair fulfill that scope. Those conditions do not require a fabricated passing
vendor result or unavailable Darwin/hardware environment before scoped closure.

Thirty external conditions retain sources, actual identities, reasons,
qualification provenance and separate vendor/platform implementation owners.
Their required capabilities remain in the original inventory. Future work must
supply a concrete new capability and reference those records. Acceptance neither
qualifies failed profiles nor promotes any parent utility or the CSH-012 gate.
