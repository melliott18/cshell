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

Linux native codec tests require `sharutils`. Native macOS uses the supplied
opt-in `uudecode` adapter; no host installation or service invocation occurs.
The stock-host diagnostic remains available explicitly:

```sh
python3 tests/host_services.py ./cshell --record build/tests/service-stock.json
```

That command returns nonzero for missing providers or failed assertions. In
particular, the retained macOS stock `uudecode` fails the Issue 8 `-` stdout
cookie requirement. A failing stock run is not a passing profile.

The separate service Dockerfile installs `at`, `cron`, `bsd-mailx`,
`exim4-daemon-light`, `cups-daemon`, `cups-client`, `sharutils` and the existing
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
fixture configures `mailx` with `sendwait` so its local transport finishes before
command-group cleanup. `atd` uses an explicitly supplied high batch-load
threshold and one-second interval; these are fixture choices, not standardized
scheduling deadlines. Cron uses real time with a 75-second observation deadline.
The date-only shared object intercepts `time` and `CLOCK_REALTIME` reads at
2024-02-29 12:34:56 UTC. It has no clock-setting code and leaves other clocks
unchanged. Native controlled-time qualification remains unavailable.

Commands have an eight-second wall deadline, bounded CPU, 1 MiB per output
file, no core dump and 64 native/1024 service descriptors. The latter supplies
Exim's actual descriptor requirement. Daemons have owned process groups and
bounded logs. Normal/error/interrupt paths stop and reap them. Unit tests force
command timeout and excess output, verify owned descendant disappearance, and
keep an unrelated process alive. The launcher has an independent 300-second
deadline, copies records even after failure, forcibly removes its container in
`finally`, and verifies removal. A missing record, timeout, failed assertion or
cleanup failure returns nonzero. Interrupted runs cannot claim qualification.

`build/tests/host-services/launcher.json`, `results.json` and `run.log` retain
setup, invocation, assertion and cleanup outcomes. Logs and JSON from initial
failed fixture attempts remain in [the evidence](evidence/csh-078/README.md).

## Assertions and boundaries

Every declared utility witness exercises the inventoried executable directly,
cshell `-c`, explicit `exec`, script-file input and stdin input. The 72 logger
priority pairs and final daemon-effect checks supplement those dispatch paths.
Missing declared case prefixes cause failure. Diagnostic messages whose wording
is unspecified are checked for nonempty stderr and positive status; every actual
byte is retained. Scheduler dates/IDs and print IDs use independent structure
checks. Utility output never generates its own expected bytes.

| Utility | Selected observations | Important remaining boundary |
| --- | --- | --- |
| at | File/stdin submission, fixed `-t`, list/remove, failed time, `now`, inherited cwd/environment/umask, output/error and silent mail | Full timespec grammar, queue filtering, process-group/terminal assertions and other environments |
| batch | Stdin execution and the same inherited state/mail observations, including silent completion | Queue/process-context and non-C environment details |
| crontab | File/stdin replace/list/remove, failed-read preservation, wildcard execution, supplied default environment, percent stdin and mail | Calendar/range/list execution, day-field OR, escapes and interrupted/resource effects |
| date | Independent fixed leap-day values, default output, common strftime conversions, TZ and `-u` | Other calendar/format/locale combinations and output/signal failures |
| logger | Private syslog datagrams, operands/stdin/file, header/tag/PID shape, default and all required priorities | Routing/error/locale combinations and PID correspondence |
| lp | Private CUPS raw spool, byte sink, `-c/-d/-n/-s/-t/-o`, stdin/dash/file, request IDs and backend metadata | No physical device: actual hardcopy, copies/banner/title rendering, class selection, notifications and destination precedence remain unqualified |
| mailx | Base send, two recipients, subject/body, dot line, `-E` and missing option argument | Startup/address/environment, full RFC5322 semantics and further delivery/error boundaries |
| uuencode | Independent historical/Base64 algorithms, 11 lengths through 8192 bytes, all 256 byte values, modes, file/stdin and errors | Other modes/pathnames, I/O/signal/locale/resource boundaries |
| uudecode | Independent encoded input, both algorithms/stdout cookies, file/stdin, preamble, `-o`, bytes and 0640 mode despite 0077 mask | Other output/mode/overwrite and I/O/signal/locale/resource boundaries |

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

On macOS, `make host-profile` builds standalone Apple/FreeBSD `uudecode` from
Apple text_cmds commit `592aaf8a50aa5810ee8183df20f0ba48bb23aa7e`,
[`bintrans/uudecode.c`](https://github.com/apple-oss-distributions/text_cmds/blob/592aaf8a50aa5810ee8183df20f0ba48bb23aa7e/bintrans/uudecode.c).
The BSD-3-Clause license remains in the source. Two pathname comparisons add
`-` alongside `/dev/stdout`, before header pathname stripping and for `-o`.
Standalone build adapters select modern Unix2003 compatibility and use the
system `b64_pton` in place of Apple's private `apple_b64_pton` helper. Base64url
extensions are outside the qualification. A small main calls `main_decode`;
no decoder code is linked into cshell. The build is offline and the profile
symlink never replaces `/usr/bin/uudecode`.
