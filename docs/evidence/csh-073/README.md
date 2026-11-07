# CSH-073 qualification evidence

The final bounded subset is distinct from the strict audit and from complete
utility qualification. [The clause map](../../host-text-contracts.md) and
[section ledger](../../../tests/host_text_contracts.json) state the exact
boundary. Full ticket acceptance remains open; failed vendor contracts and
unavailable native facilities are neither waived nor promoted.

## Final completion results

| Run | Passing assertions | Failures | Unavailable | Exit |
| --- | ---: | ---: | ---: | ---: |
| Native declared subset | 532 | 0 | 8 | 0 |
| Docker declared subset | 540 | 0 | 0 | 0 |
| Native strict audit | 548 | 14 | 8 | 1 |
| Docker strict audit | 552 | 18 | 0 | 1 |

Both platforms pass the 10 existing ownership regressions, the new 25-page/
13-section ledger validation, and all eight new harness regressions. Final run
source hashes match the retained working-tree test/build inputs exactly;
`artifacts.json` records the comparison. The completion JSON/log pairs are
`native-text-completion`, `docker-text-completion`, `native-audit-completion`,
and `docker-audit-completion` (each `.json.gz` / `.log.gz`).

The native host is macOS 14.8.7 build 23J520. Linux packages are coreutils 9.1-1,
diffutils 1:3.8-4, sed 4.9-1+deb12u1, ed 1.19-1, binutils 2.40-2, and libc6
2.36-9+deb12u14. These identities delimit the claims; newer or alternate builds
must execute the same assertions.

## Environment and reproduction

The JSON records retain the exact PATH, selected path/realpath/SHA-256 for all
25 tools plus shared ed, source-file hashes, cshell hash, OS/libc identity,
locale, mount information, resource limits and individual expected/actual
streams/status/effects. Native tools are selected from the macOS system PATH;
Linux tools are Debian packages with ownership queries and package versions.
`artifacts.json` hashes the retained files and identifies the base commit and
Docker images. No host packages were installed or system binaries modified.

Native focused qualification used:

```sh
make test-host-inventory test-host-text-harness
python3 tests/host_text.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" --boundaries \
  --record build/native-text-completion.json
python3 tests/host_text.py ./cshell \
  --path "$PWD/build/host-profile/bin:$(getconf PATH)" --boundaries --audit \
  --record build/native-audit-completion.json
```

The opt-in profile had already been provisioned by `make test-host-profile`.
It does not replace these 25 text tools. Source changes are test/docs only;
cshell's production implementation is unchanged.

Docker validation built the repository Dockerfile. Final focused runs used the
completion image and a read-only `tests/` bind mount (the last harness negative
control was added after image creation). This overlay is included in each
run's source hash. The mount is deliberate and not an unrecorded image change:

```sh
docker build -t cshell-test:csh-073-completion .
docker run --rm --tmpfs /capacity:rw,size=1m,mode=1777 \
  -v "$PWD/tests:/work/tests:ro" -v "$PWD/build:/evidence" \
  cshell-test:csh-073-completion sh -c '
    make test-host-inventory test-host-text-harness
    python3 tests/host_text.py ./cshell --boundaries --capacity-root /capacity \
      --record /evidence/docker-text-completion.json
    python3 tests/host_text.py ./cshell --boundaries --audit \
      --capacity-root /capacity --record /evidence/docker-audit-completion.json
  '
```

The actual recorder captured each command's status separately rather than
allowing the last command to hide earlier failures. Logs and JSON are gzip
compressed without timestamp-dependent headers; read them with `gzip -dc`.

## Strict failures and unavailable capabilities

- Native head rejects count 2147483648. This is a measured count boundary,
  distinct from proof that an arbitrary-width count is required.
- Native and Debian tsort reject the required Issue 8 `-w` option.
- Native sed's selected multibyte backreference returns an illegal-byte-sequence
  diagnostic on valid UTF-8 input. A separate class/repetition case passes.
- Debian tail rejects Issue 8 `-r`; Debian cut emits partial multibyte characters
  for `-c` and `-b ... -n`. These are strict output/option failures.
- Native ed writes `\n?\n` to stderr on INT; Debian ed writes an extra leading
  newline on stdout. The required `?\n` response is unchanged in the audit.
  Because the response assertion fails, no subsequent INT buffer-recovery pass
  is claimed. HUP saving is independently tested. CSH-074 owns ed repair.
- Native Linux-style blocked-write observation and the disposable <=2 MiB
  filesystem are unavailable: three write probes and one capacity probe in each
  of two modes. These eight rows are `UNAVAILABLE`, never passing assertions.

## Attempts and fixture corrections

All retained exploratory results remain evidence of their actual attempts,
not qualifications of the final fixture revision:

| Attempt | Actual outcome | Disposition |
| --- | --- | --- |
| native-text-initial | 512 pass, 16 fail | Four INT32+1 boundaries; four invalid sed branch fixtures using semicolon after a label operand; four native backreference failures; four locale-class oracles that incorrectly assumed the Han character's alphabetic classification. |
| native-text-audit-initial | 536 pass, 22 fail, 8 unavailable | Includes the initial cases plus strict audit and the first signal probes. |
| docker-text-audit-initial | 552 pass, 18 fail | Strict tail/tsort/cut failures and ed response failures; no blanket gap allowance. |
| native-text-prefinal | 532 pass, 0 fail, 8 unavailable | Corrected portable branch syntax and locale class input; unqualified requirements are explicitly audited separately. |
| native-boundaries / native-boundaries-fixed | ed INT failures; HUP pass; native capability limits | Default signal dispositions were made explicit to remove launcher inheritance as a confounder. Captured stderr identifies the native ed response mismatch. |
| native-profile-final | 1161 pass, 1 fail, 0 gaps | Existing stty PTY cleanup's `/bin/ps -axo pid=,stat=` exceeded its 5-second deadline. The utility exited 0. Cause remains unassigned; this profile is **failed**, and make did not reach the added text recipe. |
| docker-profile-final | Existing profile 1162 pass; text subset 540 pass | Full opt-in Docker profile passed before the final ed handshake/capture hardening. |
| native-text-final / native-text-audit-final | Subset 532 pass, 8 unavailable; audit 548 pass, 14 fail, 8 unavailable | Separate focused runs after the native full profile stopped. |
| docker-text-audit-final | 551 pass, 19 fail | Eighteen audit failures plus one extra printed line in ed HUP direct mode. The line-only handshake had not fenced command completion. Original failure retained. |
| native-boundaries-completion | HUP passes; INT still fails | Prompt handshake added; Linux also observes blocked `pipe_read` before signalling. This is a tighter fixture boundary, not evidence that the original vendor output never occurred. |

The early exploratory source inventories were measured at completion while
implementation was still changing. Their per-case argv/expectations/output are
retained, but those source inventories are **not** claimed as exact execution
snapshots. Final completion runs capture source identity before executing cases
and were run with the test sources held unchanged. No later passing result is
assigned as a diagnosis of the unrelated native PTY timeout.

The new harness regression checks cover independent CRC known answers, corrupt
numeric output, missing file effects, inherited signal ignores, early provider
exit, operation timeout, process reaping/fixture removal, capture byte limits,
and missing/dangling section mappings. No newly run sanitizer, hosted CI, or
whole-shell conformance result is claimed.
