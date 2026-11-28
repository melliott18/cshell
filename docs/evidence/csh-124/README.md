# CSH-124: UTF-8 ls character rendering

Based on CSH-123 commit `7d94d87`, still awaiting integration. The retained
Issue 8 `ls.html` is byte-for-byte unchanged. OPTIONS (-q, -1, -d, -i, -F, -p,
-r), DESCRIPTION, OPERANDS and STDOUT supply the listing oracle. ENVIRONMENT
VARIABLES separates LC_CTYPE interpretation/printability from LC_COLLATE sorting.
STDERR and EXIT STATUS require empty diagnostics and success for these fixtures.

Forty-eight cases run through direct exec, command strings, script files and
stdin: 192 assertions per platform. Authored filenames contain printable Greek,
CJK and Deseret characters (two, three and four UTF-8 bytes), non-printable C1
controls U+0085/U+009F, ASCII controls, punctuation and spaces. A bounded Python
child calls libc iswprint in an installed UTF-8 LC_CTYPE with C LC_COLLATE and
requires the authored classifications before the provider can run. The parent
locale is unchanged. Byte-path listdir checks exact filename storage; lstat and
stat measure type, inode and symlink referents independently of ls output.

LC_ALL is empty, LANG and LC_COLLATE are C, and LC_CTYPE selects the probed
UTF-8 locale. Literal output preserves authored bytes. With -q, each non-printable
character becomes one question mark, including two-byte controls; printable
multibyte characters stay intact. Sorting uses original UTF-8 bytes before
replacement, in either direction, preserving collisions with literal question
marks. Directory entries and reverse-authored -d operands combine plain/-F/-p
styles and optional inode numbers. Only unspecified inode padding is flexible.

Every case requires exact stdout, empty stderr, zero status, unchanged object
metadata, bytes, link contents and directory entries, and successful cleanup.
Access time is excluded because inspection can change it. FIFOs are never
opened. Harness tests reject byte-wise replacement, changed printable characters,
wrong order/inodes, missing/extra output and fixture mutations. Missing or wrong
locales, probe failures/timeouts, partial setup, failed exec and real provider
timeouts must fail with cleanup; timed-out providers must be reaped.

No selected provider source or allowance changes. CSH-125 / issue #262 owns all
21 remaining utility contracts and four retained conditions. Invalid encodings,
arbitrary repertoires, other locale definitions, non-C collation, terminal
layouts, namespace races and resource failures remain unqualified. U-034/U-040
stay partial. This qualifies host utility behavior through cshell, not a new
shell runtime feature.

## Reproduction

Build `make -j4 cshell host-profile` with documented GNU prerequisites on PATH.
The private `build/prerequisites/gfind` is copied from the CSH-123 worktree;
its exact identity is retained in the selected manifest. Use a private TMPDIR
owned by the invoking user and primary group:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh124-tmp" \
  python3 docs/evidence/csh-124/validate.py native
sh docs/evidence/csh-124/linux.sh
python3 docs/evidence/csh-124/collect.py
python3 docs/evidence/csh-124/verify.py
```

Linux reuses the unchanged CSH-119 shell/provider image with this checkout's
tests and accounting mounted read-only. Fixtures run as uid/gid 10001 on
bounded executable tmpfs. Remove the task-owned container after collection.
Native providers are rebuilt from the pinned sources. Separate stock full and
provider audits must retain their nonzero results and exact failure identities.
No privileged fixture or host-volume exhaustion is used.

## Validation result — 2026-11-17

Native macOS 14.8.7 arm64 and Linux arm64/Docker (glibc 2.36) pass all 214
filesystem harness tests, 13 ownership tests and 1,162 host-profile assertions
with zero gaps. The new UTF-8 cases use en_US.UTF-8 on macOS and the installed
locale recorded in the Linux report, with LC_COLLATE fixed to C.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Selected full filesystem profile | 13,819 pass / 0 fail | 13,891 pass / 0 fail |
| New UTF-8 assertions | 192 pass / 0 fail | 192 pass / 0 fail |
| Filesystem harness tests | 214 pass | 214 pass |
| Stock full-audit failures | 901 unchanged | 578 unchanged |
| Stock provider-audit failures | 16 unchanged | 8 unchanged |
| Complete requested make command | **exit 2**, text timeouts below | exit 0 |

The native broad command timed out in the existing CSH-073
`strings/offset-decimal/direct` and `strings/offset-decimal/string` cases.
Both returned status -9 after the unchanged five-second capture bound with no
output; the runner killed the process groups and removed their fixtures.
Initial text totals were 864 pass, 2 fail, 2 unavailable. The unavailable cases
are the pre-existing unsupplied Darwin filesystem-ENOSPC boundary, not new
allowances. The original failed command and `native-text-initial.json.gz` remain
in this evidence directory.

After both stock audits finished, `recheck_text.py` reran the exact text-profile
selection with unchanged providers, inputs, limits and assertions: 866 pass,
0 fail, the same 2 unavailable; status 0. `complete_profile.py` then ran the two
language recipes skipped by make after the initial text failure: all 9 harness
tests and 1,089 assertions passed. Their command/timing records, logs and reports
are retained. These separate passes do not erase the failed broad command or
establish the cause of the timeouts. No clean full native rerun or root-cause
fix is claimed. CSH-073 retains the existing text-environment limitation.
Reproduce the separate checks after the main validation with:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh124-tmp" \
  python3 docs/evidence/csh-124/recheck_text.py
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh124-tmp" \
  python3 docs/evidence/csh-124/complete_profile.py
```

The evidence verifier passes: source/provider provenance, exact new outputs and
locale settings, unchanged predecessor expectations, exact stock failure
identities and cleanup are checked. All 24 ticket tests and offline/live identity
checks pass with 125 reservations. The task-owned Docker container was removed.
No sanitizer, separately hosted native-Linux or hosted CI pass is claimed.
CSH-124 is ready for review, stacked on unmerged CSH-123; CSH-125 owns all remaining
filesystem contracts and the four retained conditions. Neither integration nor
whole-utility qualification is claimed.
