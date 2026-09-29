# Filesystem and pathname qualification

CSH-072 adds a **bounded selected profile** for 21 exec-accessible utilities.
It does not qualify complete utility pages, U-034/U-040 as a whole, or a complete
POSIX system. [CSH-079](tickets/CSH-079-filesystem-remaining-contracts.md) owns each
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
contracts remain explicitly open in CSH-079. No protected mount or real disk
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

The declared extension excludes strict unresolved provider contracts, whose
expectations remain in `--provider-audit`. Native Apple `find` silently succeeds
on a logical cycle; Apple `pax` returns zero for a truncated member, broken pipe
and file-size-limit write error. Those four contracts remain unqualified under
CSH-079. Linux ENOSPC for pax is separately audited. The selected profile has
zero allowances; diagnostic audit results cannot qualify a failed contract.

[Extended evidence](evidence/csh-072/extended/README.md) retains each result,
including the initial incorrect closed-input fixture and its correction.
The focused filesystem workflow retains selected and strict audit artifacts on
Ubuntu and macOS. Its diagnostic audit may fail without blocking the selected
subset, and its JSON keeps every failure visible.
