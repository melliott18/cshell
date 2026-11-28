# CSH-117: measured ls inode and file-type rendering

The separate `test/CSH-117-filesystem-environments` worktree starts at CSH-116
commit `0b5d6d8`. CSH-116 is under review in PR #247, based on CSH-115 PR #245;
these prerequisites are not represented as integrated. No shell C sources or
selected providers change.

## Contract and independent oracle

The [Issue 8 ls specification](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ls.html)
OPTIONS defines `-i` file serial numbers, `-F` file-type suffixes, `-p` directory
suffixes, and the `-d`, `-H` and `-L` symbolic-link rules. DESCRIPTION and STDOUT
supply C-locale sorting and one-entry-per-line output. The retained HTTPS source
matches the section map's SHA-256; browser retrieval returned 403 and curl
retrieved the source successfully.

Thirty-six cases run through direct exec and cshell string/file/stdin modes,
for 144 assertions per platform. Plain, `-F` and `-p` formats combine with or
without `-i`, physical/`-H`/`-L` handling, and either a directory listing with
`-A` or reversed explicit operands with `-d`. The private graph contains a
hidden file, ordinary file and hard link, three files with independently set
user/group/other execute bits, a directory and preserved child, a FIFO, and
symlinks to the ordinary file, executable file, directory and FIFO. Neither
executables nor FIFOs are opened for execution or data transfer.

Before provider execution, independent lstat measurements supply inode numbers,
file types and modes. Explicit mode probes prevent inherited umasks from
changing the oracle. Hard-link device/inode identity and a link count of two
are required. Separate stat probes verify each symlink's referent type, mode
and inode; its inode must differ from the link's. `-H` follows command-line
links only; `-L` also follows directory entries. `-d` explicitly disables the
default command-line directory-link dereference for the physical cases.

The oracle requires exact names, suffixes, inode numbers and C order, empty
stderr and zero exit status. Only inode-column space padding is accepted.
Metadata (device/inode, type/mode, uid/gid, link count, size, allocation and
mtime/ctime), file contents, link text and directory entries must remain
unchanged. Access times are excluded because inspection can update them.
Setup, capture and cleanup failures fail the assertion. Reports retain exact
provider paths/hashes, source/build provenance, channels, status, measurements
and cleanup separately. Expected values never come from provider output.

Five harness tests cover every case in every mode, explicit suffix and inode
expectations, bad output/order/channels/status and mutated objects, partial
setup/failed probes, failed exec and bounded timeout with reaping and cleanup.
The synthetic capture traverses actual entries using argv independently of the
fixture's expected-entry function; literal assertions also pin suffixes and
hard-link/referent relationships.

## Stock observations and remaining scope

Apple stock ls uses the symlink inode and type for non-directory `-H` operands.
Four new cases fail in each mode (16 strict stock failures): plain/`-p` with
`-i`, and `-F` with or without `-i`. The selected unmodified GNU coreutils 9.7
ls passes. No allowance or provider change is added. Predecessor stock failures
remain separately retained.

Sockets, devices, arbitrary graphs, other identities/ACLs, name-based owner/group
rendering, recent timestamps, remaining sorting switches, default block units,
terminal formatting, non-C collation, namespace races and resource/size failures
remain unqualified. This does not exercise kernel faults, libc injection or real
filesystem exhaustion. All 21 full utility contracts and four original U-040
conditions remain individually open under
[CSH-118](../../tickets/CSH-118-filesystem-environment-residuals.md) / [#248](https://github.com/melliott18/cshell/issues/248).
U-034/U-040 remain partial; utility/libc/platform vendors retain implementation
ownership. Historical evidence is unchanged.

## Reproduction

```sh
# Native prerequisites: documented GNU tools, including gfind, on PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-117/validate.py native

docker build -f docs/evidence/csh-117/Dockerfile.linux -t cshell-test:csh-117 .
docker run --init --name cshell-csh117-validation cshell-test:csh-117 \
  python3 docs/evidence/csh-117/validate.py linux
docker cp cshell-csh117-validation:/work/build/csh117-validation ./build/csh117-linux-results
# Collect compressed reports, logs and generated provider headers here, then:
python3 docs/evidence/csh-117/verify.py
docker rm cshell-csh117-validation
```

The Docker image layers sources onto retained `cshell-test:csh-116`
(`sha256:6cb63b44cb5a74745dbe3d7b9e8b5afb01d9cc27551a3b0443d43393c914b63a`)
and runs as its unprivileged `cshell` identity. This is Linux/Docker evidence,
not separately hosted native Linux. Native provisioning uses a private copy of
the predecessor's gfind. No new sanitizer or standalone runtime/PTY qualification
is claimed; required host suites include their existing terminal witnesses.

## Development records

The first native provisioning attempt lacked gfind; it was supplied privately
before final validation. An early metadata-update script stopped on a nonexistent
section key, leaving the clause map temporarily incomplete while a harness run
was starting. The script was corrected before the final validation. These
intermediate logs are retained separately from final-source evidence. The first
selected commands also caught a stale human-readable ownership ledger, which
was corrected before rerunning them. Linux selected validation was moved to a
separate task-owned container so completion of the stock-audit container could
not end the selected process. Both use the same image and unprivileged identity.

## Final validation — 2026-11-10

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 12795 pass, 0 fail | 12835 pass, 0 fail |
| New inode/type assertions | 144 pass | 144 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 13 / 181 pass | 13 / 181 pass |
| Stock full / provider failures | 837 / 16 retained | 578 / 8 retained |

Native runs on macOS 14.8.7 arm64 as uid 501; Linux/Docker runs LinuxKit 6.4.16
aarch64 with glibc 2.36 as uid 10001. Every ticket-listed selected target passed
with zero allowances. Final selected, stock-full and stock-provider command
statuses are `[0, 2, 1]`. The successful selected command replaces only command 0;
failed initial command records and logs remain in `development/`. The initial
Linux selected exec ended with status 137 when its stock container exited; the
separate selected container completed successfully. Both task-owned containers
were removed after evidence collection.

The verifier passes source/provider provenance, all predecessor expectations,
new-case counts, exact channels and status, measured inode/type expectations,
unchanged objects and cleanup. All 12651 native and 12691 Linux predecessor
expectations remain unchanged. It reconstructs source digests from the retained
platform-specific generated headers and checks the unchanged shell source/header
baseline. The native stock audit adds exactly 16 `-H` failures; every one is a
stdout mismatch with zero status, empty stderr, unchanged objects and successful
cleanup. All 821 previous native stock failures and all Linux stock failures
persist. No provider change or allowance is introduced.

Ticket checks pass 24 registry tests and the live identity check with 118 shared
reservations. The two historical shared-branch warnings are unchanged.
`summary.json`, `stock-failure-comparison.json` and `records.json` retain totals,
comparisons and artifact checksums. CSH-117 is ready for review and depends on
CSH-116; full utility qualification and integration are not claimed.
