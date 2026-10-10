# Filesystem and pathname qualification

CSH-072 adds a **bounded selected profile** for 21 exec-accessible utilities.
It does not qualify complete utility pages, U-034/U-040 as a whole, or a complete
POSIX system. [CSH-087](tickets/CSH-087-filesystem-environment-followup.md) owns each
remaining contract and the four original retained conditions. Implementation
ownership stays with the selected utility/libc/platform vendor.

The [machine-readable section map](../tests/host_filesystem_contracts.json)
records the Issue-8 source URL/hash, every normative page heading (including pax
subsections), concrete assertion IDs, and individual unqualified dispositions.
Sections after APPLICATION USAGE are informative and do not impose runtime
assertions. The map and [current ownership overlay](../tests/host_contracts.json)
are checked by `make test-host-inventory`.

## Running the profiles

```sh
make test-host-filesystem        # bounded stock subset, missing providers fail
make test-host-filesystem-audit  # also require Issue-8 pathname contracts
make test-host-profile           # provision the opt-in PATH, require declared assertions
make test-host-filesystem-provider-audit # strict extended vendor audit; failures remain failures
```

The stock audit is deliberately strict. A failure is not an allowance in the
selected profile. `HOST_FILESYSTEM_FLAGS` accepts `--path`, `--fixture-root` and
`--sanitizer`; the runner always records the PATH actually used. The profile
target selects its own PATH explicitly and includes the audit automatically.
The ordinary system PATH and shell builtin allocation are unchanged.

Docker and Linux CI install Debian/Ubuntu `file` and `pax` in addition to the
existing build/profile dependencies. No package is installed on the developer's
host by provisioning. Both native and Linux runs retain actual provider paths,
realpaths, hashes, OS/build identity, package versions, environment and limits.
The selected local providers are built from
[`tools/host-profile/paths.c`](../tools/host-profile/paths.c); the source and build
inputs are hashed in each run. They are standalone programs, not linked into
cshell. macOS still uses Homebrew coreutils for the pre-existing test/bracket
profile requirement.

## Assertions and independent oracles

[`host_filesystem_cases.py`](../tests/host_filesystem_cases.py) supplies ordinary
cases through direct exec and public cshell string, script-file and stdin modes.
Each invocation gets a new private tree. Python creates bytes, directories,
links and timestamps; Python/stat and a separate ustar reader check effects.
The selected utility never generates expected output for itself.

| Contract | Supplied bounded evidence |
| --- | --- |
| basename, dirname | Slash normalization, root, plain names, matching/nonmatching/whole-name suffixes. |
| cp, dd | All byte values, symlink following/physical recursive copy, mode/mtime preservation, block skip/count/swab; dd fails under a 512-byte child file-size limit and retains exactly 512 bytes. |
| df, du, file | Portable df fields and ceiling percentage, du KiB from independently measured st_blocks, empty/directory classification words. No free-space snapshot or vendor magic database is used as its own oracle. |
| find, ls | Authored file/link/prune/depth cases; UTF-8 `?` at 64 levels; 512 C-locale names in exact order and hidden-name handling. |
| ln, mkdir, mkfifo | Inode identity, dangling symlink text, replacement, explicit modes, parent creation and FIFO type. |
| mv, rm, rmdir | Byte/metadata/link preservation, replacement/removal, force-missing behavior, nonempty-directory errors, parent deletion. |
| pathchk, pwd | Portable-name rejection and measured filesystem component boundary; physical cwd with a NAME_MAX-length component. This is not a total PATH_MAX or inaccessible-ancestor qualification. |
| pax | Copy-tree bytes/link text; ustar output decoded independently; independently authored ustar input extracted with explicit mode preservation. Apple COPYFILE_DISABLE=1 suppresses its metadata extension for the declared archive profile. |
| readlink, realpath | Exact link bytes/newline suppression, missing-last-component resolution, strict existence, missing prefixes, dangling links, loops, directory requirements, last-option precedence and closed-output errors. |
| rm terminal | Owned controlling PTY, yes/no responses, exact Apple/GNU C-locale prompts and independently verified file state; direct exec and cshell string/script-file modes. |

Status and deterministic bytes are exact. POSIX's positive error classes and
unspecified diagnostics use positive/nonempty predicates; signal death never
satisfies a positive error predicate. df allows column spacing and dynamic live
counts while checking its normative header and percentage relationship. du uses
stat block counts. file permits unspecified description text around the required
classification. dd checks exact authored record counts plus a bounded vendor
transfer-statistics line. These policies are explicit in the runner and records.

## Selected provider repairs

The stock providers omit the required readlink nonlink diagnostic and differ in
realpath's Issue-8 option support. The selected readlink dynamically reads link
contents, diagnoses errors and checks output flushing. The selected realpath
uses libc resolution for existing paths, with a stat check that preserves
regular-file directory-component errors on Darwin. After ENOENT, `-E` resolves
components and symlinks before permitting only a missing final component;
`-e` requires existence and the last option wins. Missing-final fallback permits
at most 40 symlink expansions. Both providers diagnose invalid usage and output
errors. Stock-provider failures remain separately retained.

## Bounds and remaining work

The shared smoke/PTY harness owns and reaps each process/session. Cases cap
execution at five seconds, captured output at 64 KiB, ordinary file writes at
1 MiB, descriptors at 64 and CPU at six seconds; inherited lower resource limits
still apply. The dd fault deliberately lowers only the child file limit to 512
bytes and ignores SIGXFSZ so the provider must handle the write error. No actual
disk is filled. Cleanup is checked after success, failure and timeout; missing
providers, locales or fixture capabilities are failed setup, never passes.

The four retained condition IDs stay in the ownership ledger. CSH-072 supplies
larger-directory, deep UTF-8 and terminal-prompt capabilities; inaccessible
ancestors, total pathname limits, actual descriptor exhaustion, non-C collation,
mount boundaries, quotas, filesystem-capacity exhaustion/EIO, further archive formats and other individual page
contracts remain explicitly open in CSH-085. No protected mount or real disk
contents are used. [Retained results and commands](evidence/csh-072/README.md)
separate the stock audit, qualified subset and full-system limitations.

## Extended traversal, links, metadata, archives and I/O

[`host_filesystem_extended.py`](../tests/host_filesystem_extended.py) adds bounded
cases in all five areas, each through direct exec and cshell string/file/stdin:

- Traversal: distinguish `cp -RH/-RL/-RP` operand links from nested links;
  `find -H/-L`, physical operands, precedence and depth order; physical recursive
  removal of a symlink cycle and recursive FIFO copying.
- Links: `ln -L/-P` and last-option precedence, symlink-inode hard links,
  preserved existing targets, rename inode identity and decrementing link counts.
- Metadata: `cp -p` mode, source uid/gid and both timestamps; symbolic creation
  modes, parent/default umask behavior and isolated `touch -a/-m` updates.
- Archives: independently authored ustar directory/file/hard-link/symlink/FIFO
  graphs; list, selection, substitution, append and bad-checksum errors. The
  independent reader checks exact member sets, bytes, types, modes, times,
  link graphs and ustar headers without extracting provider output. It rejects
  duplicate entries and nonregular or oversized output before reading.
- I/O: EPIPE, EBADF, bounded EFBIG, directory reads and ENOTDIR. Linux adds real
  ENOSPC from its verified virtual `/dev/full` character device. Each descriptor
  or file-limit wrapper probes the expected kernel errno before executing the
  inventoried utility; missing, setup-failure or exec-failure markers fail the
  assertion. This does not supply a full filesystem, quota or EIO capability.

The selected profile now requires the previously failing provider contracts with
`--provider-audit`. It selects GNU find on macOS and a pinned locally built pax
on both platforms. The latter preserves 12-bit ustar modes and drains final
partial writes or returns failure. Its upstream source already handles truncated
members and EPIPE correctly. [Source provenance and exact patches](../tools/host-profile/vendor/pax/CSHELL-CHANGES.md)
are retained alongside the complete upstream release and license notices.

The stock Apple find/pax and Linux pax failures remain real, separately retained
failures. They are not repaired in the system installation. The focused workflow
requires all selected assertions and runs the stock extension audit as a
separate diagnostic step. Its passing selected step cannot be inferred from the
workflow status alone; detailed results and audit exit codes remain artifacts.

[Extended evidence](evidence/csh-072/extended/README.md) preserves the original
failures and intermediate fixture/CI corrections. The
[provider repair evidence](evidence/csh-072/repairs/README.md) records the new
selected scope and its integration checks. The
[remaining-environment table](tickets/CSH-080-filesystem-remaining-contracts.md#required-environments-and-manual-work)
distinguishes automated local work, disposable privileged environments and any
separate physical-terminal claim.

## CSH-080 ordinary contracts and provider faults

`host_filesystem_remaining.py` adds 60 cases (240 assertions in direct exec and
cshell string/file/stdin modes): empty/slash/UTF-8 pathname policies, dd
conversion and seek combinations, continuation after operand errors, symbolic
creation modes, pathchk -P combinations, find expressions/batched exec, C-locale
ls switches, pwd logical/physical precedence and touch date forms.

Apple dd incorrectly reports padded short input as a whole record. The opt-in
macOS profile selects GNU gdd from the existing coreutils prerequisite; the
stock audit retains the failure. No output/status filtering is used.
The exact counts remain required. `conv=ascii/ebcdic/ibm` is XSI-shaded and
outside the selected base profile; numeric touch timezone offsets are extensions.

`make test-host-filesystem-allocation` compiles the unchanged local pathname
provider with test-only call-site ENOMEM controls. It checks every allocation
reached by six successful scenarios in all four invocation modes, plus a
non-triggering end control. A checked marker distinguishes an injected failure
from loader/setup failure. Allocating libc calls can be made to return ENOMEM;
libc-internal allocation paths are not instrumented. These results do not
qualify kernel ENOMEM, quotas, filesystem ENOSPC or EIO.

[CSH-080 evidence](evidence/csh-080/README.md) separates selected, stock and
injected runs. The [residual ledger](../tests/host_filesystem_residuals.json)
retains every utility and all four original condition IDs under CSH-084,
including required environments and why current witnesses do not suffice.

## CSH-084 residual environments

`make test-host-filesystem-residual` runs 26 cases / 104 assertions on the
selected PATH. The same cases are mandatory in `make test-host-profile` and
remain strict in the separate stock audit. They add:

- Fourteen ordinary permission denials across thirteen utilities. A private
  directory loses all search bits, and Python independently requires EACCES
  from stat before dispatch. The record retains real/effective IDs, groups,
  mode and probe errno. Root or a filesystem ignoring these bits fails setup.
  Access is restored before independent file effects and in unconditional cleanup.
- Four `file -m` databases with authored string, continuation, hexadecimal
  offset and escaped-space rules and independent binary samples. Exact messages
  follow the normative magic rules; no installed database generates the oracle.
- Four readlink cases preserving `ff fe 80` bytes under C and UTF-8, with and
  without the final newline. These are selected bytes, not every repertoire.
- Four basename/dirname stdout EBADF/EPIPE cases using the existing independently
  probed kernel-fault wrapper; signal death cannot satisfy positive error status.

The selected providers require no additional repairs. The 24 harness regressions
include root/ineffective-denial rejection, altered effects/output, failed fixture
writes/symlinks, and deadline cleanup for permission, magic and byte-link fixtures.
Timeout helpers disable Python site initialization and allow two seconds to
start and report their PID; every owned PID must disappear after the deadline.
These synthetic setup failures test the harness, not real capacity exhaustion.

[CSH-084 evidence](evidence/csh-084/README.md) separates native, Linux and stock
results. [CSH-085](tickets/CSH-085-filesystem-isolated-contracts.md) retains every
remaining per-utility contract, environment and reason in the
[residual ledger](../tests/host_filesystem_residuals.json), including the five
utilities with no new CSH-084 witnesses. Existing four condition IDs and original
CSH-064 reasons remain unchanged. ACLs, privileged credentials, mount boundaries,
quotas, actual filesystem ENOSPC/EIO and libc-internal failures are not supplied.

## CSH-085 private graph, magic and subsecond environments

`make test-host-filesystem-isolated` runs 28 cases / 112 assertions through
direct exec and public string/file/stdin modes. The selected full profile also
requires them. Seven `du` cases cover recursive 512-byte totals, `-a -k`, `-s`
with a hard-link pair, operand `-H`, nested `-L`, and last-option precedence.
Pre-exec lstat measurements and a fixed authored graph supply the expected
records; a post-exec identity/allocation comparison rejects changed fixtures.
Output ordering is unspecified; duplicate, missing and extra records fail.

Sixteen `file -m` cases pair matching and nonmatching samples for byte equality,
less/greater comparisons, hexadecimal/octal masks, set/missing bits and native
short equality. Five `touch` cases check period/comma fractions, T/space date
separators, UTC/fixed-offset local time and separate access/modification changes
using exact nanosecond metadata. Setup independently proves both timestamps
representable; an unavailable capability is a setup failure, never a pass.

These are private directories under the runner's unprivileged identity, not
isolated mounted volumes. The [evidence](evidence/csh-085/README.md) separates
native/Linux selected runs, stock failures, provenance and cleanup. The
[current ledger](../tests/host_filesystem_residuals.json) and
[CSH-086](tickets/CSH-086-filesystem-unsupplied-contracts.md) retain every open
contract, required environment, reason and vendor owner. No privilege, actual
capacity, cross-device, shared-extent or full utility claim is added.

## CSH-086 owned-terminal overwrite decisions

CSH-086 adds 39 required assertions for C-locale `cp`/`mv` yes/no overwrite
responses, independent `cp -f/-i` behavior and last-option `mv -f/-i` precedence.
Each runs in an owned foreground PTY through direct provider exec and cshell
command-string/script dispatch. A test-only exec helper separates stdout from
terminal stderr and records the armed descriptor environment before exec.
Authored bytes prove source/destination preservation or replacement. Exact
vendor prompt text is checked separately from normative zero/nonzero status.
There is no shell-stdin-mode claim for these terminal interactions.

The selected profile builds pinned GNU coreutils 9.7 `cp` with a source repair
for declined-copy status; stock Apple cp and native GNU cp 9.3 declines remain failures.
The profile records the source archive, patch and executable SHA-256 identities.
Builds are offline from the vendored release and take longer than the shell
build. C-locale builds disable NLS, ACL and SELinux; those contracts stay open.
Run `make test-host-filesystem-interactive` for the focused subset; the full
`make test-host-profile` requires it automatically with zero allowances.

CSH-087 owns every unsupplied environment and the four immutable original
conditions. These bounded terminal decisions do not qualify a whole utility,
recursive/multiple-operand interaction, other locales, ACL/privileged ownership,
cross-device behavior, real filesystem exhaustion or libc-internal faults.
`ln -i` is a vendor extension absent from the selected base specification; it
is no longer mislabeled as an unqualified POSIX interactive requirement.
See `docs/evidence/csh-086/README.md` for native/Linux results and provenance.
