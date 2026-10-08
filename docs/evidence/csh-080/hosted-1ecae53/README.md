# Hosted verification of CSH-080 implementation 1ecae53

Collected 2026-10-08 from the completed 2026-10-06 workflows for exact head
`1ecae53480204bfb26251d35f621c0635698c62b`. All eight checks passed:

- [Filesystem qualification](https://github.com/melliott18/cshell/actions/runs/37516271376): macOS 15 and Ubuntu 24.04.
- [Pull-request tests](https://github.com/melliott18/cshell/actions/runs/37516271233): native macOS, native Ubuntu and Docker, including the workflow's sanitizer checks.
- [Push tests](https://github.com/melliott18/cshell/actions/runs/37516239815): the same three broad jobs.

The three `*-run.json.gz` records retain head SHA, step results and job links.
Both `filesystem-*` directories retain the complete downloaded artifact: provider
manifest, expected/actual outputs and effects, cleanup, source identities and logs.
No failed stock assertion is converted into a pass by the green workflow result.
The workflow deliberately retains those diagnostic runs separately.

| Hosted target | Selected filesystem | Allocation | Stock full audit | Stock provider audit |
| --- | --- | --- | --- | --- |
| macOS 15 | 810 pass, 0 fail | 240 pass, 0 fail | 742 pass, 48 fail | 152 pass, 16 fail |
| Ubuntu 24.04 | 826 pass, 0 fail | 200 pass, 0 fail | 774 pass, 28 fail | 176 pass, 8 fail |

All per-case cleanup records are true. Both targets' source-input identity is
`6f8c09f34217b6b8cff602346d6cd12e31a755b92234bbb16b958c9f276ba395`, matching the
original local evidence. These results qualify the implementation at 1ecae53;
they do not establish later revisions or complete any CSH-084 residual contract.
