# CSH-082 hosted validation

Audited on 2026-10-08 for PR #170 head
`bd158963d8dcf4211581c61a34d859283eada320`, based on main `e0166e0`.
The PR checkout was GitHub's synthetic merge `8a44b72`; its Git tree is
identical to the push checkout's tree, `9e83175af9be34ab7c5edeac9e5b442a75537e53`.
[audit.json](audit.json) retains exact commit/tree identities, job/step results,
failure lines, and SHA-256 hashes of the retained logs and reports.

| Workflow | Native Linux | Native macOS | Docker | Application container |
| --- | --- | --- | --- | --- |
| [PR 37514811316](https://github.com/melliott18/cshell/actions/runs/37514811316) | Pass | Pass | Pass | Pass |
| [Push 37514800844](https://github.com/melliott18/cshell/actions/runs/37514800844) | Pass | Fail: two CSH-054 timeouts | Pass | Pass |

## Application acceptance

The Linux AMD64 [application-container job](https://github.com/melliott18/cshell/actions/runs/37514811316/job/112444890582)
passes all nine runtime-image checks and all three restricted test stages:
`make test`, `make test-pty`, and `make test-harness` (98 checks).
It exercises UID/GID 10001, offline execution, 1 GiB memory, two CPUs,
256 PIDs, dropped capabilities, and no-new-privileges; runtime checks also
require a read-only root and writable `/tmp`.

The retained [application job log](application-container.log.gz) includes build
identities, runtime assertions, test commands and exits. The uploaded
[JUnit report](junit.xml) has three aggregate cases and zero failures/errors/skips.
Full [test](test.log.gz), [PTY](test-pty.log.gz), and
[harness](test-harness.log.gz) logs preserve individual results and capability
gaps. This complements the [local Linux ARM64 checks](../refresh/README.md).

Native and Docker jobs include normal and ASan/UBSan suites. The complete PR
workflow passes, including macOS's 361 signal cases and 3,950 final runtime
cases. The [passing macOS log](macos-pr.log.gz) preserves those results.

## Retained macOS push failure

The [failed macOS job](https://github.com/melliott18/cshell/actions/runs/37514800844/job/112444856222)
times out in the sanitizer signal suite's `exit operands 48 through 63` cases
in string and file modes. Both cases produce operands 48 through 61 (42 bytes)
before their unchanged five-second deadline. The suite reports 359 passed,
two failed, and zero skipped; `make test-traps` fails. The stdin case and the
normal-build counterparts pass. See the [full failed log](macos-push.log.gz).

This is another occurrence of the hosted exit-operand timeout class already
owned by [CSH-054 / #90](../../../tickets/CSH-054-signal-contract-gaps.md),
which remains open. The observations do not establish a shared root cause or
resolve that defect. CSH-057 retention passes in normal and sanitizer builds in
both jobs. The passing same-tree PR workflow does not erase the push failure;
no test expectation, timeout, or workflow check has been relaxed.

CSH-082's container acceptance checks pass on local ARM64 and hosted AMD64.
The ticket is ready for review, not integrated. Pipeline registration and a run
against an approved-main commit remain platform-side work; full POSIX/host
qualification, other architectures, and release qualification are not claimed.

The audit update changes documentation/evidence only; `src`, `include`,
`tests`, `tools`, `Dockerfile`, `Makefile`, and CI workflows match `bd15896`.
`make test-host-inventory` passes (156 utility names, 101 external contracts,
30 retained conditions, and ten inventory regression checks). Retained file
checksums, compressed-log integrity, local Markdown links, and
`git diff --check` also pass.
