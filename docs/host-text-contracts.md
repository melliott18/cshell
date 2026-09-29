# Text and byte stream qualification

CSH-073 supplies a **bounded subset**, not 25 complete utility qualifications.
The [section ledger](../tests/host_text_contracts.json) accounts for every
normative behavior section of each assigned page, the U-034 exec requirement,
U-040 common defaults, and the five retained conditions. Its per-utility
`remaining_contracts` fields identify open behavior; no `partial` or `open`
entry is a conformance disposition. CSH-073 remains their open qualification
owner; selected utility/libc/platform vendors retain implementation ownership.

## Reproduce

```sh
make test-host-inventory test-host-text-harness
make test-host-text
make test-host-profile
make test-host-text-audit  # strict audit, currently fails on both selected hosts
```

`test-host-text` uses the stock standard PATH. `test-host-profile` also executes
the text subset with its separately provisioned PATH. The tools are resolved
and hashed independently for each run. Neither command installs a replacement
text utility. Missing required executables and setup errors fail, and no known
gap signature is accepted. For a deliberately selected alternative provider:

```sh
python3 tests/host_text.py ./cshell --path /selected/bin:/usr/bin:/bin \
  --boundaries --record build/text-selected.json
```

On Linux, provision from the repository Dockerfile (Debian coreutils, diffutils,
GNU sed, binutils strings, and ed). Supply filesystem capacity only inside an
explicit disposable mount; the harness refuses filesystems larger than 2 MiB:

```sh
docker build -t cshell-text .
docker run --rm --tmpfs /capacity:rw,size=1m,mode=1777 cshell-text \
  make test-host-text HOST_TEXT_FLAGS='--capacity-root /capacity'
```

Retain the JSON outside the ephemeral container when recording evidence. Native
macOS uses its OS-provided tools with OS build and SHA-256 identities. Linux JSON
also includes package ownership queries and the full package version list.

## Assertion boundaries

Every ordinary case runs directly at the selected executable pathname and
through public cshell PATH dispatch in `-c`, file and stdin modes. Each runs in
a new directory with authored input, exact expected streams/status and relevant
file effects. Scripts redirect utility input from a private file so stdin-mode
shell source cannot be consumed as utility data. No utility under test generates
its own expected bytes: cksum uses polynomial long division with length folding;
all other expected bytes/counts/offsets are authored independently.

Numeric padding is accepted only where XBD 5 allows it for unspecified integer
precision, and od accepts its specified blank-separated values and optional
final empty line. No prompt stripping, sorting, arbitrary whitespace removal,
or output substring checks are used. Diagnostics with unspecified wording use
nonempty predicates; `cmp` EOF also checks the required grammar. Ordinary error
predicates reject signal death. Exact file lists are checked for successful
splits, suffix exhaustion and csplit cleanup. The csplit `-k` error case checks
the completed first piece; implementations may also retain an unfinished piece.

The case ledger maps the supported slices and leaves the rest open:

| Utility | New bounded assertions | Significant open contract examples |
| --- | --- | --- |
| cat | Every byte, ordered/repeated stdin, -u; FIFO TERM; Linux blocked-write TERM and ENOSPC | Native capacity, read faults, -u timing, EINTR/short-write recovery |
| cksum | Empty, text, all-byte CRC and file order | Non-regular inputs and I/O errors beyond missing files |
| cmp | Equal/different/EOF; differing byte 2147483649 and octal bytes 130/131; FIFO/write TERM | Wider offsets, non-C diagnostics; default format in audit |
| comm | All eight column-suppression combinations in C locale | Non-total collation and equal-weight ties |
| csplit | Line, BRE, discard, custom names, cleanup, -k retention | Repetition, offsets, NAME_MAX and signal cleanup |
| cut | Byte/character overlap and field/delimiter/suppression in C locale | UTF-8 -c and -b -n in strict audit; long lines and further locales |
| diff | Equal, normal, ed, forward and blank-folded comparisons | Context/unified, recursive directory loops and binary input |
| expand | Default/explicit tab stops and backspace | Multibyte widths and faults |
| fold | Default, byte width, spaces and carriage return | Multibyte widths and backspace/tab combinations |
| head | Default, bytes, lines, multi-file headings, INT32 count; FIFO/write TERM | INT32+1 boundary in audit; wider counts and native blocked writes |
| join | Default join, unpaired records, selected fields | Duplicate keys, -v, -e and non-C collation |
| od | All 256 unsigned byte values; skip/count | Other numeric types, multibyte characters, repeats, offsets and padding |
| paste | Parallel, serial, delimiter cycling and repeated stdin | Escape delimiters and I/O faults |
| pr | Headerless, double spacing and numbering | Default headers/dates, pages, columns and terminal policy |
| sed | Substitution, hold, next, range, branch, translation, script file; UTF-8 class/repetition | UTF-8 backreference in audit; other commands/addresses, allocation limits |
| sort | C, numeric, reverse, unique, fields, case, check, merge/output | Non-C collation, modifiers and temporary-file/resource failures |
| split | Lines/bytes/suffixes, empty input and suffix exhaustion | Default size, k/m, NAME_MAX and interruptions |
| strings | Whole-file scan and minimum length | Default scan policy, offsets and multibyte printability |
| tail | Line/byte/start/end/zero counts and sparse offset | -r in audit; follow mode and buffering limits |
| tee | Exact bytes, append, literal - file, 13 operands, open-error continuation | -i, latency and mid-stream write errors |
| tr | Translation, deletion, squeeze, complement, classes | -C, multibyte, equivalence classes and repeat/range combinations |
| tsort | Unique chain ordering | -w in audit; multiple cycles and independent nodes |
| unexpand | Leading/all blanks and explicit stops | Backspace, existing tabs and multibyte widths |
| uniq | Adjacent/nonadjacent duplicates, -d/-u, field/character skips, output file | Counts, combined skips, multibyte and faults |
| wc | Counts, bytes, newlines, totals and UTF-8 characters | Further locale whitespace and I/O faults |

XSI-only portions of od/pr and NLSPATH remain outside the selected base profile.
Optional shading never removes the unshaded utility's obligations.

## Retained conditions and signals

- `U-040/cat-filesystem-limits`: direct exec and cshell `exec` run cat with an
  already-open output file on a dedicated 1 MiB tmpfs. A private padding file
  first encounters measured ENOSPC; cat must diagnose failure and leave zero
  output bytes. This is filesystem exhaustion, distinct from RLIMIT_FSIZE.
  Native capacity remains unavailable. Only private files are removed afterward.
- `U-040/sed-space-limits`: UTF-8 alphabetic class plus bounded repetition
  (`éa` to `X`) supplies a new expression oracle beyond the old dot witness.
  Backreferences and maximum/allocation space still remain open.
- `U-040/head-count-interruption`: FIFO writer rendezvous proves the selected
  head opened its input; TERM must terminate that PID. A separate audit measures
  INT32+1 acceptance. The recorded macOS rejection is a count boundary, not a
  claim that every positive integer must be representable.
- `U-040/cmp-offset-interruption`: two sparse files have independent markers
  at zero-based offset 2³¹; `cmp -l` must identify byte 2147483649 with octal
  values 130/131. No checksum or selected utility computes the expected offset.
  FIFO TERM and Linux write TERM are separate assertions.
- `U-040/other-interruptions`: cat/head/cmp FIFO TERM and Linux blocked-write
  TERM are per-utility assertions. Linux `/proc/PID/wchan` must report
  `pipe_write` after a private pipe is filled, before signalling the selected
  process. macOS has no supplied equivalent observer and stays unqualified.
  No claim is made that the FIFO handshake observes a read syscall returning
  EINTR, or that termination establishes retry/recovery behavior.

The shared **ed** witness is explicitly coordinated with CSH-074: changed-buffer
acknowledgement and the next `-p READY>` command prompt precede HUP, which
must save exact `ed.hup` bytes without further
stdout/stderr. The strict audit separately requires the POSIX SIGINT `?\n`
stdout response and unchanged buffer on subsequent `1p`. This audit fails on the
selected providers; it does not count as qualified recovery. CSH-074 retains ed's
complete page and the provider repair, while CSH-073 retains the shared condition.

On Linux, ed must additionally reach `pipe_read` before the signal. The prompt
handshake replaces an earlier line-only handshake that did not fence print
completion; the original duplicate-output failure remains retained. On macOS,
only the command prompt supplies that fence.

Signal probes run directly and through cshell `exec`, which preserves the owned
PID. Initial dispositions are explicitly defaulted so launcher-inherited ignores
do not change the experiment. Five-second operation deadlines and two-second
cleanup waits and a 65,536-byte capture ceiling bound the probes. Leaders are killed if needed and reaped; private
fixtures are checked removed. Tests force an early exit and a stalled provider
and check failure, cleanup and inherited-ignore handling. These probes exercise
providers that do not create descendants for these operations; they do not claim
portable orphan/zombie reaping for arbitrary substitute programs.

## Results and open ownership

See [retained native/Linux evidence](evidence/csh-073/README.md). The strict audit
keeps unchanged expectations for GNU tail -r, tsort -w, UTF-8 cut, native sed
backreferences, and ed SIGINT output. Positive subset results do not qualify
these requirements, the full pages, U-034/U-040 families, or the CSH-012 gate.
The current ownership manifest links the section ledger; immutable CSH-064 and
CSH-068 evidence remains unchanged. CSH-073 stays open for its per-utility
remaining contracts, unavailable native capabilities and vendor requalification.
