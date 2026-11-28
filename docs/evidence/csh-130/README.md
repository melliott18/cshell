# CSH-130: ls timestamp selection and sorting

CSH-130 supplies 48 ls cases / 192 assertions for modification/access-time sorting and display on four private regular operands. Day-spaced and one-nanosecond timestamps, tied primary keys, reverse ordering, -t/-u option order, named/numeric long listings and -u without -t distinguish time selection from name sorting. Authored ranks and exact pre-exec utime/lstat readback supply the oracle. Exact channels/status, unchanged access/modification/change times, identities, modes, bytes and directory entries, and cleanup are required. Selected providers are unchanged. Ctime selection, other object graphs, clock boundaries, timestamp ranges, non-C collation, terminal layouts and resource failures remain unqualified.

Based on CSH-128 `11a53fc`, still awaiting integration. The retained Issue 8
[ls specification](ls.html) defines time/name sorting and -t/-u/-r in OPTIONS,
name ordering in DESCRIPTION, and date fields in STDOUT. Source URL and hash
remain in the section map. No provider supplies expected output.

Four regular files have opposing authored access/modification ranks, including
an equal-time pair whose filename order breaks the tie. One matrix uses days
in January 2000; the other differs by exactly one nanosecond within one second.
All operands are supplied in reverse name order. The twelve forms cover short,
named-long and numeric-long output, both -t/-u orders, and long -u without -t.
Forward and reverse order are checked independently. The filesystem must read
back the exact timestamps before execution. Contents are read before stamping;
post-exec atime is measured before the verifier reads contents again. Ctime,
all other metadata, bytes and the containing directory's entries are preserved.

Seven harness tests check literal expected orders/dates, rejection of corrupted
output, all invocation modes, metadata/content mutations, exact readback
failure, missing account lookup, partial setup failure and failed exec/timeout cleanup. No allowance,
provider source change or deadline change is introduced. CSH-131 / issue #274
retains all remaining utility contracts and the four retained conditions.

## Reproduction

Build `make -j4 cshell host-profile` with GNU prerequisites on PATH. This
worktree copies the private gfind prerequisite from CSH-128; the manifest
records its exact identity. Use a private TMPDIR owned by the invoking user
and primary group.

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh130-tmp" python3 docs/evidence/csh-130/validate.py native
sh docs/evidence/csh-130/linux.sh
python3 docs/evidence/csh-130/collect.py
python3 docs/evidence/csh-130/verify.py
```

Linux reuses the unchanged CSH-119 provider image with current tests/accounting
mounted read-only. Fixtures run as UID/GID 10001 on bounded executable tmpfs.
Native providers are rebuilt from pinned sources. Separate stock full/provider
audits retain their nonzero results.

The required command runs 50 Make targets, followed by separate stock full and
provider audits. The verifier compares every predecessor expectation and stock
failure identity, exact source/provider hashes, all 48 case IDs in four modes,
exact timestamp fields, metadata and cleanup.

## Initial Linux language-helper failure

The initial required command failed only at the final language-suite recipe in
`test-host-profile`: `ed/signal-int` in direct mode. The language report retains
1,088 passes and one failure. The child exited zero and was reaped, while the
helper marked capture incomplete and raised `ed exited before response`; fixture
cleanup succeeded. This matches the pending [CSH-129 repair](https://github.com/melliott18/cshell/pull/273).
The exact descriptor ordering in this run was not recorded.

The initial command log, command records and failed language report are retained
under `linux-initial/`. No helper, provider, expectation, timeout or allowance is
changed here. A manual complete required-command rerun uses `rerun.py`, after
preserving the initial reports. The stock audits are retained from the first run
because their source and expectations are unchanged. The verifier requires the
initial failure signature as well as a successful complete rerun; it does not
turn the failed assertion into a pass. A successful rerun does not close CSH-129.

```sh
# After the initial validate.py run finishes:
python3 docs/evidence/csh-130/collect.py --initial-linux
docker rm cshell-csh130-validation
CSH130_VALIDATION_SCRIPT=docs/evidence/csh-130/rerun.py sh docs/evidence/csh-130/linux.sh
```

## Validation result — 2026-11-23

The complete 50-target required Make command passes on native macOS 14.8.7
arm64 (UID 501) and Linux arm64/Docker with glibc 2.36 (UID/GID 10001).
Selected filesystem profiles pass 15,403 / 15,475 assertions with zero failures,
including all 192 new assertions on each platform. Both platforms pass all
246 filesystem harness tests and 13 ownership tests.

Stock full audits retain exactly 1,069 / 578 failures; stock provider audits
retain 16 / 8. The evidence verifier passes for both platforms: every
predecessor expectation and stock failure identity is retained, all new
case/mode pairs are present, source/provider provenance matches, and exact
timestamp, metadata and cleanup checks pass. Selected providers, source pins,
build flags, deadlines and allowances are unchanged.

The initial Linux required command failed only at the existing language-helper
`ed/signal-int` direct-mode response capture (1,088 passes / one failure).
The original log and failed report remain under `linux-initial/`; CSH-129 /
[PR #273](https://github.com/melliott18/cshell/pull/273) owns that defect. An
unchanged complete required-command rerun passed, including all 1,089 language
assertions. This does not close CSH-129 or turn its initial failure into an
allowance. The verifier checks both the retained failure and the final rerun.

All 24 ticket tests and offline/live identity checks pass with 131 shared
reservations. No sanitizer, hosted CI or separately hosted native-Linux result
is claimed. Linux used the unchanged predecessor provider image. Both task-owned
validation containers were removed after evidence collection.

CSH-130 is ready for review, pending integration of CSH-128. CSH-131 owns every
remaining filesystem contract and the four retained conditions.
