# CSH-039: Switch cshell to the replacement runtime and delete the legacy code

- Status: backlog
- Type: refactor
- Kind: implementation
- Parent: CSH-006
- Depends on: CSH-018, CSH-020
- Branch: Assigned when work starts
- Issue: [#41](https://github.com/melliott18/cshell/issues/41)

## Goal

Make the replacement runtime the only `cshell` implementation and remove every
legacy runtime/build dependency without waiting for the remaining POSIX features.

## Scope

- Wire the production entry point and default native/Docker builds to the new
  input, lexer, parser, state, and executor modules validated by CSH-018/020.
- Delete `src/legacy/`, `include/cshell/legacy.h`, the old input/dispatch loop,
  legacy object/scanner rules, compatibility adapters, and fallback switches.
- Remove temporary candidate executables/drivers and prototype-only test
  allowances; unit-test drivers remain where they test replacement module APIs.
- Remove tools/packages needed only by the deleted scanner from build, Docker,
  and CI instructions. Flex may remain only if the new lexer independently uses
  it with documented rationale, not because the prototype used it.
- Update current architecture, supported behavior, and build documentation.
  Preserve historical tickets and Git history as records of previous work.

## Acceptance criteria

- [ ] Clean-checkout `make`, `make test`, and `make docker-test` build/run only
  the replacement `cshell`; no environment setting or alternate public mode
  selects legacy execution.
- [ ] Command strings, script files, and stdin support the declared bootstrap
  subset: literal simple commands, external lookup/statuses, bootstrap `cd` and
  `exit`, ordered redirections, and concurrent pipelines. Empty input, EOF,
  failures, and non-interactive output follow CSH-018/020 evidence.
- [ ] Unsupported constructs/expansions fail with a diagnostic before that
  construct has side effects; no fallback, silent reinterpretation, or promise
  of compatibility with legacy extensions is used to pass the suite.
- [ ] The legacy directory/header and build dependencies are deleted, no
  replacement module imports them, and linked objects/symbols contain no legacy
  runtime. Review confirms the old dispatcher was not copied into renamed files.
- [ ] Temporary migration drivers, fallback flags, and prototype prompt/output
  allowances are gone. Any remaining temporary literal-word adapter is new code
  owned by CSH-008, explicitly bounded, and unable to call legacy code.
- [ ] Native and Docker regression/sanitizer results cover input ownership,
  child failure, descriptor restoration, high-volume pipelines, and cleanup.
  Current documentation describes the replacement and remaining POSIX gaps.

## Validation

Run clean native and Docker builds/tests; record platform and compiler versions.
Exercise the bootstrap subset through all invocation modes with exact output,
status, filesystem, and timeout assertions. Run relevant ASan/UBSan cases and
controlled failure fixtures from CSH-004/016/019/020. Inspect build commands,
dependency files, linked objects/symbols, and source references for legacy use;
inspect the diff to distinguish actual replacement from renamed/copied code.
Historical documentation references are permitted, executable legacy paths are
not. Verify the default build succeeds without the deleted sources and that no
cached generated scanner or object hides a dependency.

## Implementation notes/evidence

CSH-018 validates invocation/status using the replacement candidate; CSH-020
provides pipeline coverage. This cutover does not wait for CSH-021 lists/groups,
full expansion, compounds, or job control. Coordinate build/entry-point changes
with CSH-021 if it runs concurrently. CSH-006 cannot complete until this ticket
is done; CSH-037 later checks that legacy paths or expired adapters did not return.
