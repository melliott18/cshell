# CSH-073, CSH-074 and CSH-079 continuation

This continuation repairs concrete provider failures and adds required-contract
checks. It does **not** complete or accept these three tickets. The remaining
page obligations retain their existing owners. Earlier failed evidence is not
replaced by subsequent passes.

## Changes and normative basis

- CSH-073 adds 33 cases (132 assertions in four modes): either stdin operand for
  comm/join; empty parallel/serial paste operands; same-input sort output;
  default/k-unit split boundaries; integer od types, padding and `-v`; pr
  columns, nine-file merging, starting pages, short pages, tabs/offsets and
  single-column width; tr octal/equivalence behavior; and unexpand column state.
  [paste OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/paste.html)
  requires a newline for an empty `-s` operand. Native paste omits it. The
  checksum-pinned GNU coreutils 9.11 build now supplies paste in the repaired
  profile. These three cases belong to the strict audit, as do the previous
  required cut/tsort failures; the stock subset makes no claim for them.
- CSH-074 adds 15 patch cases (60 assertions). The private GNU patch 2.8 build
  now selects POSIX behavior, writes progress/reject/reverse messages to stderr,
  reserves stdout for filename prompting, initializes locale categories and
  evaluates the locale's affirmative expression. Anonymous intermediate files
  preserve the preceding version of each input for repeated/interleaved `-o`
  patches, including empty output and ed scripts. The original inputs remain
  unchanged. These contracts derive from
  [patch OPTIONS, Filename Determination and STDERR](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/patch.html).
  System executables are unchanged. The source archive, license, local diff and
  build hashes remain in `tools/host-profile/vendor/patch` and the result records.
- CSH-079 adds 16 assertions for actual interrupted writes: caught SIGALRM with
  `SA_RESTART`, and interruption after a nonempty output prefix, for literal,
  `%s`, `%b` printf and literal echo through direct and replacing exec paths.
  A prefilled private pipe proves the restart boundary; the signal handler
  drains only that prefill with async-signal-safe read. Partial-write payloads
  are generated after exec and are checked against an independently authored
  byte prefix. No ARG_MAX, host-stack or host-volume changes are involved.
- A separate Darwin allocation audit arms dyld interposition only during the
  real `vprintf` call. It fails individual malloc/calloc/realloc calls and
  records the caller image/symbol **before** returning NULL. This is actual
  controlled allocator failure inside libc, not the older API-return injection
  and not physical memory exhaustion.

`records.json` identifies the compressed records and their uncompressed hashes.
Each suite retains its actual source-input digest and executable/provider hashes;
the records are not relabeled as having identical source revisions. Late changes
limited the known stock paste failures to `--audit`, added the Docker lzip build
dependency, and updated documentation. The repaired audit's case expectations
were unchanged by the stock-subset selection change.

## Validation

| Environment / check | Result |
| --- | --- |
| Native macOS 14.8.7 / Darwin 23.6.0 arm64, repaired text audit with private FAT12 capacity | 924 PASS, 0 FAIL, 0 unavailable; owned image detached and removed |
| Native text syscall/allocation injections | 24 PASS, 0 FAIL |
| Native selected language/editor profile | 833 PASS, 0 FAIL |
| Native patch ASan/UBSan | 136 PASS, 0 FAIL |
| Native formatted contracts | 704 PASS, 0 FAIL; the Darwin argument-limit exclusion and omitted capacity scope remain explicit |
| Native interrupt-helper ASan/UBSan | 40 PASS, 0 FAIL |
| Native selected-PATH runtime / PTY | 3950 runtime PASS; all notification, job, terminal-control and trap PTY stages pass |
| Native ownership and harness checks | ownership inventory and 13 regressions, 160 filesystem controls, 17 text controls, eight language controls and eight formatted supervisor controls pass |
| Darwin libc allocator audit | 4 PASS, **6 FAIL**; details below |

The Debian 12 arm64 Docker continuation passes 924 text checks with real tmpfs
capacity, 833 language checks, 704 formatted contracts, 24 text fault checks,
136 sanitizer patch checks, 40 sanitizer interrupt checks, 3950 runtime cases
and all PTY stages. Ownership/text harness checks also pass. Docker image and
container identities are retained in `docker-context.json.gz`; all owned
containers are removed after evidence capture. Normal selected profiles do not
include the deliberately failing Darwin libc audit.

## Required failure: Darwin floating conversion allocation

Run `make test-host-formatted-libc-audit` on Darwin. For `printf '%.10000f' 1`,
the independent successful result is `1.` followed by 10000 zeros. Failure of
libc's stdio-buffer allocation (`__smakebuf`) recovers and produces those bytes.
Failures of three allocations originating in `__Balloc_D2A`, at 80, 36 and
16412 bytes in this run, instead terminate with SIGSEGV. The same three failures
occur in direct and cshell exec modes. Each owned process was reaped and its PID
was verified absent. The audit returns nonzero; no crash is accepted as error
handling. No root cause beyond the attested allocation boundary, or vendor fix,
is claimed. The selected Darwin libc floating-conversion path needs a repair or
an independently qualified replacement before this obligation can be accepted.

This does not resolve the historical low-stack exec observation. The personal
host exclusion remains enforced; reproduction still requires a disposable
Darwin 23.6 environment that can be reset. The earlier macOS 15 result is a
separate kernel/platform observation.

## Failed and incomplete attempts retained

- `patch-before.json.gz` retains wrong-channel failures, failed header fallback
  and repeated `-o` output, along with initial prompt-fixture failures. The final
  fixture uses the specification's permitted reject-header/format variability;
  it does not adopt the old provider's incorrect stream or output effects.
- `text-first.json.gz` retains the three native paste failures.
- `text-native-timeouts.json.gz` records two timeouts in the existing
  strings/offset-decimal fixture and two unavailable capacity cases. Their cause
  is not established. The later private-capacity run passes; it does not erase
  those timeouts.
- `formatted-setup-failure.log.gz` records a direct runner invocation before its
  echo helper was built. The Make target supplied the missing prerequisite.
- `linux-setup-failure.log.gz` records missing lzip when extracting pinned ed.
  Docker development provisioning now supplies lzip; no checksum was bypassed.

## Acceptance review

CSH-073's five retained *capability* requirements now have strict supplied
witnesses (real capacity, sed growth failure, head/cmp read interruptions/counts,
and per-utility cat/head/cmp/ed signal recovery). Its complete-page criterion
remains unmet: the per-utility remainders in `tests/host_text_contracts.json`
include additional locale, formatting, streaming and error contracts.

CSH-074's new patch obligations pass, but the other language/editor page sections
and common-default remainders in `tests/host_language_contracts.json` still need
implementation and qualification. Passing patch cases do not complete awk, bc,
ed, expr, grep, m4 or xargs.

CSH-079 is blocked for acceptance by the attested Darwin libc crash and the
unresolved disposable-environment investigation, in addition to the retained
locale/format partitions. None of these tickets is marked done or closed.

## Subsequent streaming and multibyte work

The [follow-up](streaming-multibyte/README.md) adds live-stream checks, repairs M4
character operations and substring overflow, strengthens interrupted-write
attestation, and retains newly demonstrated awk/expr/ed failures. None of the
three tickets is accepted.

## Subsequent provider repairs

The [provider repair review](provider-repairs/README.md) resolves the selected
awk/expr/ed multibyte failures and supplies an allocation-safe formatting
replacement. Historical vendor failures remain in their original records.
Full-page qualification and the disposable-Mac investigation remain open.
