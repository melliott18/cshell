# CSH-043: Define and verify redirection offset maximum

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-037
- Branch: test/CSH-043-redirection-offset
- Issue: [#74](https://github.com/melliott18/cshell/issues/74)

## Goal

Integrated in [PR #88](https://github.com/melliott18/cshell/pull/88).

Resolve the implementation-defined redirection offset maximum in
[SH-009](../posix-matrix.md#sh-009) and
[O-026](../posix-utilities.md#o-026) for each supported system.

## Scope

- Determine the effective maximum for shell redirections from the open file
  description, system `off_t`, filesystem capabilities and resource limits.
  State whether cshell adds any lower limit.
- Exercise a representative success and boundary/error case on native macOS
  and Linux/Docker using sparse files and bounded resource usage.
- Keep pathname expansion's file-size independence separate from redirection
  offset handling.

## Acceptance criteria

- [x] The user documentation names the supported maximum or its precise
  per-file determination rule and the corresponding failure behavior.
- [x] Cross-platform fixtures verify success and failure at the documented
  boundary with exact status, diagnostics and file effects.
- [x] The matrix links the decision, implementation and passing run records.

## Validation

Run the focused sparse-file probes, full native/Docker suites and sanitizers.
Record `off_t`, filesystem limit data, selected resource limits, and exact
platform/kernel/libc versions. Never allocate the full sparse-file length.

## Implementation notes/evidence

[CSH-037](CSH-037-portability-audit.md) demonstrates pathname generation and
append past 2 GiB on two platforms. That observation does not locate the actual
maximum or its error boundary.

### Implementation decision

The [user-facing offset policy](../execution.md#redirection-offset-maximum)
records native `off_t`/`open()` semantics with no extra cshell limit.
[`src/redirect.c`](../../src/redirect.c) already implements that policy, so no
runtime change is needed. The API comment now makes preservation of the open
file description explicit. The filesystem's seek/size limits and process
resource enforcement are separate from the open-description representation
maximum; `_PC_FILESIZEBITS` is recorded without treating it as an exact maximum.

`make test-redirection-offset` adds 36 cases across all three invocation modes
and joins `make test`, so normal and sanitizer CI include it on macOS/Linux.
The C helper uses the shell's build flags and native `off_t`, with Darwin's
feature macro only to expose filesystem metadata. The Python driver uses the
existing bounded runner, sparse sentinel files, exact streams/status, and
size/allocated-block checks. Seek probes never write at the huge seek boundary.
The separate pathname expansion cases remain in `test-portability`.

### Validation record

Tests were run on 2026-09-26 from a separate worktree based on `b692aa5`, branch
`test/CSH-043-redirection-offset`. Normal macOS `cshell` SHA-256:
`3cf3574d90ef47163baf4816f4ed8d9fcf37f19dc803c8fb0257406777303beb`.
It matches the pre-change executable: this ticket defines and tests existing
native redirection behavior.

| Environment | Filesystem/offset observations |
| --- | --- |
| Native macOS 14.8.7 (23J520), Darwin 23.6.0 arm64, XNU `10063.141.1.712.16~1/RELEASE_ARM64_T6000`; Apple Clang 15.0.0 (`clang-1500.3.9.4`), SDK 14.5, libSystem 1345.120.2, Python 3.12.2 | APFS, 4096-byte blocks; signed 64-bit `off_t`, maximum 9223372036854775807; `_PC_FILESIZEBITS=56`. Largest accepted seek: 9223372036854775807. `SEEK_CUR + 1` fails with `EOVERFLOW` (84), `Value too large to be stored in data type`; offset and file remain unchanged. |
| Docker Desktop 24.0.6, Debian 12.15, Linux `6.4.16-linuxkit` aarch64; GCC `12.2.0-14+deb12u1`, glibc `2.36-9+deb12u14`, Python 3.11.2; image `sha256:1bfa5d140418b2a3764367da1bf137fce70920aac9afa8b0a4e56d2f718742a2` | Overlayfs (`f_type=0x794c7630`), 4096-byte blocks; signed 64-bit `off_t`, maximum 9223372036854775807; `_PC_FILESIZEBITS=32`. Largest accepted seek: 17592186040320 (16 TiB − 4096). `SEEK_CUR + 1` fails with `EINVAL` (22), `Invalid argument`; offset and file remain unchanged. The value is the observed seek boundary, not a measured absolute file-size ceiling. |

Both hosts started with unlimited `RLIMIT_FSIZE` (Darwin reports
9223372036854775807; Python/Linux reports `RLIM_INFINITY=-1`). Test children use
soft=hard=2147487744 bytes, six CPU seconds, five wall seconds, 64 descriptors,
zero core size, and at most 65536 captured bytes. Each sparse file stays below
1 MiB of allocated data; no full-length allocation or scan is performed.

Exact selected outcomes on both platforms:

- Writing the last permitted positioned byte returns 0, emits no diagnostic,
  and grows the file from 2147487743 to 2147487744 bytes. The next byte fails
  with `EFBIG`; ignoring `SIGXFSZ`, the controlled writer emits exactly
  `offset-helper: write: EFBIG\n`, returns 23, and leaves size/tail unchanged.
- A two-byte positioned write with one byte available preserves the first
  byte, then reports the same error and status. Default `SIGXFSZ` instead
  produces status 159 on macOS or 153 on Linux, with empty stderr and unchanged
  boundary bytes. These signal numbers are host-specific.
- `pwd` through a duplicated descriptor at the limit returns 1 and emits
  `cshell: pwd: cannot write output\n`; subsequent output returns to the
  original stdout. Opening without writing, reading the final byte/EOF,
  retaining shared offsets across `<>`/duplication, and truncating to resume
  output all pass exact file-effect checks.
- The independent native append control and shell both accept a one-byte
  fresh `O_APPEND` write at the resource limit on macOS/APFS (status 0, no
  diagnostic, size 2147487745). Linux rejects it (status 23, exact helper
  diagnostic above, unchanged size). This is a host difference, not a cshell
  bypass or an inferred universal append guarantee. The fixture obtains its
  expected profile from direct native syscalls before invoking cshell.

| Validation command | Result |
| --- | --- |
| Native `make test-redirection-offset` | 36 passed, zero failures/skips. |
| Native `make -j2 test test-pty test-harness` | Passed: 36 offset, 60 portability, 1318 runtime, 13 jobs PTY, 27 runtime PTY and 64 harness cases, plus all module/fault checks; zero failures/skips. |
| `make docker-build DOCKER_IMAGE=cshell-test:csh043`, then `docker run --rm --init cshell-test:csh043 make -j2 test test-pty test-harness` | Passed with the same counts and zero failures/skips; includes the focused offset target. |
| Native sanitizer temporary copy: `make -j2 test`, then separate `make test-pty` | Both passed on macOS 14.8.7: all module/fault checks, 36 offset, 60 portability, 1318 runtime, 13 jobs PTY and 27 runtime PTY cases, zero failures/skips. Completed 2026-09-26 05:21 UTC. |
| Hosted Ubuntu 24.04/GCC and Docker Linux, implementation commit `c37890d`, [run 36220176817](https://github.com/melliott18/cshell/actions/runs/36220176817) | Both jobs passed normal, PTY, harness and full ASan/UBSan stages. Each normal/sanitized run passed all 36 offset and 1318 runtime cases. Native Linux uses ext4 (`0xef53`, `_PC_FILESIZEBITS=64`); Docker uses overlayfs (`0x794c7630`, `_PC_FILESIZEBITS=32`). Both report the same 17592186040320 seek boundary and `EINVAL` as local Docker. |

Sanitizer builds use `-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1
-fsanitize=address,undefined -fno-omit-frame-pointer`, matching linker sanitizer
flags, and `ASAN_OPTIONS=halt_on_error=1`, `UBSAN_OPTIONS=halt_on_error=1`.
Native macOS also uses `MallocNanoZone=0`. Normal builds use the default C99
warning/optimization flags; all use `_POSIX_C_SOURCE=200809L`. Later ticket and
review updates change documentation only. [PR #88](https://github.com/melliott18/cshell/pull/88)
contains the implementation and this record.

The first native combined sanitizer run passed all 36 offset cases but failed
`stopped job modes saved and shell modes restored` during harness cleanup:
`/bin/ps -axo pid=,stat=` exceeded the existing one-second cleanup deadline.
The initial Docker sanitizer run encountered five-second timeouts in multiple
offset cases during heavy concurrent host load (load average above 700) and was
stopped. A separate Docker sanitizer retry reached the focused target and
reported 17 passes and 19 failures, all with five-second timeouts; its chained
full-suite stages therefore did not run. These local Docker attempts are not
counted as passing evidence. No timeout or assertion was relaxed. Hosted Ubuntu
and Docker jobs for the same test source passed their full sanitizer suites
([run 36220176817](https://github.com/melliott18/cshell/actions/runs/36220176817));
this separates the local timeout observations from passing independent runs.

The selected boundary/error evidence resolves this ticket's scope. It does not
claim every filesystem's absolute writable maximum, every redirection failure
combination, or full POSIX conformance. SH-009/O-026 retain their wider evidence
owner [CSH-049](CSH-049-execution-evidence.md).
