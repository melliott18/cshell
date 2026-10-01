# Hosted closure verification, 2026-10-01

The terminal-fault repair is verified by hosted macOS normal, selected-PATH and
ASan/UBSan checks. CSH-057 as a whole is **not ready to close**: its separate
public repeated-resume PTY case timed out and its leader cleanup failed in the
push run. The PR stack is also still unmerged at this review.

[Push macOS job](https://github.com/melliott18/cshell/actions/runs/36883868559/job/110442116646)
checked out `4d689e87b289d8ddb3cffe2142cee8e7f06133fe`.
[PR macOS job](https://github.com/melliott18/cshell/actions/runs/36883886472/job/110442178677)
checked out synthetic merge `8858ae4193d325df73012791d1e09764c6482ef5`.
The GitHub commit API and local Git identify the same tree for both:
`51d0b6721d103b9e89dc9173ddc6e6c6725f5d3d`.

| Check | Push run | PR run |
| --- | --- | --- |
| Mach isolation regression, normal and ASan/UBSan | Passed | Passed |
| Retention, normal and ASan/UBSan | Passed | Passed |
| Terminal fault, normal and selected PATH | Passed | Passed |
| Terminal fault, ASan/UBSan | Not reached after public PTY failure | Passed |
| Repeated background resumes, normal and selected PATH | Passed | Passed |
| Repeated background resumes, ASan/UBSan | Failed | Passed |
| Ubuntu and Docker jobs | Passed | Passed |

In the push run's sanitizer phase, `repeated background resumes preserve
prompt and terminal` reached its five-second deadline waiting for step 328,
`ready\n`. Step 327 completed at 4.973 seconds; the runner reported 0.050
seconds without advancement. It then could not reap the leader within one
second. Expected status was 130; actual status was unavailable. The transcript
contained 5,684 of the expected 7,280 bytes, through the cycle-25 prompt.
The suite ended with 29 passed and 1 failed (`push-macos.log`, lines 19133–19177).

This records late progress, not proof that every interval was short or that
there was no stall. It does not establish the reason for the cleanup failure.
No timeout, assertion or production source is changed by this closure audit;
no successful rerun is used to erase the failure. This recurrence remains
owned by [CSH-057 / #99](../../../tickets/CSH-057-job-lifecycle-boundaries.md).

The PR run passed the CSH-057 checks, including the sanitizer terminal-fault
case at 15:45:24 UTC (`pr-macos.log`, line 19407). Its overall macOS job failed
in five separate CSH-054 exit-operand batches: 48–63 in string/file/stdin,
96–111 in string and 224–239 in file mode. Each exceeded five seconds; the
suite reported 356 passed and 5 failed (lines 21961–22279). These belong to
[CSH-054](../../../tickets/CSH-054-signal-contract-gaps.md), not the Mach
regression or CSH-058 signal-edge matrix. CSH-058's 2,464 checks passed in both
normal and sanitizer phases of that PR job. No diagnosis of the CSH-054
failures is claimed here.

[results.json](results.json) records the exact observations and member hashes.
[artifacts.tar.gz](artifacts.tar.gz) preserves both complete macOS logs and
run/job metadata. The initially attempted `gh run view --job --log` returned
an empty file, so logs were retrieved with the Actions job-logs API instead.
This audit does not change any historical failure or classify an issue as
unsolvable. The user's conditional closure authorization remains applicable
once the remaining CSH-057 failure is resolved and verified.
