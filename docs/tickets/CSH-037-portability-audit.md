# CSH-037: Audit integrated conformance and platform portability

- Status: in-progress
- Type: test
- Kind: implementation
- Parent: CSH-012
- Depends on: CSH-008, CSH-009, CSH-010, CSH-011, CSH-036
- Branch: test/CSH-037-portability-audit
- Issue: [#38](https://github.com/melliott18/cshell/issues/38)

## Goal

Review the complete shell against its requirements map and reproduce evidence on
supported platforms before publishing final behavior or compliance statements.

## Scope

- Audit integrated requirements and evidence, covering supported Linux/macOS
  toolchains, Docker architecture/libc, sanitizers, and applicable PTY cases.
- Exercise locales, large input, resource failures, and bounded parser/expansion
  robustness cases; compare versioned reference shells against the standard.
- Verify CSH-039 retirement evidence and confirm that no legacy runtime,
  fallback, build dependency, or expired transition adapter has returned.
- Reconcile installation, invocation, architecture, tests, limitations, and
  contribution docs with observed behavior and unresolved findings.

## Acceptance criteria

- [ ] Every applicable requirement links to passing implementation evidence or an
  explicit defect/limitation ticket; selected scope and permitted choices are clear.
- [ ] Clean-checkout native and Docker validation reproduces documented results,
  with compiler, libc, architecture, suite, and reference-shell versions recorded.
- [ ] CI covers supported platforms and applicable behavior; skipped/waived cases
  include a concrete reason and scope, with follow-up owners where needed.
- [ ] Discovered defects have regression coverage and resolved or linked tickets;
  independent review checks the matrix and reproduces a sample of evidence.
- [ ] User/developer docs reflect verified behavior; compliance claims remain
  withheld while applicable requirements are unmet and otherwise name the edition,
  selected profile, and evidence without implying external certification.

## Validation

Run the full documented validation procedure across supported platforms, inspect
CI from a clean checkout, and record bounded robustness/differential results.
Reproduce selected evidence independently and review the original CSH-012 criteria.

## Implementation notes/evidence

Record audit findings and exact results here. Closing the audit records its outcome;
open conformance defects remain visible. [CSH-012](CSH-012-conformance-and-portability.md)
requires its own completion review and does not imply certification.

### Audit run, 2026-09-25

Work started in a separate clean worktree at `b76423d` on
`test/CSH-037-portability-audit`. The public runtime now calls
`setlocale(LC_ALL, "")` before parsing invocation input. The
[`test-portability`](../testing.md#portability-audit-probes) target adds 60
bounded cases on the test hosts: C/UTF-8 locale patterns and IFS, `LC_ALL`
precedence, arithmetic and quote nesting through depth 32, a 256 KiB input
line, and sparse-file pathname/append behavior above 2 GiB. Normal shell
output, status and filesystem effects are asserted; the sparse append raises
only the harness file-size limit. It does not locate the maximum offset.
The full `make test` path also exercises existing controlled allocation,
descriptor, fork, pipe, wait and read-failure fixtures; those results are
safety and robustness evidence for their asserted paths, not language coverage.

| Environment | Build and suite result |
| --- | --- |
| Native macOS 14.8.7 (23J520), Darwin 23.6.0 arm64, Apple clang 15.0.0 (clang-1500.3.9.4), SDK 14.5, Python 3.12.2; libSystem.B.dylib current version 1345.120.2 | Clean-worktree `make -j2 test test-pty test-harness` passed. After the final sparse-append addition, `make clean && make -j2 test test-pty test-harness` passed: 60 portability, 27 runtime PTY, 1,318 runtime and 64 harness tests, with no suite skips. The normal `cshell` executable SHA-256 was `9c7e581699863965d2c0e5c4446908ceaf40e9b5358c53bac81d4c2330bff795`. The same clean build with clang `-std=c99 -Wall -Wextra -Wpedantic -Wshadow -Werror -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer` and matching linker sanitizers also passed. |
| Docker Desktop 24.0.6, Linux aarch64 (`linuxkit` 6.4.16), Debian 12 bookworm-slim, GCC 12.2.0, glibc 2.36, Python 3.11.2, base image `debian:bookworm-slim` arm64 manifest `sha256:0c8bbb8e987a035fe1d9704eb2e571b7e9a836e1caa46345290674b45b69e417`; built image `sha256:bad5f5f41570295ed615acf54f44791b7d7458b8c1ce632aaa2314613415a492` | Final `make docker-test`, `make docker-test-pty` and in-image `make test-harness` passed: 60 portability, 27 runtime PTY, 1,318 runtime and 64 harness tests, with no suite skips. Linux ASan/UBSan rerun is pending. |

The selected UTF-8 locales were `en_US.UTF-8` on macOS and `C.UTF-8` on the
Docker Linux image. All 131 matrix rows (65 language/invocation, 66 utility/
option) retain source and owner links. The audit corrected stale pre-cutover
evidence for selected runtime rows, documented the base-only target (UP and XSI
unselected), and kept partial witnesses at `implemented` scope. The current
matrix still has many base requirement families without complete passing
evidence; CSH-037 and CSH-012 therefore remain open, with no conformance claim.

The Docker image supplies `cat`, `env`, `find`, `ls` and `stty`, but no `ed`;
native macOS supplies all six. `ed` is not a dependency of the current test
suite, and this minimal image does not serve as whole-system POSIX utility
evidence. The [CI workflow](../../.github/workflows/tests.yml) runs native
Ubuntu 24.04/GCC and macOS 15/Clang plus
Docker, each with runtime, PTY, harness and ASan/UBSan checks. The branch's
hosted CI result and independent matrix review remain pending. The first hosted
run exposed two timing-sensitive failures: an Ubuntu PTY `bg` case printed its
`Running` line without the next prompt within five seconds, then passed in a
second run of the same revision; [CSH-044](CSH-044-intermittent-bg-prompt.md)
([#76](https://github.com/melliott18/cshell/issues/76)) owns root-cause and
regression work. On macOS 15, two harness timeout self-tests expired before
the helper reached its setup marker. Their test-only startup allowance was
raised from 0.3 to 1 second, while retaining a five-second end-to-end bound
and the same descendant-cleanup assertions. Hosted reruns are pending.

The source tree and Makefile contain no `src/legacy`, Flex scanner, legacy
dispatcher, alternate shell executable, or runtime fallback. The default
`cshell` links only replacement modules; the CSH-039 retirement remains intact.

The focused Mac reference observation used `/bin/bash --posix` (GNU Bash
3.2.57, SHA-256 `316f63ce5d51d7e5eb776912da68610532f414339529b7e877f73c6f9f678912d`)
and `/bin/ksh` (AT&T ksh 93u+ 2012-08-01, SHA-256
`addc8f59ef88a68084107d32505d78eca9839480aa8d3b877f73c6f9f678912d`).
The Docker observation used Bash 5.2.15-2+b13 (SHA-256
`f5918390c5b15392ad8835e8368a79c1ee9937fbb19f2349cccf5d4524183299`)
and dash 0.5.12-2 (SHA-256
`15fc4c72f49c86639a383121eec6fbdbcd32ec9d03db915cb3096928295e1a17`).
All four gave `<fallback>\n<>\n` for the specification-derived null-parameter
default case and `caf?\n` in C locale with only a UTF-8 `café` filename.
In UTF-8, Bash and ksh expanded `caf?` to `café`; Docker dash left it literal.
This disagreement is a reference observation, not a normative oracle or a
cshell failure. The [evidence rules](../posix-evidence.md) govern interpretation.

The discovered locale breadth has [CSH-042](CSH-042-locale-semantics.md) ([#73](https://github.com/melliott18/cshell/issues/73));
the undocumented exact redirection offset boundary has
[CSH-043](CSH-043-redirection-offset.md) ([#74](https://github.com/melliott18/cshell/issues/74)).
Neither selected UTF-8 cases nor a successful append beyond 2 GiB verifies the
full associated requirement row. A further row-by-row evidence review and
independent reproduction are needed before the acceptance checkboxes can be
closed.
