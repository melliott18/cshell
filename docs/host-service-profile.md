# Disposable host service qualification

CSH-078 supplies a strict **bounded profile** for `at`, `batch`, `crontab`,
`date`, `logger`, `lp`, `mailx`, `uudecode`, and `uuencode`. It does not qualify
any complete utility page or close CSH-078. The
[section/disposition map](../tests/host_service_contracts.json) accounts for all
14 behavior sections of each page, U-034 and U-040, and names 20 open residuals.
Those residuals remain owned by CSH-078; vendor implementations retain their
implementation ownership. The [current inventory](host-system-inventory.md)
and immutable CSH-064/CSH-068 evidence retain their separate meanings.

## Running the profiles

```sh
make test-host-inventory test-host-service-harness
make test-host-service-codecs       # safe native codecs/read-only date only
make test-host-profile              # includes the codec/date profile
make docker-test-host-services     # isolated Linux service execution
```

Linux native codec tests require `sharutils` and `libbsd-dev`. Both Linux and
macOS profiles build the supplied opt-in `uudecode` adapter; no host installation or service invocation occurs.
The stock-host diagnostic remains available explicitly:

```sh
python3 tests/host_services.py ./cshell --record build/tests/service-stock.json
```

That command returns nonzero for missing providers or failed assertions. In
particular, the retained macOS stock `uudecode` fails the Issue 8 `-` stdout
cookie requirement. A failing stock run is not a passing profile.

The separate service Dockerfile installs `at`, `cron`, `bsd-mailx`,
`exim4-daemon-light`, `cups-daemon`, `cups-client`, `sharutils`, `libbsd-dev` and the existing
host-profile dependencies. Package versions are resolved at image build time,
then retained in the results together with the exact image ID, executable and
source hashes. Rebuilding against newer packages requires requalification.
The Dockerfile accepts `BASE_IMAGE`; no moving tag is treated as a pinned
provider identity. The launcher resolves the built image to its immutable ID
before container creation.

## Isolation and cleanup

The launcher uses a fresh named container with `--init`, `--network none`, no
mounts, a 128-process bound and 768 MiB memory limit. It drops `SYS_TIME`,
`SYS_ADMIN` and `NET_ADMIN`. The harness verifies the dedicated image marker,
container environment, capability sets, inactive non-loopback interfaces and
absence of mounts over fixture paths before invoking any service utility.
Scheduler entries, mailboxes, CUPS configuration/backend, `/dev/log`, user
accounts and all service files exist only in that container. Exim accepts only
local delivery; no remote recipient or external printer is used.

Ordinary commands run as UID 10001 (`cshell`). UID 10002 (`recipient`) supplies
a second local mailbox. Root only sets up services and observes effects. The
fixture configures `mailx` with `sendwait` in its private system configuration
so its local transport finishes before command-group cleanup. Base sends use
`MAILRC=/dev/null` and `DEAD=/dev/null`; non-null user startup/dead-letter behavior
without UP is unspecified and is not a base qualification requirement. `atd` uses an explicitly supplied high batch-load
threshold and one-second interval; these are fixture choices, not standardized
scheduling deadlines. Cron uses real time with a 75-second observation deadline.
The date-only shared object intercepts `time` and `CLOCK_REALTIME` reads at
2024-02-29 12:34:56 UTC by default. `CSH078_CLOCK_EPOCH` supplies explicit
calendar/DST test instants. It has no clock-setting code and leaves other clocks
unchanged. Native controlled-time qualification remains unavailable.

Commands have an eight-second wall deadline, bounded CPU, 1 MiB per output
file, no core dump and 64 native/1024 service descriptors. The latter supplies
Exim's actual descriptor requirement. Daemons have owned process groups and
bounded logs. Normal/error/interrupt paths stop and reap them. Unit tests force
command timeout and excess output, verify owned descendant disappearance, and
keep an unrelated process alive. The launcher has an independent 300-second
deadline, copies records even after failure, forcibly removes its container in
`finally`, and verifies removal. A missing record, timeout, failed assertion or
cleanup failure returns nonzero. A child that cannot be reaped preserves its
output and stops the profile immediately. Interrupted runs cannot claim qualification.

`build/tests/host-services/launcher.json`, `results.json` and `run.log` retain
setup, invocation, assertion and cleanup outcomes. Logs and JSON from initial
failed fixture attempts remain in [the evidence](evidence/csh-078/README.md).

## Assertions and boundaries

Every declared utility witness exercises the inventoried executable directly,
cshell `-c`, explicit `exec`, script-file input and stdin input. The 72 logger
priority pairs and final daemon-effect checks supplement those dispatch paths.
Missing declared case prefixes cause failure. `service_case_prefixes` adds
mandatory assertions only for the guarded service environment. Native denied-write
cases require an unprivileged UID; root native runs explicitly record this
unavailable capability, while the service image supplies UID 10001. Diagnostic messages whose wording
is unspecified are checked for nonempty stderr and positive status; every actual
byte is retained. Scheduler dates/IDs and print IDs use independent structure
checks; `at -l` must use the POSIX ID-tab-date layout without extra columns. Utility output never generates its own expected bytes. The selected util-linux
logger emits a warning for combined `-f` and string operands but correctly logs
the operands; the warning bytes and independent datagrams are both checked.
For this provider, `-f -` reads a literal file named `-`; it does not select stdin.
Scheduler group checks compare jobs with their submitting environment; the
foreground atd daemon and its jobs may share a service process group.

| Utility | Selected observations | Important remaining boundary |
| --- | --- | --- |
| at | Exact POSIX list formatting and multi-ID lookup; file/stdin submission, fixed `-t`, a/c queue selection and filtered listing, multi-ID removal, failed time, `now`, inherited cwd/environment/umask, process group distinct from submission, no controlling terminal, UID/GID, output/error and silent mail | Full timespec grammar, further queue/errors and other environments |
| batch | Independently observed queue-b identity; stdin execution, inherited state, process group distinct from submission, no controlling terminal, UID/GID and mail including silent completion | Alternate shell, submission errors and non-C environment details |
| crontab | File/stdin replace/list/remove, failed-read preservation, wildcard execution, supplied default environment, percent stdin and mail | Calendar/range/list execution, day-field OR, escapes and interrupted/resource effects |
| date | Fixed leap-day/century/year/week boundaries, DST transitions, E/O modifiers, French locale/LC_ALL precedence, TZ/`-u`, full-output failure | Further widths/flags/alternative locale forms, leap seconds, closed output and signals |
| logger | Private syslog datagrams, operands/stdin/file, operands overriding `-f`, literal dash filename, kernel-verified PID, empty/UTF-8 messages, all required priorities, option/file errors and absent-sink failure | Further option/resource/signal and locale-catalog cases |
| lp | Two private CUPS raw queues, byte sinks, paused-queue `-c` copy independence, `-d/-n/-s/-t/-o`, stdin/dash/file, request IDs, backend metadata, destination precedence and absent destination error | No physical device: actual hardcopy, copies/banner/title rendering, class selection and notifications remain unqualified |
| mailx | Base send, two recipients, subject/body, dot line, parsed To/From/Date/Message-ID, no-subject nonempty delivery, `-E`, empty/UTF-8 delivery, maximum required subject length and denied transport | Further address/header, localized diagnostic and signal/resource boundaries |
| uuencode | Independent historical/Base64 algorithms, 11 lengths through 8192 bytes, all 256 byte values, 0751 mode, portable paths, option termination, UTF-8 and full-output errors | Further modes/path bounds, nonregular input, read/closed-output/signal/resource cases |
| uudecode | Independent encoded input, both algorithms/stdout cookies, file/stdin, preamble, `-o`, numeric/symbolic modes independent of umask, path preservation, overwrite/symlink/denied-write, tolerated chmod EPERM, split/noisy Base64, UTF-8 and full-output errors | Further mode/path bounds, creation/read/closed-output/signal/resource cases |

Date-setting and NLSPATH/permission database assertions are XSI, not this base
profile. Mail receive/interactive features and crontab `-e` are UP-shaded and
excluded. Base mail send is required and tested. The machine map explicitly
retains the remaining required behavior; these exclusions are not gap allowances.
A passing byte sink does not establish the physical printing contract.

## Selected provider repairs

The Linux service prefix contains an executable `batch` script implementing the
standard's definition, `at -q b -m now`. Debian's stock script omits `-m` and the
retained strict run demonstrates missing completion mail for a silent job.
The provider still uses Debian `at`/`atd` and local Exim; the wrapper does not
fabricate any queue, mail or scheduling outcome.

`make host-profile` builds standalone Apple/FreeBSD `uudecode` on macOS and Linux from
Apple text_cmds commit `592aaf8a50aa5810ee8183df20f0ba48bb23aa7e`,
[`bintrans/uudecode.c`](https://github.com/apple-oss-distributions/text_cmds/blob/592aaf8a50aa5810ee8183df20f0ba48bb23aa7e/bintrans/uudecode.c).
The BSD-3-Clause license remains in the source. Two pathname comparisons add
`-` alongside `/dev/stdout`, before header pathname stripping and for `-o`.
Standalone build adapters select the vendor's POSIX overwrite/symlink behavior
and use the system `b64_pton` in place of Apple's private helper. Linux uses
libbsd for `setmode`/`getmode` and diagnostics. The profile preserves full header
pathnames, ignores nonalphabet Base64 characters (including `-` and `_`), handles
split quanta without forming a pointer before its buffer, and evaluates symbolic
permissions independently of the caller's umask. Stock Linux sharutils failed
symbolic modes and split/noisy Base64; stock macOS behavior stripped paths and
rejected noise. Failed runs and the sanitizer finding are retained. A small main calls `main_decode`;
no decoder code is linked into cshell. The build is offline and the profile
symlink never replaces `/usr/bin/uudecode`.

The disposable service prefix also supplies an `at` adapter for listing output:
Debian's extra queue/user columns are removed while the ID and localized date
remain intact. All scheduling operations still execute Debian `at`. A `logger`
adapter enables util-linux `--socket-errors=on`, avoiding a success status when
`/dev/log` is absent. Exact underlying executable hashes are recorded alongside
the adapters.

## Remaining environments and manual work

The 20 residual IDs are groups of unqualified clauses, not 20 confirmed bugs.
Their `execution_requirement` fields identify the next capability needed.

| Remaining area | Required setup | Manual testing? |
| --- | --- | --- |
| Further codec I/O, modes/path limits, locale diagnostics, address/header cases and ordinary queue failures | More bounded fixtures in the current disposable image; small private filesystems or fault injection for storage errors | No |
| Signal interruption, terminal prompts, alternate scheduler shells and `lp -w` | Automated pseudo-terminal/login fixtures with readiness handshakes; a configured CUPS notifier for `-m`/`-w` | No; physical completion is a separate claim |
| Scheduler calendar rollovers, cron day-field matching and calendar boundaries | A controllable daemon-clock fixture, or a disposable VM whose clock can safely change. A preload variable alone does not control a set-ID `at` provider | No manual timing; never change the developer-host clock |
| Actual pages, copies, banners, title/locale/timezone rendering and physical device failures | Dedicated test printer connected only to the disposable print environment | Yes, inspect the printed pages and induced device failures |
| Native macOS service behavior | Disposable macOS VM/runner with private services and identities | Mostly automated; Linux Docker results do not establish macOS service behavior |

Queue classes, multi-file ordering and simulated-device fault paths can be tested
before a printer is available. The existing byte sink is not evidence of
nonvolatile human-readable output. No production mailbox, printer or scheduler
is needed for the automated work.
