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
The private profile builds GNU ed 1.22.6 with the exact POSIX SIGINT marker
and a FreeBSD-derived xargs with Issue 8 empty-input, NUL and size handling.
Their checked-in source, upstream hashes, local changes and licenses are under
`tools/host-profile/vendor`; neither executable is linked into cshell.
macOS otherwise uses OS providers and selects the actual Xcode/Command Line Tools m4 found
by `xcrun --find m4`. This avoids treating `/usr/bin/m4`, a developer-tool
launcher, as the implementation identity. No host packages are installed by the
harness. The profile creates only private symlinks under `build/host-profile`.
Every run records PATH, selected pathname, realpath, SHA-256, OS build or Debian
package versions/owners, cshell hash, test/build input hashes, filesystem,
credentials, controlled environment and bounds. A provider change requires a new
run; package names or executable presence alone establish no qualification.

[Retained runs and failures](evidence/csh-074/README.md) keep macOS and Linux
results separate. The stock-host inventory remains a historical observation;
newly supplied bc/m4 do not rewrite its missing-provider entries.

## Assertions and clause accounting

The [original cases](../tests/host_language_cases.py) and
[operation cases](../tests/host_language_extended_cases.py) contain 168 fixtures:
165 selected-provider cases and three explicitly instrumented backing-store
cases. Each runs through direct execution and cshell `-c`, script file and stdin;
the instrumented cases use their separate executable in every mode. Utility
input is independent of shell source input. Nine additional signal witnesses
exercise SIGHUP, HOME fallback and SIGINT through direct/string/file execution.
The selected suite therefore has 681 strict assertions with no gap allowances.
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
are retained. Sanitizer diagnostics always fail.

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
the required `?\n` marker. SIGHUP recovery is unchanged. A second build alone
interposes `tmpfile` (EMFILE) and backing-store `fwrite` (ENOSPC); the production
editor has no fault switches. Both failures must diagnose, exit normally with
nonzero status and preserve the original input file; the no-fault control proves
that the same instrumented build can read the buffer.

The standalone xargs preserves every NUL delimiter, invokes once on empty input
unless suppressed, accepts `-x` without `-n`, and clamps oversized `-s` values.
Its error pipe transfers exec failure across `fork` so 126 and 127 are retained
on both systems. Upstream `vfork` shared-memory assumptions failed on Darwin.
Independent argument-vector and byte-budget oracles exercise these paths.

Full-page acceptance remains open. In particular, the selected native m4 fails
three additional strict [reproducers](../tests/host_language_residual_cases.py):
wrap registration order, missing `mkstemp`, and nonnumeric `substr` error status.
These are separate failing qualification attempts, never expected failures or
passes in the declared subset:

```sh
python3 tests/host_languages.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --remaining-contracts --record build/tests/host-languages-remaining.json
```

`--case 'xargs/*'` (repeatable) selects focused development checks and records the
selection. Only an unfiltered run supports the complete declared subset.
The heading map retains the remaining obligations, including editor interactive
warnings/help, other inherited signals, patch prompts/preprocessor effects,
xargs confirmation prompts, broad locale/default handling and resource faults.
The absence of an assertion is not a waiver or a qualified contract.

The [expanded evidence](evidence/csh-074/expanded/README.md) retains every new
failed provider attempt, corrected run and source identity. Dedicated Linux and
macOS CI jobs run the selected contracts in ordinary and ASan/UBSan builds and
upload the JSON evidence, independently of broader runtime job failures.
