# CSH-122: literal and quoted ls filename rendering

Based on CSH-121 commit `a960541`, still awaiting integration. The retained Issue
8 `ls.html` is unchanged from the predecessor. DESCRIPTION, OPTIONS (-q, -1,
-d, -F, -p, -i, -r), OPERANDS, ENVIRONMENT VARIABLES and STDOUT define the oracle.

Forty-eight private graphs run through direct exec, command strings, script
files and stdin: 192 assertions per platform. Every non-NUL ASCII control byte
(1–31 and 127) appears in a filename, with printable spaces, quotes, backslashes,
shell metacharacters and a literal question-mark control. Directory, FIFO,
executable and directory-symlink names also contain controls. A nested guard
must remain unlisted. Sorting uses original C-locale names before replacement;
-q produces 33 colliding `control-?` names without losing entries. Optional inode
columns distinguish those entries. Reverse sorting, -d operands and directory
entries combine with plain, -F and -p rendering. Output goes to pipes, not PTYs.

Authored names supply expected characters. Independent listdir/lstat/stat probes
establish exact names, types and inode identities before provider execution.
The matcher accepts only inode padding; filename whitespace and embedded line
breaks are exact. Post-exec checks require unchanged metadata, file bytes, link
text and directory entries. Access time is excluded because inspection may
change it. No provider output supplies an expectation. No selected provider,
allowance, predecessor expectation or deadline changes.

Harness regressions exercise all four modes, exact rendering and replacement
collisions, incorrect output/inodes, fixture mutations, partial setup failure
before provider execution, failed exec, real timeout, child reaping and cleanup.
CSH-123 / issue #258 owns all 21 remaining utility contracts and all four retained
conditions. Non-ASCII names, other locales, terminal layouts, arbitrary graphs,
namespace races and resource failures remain unqualified. U-034/U-040 stay partial.

## Reproduction

Build `make -j4 cshell host-profile` with documented GNU providers on PATH. A
copy of the predecessor's private gfind is available in `build/prerequisites`;
its exact identity is recorded in the selected manifest. Use a private TMPDIR
owned by the invoking user and primary group:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh122-tmp" \
  python3 docs/evidence/csh-122/validate.py native
sh docs/evidence/csh-122/linux.sh
python3 docs/evidence/csh-122/collect.py
python3 docs/evidence/csh-122/verify.py
```

Linux reuses the unchanged CSH-119 shell/provider image and mounts this
checkout's tests and accounting read-only. Fixtures run as uid/gid 10001 on
bounded executable tmpfs mounts. The task-owned container is removed after
validation. Stock full and provider audits run separately and retain nonzero
results. No privileged fixture, protected mount or host-volume filling is used.

## Validation result — 2026-11-15

The complete requested make command passes on native macOS 14.8.7 arm64 and
Linux arm64/Docker (glibc 2.36). Both platforms pass all 204 filesystem harness
tests and 13 ownership tests. The selected host utility profiles each pass
1,162 assertions with zero failures or gaps.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Selected full filesystem profile | 13,563 pass / 0 fail | 13,603 pass / 0 fail |
| New filename-rendering assertions | 192 pass / 0 fail | 192 pass / 0 fail |
| Filesystem harness tests | 204 pass | 204 pass |
| Ownership tests | 13 pass | 13 pass |
| Stock full-audit failures | 901 unchanged | 578 unchanged |
| Stock provider-audit failures | 16 unchanged | 8 unchanged |
| Complete requested make command | exit 0 | exit 0 |

The CSH-121 native sampler timeouts do not recur in this run. This does not
establish their cause or rewrite the predecessor's retained failed run. No
sampler deadline, allowance, provider or predecessor expectation changed.

All 24 ticket tests and the offline/live identity checks pass with 123 shared
reservations. No sanitizer, separately hosted native-Linux or hosted CI pass is
claimed. Integration depends on the unmerged CSH-121 stack; neither integration
nor whole-utility qualification is claimed.

The evidence verifier passes: source and provider hashes, every new case/mode,
exact output/status/effects, cleanup, unchanged predecessor expectations and
exact stock failure identities are checked. There are no new stock failures.
The task-owned Docker container was removed. CSH-122 is ready for review.
