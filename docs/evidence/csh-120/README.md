# CSH-120: recursive ls hidden directories and directory aliases

Based on CSH-119 commit `b9eb862`, not yet integrated. No shell implementation
or selected-provider changes. The retained Issue 8 ls source is identical to
CSH-119 and checked against the section-map SHA-256. DESCRIPTION, OPTIONS
(-R, -A, -a, -L, -r, -1, -i, -F, -p) and STDOUT define the bounded oracle.

Forty-eight private acyclic graphs run in direct exec and string/file/stdin
modes, for 192 assertions per platform. The authored graph includes nested
hidden directories, a sibling branch, visible and hidden directory symlinks,
and an unchanged guard outside the operand. Hidden directories are descended
into only when selected; directory links are descended into only with -L.
Dot and dot-dot are listed with -a but never recursively descended into.

Pre-exec lstat and stat independently establish object and alias identities.
Raw pathname probes preserve trailing `/.`, which pathlib would normalize away
and incorrectly measure as the symlink itself. Every section has exact C-sorted
(or reverse C-sorted) names, measured inode values and required suffixes.
The matcher requires exactly the authored section set, permits unspecified
section order and the standard's optional operand heading, and allows only
inode-column space padding. No provider output defines expectations.
Metadata, bytes, link text, directory entries and the outside guard must remain
unchanged. Access times are excluded because inspection can change them.
Setup errors, execution failures, mismatches and cleanup errors are failures.

Harness regressions cover all 192 case/mode pairs, missing/duplicate/unexpected
sections, incorrect names/dot entries, graph mutations, partial setup failures,
failed exec and real timeout cleanup with child reaping in every mode.
The unconditional symlink fault in the general harness occurs during common
setup. The separate `setup_regression.py` witness specifically observes every
new directory and file and the first directory alias before failing creation
of the second alias; it requires no provider execution and complete cleanup in
all four modes. These four witnesses passed separately on each platform after
the full command was launched; `validate.py` now runs them on reproduction. The
harness uses the platform ls; provider qualification uses the exact selected
profile with zero allowances.

CSH-121 / issue #254 owns all 21 remaining utility contracts and all four
retained conditions. Arbitrary/cyclic graphs, devices, other credentials/ACLs,
terminal layouts, non-C locales, namespace races and resource failures remain
unqualified. U-034/U-040 remain partial. Historical evidence is unchanged.

## Reproduction

From the repository root, build `make -j4 cshell host-profile` with the documented
GNU providers on PATH. This run copied the predecessor worktree's private gfind
into `build/prerequisites/`; its exact selected hash is retained in the manifest.
Create an owned private TMPDIR with the invoking user's group, then run:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh120-tmp" \
  python3 docs/evidence/csh-120/validate.py native
```

Run `sh docs/evidence/csh-120/linux.sh` for Linux/Docker. It mounts the current
sources for tests, Makefile and accounting read-only over the CSH-119 image,
reusing its unchanged shell/provider build. The recorded image identity is
`sha256:78737251d7b568e1b88cfdb03050e7417859381091358b85600a85376c53a817`.
Fixtures run as uid/gid 10001 on bounded executable tmpfs mounts. Reports are
bound to this worktree. No protected mount, host-volume filling, privileged
fixture identity or claimed real filesystem-exhaustion environment is used.

Validation uses `make -k` to collect all independent requested targets while
preserving the nonzero status of any failed target. Stock full and provider
audits run separately and must retain their nonzero results. Run `python3 docs/evidence/csh-120/collect.py` to copy native and
Linux report archives here and compress raw logs losslessly, then run
`python3 docs/evidence/csh-120/verify.py`. The verifier checks the source and
provider hashes, all predecessor expectations, the exact new case/mode set,
channels/status, unchanged objects, cleanup and unchanged stock failure sets.

## Validation result — 2026-11-13

The complete requested command passes on both native macOS 14.8.7 arm64 and
Linux arm64 (Docker, glibc 2.36). Every focused filesystem target passes.
Both host utility profiles pass 1,162 assertions with zero failures or gaps.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Combined selected filesystem assertions | 13,227 pass / 0 fail | 13,267 pass / 0 fail |
| New recursive ls assertions | 192 pass / 0 fail | 192 pass / 0 fail |
| Filesystem harness tests | 196 pass | 196 pass |
| Additional partial-graph setup/cleanup modes | 4 pass | 4 pass |
| Retained stock full-audit failures | 853 | 578 |
| Retained stock provider-audit failures | 16 | 8 |

The evidence verifier passes: exact source/provider provenance, unchanged
predecessor expectations, the exact new case/mode set, observed channels/status,
unchanged graphs, cleanup and identical stock failure identities are required.
All 24 ticket tests, the offline/live identity checks (121 reservations), and
13 ownership tests pass. Selected profiles use zero allowances; stock failures
remain separately nonzero. No sanitizer or separately hosted native-Linux run
is claimed. Both task-owned containers were removed.

The code is ready for review; integration still depends on the unmerged
CSH-119 stack. This evidence does not rewrite or close the predecessor tickets.
