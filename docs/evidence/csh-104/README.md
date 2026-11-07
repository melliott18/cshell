# CSH-104 portable numeric magic qualification

This work supplies 360 independently authored `file` cases, each required in
both direct execution and cshell string/file/stdin modes (1440 assertions).
It is stacked on CSH-103 commit `27571a4`; integration remains gated on that
branch. The selected profile has no failure allowances.

## Contract and implementation

POSIX `file`, EXTENDED DESCRIPTION (`type` and `value`), defines signed `d`
and unsigned `u` types with C/S/I/L suffixes or explicit byte counts. The
fixtures use native C char/short/int/long widths, signed minimum/maximum,
unsigned maximum and high-bit ordering, hexadecimal/octal masks and constants,
bit-set/bit-missing predicates, and complete versus truncated `x`/equality
fields. Each predicate has positive and negative witnesses. Python integer
arithmetic and native ABI widths provide independent bytes and expectations;
no provider output or differential shell supplies an oracle. Literal messages
keep numeric parsing independent of printf conversion behavior.

Before each exact provider execution, fixture sample/database bytes are read
back and ABI widths are checked through ctypes and struct. Exact channels,
status and unchanged sample/database contents are required. Setup corruption,
output/status/content faults, missing interpreters and timed-out children have
cleanup regressions. All fixtures remain private regular files; no mounts,
privileged identities or capacity exhaustion are used.

The pinned file 5.46 provider needed three repairs:

- `dL`/`uL` used four-byte storage regardless of native C long width.
- Eight-byte numeric fields omitted the input-length guard and could match
  zero-padding beyond EOF.
- Parsing the signed 64-bit minimum negated INT64_MIN in signed arithmetic.
  Unsigned subtraction now avoids that undefined behavior.

`message-formats.patch` retains every CSH-103 repair and adds these changes.
The manifest records exact binary, release archive, patch, build script and
matching default magic database hashes. Stock and unpatched failures remain
separate. The `long` keyword alias, default d/u widths, further message/type
combinations, multi-database precedence, encodings/locales and resource failures
remain open with all other individual dispositions under CSH-105. All four
original U-040 conditions remain open; U-034/U-040 are still partial.

## Validation

Final results are summarized in `summary.json` and verified in `verification.log`.

| Check | macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 5735 pass, 0 fail | 5775 pass, 0 fail |
| New portable numeric assertions | 1440 pass | 1440 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Allocation probes | 240 pass | 200 pass |
| Ownership / filesystem harness tests | 10 / 116 pass | 10 / 116 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Harness suite | 93 tests pass | 93 tests pass, one Darwin-only skip |
| Focused ASan/UBSan assertions | 2420 pass | 2420 pass |
| Regular / sanitizer format regressions | 14 / 14 pass | 14 / 14 pass |
| Stock full / provider audit failures | 373 / 16 retained | 270 / 8 retained |
| Unpatched file 5.46 new failures | 88 retained | 88 retained |

The stock audits add 96 Apple and 88 Linux numeric failures; every earlier
stock failure is retained. The verifier requires all CSH-103 selected
expectations unchanged and one current source identity across final reports. Full reports retain platform,
compiler/build logs, source and binary identities, actual output/status/effects,
setup and cleanup. `verify.py` compares every old expectation with CSH-103
(only per-run inode facts may vary), checks exact new assertions, requires
unchanged prior stock failure IDs, and verifies current source/provider hashes.
The hosts are macOS 14.8.7 (23J520), Apple Clang 15, arm64/libSystem,
UID 501; and Debian bookworm, GCC 12, aarch64/glibc 2.36, UID 10001.
Native means macOS; Linux evidence comes from an unprivileged Docker container,
not a separately hosted native-Linux runner.

Focused ASan/UBSan runs instrument file/libmagic and require all 2420 numeric,
string and message assertions, plus the existing 14 malformed-format checks.
cshell and other providers remain regular builds in those runs. Runtime,
terminal and harness checks use the selected utility profile.

The `development/` directory retains preliminary failures separately. The
first authored octal spelling was corrected before provider diagnosis; the
corrected pre-repair provider report has 88 failures. The first sanitizer run
has 16 signed-minimum failures, which drove the third repair. Preliminary
inventory/provisioning failures are not counted as final passing evidence. A pre-final Linux run was
stopped after the sanitizer finding; its incomplete results are not accepted.
Intermediate normal runs overlapped source edits and do not supply final identity evidence. Native provisioning copies the exact
gfind executable already qualified by CSH-103 into this worktree's local-bin;
its identity is retained in the manifest. No system installation changes.

## Reproduction

```sh
# Supply gtest, g[, gfind and gdd on the provisioning PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-104/validate.py native
python3 docs/evidence/csh-104/supplement.py native
python3 docs/evidence/csh-104/provider_checks.py native

docker build -f docs/evidence/csh-104/Dockerfile.linux -t cshell-test:csh-104 .
docker create --init --name cshell-csh104-validation cshell-test:csh-104 \
  sh -c 'python3 docs/evidence/csh-104/validate.py linux && python3 docs/evidence/csh-104/supplement.py linux && python3 docs/evidence/csh-104/provider_checks.py linux'
docker start -a cshell-csh104-validation
docker cp cshell-csh104-validation:/work/build/csh104-validation ./build/csh104-linux-results
docker cp cshell-csh104-validation:/work/build/csh104-supplement ./build/csh104-linux-supplement
docker cp cshell-csh104-validation:/work/build/csh104-provider-checks ./build/csh104-linux-provider-checks
docker rm cshell-csh104-validation

# Retain reports here before verifying.
python3 docs/evidence/csh-104/verify.py
```

Selected validation must return zero; separate stock full/provider audits must
remain nonzero. Provider checks retain unpatched failures and reject sanitizer
diagnostics. SHA256SUMS covers every retained evidence file except itself.
