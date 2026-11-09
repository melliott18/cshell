# CSH-116: measured ls directory totals

The separate `test/CSH-116-filesystem-environments` worktree starts at CSH-115
commit `ed627f7`. CSH-115 is still under review in PR #245; this change depends on
that implementation and is not represented as integrated. No shell C sources or
selected providers change.

## Contract and independent oracle

The [Issue 8 ls specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html)
DESCRIPTION and OPTIONS define directory-entry selection, C-locale ordering,
`-A`, `-L`, `-R`, and `-s`/`-k`. STDOUT defines a total of the listed files,
1024-byte units under `-k`, rounding, and directory headings. A single recursive
operand may omit its first heading; later headings and separators are required.
The retained HTTPS source matches the section map's SHA-256. The browser fetch
returned 403; curl retrieved the source successfully.

Thirty-two cases run by direct exec and cshell string/file/stdin modes, for 128
assertions on each platform. Both `-s -k` and `-k -s` orders combine visible-only
or `-A` selection, physical or `-L` file-symlink handling, and empty, populated,
multiple-operand or recursive directory listings. The reverse-authored multiple
operands must sort in C order. The fixture contains regular files, empty files,
a hard-link pair, a FIFO, a file symlink, hidden files and one child directory.
FIFOs are never opened.

Before execution, Python lstat measures each object's `st_blocks` in kernel
512-byte units. Separate type, size, hard-link identity/link-count and stat
symlink-referent probes establish the fixture. Each total sums raw allocation
for the selected immediate entries and then rounds to 1024-byte units. Hard-link
names count separately. The enclosing directory, hidden entries when not
selected, and descendants outside that listing are excluded. No utility output
supplies expected values. Synthetic odd-block tests verify summation before
rounding, without claiming a physical rounding boundary on either filesystem.

Every assertion requires the expected total and per-entry allocation, names,
order, section headings/separators, empty stderr and zero status. Column padding
and the explicitly permitted initial recursive heading omission are accepted.
Device/inode, mode, uid/gid, size, link count, allocation and mtime/ctime must
remain unchanged, as must file bytes, link text and directory entries. Access
times are excluded because inspection can change them. Cleanup failures fail
the assertion. Provider paths/hashes, build provenance and source digests are
retained separately from output, status and effects.

Five harness tests cover the complete matrix in all modes, bad totals/headings/
ordering/missing entries/channels/status and changed objects, synthetic rounding
and hard-link accounting, partial setup and failed probes, failed exec and
bounded timeout with reaping and cleanup. The synthetic capture derives output
by traversing actual entries independently of the authored expected-sections
function.

## Stock observation

Apple stock ls omits `total 0` for an empty listed directory, both alone and
among multiple operands. The STDOUT-derived strict total-line witnesses retain
64 new native stock failures. The selected GNU ls supplies the total line.
All predecessor stock failures remain; no allowance or provider change is added.

## Remaining scope

These are measured st_blocks witnesses on the supplied filesystems. Default
units, other accounting methods, shared physical extents, arbitrary graphs,
physical rounding boundaries, capacity/exhaustion, terminal layouts, non-C
collation, other identities/ACLs and resource errors remain unqualified. No
kernel fault or libc injection is claimed. All 21 full utility contracts and
four original U-040 conditions remain individually open under
[CSH-117](../../tickets/CSH-117-filesystem-environment-residuals.md) / [#246](https://github.com/melliott18/cshell/issues/246).
U-034/U-040 remain partial; utility/libc/platform vendors retain implementation
ownership. Historical evidence is unchanged.

## Reproduction

```sh
# Native prerequisites: documented GNU tools, including gfind, on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-116/validate.py native

docker build -f docs/evidence/csh-116/Dockerfile.linux -t cshell-test:csh-116 .
docker run --init --name cshell-csh116-validation cshell-test:csh-116 \
  python3 docs/evidence/csh-116/validate.py linux
docker cp cshell-csh116-validation:/work/build/csh116-validation ./build/csh116-linux-results
# Collect compressed reports, logs and generated provider headers here, then:
python3 docs/evidence/csh-116/verify.py
docker rm cshell-csh116-validation
```

The Docker image layers current sources onto the retained `cshell-test:csh-115`
image (`sha256:9c8fa9d9bb9146511aa28a966d9f673ee7efdc920de02f0265fa5496638eccae`)
and runs as its unprivileged `cshell` identity. This is Linux/Docker
evidence, not a separately hosted native-Linux run. Native provisioning uses a
private copy of the same gfind executable as CSH-115. No sanitizer qualification
is claimed.

## Development records

The first native provisioning attempt lacked gfind; it was supplied privately
before validation. An early negative harness test removed the optional first
recursive heading and incorrectly expected failure. The test now removes a
required file entry; a separate regression accepts both permitted initial
heading forms and rejects omission of later headings. Development logs are
retained separately and are not represented as final-source passes. The native
selected command was rerun after correcting that test; its successful result
replaces only command 0 in the final command record. The original failed command
and its status remain in `development/`.

## Final validation — 2026-11-09

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12651 pass, 0 fail | 12691 pass, 0 fail |
| New directory-total assertions | 128 pass | 128 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 13 / 176 pass | 13 / 176 pass |
| Stock full / provider failures | 821 / 16 retained | 578 / 8 retained |

Every ticket-listed selected target passed with zero allowances. Final selected,
stock-full and stock-provider command statuses are `[0, 2, 1]` on both platforms.
The native stock audit adds exactly 64 empty-directory total-line failures;
all 757 predecessor native failures and all Linux stock failures persist.
The task-owned Linux container was removed after collecting its results.

`python3 docs/evidence/csh-116/verify.py` passes source/provider provenance,
exact predecessor expectations, new-case counts, channels, effects and cleanup.
All 12523 native and 12563 Linux predecessor expectations are unchanged. The
verifier reconstructs each platform's source digest using its retained generated
provider headers and checks the unchanged shell source/header baseline. Every
new expected total is reconstructed from the retained pre-exec measurements.

Ticket validation passes 24 registry tests and the live check with 117 shared
reservations. The two existing historical shared-branch warnings are unchanged.
No new sanitizer, standalone runtime/PTY or separately hosted native-Linux run
is claimed. The required host suites include their existing terminal witnesses.

`summary.json` and `stock-failure-comparison.json` retain the verification
results; `records.json` checksums the compressed reports and logs. This is ready
for review, dependent on CSH-115, and is not marked integrated or fully conforming.
