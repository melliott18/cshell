# CSH-132: ls size/time sorting precedence

CSH-132 supplies 54 ls cases / 216 assertions for size/time sorting precedence on private regular operands and a hard-link pair. Authored 3/7/19-byte contents, exact atime/mtime readback and measured ctime order distinguish size, modification, access and change-time orders. Short, named and numeric long listings cross -S/-t precedence, retained -u/-c date selection, equal-size C-name ties and reversal. Exact channels/status, unchanged timestamps, identities, modes, bytes, directory entries and cleanup are required. Selected providers are unchanged. Other option permutations, object graphs, size limits, clock boundaries, non-C collation, terminal layouts and resource failures remain unqualified.

Based on CSH-131 `6a7169a`, awaiting integration. The retained Issue 8
[ls specification](ls.html) defines decreasing size and increasing filename
keys in OPTIONS (-S), reversal (-r), and last-option precedence for sorting.
Its OPTIONS note explicitly preserves the last -c/-u timestamp for long output
even when a later -S selects size sorting. STDOUT defines long fields and dates.
The section map retains the normative URL and SHA-256. No ls provider generates
expected output.

The four reverse-authored operands have three inodes. Alpha has seven bytes,
bravo/delta nineteen, and charlie three. The size, modification, access and
change-time orders all differ. Byte counts are authored, written, read back and
independently measured with lstat. All reads precede exact atime/mtime stamping;
chmod then establishes strict ctime order, with a hard link supplying the tie.
Current change time has pre/post recent/nonfuture clock guards. Ctime retries
have a two-second monotonic bound per inode. No clocks are adjusted and no
filesystem is filled. Each mode requires exact status, both channels, metadata,
contents and cleanup. This does not qualify arbitrary option permutations,
symlink size selection or filesystem size/capacity limits.

Five new harness tests exercise literal independently authored orders/dates,
malformed output, all cases in all four modes, content/timestamp/mode/identity
mutations, partial setup failure, failed exec and timeout cleanup. Existing
clock-category and coarse-timestamp timeout regressions remain required.
Providers, source pins, build flags, allowances and execution deadlines are
unchanged. CSH-133 / issue #278 retains every remaining utility contract and
all four original conditions.

## Reproduction

Build `make -j4 cshell host-profile` with GNU prerequisites on PATH. The native
worktree copies the gfind prerequisite from CSH-131; its exact executable
identity is retained in the profile manifest. Use a private TMPDIR owned by
the invoking UID and primary GID.

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh132-tmp" python3 docs/evidence/csh-132/validate.py native
sh docs/evidence/csh-132/linux.sh
python3 docs/evidence/csh-132/collect.py
python3 docs/evidence/csh-132/verify.py
```

Linux uses the unchanged CSH-119 provider image with this worktree's tests and
accounting mounted read-only, UID/GID 10001, a 512 MiB fixture tmpfs and a
separate 512 MiB report tmpfs. The
required command contains 52 Make targets followed by separate stock full and
provider audits. The verifier checks all predecessor expectations and stock
failure identities, exact new case/mode coverage, source/provider provenance,
metadata, sizes, timestamp/clock categories and cleanup.

## Report storage failure and rerun

The [initial Linux run](linux-initial/README.md) passed its complete selected
command but exhausted its 256 MiB report tmpfs during the final stock-provider
report write. Its truncated report is retained as failed infrastructure evidence.
The complete Linux rerun uses 512 MiB for reports; fixture limits and utility
expectations are unchanged. The driver now requires every report to parse as
JSON before accepting the command sequence. Matching the expected nonzero
stock-audit exit status is insufficient.

## Validation result — 2026-11-25

The complete 52-target required Make command passes on native macOS 14.8.7
arm64 (UID 501/GID 20) and Docker Linux arm64 with glibc 2.36 (UID/GID 10001).
Selected filesystem profiles pass 15,747 / 15,819 assertions with zero failures,
including all 216 new assertions on each platform. Both platforms pass all
258 filesystem harness tests and 13 ownership tests. All 24 ticket-registry
tests and offline/live identity checks pass with 133 shared reservations.

Stock full audits retain exactly 1,069 / 578 failures; stock provider audits
retain 16 / 8. The evidence verifier passes for both platforms: predecessor
expectations and stock failure identities are unchanged, all new case/mode
pairs are present, source/provider provenance matches, and exact sizes,
metadata, timestamps, clock categories and cleanup pass. Provider sources,
source pins, build flags, execution deadlines and allowances are unchanged.

The initial Linux report-capacity failure is retained separately. Its complete
selected command passed, but its final stock-provider report was truncated.
The complete rerun passes with a 512 MiB report tmpfs and mandatory JSON parsing;
the 512 MiB fixture tmpfs and all utility expectations are unchanged.

No sanitizer, hosted CI or separately hosted native-Linux result is claimed.
Linux used the unchanged predecessor provider image with current tests and
accounting mounted read-only. The task-owned validation containers were removed
after collecting evidence.

CSH-132 is ready for review, pending integration of CSH-131. CSH-133 / issue #278
owns every remaining filesystem contract and the four retained conditions.
