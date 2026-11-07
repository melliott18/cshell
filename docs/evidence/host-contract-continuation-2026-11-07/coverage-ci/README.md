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

Native and Debian language coverage passes 1,089 assertions; formatted contracts
pass 789. The bc sanitizer subset passes 112 assertions on both; native formatted
sanitizers pass 687. Final provider identities, text and hosted CI results will
be retained after the remaining runs finish. Earlier records are not relabeled.

CSH-073/074 retain full-page and common-default obligations. CSH-079 still needs
the unavailable disposable resettable Mac for the historical low-stack failure
and retains other declared partitions. No excluded host experiment is run and
no ticket is accepted solely from these finite suites.
