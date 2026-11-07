# Awk, expr, ed and formatting provider repairs

This continuation repairs the demonstrated multibyte failures and the selected
printf allocation-failure paths. CSH-073 and CSH-074 still retain full-page
coverage obligations; CSH-079 still retains the historical Darwin low-stack
investigation and other explicitly unqualified partitions. None is accepted.
The user has no disposable resettable Mac available. No excluded low-stack exec
experiment was performed on the personal host.

## Selected provider changes

- Build GNU Awk 5.3.2 offline from a checksum-pinned complete source archive,
  with its license and reviewable patch. Select POSIX mode regardless of ambient
  POSIXLY_CORRECT, preserving character-oriented string/regex operations and
  locale-aware numeric input while program literals retain the decimal point.
  GNU Awk's POSIX-mode system() previously exposed raw wait status (1792 for
  exit 7); the patch returns the command exit status as required by Issue 8.
- Select GNU expr from the already-required Homebrew coreutils package on
  Darwin; Linux retains its GNU coreutils expr. No system package was installed
  or overwritten. The run records retain each executable hash and package/OS
  identity; the focused final native record also names GNU coreutils 9.3.
- Link the private GNU ed 1.22.6 and its fault helper with the configured GNU
  regex implementation shipped in the pinned M4 archive. The build explicitly
  requests included regex on both platforms. This repairs Darwin's multibyte
  BRE backreference failure. Optional text-profile overrides retain this ed
  selection rather than restoring the system-regex build.
- The FreeBSD printf parser now calls a small standalone adapter around pinned
  GNU vasnprintf. This avoids the attested Darwin __Balloc_D2A failure paths.
  Formatting completes before exact bytes are written; allocation, overflow and
  write errors propagate through the existing diagnostic/status adapter.
  Conversion buffers are released on both success and failure. This is a
  selected-provider replacement, not a repair or qualification of stock libc.
- The allocation audit also exposed a dropped conversion character after the
  parser's L modifier. Preserve that character in the separate format buffer.
  Truncated L modifiers now produce the missing-format diagnostic before
  accessing beyond the format buffer. L is a declared provider extension,
  not a POSIX utility requirement.
- Skip GNU vasnprintf's zero-length memcpy when the zero numerator has a null
  limb pointer. Linux UBSan exposed this in existing zero-format cases; expected
  output remains unchanged. The patch is retained beside the pinned archive.

The M4 build records now include the GNU library hash and included-regex choice.
Normal, sanitizer and uninstrumented resource builds have separate output roots;
ASan startup mappings must not contaminate measured resource limits. These
standalone utilities and the portability library are never linked into cshell.

Normative sources: [awk string functions, environment and system()](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/awk.html),
[expr matching](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/expr.html),
[ed regular expressions and substitution](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html),
and [printf](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html).
[GNU's release announcement](https://lists.gnu.org/archive/html/info-gnu/2025-04/msg00003.html)
identifies the Awk archive; its bytes, SHA-256 and licenses are retained locally.
GNU documents its [regex portability replacement](https://www.gnu.org/software/gnulib/manual/html_node/regcomp.html).

## Strict assertions

All 22 previous multibyte cases now belong to the ordinary repaired profile,
without failure allowances. Fifteen additional cases check combining-character
positions, UTF-8 field separators and regex splitting, global replacement,
French numeric input versus program literals, command exit statuses, expr
backreferences/empty/longest captures and intervals, and ed backreferences,
capture replacement and numbered substitutions. The focused selection is 148
assertions; the complete language/editor suite is 981 assertions, including
fault helpers and signal recovery.

The Darwin allocation probe arms real malloc/calloc/realloc interposition only
inside the selected formatter. It writes caller image/symbol, size and ordinal
before returning NULL. A control must attest execution inside GNU vasnprintf;
a libc-only control cannot qualify the replacement. Every observed allocation
ordinal is then failed individually. Fixed, scientific, alternate general and
hexadecimal formats use precision 10000, with both ordinary and L conversions.
All hexadecimal normalization alternatives are independently authored values
for exactly one. Tests require exact success or a normal status-1 ENOMEM
diagnostic, bounded output, child reap and PID disappearance. This is controlled
allocator failure, not physical RAM exhaustion or an injected API return.

## Validation and boundaries

| Check | Native macOS 14.8.7 / Darwin 23.6 arm64 | Debian 12 arm64 |
| --- | --- | --- |
| Language/editor profile | 981 PASS | 981 PASS |
| Focused multibyte/locale selection | 148 PASS | Covered by full profile |
| Formatted contracts | 719 PASS | 719 PASS |
| Selected formatter allocation audit | 176 PASS, 0 FAIL | Darwin interposition is not applicable |
| Native-libc comparison | 4 PASS, 6 FAIL retained | Not rerun |
| Awk/ed/M4 ASan/UBSan | 429 PASS | 429 PASS |
| Formatted-provider ASan/UBSan | 617 PASS | 617 PASS |
| Post-startup 64 KiB stack formatting | PASS | PASS |
| 16 MiB address-space formatting ENOMEM | Not a Darwin capability | PASS |

Runtime integration passes 3,950 assertions and the runtime PTY suite passes
33 on each platform. The native harness passes 37 tests; ownership/inventory
checks, 160 filesystem controls, ticket validation and the live identity check
(114 reservations) pass.

The source and helper hashes identify exactly what each record exercised.
The final GNU zero-conversion patch is included in the rebuilt library and
its linked clients; records identify each actual revision separately. Later clause prose and version-recording changes do not
retroactively replace those source identities. The native stock-libc comparison
still fails at the original three allocator sites in direct and exec modes;
passing replacement tests do not erase those vendor failures.

## Reproduction

```sh
make test-host-languages
python3 tests/host_languages.py ./cshell --path "$PWD/build/host-profile/bin:/bin:/usr/bin" --multibyte-audit --record build/multibyte.json
make test-host-formatted-contracts
make test-host-formatted-allocator       # Darwin selected-provider audit
make test-host-formatted-libc-audit      # Darwin comparison; remains nonzero
make test-host-formatted-sanitize
```

The existing host-language CI job now also retains the normal Darwin allocator
record before cleaning for sanitizer builds. The checked source archives make
provider builds offline; gencat/locales and the documented existing host packages
remain prerequisites. `records.json` lists retained compressed records with
uncompressed SHA-256 hashes. `resource-check.py.gz` is the exact focused resource
driver and accepts its result filename as the only argument.

Initial attempts are retained: the first new Awk run had four raw-wait-status
failures; the expanded allocation audit had eight L-format control failures
before the conversion-buffer correction. Linux formatter sanitizers then found
20 zero-conversion failures at a null zero-length memcpy; those failures and
the corrective vendor patch are retained. Initial truncated-L sanitizer runs
used stale provider binaries and each retained ten failures; explicitly rebuilding
the printf targets before rerunning produced 617 passes on each platform.
These failed records remain separate from the final binaries. A clause-ledger setup typo named a
nonexistent Input Records heading and was corrected to STDIN. Passing reruns
never recategorize these as permitted gaps.

## Acceptance review

CSH-073's five retained capabilities remain supplied, including ed signal
recovery. It still lacks full-page/common-default qualification for its 25
utilities. CSH-074's demonstrated awk/expr/ed failures are repaired, but its
section ledger still retains other grammar, command, locale, error and
interaction contracts across eight utility pages. CSH-079's tested formatter
allocation paths now have a qualified replacement; its historical low-stack
investigation cannot be completed without the unavailable resettable Mac, and
other declared locale/format partitions remain open. No ticket is marked done
or closed on the strength of these finite passing suites.
