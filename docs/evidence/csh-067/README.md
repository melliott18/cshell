# CSH-067 validation record

Date: 2026-09-29. Baseline: `f07568223c02f488924e8599bf9b9f1013b03164`.
Branch: `test/CSH-067-locale-pathname-qualification`. The accompanying test and
provisioning changes form the source under review; production C sources are
unchanged. [Source manifest](source-sha256.json) fingerprints test inputs.

## Environments

- Native macOS 14.8.7 (23J520), arm64, Apple Clang 15.0.0, LibSystem
  1345.120.2 (executable `otool -L`), APFS. UID/EUID 501, GID 20;
  supplementary groups and locale inventory are in [native.json](native.json).
  Supplied Apple `ja_JP.eucJP` decodes SS2 `8e b6` and SS3 `8f a2 af`.
- Docker Debian bookworm, aarch64, LinuxKit 6.4.16, GCC 12.2.0,
  glibc 2.36, overlayfs. UID/EUID/GID 10001, no supplementary group beyond
  10001. Docker builds Linux objects; no Darwin binary is reused.
  [linux.json](linux.json) records compiled `csh_067.UTF-8`,
  `ja_JP.EUC-JP`, GB18030/UTF-8 candidates, definition/dependency hashes,
  credentials and binaries. The libc file SHA-256 is
  `e4ac8ae1d81e4865e3aadedb962879cf9415903b3f2ba81ec75e9962b86ab8b0`.
  This is Linux **container** evidence; native Ubuntu CI is separately configured,
  not claimed to have run by these local records.

Q runs each shell case with the shared five-second deadline, 65,536-byte output
bound, resource limits and process-group cleanup. Scripts and exact expected /
actual stdout/stderr are hex in JSON; all status assertions are exact. Directory
permissions are real owned fixtures, capability-checked before tests. Injected
readdir errors are explicitly marked `instrumented public runtime`; a marker
proves an error occurred after returning the real `match` entry. They do not
claim an unmodified executable experienced kernel EIO or a failing mount.

## Commands and results

| Check | Native macOS | Linux container |
| --- | --- | --- |
| `make test-locale-pathname` | 50 passed, 0 failed, 1 capability skip | 56 passed, 0 failed, 0 skipped |
| `make test-portability` (existing driver, in addition to Q dependency above) | 2,206 passed, 0 failed, 5 capability groups skipped | 727 passed, 0 failed, 3 capability groups skipped |
| CSH-053 included in portability | 2,044 passed, 0 failed, 4 raw-filename capability skips | 553 passed, 0 failed, 3 locale capability skips |
| `make test-fields` | 110/110 | 110/110 |
| `make test-harness` | 86 tests, OK | 86 tests, OK |
| ASan/UBSan `make test-locale-pathname test-fields` | 50 passed / 1 skip; 110/110 API checks | 56 passed / 0 skips; 110/110 API checks |

Log trailing whitespace is normalized; byte assertions remain exact in JSON.
Normal aggregate logs: [native.log](native.log), [linux.log](linux.log).
Final focused runs and detailed results: [native-focused.log](native-focused.log),
[native.json](native.json), [linux-focused.log](linux-focused.log),
[linux.json](linux.json). Sanitizer logs/results:
[native-sanitizer.log](native-sanitizer.log), [native-sanitizer.json](native-sanitizer.json),
[linux-sanitizer.log](linux-sanitizer.log), [linux-sanitizer.json](linux-sanitizer.json).

Sanitizer flags after `make clean`:

```sh
make -j4 test-locale-pathname test-fields \
  CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Docker normal validation uses `docker build -t cshell-test:csh-067 .`, followed
by `docker run --init cshell-test:csh-067 make ...`. Root-only focused validation
([log](linux-root.log), [record](linux-root.json)) tests the capability gate:
51 pass, 0 fail, 1 permission group skips because UID 0 bypasses owner mode
restrictions. The non-root run, not the root run, qualifies that permission group.

## Retained boundaries

The [condition map](../../locale-pathname-qualification.md) assigns P1–P6.
Native Q's skip is the supplied libc-specific collation definition. Native
portability skips are four raw-name groups (APFS EILSEQ) and one untranslated
libc diagnostic group; source decoding passes independently. Linux portability
skips Shift-JIS, Big5 and GBK candidate locales, but executes GB18030 raw
pathnames. French libc diagnostics pass on Linux. The module/API records remain
separate from public shell evidence. All named prerequisites remain visible;
no skip becomes a pass and no family is promoted to fully verified.

No production defect was confirmed in these exercised conditions. New public
regressions preserve the existing behavior and prevent the formerly API-only
boundaries from being mistaken for public-runtime coverage.
