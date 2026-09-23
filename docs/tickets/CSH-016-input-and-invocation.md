# CSH-016: Introduce input sources and shell invocation modes

- Status: done
- Type: feat
- Kind: implementation
- Parent: CSH-003
- Depends on: CSH-001
- Branch: feat/CSH-016-input-and-invocation
- Issue: [#17](https://github.com/melliott18/cshell/issues/17)

## Goal

Provide a reusable input interface for command strings, script files, and stdin,
with explicit invocation data that later parsing and state modules can consume.

## Scope

- Add owned input-source APIs independent of direct scanner access to stdin.
- Parse `-c`, script-file, and stdin invocation into owned input sources; keep
  command execution and default-binary wiring in CSH-018 and CSH-039.
- Retain POSIX invocation operands for `$0` and positional-parameter storage.
- Select interactive mode and prompting according to documented POSIX rules.
- Preserve source location and input continuity needed for multiline parsing.

## Acceptance criteria

- [x] API fixtures read command strings, script files, and redirected stdin
  correctly; empty sources and a final line without newline reach explicit EOF
  without stale data, busy loops, or dropped bytes. No command execution is
  required to validate this input layer.
- [x] Non-interactive modes emit no startup banner or prompt; terminal detection
  and explicitly selected interactive behavior have focused tests.
- [x] Missing command-string operands, invalid usage, and unreadable scripts
  produce diagnostics and failure statuses without leaking input resources.
- [x] Invocation tests inspect the correct `$0` and argument vector at the API
  boundary, even though language-level parameter expansion is not yet present.
- [x] Long input, repeated reads, and injected allocation/read failures release
  owned storage and never expose partial command data as complete input.
- [x] The input module and fixtures build without the legacy header, scanner,
  or executor; no compatibility adapter is required.
- [x] Input ownership, error reporting, and source-position interfaces are
  documented for the lexer/parser and CSH-022 state-storage consumers.

## Validation

Build API fixtures natively and in Docker; read empty, single-command,
multi-command, long, and unterminated-final-line sources under bounded timeouts.
Use ASan/UBSan and controlled allocation/read failure fixtures for cleanup.
Test invocation operand mapping with API fixtures and prompt selection with a
small pseudo-terminal fixture. Check source cleanup with sanitizer diagnostics.
CSH-018 supplies the final cross-mode status matrix using the CSH-017 harness.

## Implementation notes/evidence

This ticket establishes input and invocation contracts, not parameter expansion.
Retain argument strings with explicit ownership so CSH-022 can build on this API
without waiting for the entire CSH-003 milestone. Keep multiline syntax rules in
the lexer/parser tickets while ensuring input acquisition does not discard data.


### Implemented contract

`include/cshell/input.h` and `src/input.c` own copied string sources and
close-on-exec file/descriptor sources. Physical-line reads preserve all bytes,
including descriptor-input NULs and final lines without newlines, and report
byte offsets plus physical line/column positions. Reads stop at each newline;
EOF and failures are sticky, and failed partial lines are discarded.

`include/cshell/invocation.h` and `src/invocation.c` retain owned `$0` and
positional arguments for `-c`, script, and stdin/`-s` modes. They support `-i`,
grouped options, `--`, and lone `-`; unsupported shell options and combined
`-c`/`-s` are diagnosed. Automatic interactive selection follows Issue 8's stdin
source plus stdin/stderr terminal rule, including `-s` with operands. Prompt
selection is a caller-driven policy for interactive stdin; these modules never
print or execute commands.

The [API contract](../input-and-invocation.md) documents ownership, diagnostics,
statuses, nonblocking-input normalization, source positions, and consumer
responsibilities. CSH-019 must add protection/relocation of private input
descriptors when user redirections target those descriptor numbers. Full shell
options, prompt expansion, execution, and default-binary wiring remain with
their existing owners.

Specification references: POSIX.1-2024
[`sh` options and operands](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_04),
[stdin](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_06),
[exit status](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/sh.html#tag_20_110_14),
and [PS1/PS2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_05_03).

### Validation evidence (2026-09-23)

Native environment: macOS/Darwin arm64, Apple Clang 15.0.0, GNU Make 3.81,
Python 3.12.2. Docker environment: Linux aarch64, Debian Bookworm, GCC 12.2.0,
GNU Make 4.3, Python 3.11.2, glibc 2.36, Docker Engine 24.0.6; tests ran as
unprivileged UID 10001.

- `make clean`, `make -j8`, `make test`: all 63 input/invocation checks and
  three prototype smoke checks passed. Handwritten code compiled without
  warnings; the existing generated legacy scanner retains its signedness warning.
- `make test-input CC=clang CFLAGS='-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer' LDFLAGS='-fsanitize=address,undefined'`
  after `make clean`: all 63 checks passed with ASan/UBSan on macOS.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-016`: all 63 input checks and
  three smoke checks passed on Linux, including unreadable-file permission cases.
- The Docker image also passed all 63 input checks after a clean GCC build with
  the same sanitizer flags, `ASAN_OPTIONS=detect_leaks=1:halt_on_error=1`, and
  `UBSAN_OPTIONS=halt_on_error=1`. No sanitizer or leak diagnostics appeared.
- A temporary source-only snapshot containing the two replacement modules,
  headers, Makefile, and input fixtures passed `make test-input LEX=false` with
  `-Werror`. No legacy header, source, scanner, or executor was present.
- `tests/input.py` enforces five-second subprocess timeouts and bounded captured
  output. Cases cover empty/multiple/unterminated lines, 200 KB lines, multiline
  syntax preservation, owned operands, source locations, and pseudo-terminal
  stdin/stderr combinations. Descriptor fixtures check close-on-exec, cleanup,
  shared offset behavior, blocking FIFO input, and no read-ahead past newline.
- `tests/input_faults.c` fails each constructor/invocation/line-growth allocation
  in sequence and injects read errors at every byte boundary, including EOF.
  It verifies cleanup, discarded partial data, sticky diagnostics, and EINTR
  recovery. Fault checks remain enabled with `-DNDEBUG`.
- Independent source/test review, strict compilation, local Markdown links,
  and `git diff --check` passed. Existing Mermaid diagrams were unchanged.

The implementation is based on the CSH-038 roadmap branch (`6118669`) because
its updated CSH-016 scope was already published in issue #17 while PR #42 was
still open when this branch was created. Both are now integrated into `main`,
as recorded below. Default `cshell` command execution is unchanged; no general
POSIX conformance claim is made. Local and Docker validation above used arm64.


### Integration validation

Merged the newer CSH-017 harness/CI and CSH-036 conformance documentation into
the implementation branch before main integration. Resolved shared build and
entry-point documentation while retaining candidate selection, Docker controls,
and harness self-tests. `make test` now runs the independent input API checks
alongside the selected behavioral suite; hosted CI uses the same targets.

A clean native build followed by `make test test-harness` passed all 63 input
API checks, the current four prototype fixtures, and 23 harness self-tests.
`make docker-test DOCKER_IMAGE=cshell-test:csh-016-merge` plus the image's
`make test-harness` passed the same checks on Linux arm64. The production input
and invocation implementation is unchanged from the sanitizer-validated
`8f91ff3` revision above. Matrix annotations distinguish API evidence from
remaining runtime and conformance requirements.


Integrated into `main` through [pull request #45](https://github.com/melliott18/cshell/pull/45)
on 2026-09-23. Implementation commit: `8f91ff3`; validated integration head:
`3b8bed4`; merge commit: `0e527c3`.

Both [pull-request CI](https://github.com/melliott18/cshell/actions/runs/35918534833)
and [branch CI](https://github.com/melliott18/cshell/actions/runs/35918535248)
passed all three jobs for `3b8bed4`: Ubuntu 24.04/GCC, macOS 15/Clang, and Docker
Linux. Each job ran the input API checks, selected prototype fixtures, and
harness self-tests. CSH-003 remains incomplete until CSH-018 and its remaining
runtime acceptance criteria are complete.
