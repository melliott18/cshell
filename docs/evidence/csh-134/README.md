# CSH-134: ls symbolic-link time sorting

CSH-134 adds 72 cases / 288 assertions for modification/access-time sorting of
private symbolic links. The matrix crosses directory entries and reverse-authored
operands, physical/-H/-L selection, short/named/numeric long output, and reversal.
Selected providers are unchanged; full filesystem contracts remain open.

Based on CSH-133 `58a2b54`, awaiting integration. The retained Issue 8
[ls specification](ls.html), OPTIONS -t and -u, specifies the selected timestamp
and link/referent behavior. DESCRIPTION distinguishes operand links from directory
entries. OPTIONS -r and -k and STDOUT define reversal, units and long fields.
The section map retains the normative URL and SHA-256. The online specification
returned HTTP 403 during this task; the retained predecessor copy is unchanged.
No ls invocation supplies expected output.

Four links have distinct access/modification dates, and their three regular-file
referents have different orders. Alpha and delta share a referent and have equal
link timestamps, so each selection exercises a C-name tie. Authored timestamps
are whole days after 2000-01-02 UTC. The expected forward orders are:

| Selected metadata | Modification | Access |
| --- | --- | --- |
| Link | bravo, charlie, alpha, delta | alpha, delta, bravo, charlie |
| Referent | alpha, delta, charlie, bravo | charlie, bravo, alpha, delta |

-H follows operand links; -L follows both operand and directory-entry links.
Every reverse case reverses the complete order, including ties. Long listings
check the selected exact date, type, size, link count and account/numeric IDs.
Directory totals sum selected raw 512-byte block counts before rounding to 1024
bytes, counting every listed name. This only qualifies measured accounting on
the supplied filesystems.

Independent pre-exec lstat/stat, content/link readback and account lookup establish
the graph. Final utime/lstat probes establish exact access and modification times
**after** all stat/readlink probes, since following a link can update its access
time. Post-exec checks require unchanged metadata including ctime and regular-file
atime, bytes, link text and directory entries. Symlink and directory access times
may change during traversal and are excluded from preservation assertions.

Five harness tests check independently authored orders and fields, malformed
output, all four execution modes, metadata/content/link/identity mutations,
partial final-timestamp setup failure, failed exec and timeout cleanup. Stock
Apple ls retains strict -H operand sorting failures. These are not allowances;
the selected GNU coreutils 9.7 provider must pass every assertion. No provider
source, pin, build flag, deadline or allowance is changed.

## Reproduction

Build `make -j4 cshell host-profile` with GNU prerequisites on PATH. This worktree
copies the gfind prerequisite from CSH-133. Use a private TMPDIR owned by the
invoking UID and primary GID. Run only one build against the native build tree
at a time. The native ls binary hash matches CSH-133; rebuilt file and iconv
hashes differ, with unchanged sources, pins and flags. Exact build logs and
provider manifests are retained.

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh134-tmp" python3 docs/evidence/csh-134/validate.py native
sh docs/evidence/csh-134/linux.sh
python3 docs/evidence/csh-134/collect.py
python3 docs/evidence/csh-134/verify.py
```

Linux uses the unchanged CSH-119 provider image with current tests/accounting
mounted read-only, UID/GID 10001, a 512 MiB fixture tmpfs and separate 512 MiB
report tmpfs. Validation runs all 54 required Make targets, then separate stock
full and provider audits. Reports must parse even when the stock command fails.
The verifier checks exact new case/mode coverage, predecessor expectations and
stock failure identities, source/provider provenance, timestamp readback,
link/referent identities, output and cleanup.

All 21 utility residuals and four original U-040 conditions transfer to
[CSH-135](../../tickets/CSH-135-filesystem-environment-residuals.md) /
[issue #282](https://github.com/melliott18/cshell/issues/282). U-034/U-040 remain
partial. Ctime selection on links, dangling or cyclic links, nanosecond link
ordering, other graphs, timestamp boundaries, non-C collation, terminal layouts
and resource failures remain unqualified. No sanitizer, hosted CI or separately
hosted native-Linux result is claimed; this ticket changes no C source.

## Native observer retry

The initial native 54-target Make invocation returned 2 because the unchanged
CSH-073 `cmp/write-termination` exec-mode witness could not obtain a Darwin
`sample` observation. The tool reported that it could not examine the child,
although the process appeared to exist. The harness reaped the child and removed
the fixture. This is retained as a failure, not an allowance or utility pass.

`native-text-observer-failure.json.gz` preserves the original 865 pass / 1 fail /
2 unavailable report. `recover-native.py` reran the complete text recipe unchanged
and then ran the two language recipes that Make had not reached. The text retry
passed 866 assertions with zero failures and the same two existing unavailable
capacity witnesses. The language harness and all 1,089 language assertions passed.
The recovery command log records all three zero exit statuses. No elevation,
source edit, provider change, limit increase or expectation change was used.

The verifier requires identical source/provider identities, limits, binary,
case coverage and expectations between the original and retry, unchanged verdicts
for every other case, and successful original cleanup. It also requires exactly
one failed Make recipe in the original log. The initial Make command therefore
remains nonzero in the evidence; validation completion uses the recorded recipe
retry. The Linux 54-target command passed without a retry.

To reproduce a retry only if this observer failure occurs:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh134-tmp" python3 docs/evidence/csh-134/recover-native.py
```

## Validation result — 2026-11-27

Selected filesystem profiles pass 16,179 assertions on native macOS 14.8.7
arm64 (UID 501/GID 20) and 16,251 on Docker Linux arm64/glibc 2.36
(UID/GID 10001), with zero failures. All 288 new assertions pass on each
platform. Both general host profiles pass 1,162 assertions with zero gaps;
both filesystem harnesses pass 268 tests and both ownership harnesses pass 13.
The 24 ticket-registry tests and offline/live identity checks pass with 135
shared reservations.

All 54 required Linux Make targets passed in one invocation. The native
54-target invocation returned 2 solely for the existing Darwin `sample`
observer failure in `cmp/write-termination` (exec). The full text recipe passed
unchanged on retry (866 pass, zero fail, two existing unavailable capacity
witnesses), followed by the previously unreached language harness and all 1,089
language assertions. All three recovery recipes returned zero. The original
failure, nonzero Make status, child/fixture cleanup and successful retry are
retained separately; no allowance, source/provider change, elevation or limit
increase was introduced. See the evidence's native observer retry section.

Stock full audits retain 1,141 / 578 failures; stock provider audits retain
16 / 8. The 48 additional native failures are exactly the -H operand time-sort
cases. Every predecessor expectation and stock failure identity is preserved.
The combined evidence verifier passes for both platforms, including exact
case/mode coverage, unchanged sources outside tests/accounting, selected-provider
provenance and ls hashes, unchanged limits, timestamp readback, output and cleanup.

The native fixture root is empty and the Linux validation container was removed.
Both Linux tmpfs limits remained 512 MiB. Native file/iconv binary hashes changed
on rebuild with unchanged sources, pins and flags; the native ls and cshell
hashes match CSH-133. No sanitizer, hosted CI or separately hosted native-Linux
result is claimed.

CSH-134 is ready for review, pending integration of CSH-133 / PR #281.
CSH-135 / issue #282 owns all 21 remaining utility contracts and four retained
conditions. U-034/U-040 remain partial.
