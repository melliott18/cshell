# CSH-050 merged-fix acceptance review

Reviewed `66f8900420525f54b2b53d7342b336f0d7656a5f` on 2026-09-28.
This is a source, evidence and acceptance review. It changes documentation only;
it does not claim a new local runtime run or a fresh normative-source audit.

## Acceptance disposition

| CSH-050 criterion | Disposition and evidence |
| --- | --- |
| Clause/condition map for all requirements | Met within the declared scope. The [eleven-family map](../../jobs-signals-evidence.md) preserves sources, selected policies, implementation, exact assertions and residual conditions. No whole family is promoted. |
| Applicable cases pass on native macOS and Linux/Docker; skips have reasons/owners | **Not yet accepted.** Merged fixes and the complete `faf2e95` hosted run support the corrected paths, but the historical retention failure remains unclassified. Exact-current-main macOS sanitizer validation was also pending at the retained snapshot. Known host/capability limits are separately sourced; they are not blanket exclusions. |
| Source/suite, binary, toolchain, platform and assertions recorded | Met for the retained local records. All four artifact inventories verify. Hosted run metadata identifies source and stages but supplies no binary hashes; it supplements rather than replaces the identified local records. |
| Forward/reverse ownership and scoped matrix claims | Met: all 11 CSH-050 IDs agree in the forward matrices and reverse map. Parent rows remain implemented subsets and CSH-012's compliance gate remains closed. |

Keep CSH-050 in `review`, with the platform criterion unchecked. This is an
evidence-acceptance limitation, not a claim that the retention bug has been
reproduced on current main. CSH-057's checked behavioral criteria and passing
regressions do not by themselves discharge CSH-050's explicit instruction to
never count an intermittent failure as a pass.

## Merged changes reconciled

| Change | Integrated revision | Review conclusion |
| --- | --- | --- |
| PR #114, focused jobs/signals/traps entry point | `9f05719` | Retain the 207 unchanged trap/exit definitions and combined target as scoped evidence. |
| PR #112, completed-child continuation rejection | `19cd70e` | Corrects the observed status 1 versus 130 path; later departure/status-gap work is separately identified below. |
| [PR #120](https://github.com/melliott18/cshell/pull/120), partial `kill` delivery | `6498859` | Successful group/stage deliveries clear stopped state independently of earlier invalid operands or denied siblings. Cumulative errors and denied-stage state remain. The 14 cases include eight baseline failures; normal native/Docker and focused sanitizer results are retained in [CSH-050 acceptance evidence](../csh-050-acceptance/README.md). |
| [PR #121](https://github.com/melliott18/cshell/pull/121), PTY runtime repairs | `87fdfe8` | Parent-only group assignment uses the existing launch barrier. Darwin wait cleanup restores the caller mask after clearing deferred restoration. Rejected continuation waits only for owned positive PIDs whose group query returns ESRCH; live errors remain errors. [Failing-before regressions, inherited-mask checks, platform runs and unchanged-bound repetitions](../csh-057-timeouts/README.md) support these repairs. |
| [PR #124](https://github.com/melliott18/cshell/pull/124), isolated diagnostic workers | `893b10b` | Spawned single-threaded processes replace threads around the runner's `preexec_fn`. Success and intentional-failure controls validate diagnostic isolation. This launcher was not used by hosted CI and cannot explain its retention timeout. |

All five merge revisions are ancestors of the reviewed commit. Inspection of
the merged runtime diffs found no new actionable correctness defect in these
repairs. This is not an exhaustive review of the shell. No deadlines, assertions,
runtime code or fixture oracles are changed here.

## Current validation and provenance

- [Run 36487917937](https://github.com/melliott18/cshell/actions/runs/36487917937)
  at `faf2e9525dfe2c2c2cba4598a1d63d49552fc1d7` completed successfully on native
  Ubuntu/GCC, native macOS/Clang and Docker, including normal, terminal,
  host-profile, harness and ASan/UBSan stages. It includes PRs #120 and #121.
- [Run 36495093736](https://github.com/melliott18/cshell/actions/runs/36495093736)
  tests exact reviewed `66f8900`, including PR #124 and CSH-062 host changes.
  At the retained snapshot, Ubuntu and Docker completed successfully. macOS
  normal, terminal, profile and harness stages passed; ASan/UBSan was still
  running. That snapshot is not a complete current three-platform pass.
- [hosted-previous.json](hosted-previous.json) and
  [hosted-current.json](hosted-current.json) retain source, job URLs, stage
  results and retrieval timestamps. The workflow's sanitizer environment uses
  `detect_leaks=0`; controlled smoke environments further limit inherited
  options. No blanket leak-check claim follows from these runs.
- [checks.json](checks.json) records 184 verified entries: 17 CSH-050 baseline,
  19 partial-delivery, 114 timeout-investigation and 34 retention-review
  artifacts. Each byte count and SHA-256 matches its manifest. The same check
  verifies merge ancestry and all 11 forward/reverse scope IDs. Historical
  failures, incomplete runs and their exact identities remain unchanged.

The preceding complete hosted run is useful integration evidence, but its
result is not relabeled as a run of `66f8900`. There is no reason to repeat a
full local suite solely for these documentation edits.

## Remaining observation and closure evidence

The [historical hosted retention failure](https://github.com/melliott18/cshell/actions/runs/36455644289/job/109041175577)
hit the unchanged 60-second outer limit with fully buffered, empty stdout.
Its phase and last child are unrecoverable. The
[retention investigation](../csh-057-retention-review/README.md) records later
hosted sanitizer passes of 40.556, 54.911 and 41.413 seconds and progressing
local fork/wait measurements across the 619-child fixture. Cumulative
sanitizer process cost is the leading hypothesis; neither the cause nor a
new retention deadlock is established. The diagnostic redundant-wait
optimization was not effective and is not applied to production.

CSH-057 retains this observation. For a recurrence, preserve the merged
flushed capacity/round/phase checkpoints, last-output timing, parent/child
stacks and alarm state before proposing a repair or timing classification.
Acceptance needs a supported disposition distinguishing a shell/fixture defect
from a demonstrated environment limit, plus validation appropriate to that
disposition. More passing retries or a larger timeout alone do not supply it.
Until such evidence exists, the observation remains unclassified rather than
being assigned a speculative repair.

The unrelated external-host conditions remain separate: CSH-061/062 supply
scoped integrated evidence, and
[CSH-063](../../tickets/CSH-063-host-platform-residual-qualification.md) owns
the remaining host-platform inventory. Qualified PATH results do not qualify
stock Debian `kill`; signal-permission interposition does not prove cross-user
kernel enforcement; missing locales, credentials or physical terminals retain
their named capability scope and owners. These boundaries and CSH-012's
requirement-level review are not resolved by marking a narrower ticket done.
