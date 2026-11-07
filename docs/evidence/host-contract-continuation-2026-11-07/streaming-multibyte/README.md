# Streaming, multibyte operations and interrupted-write attestation

This follow-up adds finite strict contracts and repairs M4. CSH-073 and CSH-074
remain in review; CSH-079 remains blocked. None is accepted. The user confirmed
that no disposable resettable Mac is currently available. No low-stack exec
experiment was run on the personal host.

## Changes

- `host_text_streams.py` checks output before input EOF for cat -u and tee,
  including two file copies and append. Tail -f checks regular-file append,
  retained-descriptor behavior after rename, named-FIFO close/reopen, and ignored
  follow mode on a stdin pipe. Direct and replacing cshell exec modes each run
  seven cases. Exact bytes, status, stderr, intermediate effects, owned-child
  reaping and fixture removal are required. Each case has an eight-second bound.
  The rename case records the selected descriptor-follow policy. The remaining
  cases derive from the cat, tee and tail DESCRIPTION/OPTIONS sections.
- Pinned GNU M4 now interprets len/index/substr/translit arguments as characters
  in multibyte locales. Output is re-encoded with a conversion state, and
  substring bounds use subtraction to avoid signed integer overflow. Leading
  and trailing translit hyphens are literal; interior GNU ranges retain their
  extension behavior. The old provider returned malformed UTF-8 and, for a
  large substring count, a segmentation-fault diagnostic with status 2.
  Eleven new cases (44 public-mode assertions) cover character positions,
  combining characters, missing/empty search strings, substring bounds,
  translations/deletions, edge hyphens, and INT_MAX counts in UTF-8 and C.
- `--multibyte-audit` adds a separately selectable 22-case, 88-assertion language
  audit. Known failures return nonzero and remain outside the passing subset.
  A preliminary duplicate-source translit case was removed: POSIX explicitly
  leaves duplicate source characters unspecified. Its raw exploratory result is
  retained, but it is not counted as a provider failure or a qualified contract.
- The CSH-079 restart helper captures the interrupted instruction pointer through
  SA_SIGINFO, and resolves its symbol after leaving the signal handler. Restart
  success requires a write syscall symbol, the exact drained prefill and exact
  resulting payload. A single restart alarm prevents a subsequent timer from
  replacing that evidence. Other dispositions retain recurring alarms because
  echo can attempt its trailing newline after an earlier output failure.
  Negative controls reject a signal observed in setitimer, missing signal,
  residual prefill, stream error, buffered cat and missing tee file writes.

Normative sources: [cat](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/cat.html),
[tee](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tee.html),
[tail](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/tail.html), and
[m4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/m4.html).
Each additional language fixture names its own page and sections. These witnesses
are not a disposition for every other section of those pages.

## Validation

| Check | macOS 14.8.7 / Darwin 23.6 arm64 | Debian 12 arm64 |
| --- | --- | --- |
| Live streams | 14 PASS | 14 PASS |
| Interrupted output with write-location attestation | 40 PASS | 40 PASS |
| M4 ordinary contract suite | Included in 877 language/editor PASS | 148 PASS |
| M4 ASan/UBSan contract suite | 148 PASS | Not rerun with sanitizers |
| Interrupt helper ASan/UBSan | 40 PASS | Not rerun with sanitizers |
| Broader multibyte audit | 72 PASS, **16 FAIL** | 76 PASS, **12 FAIL** |

Native language/editor qualification includes the ed fault helper and signal
recovery. The focused Linux run qualifies the changed M4 and stream/interrupt
paths; it does not claim a rerun of all unchanged language providers. Native
harness validation passes 36 tests. Linux text harness validation passes 18.
Ownership accounting and all 160 filesystem controls also pass. The live ticket
identity check passes with 114 reservations.

The native audit fails awk length/substr/index and match positions, expr match
length, and ed multibyte backreferences in all four invocation modes. Debian's
selected awk fails length/substr/index, match positions and global dot
substitution in all four modes. These are required-contract failures, not missing
locale capabilities or accepted platform variants. They need provider repairs.

The full CSH-073 per-page remainder remains in `host_text_contracts.json`;
this follow-up closes only the listed streaming evidence gaps. CSH-074 still
owns its page remainders and the newly demonstrated failures. CSH-079's prior
Darwin libc allocator crashes and unavailable historical low-stack investigation
remain unresolved. The low-stack checklist item is unchecked to distinguish an
explicit blocker disposition from completed reproduction.

## Reproduction and retained attempts

From the repository root, after provisioning the documented selected profile:

```sh
python3 tests/host_languages.py ./cshell --path "$PWD/build/host-profile/bin:/bin:/usr/bin" --ed-faults build/tests/host_ed_faults --record build/languages.json
python3 tests/host_languages.py ./cshell --path "$PWD/build/host-profile/bin:/bin:/usr/bin" --case 'm4/*' --record build/m4.json
python3 tests/host_languages.py ./cshell --path "$PWD/build/host-profile/bin:/bin:/usr/bin" --multibyte-audit --record build/multibyte-audit.json
PYTHONPATH=tests python3 -m unittest test_host_text test_host_languages test_host_formatted
```

`focused.py.gz` is the exact stream/interrupt driver (decompress and run from the
repository root with a result-file argument). Sanitizer builds use
`-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`; M4 build metadata
retains effective flags and source/patch/binary hashes. Records retain their
actual source digests, not a retroactively substituted final commit identity.

Initial interrupted-helper compilation failed because Darwin requires
`sys/ucontext.h`; a stale-helper run consequently lacked the new symbol field.
A second attempt exposed that making all alarms one-shot hangs echo's trailing
newline after EINTR; recurring alarms were restored except for restart mode.
One initial harness run failed the existing ed diagnostic-capture negative
control; its isolated rerun and final suite pass. Its cause is unestablished and
the failure is retained. The first Linux text harness run used an older
provisioning module from the reused image and rejected the current paste-aware
manifest fixture. Copying the current module into that task-owned container
restored all 18 passing controls. No passing rerun erases these attempts. The original
multibyte audit retains the obsolete unspecified translit case separately from
final contract results. `records.json` supplies uncompressed SHA-256 hashes for
all retained records. All task-owned test containers and temporary children were
removed after collection; no system provider was replaced.
