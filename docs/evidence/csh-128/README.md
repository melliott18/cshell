# CSH-128: ls date formatting

CSH-128 supplies 60 ls cases / 240 assertions for recent, old and future modification dates on regular files, hard links, directories, FIFOs and symlinks. Named and numeric long listings use UTC and a fixed +05:45 offset, including date rollover and minute offsets. Authored integer timestamps, exact pre-exec utime/lstat readback and before/after interior clock-category checks supply the oracle. Exact date fields, channels/status, unchanged metadata including ctime, bytes, links, entries and cleanup are required. Selected providers are unchanged. Six-month and current-instant boundaries, clock changes, DST, timestamp ranges, other locales and arbitrary timezone definitions remain unqualified.

Based on CSH-127 `44cedbe`, still awaiting integration. The unchanged retained Issue 8 ls specification defines date formatting in STDOUT, -l/-n/-d in OPTIONS and TZ in ENVIRONMENT VARIABLES. Calendar expectations use integer timestamps, Python UTC conversion and literal English months; no provider supplies expected output. The recent timestamp is two UTC dates before setup at 23:47:23; future is 400 UTC dates later at the same time; old is 2000-01-02 UTC. A fixed +05:45 offset exercises day rollover and minutes. Before and after execution, the timestamp must remain well inside its declared age category. Atime is excluded from mutation comparisons because content inspectors may update it. Ctime and all other measured metadata must remain unchanged. No FIFO is opened.

Seven harness regressions check independently literal calendar expectations, all invocation modes, mutation detection, exact readback rejection, partial setup failures, invalid clock categories and failed exec/timeout cleanup. Selected provider sources and build flags are unchanged. No allowances are added. CSH-130 / issue #271 retains all remaining utility contracts and four retained conditions.

## Reproduction

Build `make -j4 cshell host-profile` with GNU prerequisites on PATH. This worktree copies the private gfind prerequisite from CSH-127; its exact identity is in the manifest. Use a private TMPDIR owned by the invoking user and primary group.

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh128-tmp" python3 docs/evidence/csh-128/validate.py native
sh docs/evidence/csh-128/linux.sh
python3 docs/evidence/csh-128/collect.py
python3 docs/evidence/csh-128/verify.py
```

Linux reuses the unchanged CSH-119 provider image with current tests/accounting mounted read-only. Fixtures use unprivileged UID/GID 10001 on bounded executable tmpfs. Native providers are rebuilt from pinned sources. Separate stock full/provider audits retain their nonzero results.

The complete required command runs 49 Make targets, followed by separate stock full and provider audits. The verifier compares every predecessor expectation and stock failure identity, exact source hashes, selected executable hashes, all 60 case IDs in four invocation modes, exact date fields, metadata and cleanup.

## Validation result — 2026-11-21

The complete 49-target required Make command passes on native macOS 14.8.7
arm64 (UID 501) and Linux arm64/Docker with glibc 2.36 (UID/GID 10001).
Selected filesystem profiles pass 15,211 / 15,283 assertions with zero
failures, including all 240 new assertions on each platform. Both platforms
pass all 239 filesystem harness tests and 13 ownership tests.

Stock full audits retain exactly 1,069 / 578 failures; stock provider audits
retain 16 / 8. The evidence verifier passes for both platforms: every
predecessor expectation and stock failure identity is retained, all new
case/mode pairs are present, source/provider provenance matches, and
metadata, date fields and cleanup checks pass. Selected providers, source
pins, build flags, deadlines and allowances are unchanged.

All 24 ticket tests and offline/live identity checks pass with 130 shared
reservations. No sanitizer, hosted CI or separately hosted native-Linux
result is claimed. Linux used the retained predecessor provider image and
the task-owned container was removed after collection.

CSH-128 is ready for review, pending integration of CSH-127. CSH-130 owns
every remaining filesystem contract and the four retained conditions.
