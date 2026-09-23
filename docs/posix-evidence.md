# POSIX evidence and fixture conventions

The [requirements matrix](posix-matrix.md) records scope and ownership. This
document defines what its evidence states mean, bounds the existing smoke
coverage, and provides one reproducible reference-shell comparison. Neither the
matrix nor agreement between reference shells establishes cshell conformance.
The [POSIX tracking page](posix.md) identifies the target edition and policy.

## Evidence states

Use one of these states for each inventoried requirement. Ticket lifecycle
statuses such as `review` and `done` are separate from requirement evidence.

| State | Meaning and evidence required |
| --- | --- |
| **missing** | The requirement is open: implementation is absent, known to be incomplete, or has not been established. Name the implementation owner and intended fixtures. Existing fragments and passing smoke witnesses do not close the requirement. |
| **implemented** | The scoped behavior is present and its code is linked, but the required passing cases or environment coverage are incomplete. Record the remaining gaps; source inspection alone cannot advance it to verified. |
| **verified** | Link the reviewed specification interpretation, implementation revision, actual fixture assertions, and passing run records for the named platforms/profile. Limit the claim to those assertions. Split a row into narrower stable IDs if only part is verified. |
| **inapplicable** | Cite the standard's applicability condition and the documented project profile decision that excludes it. Record the decision owner and any condition that would reopen it. Missing implementation, unavailable infrastructure, or a skipped test is not inapplicability. |

An intended fixture name is a plan, not a passing test. Record execution results
separately as `pass`, `fail`, `not-run`, or `skip`, with a reason and owner for
every unexecuted case. A reference-only pass does not change cshell's evidence
state. A failure reopens the affected behavior even if an earlier revision
passed. CSH-036 defines this baseline;
[CSH-037](tickets/CSH-037-portability-audit.md) audits the eventual evidence.

## Fixture contract

[CSH-017](tickets/CSH-017-test-harness-and-ci.md) owns the executable harness and
fixture format. The following is its evidence contract, not a claim that a new
fixture loader or fixture directory already exists. Use stable case IDs grouped
by language, invocation, utility, and terminal behavior. Link each actual fixture
back to every matrix row it asserts, and link those rows to the fixture and run
record. Tickets should list their matrix IDs so traversal works in both
directions.

Each fixture and its run record need:

- **Identity and applicability:** case ID, matrix IDs, owning ticket, edition
  (`POSIX.1-2024`), exact normative section URLs, option/profile prerequisites,
  and classification: required, conditional, unspecified, implementation-defined,
  permitted alternative, extension, or behavior outside the standard's guarantees.
- **Inputs:** literal script bytes, invocation mode and complete argument vector,
  stdin bytes, initial files/modes, working directory, environment, locale, time
  zone, umask, descriptors, and terminal/process-group setup when relevant.
- **Expected-result provenance:** the normative rule and reasoning that produce
  each expectation; any selected implementation policy with its decision record;
  and separate reference observations. Never generate the normative oracle merely
  by copying the majority shell output.
- **Assertions:** exact stdout/stderr bytes or a justified predicate, exit status
  or allowed status relation, filesystem effects, relevant signal/job/terminal
  state, and completion bounds. Assert exact diagnostic text only where specified;
  a diagnostic requirement does not normally prescribe one shell's wording.
- **Execution identity:** cshell and suite revision (including dirty-tree state),
  executable path and resolved realpath, executable hash or immutable build ID,
  build flags, compiler and scanner versions, OS/release/architecture, libc or
  system-library build, and harness/Python version. Record a UTC run timestamp.
- **Reference identity:** each resolved executable, version/build evidence, full
  invocation and mode (for example Bash POSIX mode), and probe result. `/bin/sh`
  is a pathname, not a version. Where a shell lacks a version option, record its
  package/OS build and executable hash; a failed version probe is not a failed
  behavioral fixture. Record relevant helper utility versions as well.
- **Result:** actual observations, pass/fail/not-run/skip, elapsed bound, cleanup
  result, platform/capability skips, artifact/log location, and the follow-up
  owner for discrepancies. Capture the controlled environment, or the inherited
  variable names and relevant values needed to reproduce the case.

Use separate adapters for stdin, script, and `-c`, retaining identical assertions
where their semantics agree. Unsupported invocation modes remain not-run until
[CSH-016](tickets/CSH-016-input-and-invocation.md) and
[CSH-018](tickets/CSH-018-status-and-cli-integration.md) integrate them. Keep parser,
expansion, command execution, utility, and PTY cases separately identifiable so
one successful end-to-end example does not hide missing boundary cases.

## Standard and extension decisions

The standard is the authority. Its terminology distinguishes
[implementation-defined](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html#tag_01_06_02),
[unspecified](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html#tag_01_06_08),
and [undefined](https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap01.html#tag_01_06_07)
behavior. The fixture's classification determines its oracle:

| Classification | Fixture and decision rule |
| --- | --- |
| Required | Derive assertions from the selected edition's normative text. Other shells can expose an error in the interpretation, but cannot overrule it. |
| Conditional / option-dependent | Record the exact condition and selected profile. Test all applicable branches; an unavailable runner capability is a scoped skip with an owner, not an exclusion of the requirement. |
| Permitted alternatives | Assert the allowed set or invariant, including any restrictions on when alternatives are allowed. Avoid requiring agreement where the standard permits differences. |
| Unspecified | Do not choose one reference result as mandatory. Check only guarantees that still apply; otherwise report the observation without a conformance verdict. A project stability promise may be tested separately. |
| Implementation-defined | The owner records cshell's chosen behavior and its required documentation before the expected result is finalized. Test that documented choice within the permitted range. An unresolved choice remains open in the matrix. |
| Extension | Label and run separately from standard cases. Legacy `\|&` and `>>&` acceptance does not verify POSIX pipeline or redirection rules; reject, retain, or gate extensions through an explicit owning-ticket decision. |
| Undefined / outside guarantees | Use bounded robustness checks if useful, but do not turn another shell's behavior into a normative expected result. Identify which input precondition was violated. |

Issue 8 additions require particular care: an older reference shell's rejection
of dollar-single-quoting or `pipefail` does not weaken the Issue 8 requirement.
If references disagree, retain their raw observations, re-read the normative
section, and assign an interpretation or implementation issue to the owning
ticket. Unresolved interpretation is not a waived test or a passed requirement.

<a id="existing-smoke-evidence"></a>

## Existing smoke witnesses

The only current cases are the three entries in
[`tests/smoke.py`](../tests/smoke.py). The following IDs name those existing
entries for cross-referencing; they do not rename cases in the runner. For every
case, a pass requires completion within five seconds by default, process status
0, empty captured stderr, at most 65,536 bytes of stdout, and the expected stdout
after **every** byte sequence `Shell> ` has been removed. That normalization is
a prototype allowance, not a standard output rule.

<a id="smoke-exit"></a>

### SMOKE-EXIT — `exit`

Input is `exit\n`; normalized stdout is empty. A passing run demonstrates startup
and the prototype's bare explicit-exit path for this initial state. It supplies
a partial witness for [SH-001](posix-matrix.md#sh-001) and
[U-008](posix-utilities.md#u-008). It does not verify EOF termination, last-command
status propagation, numeric/invalid/excess operands, traps, interactivity,
prompt placement, or complete `exit` utility semantics.

<a id="smoke-external"></a>

### SMOKE-EXTERNAL — `external command`

Input is `/bin/echo cshell-smoke-ok\nexit\n`; normalized stdout is
`cshell-smoke-ok\n`. A passing run demonstrates one absolute-path external
command with one plain argument followed by explicit exit, a partial witness
for [EXEC-004](posix-matrix.md#exec-004) and [SH-001](posix-matrix.md#sh-001).
It does not verify PATH search, quoting, expansion, environment assignments,
nonzero/signal-derived statuses, command-not-found behavior, executable format
fallback, descriptor semantics, or the shell's full command-search algorithm.
The host `/bin/echo` supplies its output; this is not evidence of a cshell `echo`
builtin or complete host-utility conformance.

<a id="smoke-sequence"></a>

### SMOKE-SEQUENCE — `successive commands`

Input is `/bin/echo first second third\n/bin/echo fourth\nexit\n`; normalized
stdout is `first second third\nfourth\n`. A passing run demonstrates two
newline-separated absolute-path commands, simple space-separated arguments, and
the observed output order before explicit exit. It is another partial witness
for [EXEC-004](posix-matrix.md#exec-004) and [SH-001](posix-matrix.md#sh-001), not
general grammar coverage. It does not verify semicolon lists, AND-OR lists,
pipelines, asynchronous commands, functions, compounds, redirections, expansion,
or general argument tokenization.

Each case gets a fresh working directory and `LC_ALL=C`, but otherwise inherits
the runner's environment. No case asserts filesystem effects, inspects terminal
state, or measures child reaping. The runner starts a new session and kills the
original process group on timeout. That is a cleanup mechanism, not a tested
proof of all descendant cleanup paths. Output files bound memory reads, but
their disk growth is not capped while the process runs; CSH-017 owns stronger
resource bounds and harness self-checks. Passing all three cases does not mark
any entire POSIX requirement verified.

## Native, Docker, and terminal evidence

[`make test` and `make docker-test`](testing.md) run the same three cases. A native
pass and a Docker pass are separate environment observations of the same
assertions, not additional language coverage. Attach actual run results to the
implementation ticket; the existence of either target does not imply it ran.
For Docker, record the resolved image ID/digest, base image, package/toolchain
versions, engine/platform architecture, libc, and invocation. A mutable local
image tag alone is insufficient. For native macOS, record the macOS build and
Darwin/system-library build; Linux results do not establish Darwin behavior.

[CSH-033](tickets/CSH-033-pty-test-harness.md) owns bounded PTY setup and teardown;
[CSH-034](tickets/CSH-034-job-control.md) and
[CSH-035](tickets/CSH-035-traps-and-signal-semantics.md) own behavior. PTY records
must include controlling-terminal setup, terminal attributes, foreground/process
group IDs, injected input/signals and synchronization points, output, bounded
waits, exit status, and restoration/cleanup observations. Harness self-checks
must verify timeout handling before those mechanisms serve as shell evidence.
Record unavailable PTY capabilities with their platform and reason. Piped stdin
smoke tests cannot substitute for terminal evidence. Sanitizer and compiler
checks establish their specific safety/build observations, not language results.

<a id="sample-differential-case"></a>

## Sample differential case: null parameter defaults

Case ID: `expansion/parameter-default-null`; owner:
[CSH-024](tickets/CSH-024-value-expansions.md), with harness integration in CSH-017.
This is a documented reference-only case. Its future executable fixture is
pending; cshell's [EXP-003](posix-matrix.md#exp-003) remains missing. The prototype
was not run on this script. The comparison also exercises quoting, assignment,
and [U-035 `printf`](posix-utilities.md#u-035); it verifies none of those cshell
requirements.

Literal script (including the final newline):

```sh
CSH_SAMPLE=
printf '<%s>\n' "${CSH_SAMPLE:-fallback}" "${CSH_SAMPLE-fallback}"
```

**Specification-derived expectation.**
[Shell Command Language 2.6.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_02)
distinguishes null-or-unset checking with `:-` from unset-only checking with `-`.
The assignment makes the parameter set but empty, so these expansions produce
`fallback` and an empty string respectively.
[Double-quoting](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_02_03)
and [field-splitting rules](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_06_05)
retain each argument.
[`printf` operands](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html#tag_20_96_05)
and its [extended description](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html#tag_20_96_13)
give the formatted bytes for the two operands, reusing the format. Its
[successful exit status](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html#tag_20_96_14)
and the shell's
[exit-status rules](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_02)
supply status 0. The oracle is stdout `b'<fallback>\n<>\n'`, stderr `b''`, status
0, and no created working-directory entries. This expectation was derived from
the specification before comparing the two shells.

**Reference observations, 2026-09-23 at 20:21:24 UTC.** Executed on macOS 14.8.7, build 23J520,
Darwin 23.6.0 (`xnu-10063.141.1.712.16~1/RELEASE_ARM64_T6000`), arm64, with
Python 3.12.2. Both executable paths resolve to themselves. Both are OS-supplied
binaries; the OS build and hashes identify their builds:

| Executable and mode | Version probe | SHA-256 |
| --- | --- | --- |
| `/bin/bash --posix` | `--version`: `GNU bash, version 3.2.57(1)-release (arm64-apple-darwin23)`, status 0, stdout | `316f63ce5d51d7e5eb776912da68610532f414339529b7e877b367db7396f16b` |
| `/bin/ksh` (default mode) | `--version`: `sh (AT&T Research) 93u+ 2012-08-01`, status 2, stderr | `addc8f59ef88a68084107d32505d78eca9839480aa8d3b877f73c6f9f678912d` |

Each used `-c SCRIPT csh-036-sample`, stdin `/dev/null`, stdout/stderr pipes,
umask `022`, a new session, a five-second timeout, and the same fresh temporary
working directory. Its recorded path was
`/var/folders/1s/p32k5z617vqc6qxm89nx29dc0000gn/T/csh-036-differential-zgcmiza8`.
The complete supplied environment was:

```text
HOME=<working directory>
TMPDIR=<working directory>
LC_ALL=C
LANG=C
TZ=UTC0
PATH=/usr/bin:/bin
```

No other environment variables were supplied; no PTY was attached. A separate
`command -V printf` probe reported a shell builtin in both versions, so the
recorded shell builds also identify the formatting utility used here. For both
shells the actual stdout was `b'<fallback>\n<>\n'`, stderr was `b''`, status was
0, no timeout occurred, and the directory remained empty. The temporary
directory was removed after both runs. Agreement is supporting reference
evidence only; these old shell versions are not reference authorities for
Issue 8 additions.

The following reproducer executes only those reference shells and prints their
resolved paths, hashes, versions, actual environment, and observations. The
generated temporary path will differ. It is a standalone example, not the
CSH-017 harness or an installed fixture:

```python
import hashlib
from datetime import datetime, timezone
import os
from pathlib import Path
import platform
import signal
import subprocess
import tempfile

script = ('CSH_SAMPLE=\n'
          'printf \'<%s>\\n\' "${CSH_SAMPLE:-fallback}" '
          '"${CSH_SAMPLE-fallback}"\n')
print("UTC:", datetime.now(timezone.utc).isoformat(),
      "platform:", platform.platform(), "Python:", platform.python_version())
with tempfile.TemporaryDirectory(prefix="csh-036-differential-") as directory:
    environment = dict(HOME=directory, TMPDIR=directory, LC_ALL="C",
                       LANG="C", TZ="UTC0", PATH="/usr/bin:/bin")
    print("environment:", environment, "cwd:", directory, "umask: 022")
    for executable, options in (("/bin/bash", ["--posix"]), ("/bin/ksh", [])):
        binary = Path(executable).resolve()
        version = subprocess.run([str(binary), "--version"], cwd=directory,
                                 env=environment, stdin=subprocess.DEVNULL,
                                 capture_output=True, timeout=5)
        print(binary, hashlib.sha256(binary.read_bytes()).hexdigest(),
              "version:", version.returncode, version.stdout, version.stderr)
        process = subprocess.Popen(
            [str(binary), *options, "-c", script, "csh-036-sample"],
            cwd=directory, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True, umask=0o022)
        timed_out = False
        try:
            output, errors = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            output, errors = process.communicate()
        entries = os.listdir(directory)
        print("observed:", output, errors, process.returncode,
              "timeout:", timed_out, "entries:", entries)
        assert not timed_out
        assert (output, errors, process.returncode, entries) == (
            b"<fallback>\n<>\n", b"", 0, [])
```

This small known-input example has a timeout but is not a general hostile-input
runner. CSH-017 must add output/resource bounds and its own cleanup self-checks
before expanding it into a differential suite. Adding this reference observation
does not introduce a passing cshell expansion test.
