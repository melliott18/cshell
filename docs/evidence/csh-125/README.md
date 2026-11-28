# CSH-125: ls stream formatting and precedence

Based on CSH-124 commit `0d0fd9c`, still awaiting integration. The retained
Issue 8 `ls.html` is byte-for-byte unchanged. DESCRIPTION, OPTIONS (-m, -1, -l,
-d, -F, -p, -r), OPERANDS and STDOUT supply the ordering, suffix, separator and
precedence oracle. ENVIRONMENT VARIABLES supplies C locale and COLUMNS; these
witnesses exercise the selected providers' COLUMNS-controlled stream widths.
STDERR and EXIT STATUS require empty diagnostics and success.

One hundred cases run through direct exec, command strings, script files and
stdin: 400 assertions per platform. The private graph contains regular files,
an executable, directory, FIFO and directory symlink. Commas and spaces in
filenames remain literal data. Independent pre-exec lstat/stat/listdir probes
establish types, modes, inodes, referents and exact directory entries.

The 96 matrix cases combine directory listings and reverse-authored -d operands,
plain/-F/-p suffixes, C/reverse order, COLUMNS=1/4096, and -m, -1 -m, -l -m,
-m -1. Four further cases cover empty directories and a single comma-containing
filename at both widths. At width 4096 the entire authored list fits. At width
1 every entry exceeds the line width and each separator must wrap. No filename
is truncated. Only the standard's optional single space before a wrapping
newline is flexible; an initial blank line, extra/trailing separator, wrong
order, omitted suffix or extra output fails. The final -1 cases require one
entry per line without stream separators. No width-boundary algorithm or
terminal default is inferred from these two extremes.

Every case requires exact stdout, empty stderr, zero status, unchanged object
metadata, bytes, link text and directory entries, and successful cleanup.
Access time is excluded because inspection can change it. FIFOs are never
opened. Six harness regressions cover the full literal oracle matrix and output
corruption, integration in all four modes, object mutations, probe failures,
partial setup, failed exec and bounded provider timeouts with process reaping.

Selected providers, sources and build flags are unchanged. Stock Apple ls adds
148 failed assertions: it emits an initial blank line when the first name
exceeds COLUMNS=1, including the single-file case. These are failures, not
allowances. Every older stock failure and expectation must remain intact.
CSH-126 / issue #264 owns all 21 remaining utility contracts and four retained
conditions. Intermediate widths, multibyte display widths, terminal defaults,
other option combinations, arbitrary graphs, invalid filename encodings,
non-C collation and resource failures remain unqualified. The native filesystem
rejected a disposable invalid-byte filename with EILSEQ during scope exploration;
no invalid-encoding qualification is claimed. U-034/U-040 stay partial.

## Reproduction

Build `make -j4 cshell host-profile` with documented GNU prerequisites on PATH.
The private `build/prerequisites/gfind` is copied from the CSH-124 worktree;
its exact identity is retained in the selected manifest. Use a private TMPDIR
owned by the invoking user and primary group:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh125-tmp" \
  python3 docs/evidence/csh-125/validate.py native
sh docs/evidence/csh-125/linux.sh
python3 docs/evidence/csh-125/collect.py
python3 docs/evidence/csh-125/verify.py
```

Linux reuses the unchanged CSH-119 shell/provider image with this checkout's
tests and accounting mounted read-only. Fixtures run as uid/gid 10001 on
bounded executable tmpfs. Remove the task-owned container after collection.
Native providers are rebuilt from pinned sources. Separate stock full and
provider audits retain their nonzero results and exact failure identities.
No privileged fixture or host-volume exhaustion is used.

## Validation result — 2026-11-18

Native macOS 14.8.7 arm64 (UID 501) and Linux arm64/Docker with glibc 2.36
(UID/GID 10001) pass the complete 46-target required Make command. Both pass
all 220 filesystem harness tests, 13 ownership tests and 1,162 host integration
assertions with zero gaps. All 24 ticket tests and offline/live identity checks
pass with 126 reservations.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Selected full filesystem profile | 14,219 pass / 0 fail | 14,291 pass / 0 fail |
| New stream-format assertions | 400 pass / 0 fail | 400 pass / 0 fail |
| Filesystem harness tests | 220 pass | 220 pass |
| Stock full-audit failures | 1,049 (901 retained + 148 new) | 578 unchanged |
| Stock provider-audit failures | 16 unchanged | 8 unchanged |
| Complete requested make command | exit 0 | exit 0 |

The evidence verifier passes: exact new outputs and COLUMNS settings, every
predecessor expectation, exact stock failure identities, source/provider
provenance and cleanup are checked. No allowance was added. Native stock's
148 new failures all have successful status, empty diagnostics, unchanged
fixtures and an extra initial newline; only stdout fails. The selected GNU
provider passes all new cases. The task-owned Docker container was removed.
No sanitizer, separately hosted native-Linux or hosted CI result is claimed.

CSH-125 is ready for review, stacked on unmerged CSH-124. CSH-126 owns every
remaining filesystem contract and the four retained conditions. Integration
and whole-utility qualification are not claimed.
