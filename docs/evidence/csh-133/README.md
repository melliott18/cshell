# CSH-133: ls symbolic-link size sorting

CSH-133 supplies 36 ls cases / 144 assertions for symbolic-link size sorting on directory entries and reverse-authored operands. Authored 12/14/18-byte link texts and 19/7/3-byte regular referents distinguish physical, -H and -L ordering, equal-size C-name ties and reversal. Short, named and numeric long listings require exact size/type/date fields and measured 1024-byte directory totals. Independent lstat/stat, byte/link readback and exact old UTC timestamps supply the oracle. Exact channels/status, unchanged metadata/bytes/link text/directory entries and cleanup are required. Selected providers are unchanged. Dangling or cyclic links, other object graphs, arbitrary option permutations, size/capacity limits, non-C collation, terminal layouts and resource failures remain unqualified.

Based on CSH-132 `5fcae68`, awaiting integration. The retained Issue 8
[ls specification](ls.html) explicitly selects symbolic-link versus referent
size for -S according to -H/-L. DESCRIPTION distinguishes operand links from
directory entries; OPTIONS specifies decreasing size, increasing filename ties,
-r reversal and -k units; STDOUT defines long fields and directory totals.
The section map retains the normative URL and SHA-256. Expected output never
comes from another ls invocation.

Four links have authored lengths of 12, 18, 14 and 12 bytes; their referents
have 19, 3, 7 and 19 bytes. Physical order is bravo, charlie, alpha, delta;
followed order is alpha, delta, charlie, bravo. Alpha and delta name the same
referent but remain distinct listed entries. -H follows operand links only;
-L follows both operand and directory-entry links. Short, named and numeric
long forms each run forward and reversed. Directory totals sum the selected
raw 512-byte st_blocks counts before rounding to 1024 bytes, counting every
listed name. This qualifies measured accounting on these filesystems only.

Independent pre-exec lstat/stat, content/link readback, account lookup and exact
old UTC timestamp readback establish the oracle. Post-exec checks require
unchanged types, modes, identities, sizes, link counts, allocations, mtime,
ctime, bytes, link texts and directory entries. Access times are excluded
because directory enumeration and readlink can update them. All fixtures are
private, bounded, acyclic and owned by one unprivileged identity.

Five new harness tests check independently authored expected orders and fields,
malformed output, all four execution modes, metadata/content/link/identity
mutations, partial setup failure, failed exec and timeout cleanup. Stock Apple
ls produces 24 new strict failures: its -H operand listings retain the physical
size order. The selected GNU coreutils 9.7 provider is unchanged. No failure
allowance, provider source change or deadline increase is introduced.

## Reproduction

Build `make -j4 cshell host-profile` with GNU prerequisites on PATH. This
worktree copies the gfind prerequisite from CSH-132; exact executable and build
identities are retained. Native file and iconv are rebuilt with different executable
hashes from CSH-132; their sources, pins and build flags are unchanged. The
native ls hash matches CSH-132 exactly. Use a private TMPDIR owned by the invoking UID and
primary GID.

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh133-tmp" python3 docs/evidence/csh-133/validate.py native
sh docs/evidence/csh-133/linux.sh
python3 docs/evidence/csh-133/collect.py
python3 docs/evidence/csh-133/verify.py
```

Linux uses the unchanged CSH-119 provider image with current tests/accounting
mounted read-only, UID/GID 10001, a 512 MiB fixture tmpfs and separate 512 MiB
report tmpfs. The required command contains 53 Make targets, followed by
separate stock full and provider audits. Every JSON report must parse, including
expected-failing stock reports. The verifier checks exact new case/mode coverage,
every predecessor expectation and stock failure identity, source/provider
provenance, link/referent sizes and identities, dates and cleanup.

All 21 utility residuals and four original U-040 conditions transfer to
[CSH-134](../../tickets/CSH-134-filesystem-environment-residuals.md) /
[issue #280](https://github.com/melliott18/cshell/issues/280). U-034/U-040 remain
partial. No sanitizer, hosted CI or separately hosted native-Linux result is
claimed; no C source changes in this ticket.

## Validation result — 2026-11-26

All 53 required Make targets pass on native macOS 14.8.7 arm64 (UID 501/GID 20)
and Docker Linux arm64 with glibc 2.36 (UID/GID 10001). Selected filesystem
profiles pass 15,891 / 15,963 assertions with zero failures, including all 144
new assertions on each platform. Both general host profiles pass 1,162 assertions
with zero gaps. Both platforms pass 263 filesystem harness tests and 13 ownership
tests. The 24 ticket-registry tests and offline/live identity checks pass with
134 shared reservations.

Stock full audits retain 1,093 / 578 failures; stock provider audits retain
16 / 8. The 24 additional native failures are exactly the -H operand cases:
Apple ls sorts by physical link size rather than referent size. Every predecessor
expectation and stock failure identity remains unchanged. The combined evidence
verifier passes for both platforms, including exact case/mode coverage, unchanged
source inputs outside the test/accounting changes, provider provenance, measured
link/referent metadata, exact output, and cleanup.

Provider selections, sources, pins, build flags, deadlines and allowances are
unchanged. Rebuilt native file and iconv have different binary hashes, retained
in their exact manifests; the native ls binary hash matches CSH-132. Both Linux
tmpfs limits remain 512 MiB. All reports parse as JSON, the Linux validation
container was removed, and the native fixture root is empty. No sanitizer,
hosted CI or separately hosted native-Linux result is claimed.

CSH-133 is ready for review, pending integration of CSH-132 / PR #279.
CSH-134 / issue #280 owns all 21 remaining utility contracts and the four
retained conditions. U-034/U-040 remain partial.
