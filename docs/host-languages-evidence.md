# Host languages, editors and argument construction

CSH-074 adds a strict **bounded operation-contract subset** for awk, bc, ed, expr, grep,
m4, patch and xargs. These witnesses do not qualify entire normative pages or
the POSIX base system. [CSH-074](tickets/CSH-074-host-languages-editors.md) remains
the open owner of the full contracts and remaining editor conditions.

## Providers and reproduction

```sh
make test-host-languages       # Build/select private providers; missing tools fail
make test-host-profile         # Selected profile plus existing host assertions
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-host-languages
```

The Dockerfile and Linux CI explicitly install Debian/Ubuntu `bc` and `m4`.
The private profile builds GNU ed 1.22.6 with the exact POSIX SIGINT marker,
a FreeBSD-derived xargs with Issue 8 empty-input, NUL and size handling,
GNU M4 1.4.20 with wrap-order and error-status corrections,
and GNU patch 2.8 with output-backup correction.
Their checked-in source, upstream hashes, local changes and licenses are under
`tools/host-profile/vendor`; none of these executables is linked into cshell.
The M4 provider builds offline from its pinned complete source archive and
reviewable patch. GNU M4/gnulib retain their upstream warning policy: the build
removes only `-Werror` from the requested CFLAGS, preserving sanitizer, language
and optimization flags. Requested/effective flags, patch/archive hashes and
the executable hash are retained in `build/host-m4-build.json` and the run record.
The earlier native Xcode m4 observations remain historical evidence. No host packages are installed by the
harness. The profile creates only private symlinks under `build/host-profile`.
Every run records PATH, selected pathname, realpath, SHA-256, OS build or Debian
package versions/owners, cshell hash, test/build input hashes, filesystem,
credentials, controlled environment and bounds. A provider change requires a new
run; package names or executable presence alone establish no qualification.

[Retained runs and failures](evidence/csh-074/README.md) keep macOS and Linux
results separate. The stock-host inventory remains a historical observation;
newly supplied bc/m4 do not rewrite its missing-provider entries.

## Assertions and clause accounting

The [original cases](../tests/host_language_cases.py),
[operation cases](../tests/host_language_extended_cases.py),
[terminal cases](../tests/host_language_terminal_cases.py) and
[patch interactions](../tests/host_language_patch_cases.py) contain 191 fixtures:
188 selected-provider cases and three explicitly instrumented backing-store
cases. Each runs through direct execution and cshell `-c`, script file and stdin;
the instrumented cases use their separate executable in every mode. Utility
input is independent of shell source input. Nine additional signal witnesses
exercise SIGHUP, HOME fallback and SIGINT through direct/string/file execution.
The selected suite therefore has 773 strict assertions with no gap allowances.
Eight assertions for legacy XSI `-I`/`-L` are supplemental regressions; they do not
qualify the optional Issue 8 XSI profile.

| Page | Bounded witnesses |
| --- | --- |
| [awk](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/awk.html) | Fields, records, variables, program files, arrays, loops, functions, ERE ranges, strings, math/formatting, getline/output files, exit/END and missing inputs |
| [bc](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/bc.html) | Arithmetic, scale, bases, arrays/functions/loops, library values, file/stdin ordering, quit and inaccessible operands; invalid bc programs are not used as normative error tests because their noninteractive behavior is undefined |
| [ed](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html) | Editing, addresses, marks, BRE/global commands, undo, file effects, error statuses, 4096-byte buffer, all four editing/global forms, prompt toggling, shell I/O, exact SIGINT recovery, SIGHUP cwd/HOME recovery and isolated backing-store failure injection |
| [expr](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/expr.html) | Arithmetic precedence, comparisons, Boolean expressions, BRE capture/length, null/zero and syntax-error status |
| [grep](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/grep.html) | BRE/ERE/fixed patterns, case folding, inversion/count/line numbers, pattern files, multiple files, quiet/list modes, invalid patterns and missing inputs |
| [m4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/m4.html) | Definitions/options, argument substitution, arithmetic/strings, macro stack, conditionals, diversions, includes and explicit exit |
| [patch](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/patch.html) | Normal/context/unified/ed formats, backups, directory stripping, blank matching, offset search and multiple files, reversal, input/output selection, reject status/file and preservation of rejected input |
| [xargs](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/xargs.html) | Quoting/escaping, NUL delimiters including empty arguments, empty-input invocation and suppression, strict byte bounds, oversized-limit clamping, argument and line batches, replacement, EOF marker, default echo, tracing, size rejection, missing/non-executable utility, child nonzero/255 and stopping after 255 |

The [machine clause map](../tests/host_language_contracts.json) enumerates every
normative heading/subheading of the eight fetched Issue 8 pages, ending before
the informative sections. It retains page hashes, anchors, witness IDs and
individual section dispositions. A `partial` row is not a pass for that section;
`unqualified` explicitly retains missing coverage. The map separately retains
U-034 exec accessibility, U-040 defaults and `U-040/ed-buffer-temp-signal`.
One UTF-8 grep witness additionally checks multibyte character matching. Broader
locale behavior, complete grammars and option interactions, physical capacity
exhaustion, other storage faults and other signal conditions remain open. Neither a finite successful buffer nor a rejected
pathname measures maximum buffer or temporary-store capacity.

The immutable CSH-064 residual text remains unchanged. The
[current ownership overlay](../tests/host_contracts.json) links these newer
witnesses without dropping the residual or vendor implementation ownership.
CSH-073's shared `U-040/other-interruptions` may reference these specific ed
recovery witnesses; it is not resolved by them.

## Bounds and failure evidence

Ordinary cases use the shared smoke runner's five-second deadline, 64-KiB
combined output bound, one-MiB file bound, 64 descriptors, CPU bound and disabled
core dumps. Each case has a private directory, HOME and TMPDIR and must remove
its fixture directory even on failure. Expected text and file bytes are authored
in Python, never generated by the utility being qualified. Diagnostics use
predicates only where wording or status is unspecified; the actual bytes/status
are retained. Sanitizer diagnostics always fail, including editor diagnostics retained inside
the signal driver's result. Eight harness controls include a fake recovered editor
that emits a sanitizer diagnostic and must still fail.

Signal cases use a seven-second outer deadline and two-second response/wait
bounds. The driver observes ed print the modified buffer and a later shell-escape
helper create a private readiness marker, then signals only its child. The
second handshake places SIGHUP after the print operation has completed. For
SIGINT, an additional editor prompt proves that the shell escape has returned:
`system()` temporarily ignores SIGINT while its child is running. The PTY
transcript requires the exact marker, restored command mode and unchanged buffer. SIGHUP must recover the exact buffer without overwriting the
original operand. A directory named `ed.hup` forces the cwd write failure and
HOME fallback without privileges or changes to the developer filesystem.
The driver reaps ed; inherited process-group cleanup catches descendants.
A fault test forces a hung editor and descendant, checks bounded failure and
cleanup, and verifies an unrelated child survives. Container zombies, where
present, are dead processes rather than successful evidence of reaping by PID 1.

## Private provider repairs and remaining contracts

SIGINT is now part of the default suite; `--ed-sigint` remains a compatibility
flag. The standalone GNU ed change removes its extra presentation newline from
the required `?\n` marker. SIGHUP recovery is unchanged. A sanitizer-discovered upstream regex defect is
also repaired: zero-length prefix copies are skipped before the replacement
buffer has been allocated. A second build alone
interposes `tmpfile` (EMFILE) and backing-store `fwrite` (ENOSPC); the production
editor has no fault switches. Both failures must diagnose, exit normally with
nonzero status and preserve the original input file; the no-fault control proves
that the same instrumented build can read the buffer.

The standalone xargs preserves every NUL delimiter, invokes once on empty input
unless suppressed, accepts `-x` without `-n`, and clamps oversized `-s` values.
Its error pipe transfers exec failure across `fork` so 126 and 127 are retained
on both systems. Upstream `vfork` shared-memory assumptions failed on Darwin.
Independent argument-vector and byte-budget oracles exercise these paths.

The private M4 provider repairs the three native failures: wrap text is copied
onto a fresh obstack in registration order while preserving allocation lifetimes;
failed temporary-file creation and nonnumeric arguments retain a nonzero final
status. All six [provider regressions](../tests/host_language_provider_cases.py)
are required by default. They include 64 ordered wrap registrations, expansion
using earlier wrap definitions, continued processing after errors and two unique
empty temporary files with mode 0600. File names are checked independently in
the fixture directory rather than derived from M4 output.

The selected provider regressions can also be run alone:

```sh
python3 tests/host_languages.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --provider-regressions --record build/tests/host-languages-provider.json
```

The legacy `--remaining-contracts` spelling is an alias for this selection;
it no longer denotes excluded tests. The original failed m4 results remain in
the evidence, and the default suite now requires their repaired expectations.
Full-page acceptance remains open for the other obligations in the heading map.

`--case 'xargs/*'` (repeatable) selects focused development checks and records the
selection. Only an unfiltered run supports the complete declared subset.
The heading map retains the remaining obligations, including other inherited signals, patch prompts, further preprocessor
and backup interactions, broad locale/default handling and resource faults.
The absence of an assertion is not a waiver or a qualified contract.

The [expanded evidence](evidence/csh-074/expanded/README.md) retains every new
failed provider attempt, corrected run and source identity. Dedicated Linux and
macOS CI jobs run the selected contracts in ordinary and ASan/UBSan builds and
upload the JSON evidence, independently of broader runtime job failures.


## Terminal and backup continuation

[Retained continuation records](evidence/csh-074/terminal-backup/README.md) include
provider failures and separate ordinary/sanitizer environment results.

Eleven terminal fixtures add 44 assertions across direct, string, script-file and
stdin dispatch. The shell uses `exec` and receives source independently of the
utility's interactive input. A controlling PTY carries ed stdout or xargs stderr;
the other output stream is captured separately, so a message on the wrong stream
fails. Exact transcripts cover unsaved-buffer warnings on quit/edit/EOF,
warning rearming after a new edit, help-mode toggling, SIGQUIT ignoring and
xargs confirmation of each batch. Only unspecified help-message text uses a
nonempty-line expression. The C locale's affirmative and negative responses
are authored independently. Capability failure is a retained failure, never a skip.

Six patch fixtures add 24 assertions for conditional source output, operand
precedence and backup interactions. macOS patch 2.0-12u11-Apple overwrites the
first backup when two patches target one file. The profile now supplies pinned
GNU patch 2.8 on both platforms, which retains that first backup. GNU patch's
`-b -o result` path also needed a correction: copy an existing output before the
shared output stream truncates it. A nonexistent output creates no backup and
the input is preserved. The offline archive, license, local diff, hash and build
flags are recorded as for M4. These regressions remain required in the suite.

## Remaining work and environment requirements

| Remaining obligation | Environment | Manual interaction needed? |
| --- | --- | --- |
| Additional grammars, option interactions, patch prompts and inherited signals | Existing native macOS/Linux and automated controlling PTYs | No |
| Broader locale precedence, multibyte processing and localized confirmations | Explicitly generated locales/catalogs; the Docker image already supplies several | No; record which locale data is actually present |
| Physical storage capacity and real filesystem failure behavior beyond injected errors | Disposable size-limited filesystem or disk image, isolated from the host filesystem | No; setup privileges may be needed |
| Reproduced native job-control hang | Clean macOS 14 comparison environment; macOS 15 CI provides a separate comparison | No terminal typing; OS-level investigation remains open |

The native macOS 14.8.7 job-failure fixture still fails at both its default
five-second bound and a longer diagnostic run (the fixture's own alarm exits at
ten seconds). A sample of its owned child shows it inside `sigprocmask`; `ps`
reports `UE`, and group cleanup fails. This is evidence of a kernel-bound wait,
not yet a proven root cause. No repeated retries, weakened oracle, successful
Linux run or macOS 15 run resolves that local failure. A clean macOS 14 VM or
fresh host session would distinguish persistent host state from a reproducible
OS/runtime interaction. Restarting the user's host is not part of this change.

Sections whose entire normative content is “None” now have explicit
`not-applicable` accounting, instead of fictitious missing cases. Other
unqualified headings and partial sections remain open. No physical terminal or
human confirmation requirement has been identified for these CSH-074 cases.
