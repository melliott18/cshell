# Controlled credential sanitizer policy

The first CSH-136 hosted Docker job passed its ordinary controlled-credential
stage, then failed 24 owner/group `test` and `[` assertions in its newly reached
sanitizer stage: 2,257 passed, 24 failed, zero gaps. The exact identity output was
correct, but LeakSanitizer terminated every unequal-ID provider. The permission
sanitizer and final unprivileged full sanitizer stages were not reached.

- [Hosted failing job](https://github.com/melliott18/cshell/actions/runs/46170463319/job/141057473243)
- [GCC 12 runtime source](https://github.com/gcc-mirror/gcc/blob/releases/gcc-12/libsanitizer/sanitizer_common/sanitizer_linux.cpp): Linux `GetEnv` reads `/proc/self/environ`, and returns null if it cannot read that file.

The independent child in `results.json` confirms `getenv("ASAN_OPTIONS")` still
sees `halt_on_error=1:detect_leaks=0`, while opening `/proc/self/environ` returns
EACCES after the same unequal-ID exec. This is unavailable sanitizer option
discovery, not a missing Python environment handoff. Leak scanning is already
disabled by the Linux harness because its inspection cannot operate with these
credentials. The provider now supplies the same policy through default-option
hooks in Linux ASan builds; ordinary builds and Darwin have no hooks.

`run.py` compiles the retained `before.c` and the current provider with identical
GCC ASan/UBSan flags. The same helper, shell, private inode owner/group modes,
identity pairs, stdout/status expectations, and string/file/stdin modes run
against both. All 24 fail before and all 24 pass after. Two separately compiled
fault controls preserve fatal memory and undefined-behavior diagnostics after
unequal-ID exec. The memory control uses ASan alone so UBSan object-size detection
does not terminate first. No predicate, credential, timeout, or diagnostic
assertion is relaxed.

Reproduce from repository root with the existing Debian development image:

```sh
output=$(mktemp -d /tmp/cshell-controlled-sanitizer.XXXXXX)
docker run --rm --init --user 0 \
  -v "$PWD:/repo:ro" \
  -v "$PWD/docs/evidence/csh-136/controlled-sanitizer:/input:ro" \
  -v "$output:/output" \
  cshell-test:csh-129 python3 /input/run.py
```

The recorded local image is
`sha256:5ebc339af9a9c1bf34467c546a1be3c21ba56504f30b65e23edae5bcd8e78a48`.
`results.json` retains compiler/platform identity, source hashes, all original
failures, passing results, proc-access evidence and fatal fault diagnostics.
The container is removed on completion. This focused arm64 reproduction does
not replace the pending complete hosted Docker sanitizer run.

Development records remain separate: `initial-diagnostic-results.json` used an
instrumented diagnostic child whose buffered stdout was lost on the expected
LSan termination and an optimized-away fault; `initial-fault-control-results.json`
fixed the diagnostic but UBSan detected the deliberate memory error first.
The final diagnostic is uninstrumented and the two fatal controls are independent.
Both development runs already reproduced all 24 original failures and all 24
fixed passes.
