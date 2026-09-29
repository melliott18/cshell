# CSH-069 historical failure triage

Base: `f07568223c02f488924e8599bf9b9f1013b03164`. The production sources are
unchanged. This completes the finite H01–H11 review, with a repaired fixture
race and a deliberately limited disposition of the original H11 occurrence.
CSH-069 remains the recurrence owner; reopen it after integration for a new
occurrence or new causal evidence. No strict runtime failure is waived.

## H11: demonstrated fixture race, limited historical attribution

The original [Docker log](../csh-012/closure-5b56328/ci-job-109228225575.log.gz)
records a nonzero `waitid` return at `context_fixture.c:136` and abort status
-6 at `5b56328143adc72f48f8af581b93fcb758af060e`. It does **not** record errno.
The 20-second API deadline did not fire. The separate passing PR job is not
used to diagnose this failure, and skipped later stages remain not run.

`execute_plan` polls owned background children after each list item, including
the final asynchronous item. Consequently, in `run("exit 12 &\n")`, the child
can exit and be reaped before `run` returns. The original fixture then required
that already-collected child to remain waitable. This is a fixture ordering
error; changing production reaping would be inappropriate.

The test-only `context_schedule.h` substitutes a `waitpid` wrapper in one
executor object. Armed only for this single command, it first waits with
`WEXITED | WNOWAIT`, then performs the original real `waitpid(..., WNOHANG)`.
It neither consumes the status itself nor fabricates a return value. This
forces the child-completes-before-launch-poll ordering without sleeps or load.
The parent asserts that exactly one forced poll occurred in the repaired test.

`before.patch` adds only that scheduling/diagnostic support to the base
Makefile and fixture; `before_fixture.c` is the resulting pre-repair fixture.
The native and Linux reproductions both abort with **ECHILD (errno 10)** at the
formerly unconditional wait. Their failure is retained, not converted to a pass.
The fixed fixture separately checks early collection, then uses a pipe-gated
helper to ensure another child survives the launch poll. After `run` returns,
the parent releases the helper, observes its zombie, and verifies the next
execution boundary reaps it while leaving an unrelated exited child waitable.
Descriptor counts return to baseline. Unexpected waits now report PID/errno and
retry EINTR. Both ordinary and forced-schedule fixtures run in `make test-context`
and therefore the existing default, Docker and sanitizer CI paths.

This proves and repairs a concrete mechanism capable of producing H11's
assertion. It does **not** recover the missing errno or scheduling trace from
the historical job. The original occurrence remains unknown-cause within this
explicit scope: accept the finite historical observation after fixing the
reproduced race, preserve its failed result, and investigate any recurrence
under CSH-069 using the new diagnostics. No blanket scheduling/load explanation
is assigned to H01–H10, or even to every possible failure at H11's old assertion.

## H01–H10: retained individual dispositions

The [eleven-entry ledger](../../defect-dispositions.md#historical-and-new-observations)
and its immutable [machine snapshot](../csh-012/closure-5b56328/defect-dispositions.json)
remain the source of original identities, bounds, failed attempts, not-run stages,
and explicitly unavailable details. `audit.py` checks every original referenced
record's hash/size. Similar symptoms across different revisions are not duplicate
attempts and are not merged into a claimed common cause:

- H01/H02 and the local portion of H07 lack sufficient original identity/log
  detail for a causal reconstruction; the narrative's uncertainty is retained.
- H03/H04/H05/H06/H08/H09/H10 retain their own raw evidence and source manifests.
  Later serial successes demonstrate their own results only.
- H02/H04/H05/H06/H08/H10 overlap categories of setup/cleanup mechanisms repaired
  elsewhere. Those repairs have not been demonstrated to account for each
  original attempt, so the observation-specific unknown-cause dispositions stand.
- H07's hosted repeated-resume byte mismatch is distinct from timeout failures.
  H09's control-flow deadlines are distinct from the formal CSH-057 retention
  disposition. The CSH-050 self-stop/partial-kill and CSH-058 leaked-launcher-alarm
  repairs remain separate. None is evidence that H11 was repaired previously.

The existing acceptance reasons and bounds remain valid: finite historical
accounting with explicit missing evidence, existing strict tests, and same-ticket
recurrence ownership. This completes triage, not a claim that those failures
cannot recur or that their root causes are now known. CSH-012 audit closure is
unchanged; only omissions or false accounting reopen that audit.

## Validation and all attempts

| Attempt | Result and scope |
| --- | --- |
| `native-before-build.log` + `native-before.json` | Build succeeds; original fixture with forced schedule aborts, -6/ECHILD. |
| `native-context.log` | First repaired run: 60 context behaviors, ordinary API, forced schedule and fault checks pass. |
| `native-regression.json` | Context (60), execution (61), pipeline (52), API and fault checks pass. |
| `docker-build.log` | Repository Dockerfile builds `cshell-test:csh-069` successfully. Image identity retained in `platform.json`. |
| `docker-before-build.json` + `docker-before.json` | Build succeeds; original fixture with forced schedule aborts, -6/ECHILD. |
| `docker-regression.json` | Same context, execution, pipeline, API and fault checks pass on Debian/Linux. |
| `native-sanitizer.json` | Context ordinary/forced/fault checks pass with ASan/UBSan; Darwin leak detection disabled. |
| `docker-sanitizer.json` | **Build fails**, make status 2: the initial recorder incorrectly inherited the fixture's 2 MiB `RLIMIT_FSIZE` for compiler objects. GCC reports file-size-limit termination in `execute.o`; context tests did not run. |
| `docker-sanitizer-build-limit-fixed.json` | Context ordinary/forced/fault checks pass with ASan/UBSan and LeakSanitizer after correcting the recorder's build limits. |

The original recorder is retained as `record-initial.py`, matching its recorded
hash. `record.py` now bounds builds by elapsed time independently of the fixture
resource limits; fixture subprocess limits and strict assertions are unchanged.
No source/test change separates the failed build and the corrected-build attempt.
JSON records retain exact command arguments, platform/compiler, sanitizer options,
input hashes, binary hashes, exit status and compressed-log hash. Logs concatenate
stdout then stderr. Initial native records use the smaller original identity
manifest; they are not silently replaced by later records. Native Linux outside
Docker, full `make test`, PTY and hosted CI were not rerun for this fixture-only
change; existing broad evidence is not claimed as new validation.

From this checkout, ordinary regression:

```sh
make -j4 test-context test-execute test-pipeline
python3 docs/evidence/csh-069/audit.py
```

Reproduce the expected old assertion failure (clean first if switching flags):

```sh
make -j4 -f Makefile -f docs/evidence/csh-069/before.mk \
  build/tests/context_before build/tests/execute_helper
python3 docs/evidence/csh-069/record.py --name reproduced-before --fixture -- \
  build/tests/context_before build/tests/execute_helper
# Recorder returns 1; JSON records the fixture's -6/ECHILD.
```

For Linux use the repository Dockerfile and mount this evidence directory at
`/evidence`; use `-f /evidence/before.mk CSH069_EVIDENCE_DIR=/evidence` when building
the old fixture. The forced ordering changes only a test-linked object; `cshell`
continues to link the ordinary executor.
