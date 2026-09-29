# Host languages, editors and argument construction

CSH-074 adds a strict **bounded C-locale subset** for awk, bc, ed, expr, grep,
m4, patch and xargs. These witnesses do not qualify entire normative pages or
the POSIX base system. [CSH-074](tickets/CSH-074-host-languages-editors.md) remains
the open owner of the full contracts and remaining editor conditions.

## Providers and reproduction

```sh
make test-host-languages       # Stock getconf PATH; missing tools are failures
make test-host-profile         # Selected profile plus existing host assertions
CSH_TEST_PATH="$PWD/build/host-profile/bin:$(getconf PATH)" make test-host-languages
```

The Dockerfile and Linux CI explicitly install Debian/Ubuntu `bc` and `m4`.
macOS uses OS providers and selects the actual Xcode/Command Line Tools m4 found
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

The [case definitions](../tests/host_language_cases.py) contain 82 independently
authored fixtures. Each runs four ways: direct execution of the inventoried
pathname and public cshell PATH dispatch through `-c`, script file and stdin.
Utility input is independent of shell source input. Six additional SIGHUP
witnesses use direct execution and cshell string/file `exec` dispatch. Thus the
default subset has 334 strict assertions and no known-gap allowance.

| Page | Bounded witnesses |
| --- | --- |
| [awk](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/awk.html) | Fields, records, variables, program files, arrays, loops, functions, ERE ranges, strings, math/formatting, getline/output files, exit/END and missing inputs |
| [bc](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/bc.html) | Arithmetic, scale, bases, arrays/functions/loops, library values, file/stdin ordering, quit and inaccessible operands; invalid bc programs are not used as normative error tests because their noninteractive behavior is undefined |
| [ed](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html) | Editing, addresses, marks, BRE/global commands, undo, file effects, error statuses, 4096-byte buffer, and synchronized SIGHUP recovery in cwd and HOME |
| [expr](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/expr.html) | Arithmetic precedence, comparisons, Boolean expressions, BRE capture/length, null/zero and syntax-error status |
| [grep](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/grep.html) | BRE/ERE/fixed patterns, case folding, inversion/count/line numbers, pattern files, multiple files, quiet/list modes, invalid patterns and missing inputs |
| [m4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/m4.html) | Definitions/options, argument substitution, arithmetic/strings, macro stack, conditionals, diversions, includes and explicit exit |
| [patch](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/patch.html) | Normal/context/unified formats, reversal, input/output selection, reject status/file and preservation of rejected input |
| [xargs](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/xargs.html) | Quoting/escaping, argument and line batches, replacement, EOF marker, default echo, tracing, size rejection, missing/non-executable utility, child nonzero/255 and stopping after 255 |

The [machine clause map](../tests/host_language_contracts.json) enumerates every
normative heading/subheading of the eight fetched Issue 8 pages, ending before
the informative sections. It retains page hashes, anchors, witness IDs and
individual section dispositions. A `partial` row is not a pass for that section;
`unqualified` explicitly retains missing coverage. The map separately retains
U-034 exec accessibility, U-040 defaults and `U-040/ed-buffer-temp-signal`.
Non-C locale behavior, complete grammars and option interactions, temporary
backing-store failures, capacity exhaustion, storage faults and other signal
conditions remain open. Neither a finite successful buffer nor a rejected
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
second handshake places the signal after the print operation has completed. SIGHUP must recover the exact buffer without overwriting the
original operand. A directory named `ed.hup` forces the cwd write failure and
HOME fallback without privileges or changes to the developer filesystem.
The driver reaps ed; inherited process-group cleanup catches descendants.
A fault test forces a hung editor and descendant, checks bounded failure and
cleanup, and verifies an unrelated child survives. Container zombies, where
present, are dead processes rather than successful evidence of reaping by PID 1.

## Strict SIGINT reproducer and remaining work

```sh
python3 tests/host_languages.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" \
  --ed-sigint --record build/tests/host-languages-sigint.json
```

This opt-in adds three strict PTY SIGINT transcript assertions. It is expected
to fail on the retained providers and is excluded from the declared passing
subset, never counted as a gap or a pass. Recovery data and both streams remain
in the record. macOS writes the marker to stderr; the normative ASYNCHRONOUS
EVENTS section calls for stdout. The published
[Apple source](https://github.com/apple-oss-distributions/text_cmds/blob/main/ed/main.c)
corroborates that stream choice, but is not asserted to be the exact installed
build. GNU ed writes a leading newline before the stdout marker; the strict
transcript mismatch remains pending a normative disposition or provider change.
No provider repair or whole SIGINT contract qualification is claimed.
