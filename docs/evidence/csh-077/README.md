# CSH-077 all-attempt evidence

This evidence qualifies the [declared terminal subset](../../host-terminal-contracts.md),
not complete utility pages or physical hardware. Full residual ownership is
[CSH-081 / #159](../../tickets/CSH-081-host-terminal-residual-contracts.md).
Earlier development records called that proposed owner CSH-079; concurrent
allocation was discovered before review and the current manifest uses CSH-081.
Historical run JSON is not rewritten to change that name.

## Final commands and outcomes

| Environment / command | Outcome / retained evidence |
| --- | --- |
| Native macOS `make test-host-profile` | 640 terminal assertions, 6 harness regressions, 10 ownership regressions, and 1,162 existing host assertions pass, zero gaps. `native-terminal-final.json.gz`, `native-profile-final.json.gz`, `csh-077-native-final.log.gz`. The terminal record verifies unchanged source hashes for the whole run. |
| Docker Debian `docker build -t cshell-test:csh-077-final .`, then `docker run --name csh077-verified cshell-test:csh-077-final make test-host-profile` | Build and tests complete: same 640 / 6 / 10 / 1,162 passing counts with zero gaps in `csh-077-docker-verified.log.gz`. Build identity is sha256:7f8c2915d18ff04ec55c73b1882945dbba0d75c51fd51e23007a82cafe25096a, retained in `csh-077-docker-build-verified.log.gz`. **Final container JSON could not be retrieved**: Docker subsequently returned HTTP 500 for archive/inspect/remove. Earlier Docker raw identities/cases remain in `docker-profile-attempt-2.json.gz` and `docker-existing-profile.json.gz`; these are separate earlier runs, not substitutes for unavailable final JSON. |
| Native `CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty` | 3,950 execution witnesses, 1 notification fixture and 30 public job PTY cases pass; the existing `execute_faults --jobs-terminal` fixture times out. The overall command **fails**; later default PTY stages are not run. Full output is `csh-077-runtime.log.gz`; see below. |
| Native `CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime-pty` | Completes successfully, including the 33 trap PTY cases (`csh-077-runtime-pty.log.gz`). This does not erase the earlier fault-fixture failure. |
| `make test-host-inventory` | 156 names, 101 external contracts, 30 retained conditions and 10 accounting regressions pass (`csh-077-inventory-final.log.gz`). |
| Forced output/exit regression against pre-fix capture | Fails with missing `tail\n`; `csh-077-race-before.log.gz`. The corrected six-test harness passes (`csh-077-harness-final.log.gz`). |

Native OS/compiler/base commit/branch appear in `native-identity.json`; exact
binary/provider hashes, PATH, package/OS identities, environment, source hashes,
termios snapshots, input offsets, stdout/stderr/terminal bytes, statuses, limits,
setup failures and directory removal are in the compressed per-run JSON.
Build logs document the explicit Debian ncurses-bin/bsdextrautils installation.
No host package installation or real login database mutation was performed.

## Development attempts (all retained)

| Raw record | Passed / failed | Disposition |
| --- | --- | --- |
| native-attempt-1 | 0 / 605 | Harness session leader acquired the PTY and Darwin revoked it at leader exit; parent inspection got ENOTTY. Repaired isolation: runner owns an isolated session, commands have groups but are not session leaders. |
| native-attempt-2 | 570 / 35 | Includes real stock failures plus fixture mistakes: live window was 80 despite a 40-column terminfo entry; init/reset also configured tabs; Darwin database filename lacked required x suffix. Corrected fixtures separate plain/tab-capable terminals, set ioctl size explicitly, and use vendor-format private paths. |
| native-attempt-3 | 590 / 20 | Stock tabs relative-list, tput invalid-operand and who missing-file failures; positive who records referenced nonexistent devices and were correctly filtered by Apple. Fixed the fixture to name its actual owned PTY. |
| docker-attempt-1 | 585 / 20 | Stock mesg invalid-operand status and who missing-file success; tabs expected-width mistake. No failed assertion is a qualified result. |
| native-profile-attempt-1 | 605 / 5 | Adapters fix reproduced contracts; positive who still had the nonexistent-device fixture error. |
| native-profile-attempt-2 | 610 / 0 | Passing original subset; predates 30 added saved-state/window/multi-operand/query assertions. |
| docker-profile-attempt-1 | 605 / 5 | Incorrect fixture expectation assumed ISO-date GNU output under C locale. Actual C locale is Jan/space/day/time, now independently authored for both selected vendors. |
| native-profile-attempt-3 | 640 / 0 | Expanded subset passes, but capture still contained the latent output/exit race. |
| native-profile-attempt-4 | 639 / 1 | tabs/relative command had status 0 but empty captured terminal output. Capture could select no events, then observe a just-exited child and stop before the final drain. Forced-order regression demonstrates this mechanism; fixed by requiring exit to be observed **before** the final empty select. |
| docker-profile-attempt-2 | 640 / 0 | Expanded subset, before final race regression/source-stability check. Existing integration also passes 1,162, retained separately. |
| native-profile-attempt-5 | 640 / 0 | Capture repair passes before adding source-stability enforcement and fuller setup-error records. |
| native-terminal-final | 640 / 0 | Final source and setup records, strict full declared subset. |

Each `*.json.gz` name above is literal with the extension appended. Intermediate
build/profile logs are retained too. The two final Docker rechecks completed
successfully (`csh-077-docker-profile-final.log.gz` and
`csh-077-docker-verified.log.gz`); their post-run raw extraction was unavailable
as described above. The final source record does not promote the earlier stock
host or profile attempts into later results.

## Existing native PTY fault failure and cleanup limitation

`tests/fixtures/jobs-fault-pty.json` ran the unchanged
`build/tests/execute_faults --jobs-terminal`. It exceeded the existing 5-second
exit deadline without output. Cleanup's ps snapshot then timed out near its own
deadline; group kill reported EPERM and the leader status was -9. The relevant
helper/source and `tests/pty_harness.py` are unchanged by CSH-077. The helper uses
internal jobs APIs and fixed `/usr/bin/true`, not the four new adapters; this
excludes those adapters from that fixture's dispatch path but does **not**
establish the timeout's cause.

A remaining owned helper PID 42555 was found with PPID 1, group 42555 and Darwin
state UE. An explicit SIGKILL was sent; the same state remained in the immediate
snapshot (`native-job-fault-cleanup.json`). No unrelated process was signalled.
Cause and eventual cleanup are unresolved; this is not a passing or cleaned-up
fixture. Further job-control/platform diagnosis is outside the terminal-provider
qualification and must preserve this failure. No retry-to-green is used as its
disposition. The CSH-077 harness's own normal/flood/forked-timeout cleanup tests
pass separately.

After final Docker tests, archive/inspect/remove API calls returned HTTP 500.
`docker-artifact-retrieval.json` records the unavailable artifacts and containers
whose removal could not be confirmed (`csh077-verified`, `csh077-validation`).
The Docker service was not restarted or otherwise changed.

## Evidence integrity and limits

`artifacts.json` hashes retained files. Compressed JSON parses independently.
Physical serial behavior, full locale/signal/I/O/resource partitions and all
registered sender/recipient delivery remain unqualified under CSH-081. Private
who records are not live login sessions. Device permission metadata is not a
universal message-access proof. Passing selected cases never imply a full host
or shell compliance claim.
