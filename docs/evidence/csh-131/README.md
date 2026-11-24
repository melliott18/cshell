# CSH-131: ls change-time selection and sorting

CSH-131 supplies 32 ls cases / 128 assertions for status-change-time sorting and display on private regular operands and a hard-link pair. Strict pre-exec chmod/lstat ordering and the shared-inode tie supply an independent oracle; authored access and modification orders differ from change time. Short, named and numeric long listings, both -t/-c orders, -c without -t, last -c/-u precedence and reversal are checked. Measured current ctime is rendered in UTC with before/after recent/nonfuture clock guards. Exact channels/status, unchanged access/modification/change times, identities, modes, bytes, directory entries and cleanup are required. Selected providers are unchanged. Other object graphs, arbitrary timestamp resolutions, clock changes and boundaries, timestamp ranges, non-C collation, terminal layouts and resource failures remain unqualified.

Based on CSH-130 `9eac8d4`, awaiting integration. The retained Issue 8
[ls specification](ls.html) defines -c/-u last-option precedence and -t/-r
sorting in OPTIONS, filename tie breaking in DESCRIPTION, and dates in STDOUT.
The section map retains its source URL and hash. No provider supplies expected output.

The four reverse-authored operands have three inodes. Chmod establishes the
strict order alpha < bravo/delta < charlie; an independently measured hard link
supplies the equal-time pair. Atime and mtime have distinct January 2000 orders.
Chmod retries have a two-second monotonic bound per inode, and setup fails if
strict order cannot be proved. The fixture does not assume nanosecond resolution.
Current ctime is converted using numeric UTC calendar arithmetic and literal
English month names. Before/after wall-clock guards reject future or day-old
ctime; no clock is adjusted. All metadata is measured before content verification
can update atime. The provider must preserve the exact measured timestamps.

Seven harness tests cover all forms and invocation modes, independent literal
orders/dates, malformed output, metadata/content/hard-link mutation, partial setup,
coarse-clock setup timeout, clock guards and failed exec/timeout cleanup.
No provider, allowance or provider deadline is changed. CSH-132 / issue #276
retains every remaining utility contract and the four retained conditions.

## Reproduction

Build `make -j4 cshell host-profile` with GNU prerequisites on PATH. The native
worktree copies the gfind prerequisite from CSH-130; the manifest records its
exact identity. Use a private TMPDIR owned by the invoking UID and primary GID.

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh131-tmp" python3 docs/evidence/csh-131/validate.py native
sh docs/evidence/csh-131/linux.sh
python3 docs/evidence/csh-131/collect.py
python3 docs/evidence/csh-131/verify.py
```

Linux uses the unchanged CSH-119 provider image, current tests/accounting mounted
read-only and UID/GID 10001 on bounded executable tmpfs. The required command
contains 51 Make targets followed by separate stock full/provider audits.
The verifier checks all predecessor expectations and stock failure identities,
new case/mode coverage, source/provider provenance, measured timestamps and cleanup.

## Validation result — 2026-11-24

The complete 51-target required Make command passes on native macOS 14.8.7
arm64 (UID 501/GID 20) and Linux arm64/Docker with glibc 2.36 (UID/GID 10001).
Selected filesystem profiles pass 15,531 / 15,603 assertions with zero failures,
including all 128 new assertions on each platform. Both platforms pass all
253 filesystem harness tests and 13 ownership tests. All 24 ticket-registry
tests and offline/live identity checks pass with 132 shared reservations.

Stock full audits retain exactly 1,069 / 578 failures; stock provider audits
retain 16 / 8. The evidence verifier passes for both platforms: every
predecessor expectation and stock failure identity is retained, all new
case/mode pairs are present, source/provider provenance matches, and exact
metadata, timestamp, clock-category and cleanup checks pass. Selected provider
sources, source pins, build flags, deadlines and allowances are unchanged.

No sanitizer, hosted CI or separately hosted native-Linux result is claimed.
Linux used the unchanged predecessor provider image with current tests and
accounting mounted read-only. The task-owned validation container was removed
after evidence collection.

CSH-131 is ready for review, pending integration of CSH-130. CSH-132 / issue #276
owns every remaining filesystem contract and the four retained conditions.
