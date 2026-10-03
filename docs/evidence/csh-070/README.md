# CSH-070 formatted-output evidence

The selected providers, whole-page accounting and individual residual
boundaries are in [the contract map](../../host-formatted-output.md).
[CSH-079 / #157](../../tickets/CSH-079-formatted-output-residuals.md) owns the
remaining utility contracts, Darwin resource prerequisites and retained native
cleanup observations. No unavailable or failed configuration is called passing.

## Identity and reproduction

Base revision: `60295934db1c971a2b3aac582f88b0f766eccce2`.
The final build/test input digest is
`dc2b3476890b7819faed5645ae8ed0cc817911ebb6f095e4619e7b95244ca873`;
source dictionaries are embedded in the final native and Linux JSON records.
They hash actual uncommitted inputs as well as checked-in files. Documentation
outside the input set can be finalized after the run without altering a binary.
Each record includes realpaths, SHA-256 identities, kernel/OS, compiler, locale
inventory, catalog binaries, libc and Linux package versions. The selected
provider version is the vendored revision plus these exact adapter source hashes.

```sh
make -j4 test-host-inventory test-host-profile test-host-formatted-sanitize
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime test-pty
# If make stops before a distinct terminal stage, run that stage separately:
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-runtime-pty

docker build -t cshell-csh070 .
docker run --name csh070-profile cshell-csh070 make -j4 test-host-profile
# Use the same image/source snapshot for the sanitizer and integration commands.
```

The retained Docker run copied subsequent source corrections into its private
`/work`, then committed that disposable container as the validation image. There
are no bind-mounted test fixtures or host account changes. `commands.json`
records each attempt, setup error, status and not-run stage. The image identity
is retained in `docker-image.json`.

## Strict selected results

| Record | Result and scope |
| --- | --- |
| `native-focused.json.gz` | 351 PASS, zero failures/allowances; two explicit unqualified resource scopes. |
| `linux-focused.json.gz` | 356 PASS, zero failures/allowances for the supplied controls. Other whole-page scope remains in CSH-079. |
| `native-profile.json.gz`, `linux-profile.json.gz` | Each 1162 PASS, zero failures and zero gaps in the existing full host-profile assertion set. This is still a bounded integration profile. |
| `native-sanitize.json.gz` | 346 PASS ordinary provider assertions with ASan/UBSan. Resource/threshold probes are separately run without sanitizers. |

Every new ordinary oracle runs directly and through cshell `exec`, command
strings, script files and stdin. Expectations are authored independently;
no selected utility generates expected output. Both profiles build catalogs
from checked-in French/German messages. Raw streams, statuses, invocations and
resource/threshold parameters are retained. Separate two-case harness regressions
check strict rejection of utility failure and timeout/reaping with an unrelated
child that must survive.

## Causal before/after probes

`reproduce_before.py` extracts the original provider from the immutable base.
It adds only an entrypoint-name hook so the same resource fixture can call that
provider after setting limits. It compiles native or Linux binaries separately;
source and executable hashes are in `native-before.json` / `linux-before.json`.
The script is an evidence recorder: failed assertions are expected for this
baseline, and its process exit indicates recording completed, not qualification.

```sh
python3 docs/evidence/csh-070/reproduce_before.py --record /tmp/native-before.json
# Copy build/csh070-before and the recorder into the private Docker /work.
# Restore ownership to the container's cshell user after docker cp, then run:
python3 reproduce_before.py --run-only --record /tmp/linux-before.json
```

| Required result | Original | Fixed |
| --- | --- | --- |
| Float operand `'A` uses strtod parsing: zero accumulated value, diagnostic, status 1, continue | Reports success with character value | Exact required result on both hosts |
| Integer operand `'Aextra`: accumulated 65, diagnostic, status 1, continue | Ignores trailing text with status 0 | Exact required result on both hosts |
| 256 KiB format under measured post-startup 64 KiB stack | Linux SIGSEGV | Exact 262145 output bytes on both hosts |
| Linux libc formatting ENOMEM under 16 MiB RLIMIT_AS | Empty stdout with status 0 | Empty stdout, exact ENOMEM diagnostic, status 1 |

Native resource baseline crashes are intentionally not repeated after the
separate near-ARG_MAX Darwin exec failure. The new normal-stack runtime is not
changed; repairs are confined to the opt-in external provider.

## Measured adjacent exec boundaries

The unit for single is **payload bytes excluding NUL**, and for aggregate is
**the number of 1024-byte operands**. Every pair is largest verified success /
smallest E2BIG, including repeated endpoint checks. The exact argv[0] is retained;
path length contributes to total bytes. A 14-byte environment is `LC_ALL=C` plus
empty PAD, including terminating NULs; adding 4096 padding bytes makes 4110.

| Host / stack | Environment bytes | Single | Aggregate |
| --- | ---: | ---: | ---: |
| macOS / 8 MiB | 14 | 1048424 / 1048425 | 1014 / 1015 |
| macOS / 8 MiB | 4110 | 1044328 / 1044329 | 1010 / 1011 |
| Linux / 1 MiB | 14 | 131071 / 131072 | 253 / 254 |
| Linux / 1 MiB | 4110 | 131071 / 131072 | 249 / 250 |
| Linux / 8 MiB | 14 | 131071 / 131072 | 2030 / 2031 |
| Linux / 8 MiB | 4110 | 131071 / 131072 | 2026 / 2027 |

These numbers qualify only the recorded layouts, environments, binaries and
kernels. They are not portable maxima and do not qualify other providers.

## Failed attempts and unavailable capabilities

- The initial native build emitted format-security warnings for argument-free
  translated format strings. Calls now use literal `%s` where no formatting is
  needed; the final build has no such warnings. The initial focused runner reused
  smoke's `.home` directory and failed setup. Per-case disposable directories
  repair that fixture defect.
- The second focused attempt assumed the wrong Darwin diagnostic program name
  and failed assertions, then failed JSON serialization of bytearrays. Both
  harness defects are corrected; the raw failed log is retained. That attempt
  also entered the low-stack exec configurations before reporting failed setup.
- `native-attempt-3.json.gz` retains 349 passing assertions and four **failed**
  1 MiB-stack searches. Near-ARG_MAX execs did not terminate after timeout and
  SIGKILL. Seven owned processes from the early attempts remained in `UEs`
  state with PPID 1; their PIDs, repeat SIGKILL and final observations are retained
  in `native-low-stack-cleanup.json`. Final signal-0 checks still found all seven
  PIDs; a later ps inventory itself hung and was interrupted. This is not successful process cleanup.
  The selected Darwin profile now uses only 8 MiB; smaller stacks require a
  disposable macOS environment with reset capability, owned by CSH-079.
- The first Linux profile failed while compiling UTF-8 catalogs under LC_ALL=C;
  no qualification assertions ran. gencat now runs under the supplied UTF-8
  locale and publishes its output only after success. `linux-focused-attempt-2`
  is a distinct later passing intermediate snapshot.
- The first native full profile (`native-profile-attempt-4`) had 1161 passes
  and one failure: stty's PTY cleanup inventory command `ps -axo pid=,stat=`
  timed out after successful utility output/status. The final profile passes,
  but it does not establish a repair or cause for that prior failure.
- Native runtime integration has 3949 passes and one pipe-cleanup ps timeout in
  `caught action resets in subshell` string mode. The following PTY make stage
  was not run by that command. A separate PTY command passed the notification
  control and 30 job cases, then the terminal failure-injection fixture timed
  out without output; cleanup recorded another ps timeout and EPERM killing
  its reported group. A subsequent PID lookup found no leader at that PID.
  These failures retain unknown cause and CSH-079 recurrence ownership.
  A separately run runtime-PTY stage passed 32 cases and failed one ps cleanup
  check after terminal main-parser syntax recovery.
  The separately run runtime-PTY target passed 32 cases and failed one ps
  cleanup check after terminal main-parser syntax recovery.
- The first Linux baseline/sanitizer/integration command stopped at baseline
  compilation because docker-copied native binaries had incompatible ownership.
  Its sanitizer and integration stages were not run. A fresh disposable
  container restored only that private directory's ownership before rerunning.
- Darwin libc allocation-exhaustion instrumentation is unavailable. The Linux
  memory control is not counted as Darwin evidence. Other locale/catalog,
  format, signal/interruption and exec-layout contracts remain individually
  assigned in CSH-079, without altering immutable CSH-064 conditions/reasons.

No causal link between the native ps/PTY failures and the stuck exec processes
is asserted. No whole POSIX utility page or system is promoted by these results.

## Incomplete Linux follow-on validation

The final Linux ASan/UBSan run started but did not produce a result before the
Docker API began returning internal-server errors. The last observed processes
included sanitizer tracing children; no causal diagnosis of the engine failure
is claimed. `linux-sanitize-incomplete.log.gz` retains the available output.
The queued Linux runtime/PTY command was not observed to start, and is recorded
as not run, not passing. Only native sanitizers and the separately completed
Linux host profiles are positive qualification evidence.

`docker-cleanup.json` records the bounded attempt to stop only the owned
`cshell-csh070-extra-2` validation container. If termination could not be
confirmed, it remains an explicit cleanup limitation. The shared Docker engine
was not restarted. CSH-079 owns completion of this follow-on validation after
the environment is usable, independently of the passing selected profile.
