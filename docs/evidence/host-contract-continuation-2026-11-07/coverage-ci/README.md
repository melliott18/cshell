# Additional coverage and CI repairs

This continuation adds 27 language cases for bc grammar, scale arithmetic,
function/array scope, ordered file input, awk record/field/getline state, ed
address/global/undo interactions and unused expr stdin. Sixteen UTF-8 text cases
cover wide/combining display columns, whole-character byte folding, uniq skips
and word/character counts. Fourteen formatting cases add 70 input-mode assertions
for precision/exponent boundaries, signed zero, dynamic fields, long double and
integer limits. Expected bytes are authored from the cited utility contracts.

The new empty-return bc case exposes GNU bc's rejection of POSIX `return()`.
Select checksum-pinned GNU bc 1.08.2 with that grammar production restored.
The generated parser is retained alongside the grammar patch; ordinary builds
need no Bison or documentation generator. Source archives and licenses remain
with the providers. The text audit selects five additional GNU coreutils 9.11
programs (expand, unexpand, fold, uniq and wc) through its verified manifest.

Ubuntu CI exposed inherited Make flags restoring -Werror in vendor builds and
-B triggering unnecessary upstream regeneration and configure races. Clear
MAKEFLAGS/MFLAGS/MAKEOVERRIDES at vendor boundaries; configured optimization and
sanitizer flags remain. A fresh Linux build of file, cp/rm, mkdir/mkfifo, ln and
touch passes with outer -Werror and ASan/UBSan flags.

Ubuntu's stock mv also returns status 1 after declined overwrites. POSIX mv
EXIT STATUS excludes declined files from failure. Select the already pinned
shared coreutils source with the same narrowly scoped decline repair as cp;
actual errors and --update=none-fail remain failures. Linux interactive and
operand-decision suites pass 39 and 68 assertions. Darwin retains its stock mv.

Native and Debian language coverage passes 1,089 assertions, the ordinary text
audit passes 948 with zero unavailable cases, and formatted contracts pass 789.
The bc sanitizer subset passes 112 and formatted sanitizers pass 687 on each
platform. The 160 filesystem harness tests, text/language harnesses, ownership
checks and live ticket identity check pass. Both a fresh sanitizer vendor build
and a forced (-B) file rebuild finish successfully. No host-wide limit changes
are made.

Review removed evaluation-order dependencies from two awk fixtures by assigning
function/conditional results before printing dependent values. The resulting
eight direct/public-mode assertions pass on each platform; the earlier full
records retain their actual fixture hashes.

`records.json` indexes compressed raw evidence by uncompressed SHA-256. It
retains the initial Linux bc failure, CI failures, setup attempts (missing local
find PATH, missing container lzip and unnecessary bc documentation generation),
and passing reruns separately. The initial native direct driver also mistakenly
looked for a bc symlink instead of using PATH fallback; those setup failures are
retained separately from provider failures. No successful later run erases them.
At code revision `6300187`, the previously failing hosted Ubuntu language and
terminal jobs pass, including their sanitizer stages. Filesystem and other hosted
runs are still being checked; local results do not stand in for hosted macOS
qualification.

CSH-073/074 retain full-page and common-default obligations. CSH-079 still needs
the unavailable disposable resettable Mac for the historical low-stack failure
and retains other declared partitions. No excluded host experiment is run and
no ticket is accepted solely from these finite suites.

## Reproduction and sources

```sh
make test-host-languages
make test-host-text-repaired
make test-host-formatted-contracts test-host-formatted-sanitize
python3 tools/tickets.py check --live
```

The recorded 948-assertion text runs use `tests/host_text.py --audit` with the
repaired profile; the broader Make target additionally requires its owned
boundary/capacity fixtures. The bc builder accepts `--build-root` for isolated
normal and ASan/UBSan artifacts.

Normative requirements: [bc grammar and operations](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/bc.html),
[awk expressions and input](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/awk.html),
[ed commands](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ed.html),
[fold columns and character boundaries](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/fold.html),
[uniq character skipping](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/uniq.html),
[printf conversions](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/printf.html),
and [mv exit status](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html).
[GNU bc 1.08.2 release](https://lists.gnu.org/archive/html/info-gnu/2025-05/msg00006.html)
identifies the retained archive. No reference utility output supplies an oracle.
