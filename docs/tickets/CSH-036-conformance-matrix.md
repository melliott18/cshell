# CSH-036: Map POSIX requirements to implementation and test evidence

- Status: ready
- Type: docs
- Kind: implementation
- Parent: CSH-012
- Depends on: CSH-001
- Branch: Assigned when work starts
- Issue: [#37](https://github.com/melliott18/cshell/issues/37)

## Goal

Create the requirements and evidence map now, so implementation tickets can add
coverage continuously and the final audit has an explicit, reviewable baseline.

## Scope

- Inventory applicable POSIX.1-2024 Shell Command Language, `sh`, required utility,
  and selected option-group requirements with precise source links.
- Map requirements to owning tickets, intended fixtures, and current evidence;
  distinguish missing, implemented, verified, and inapplicable behavior.
- Define differential fixture conventions, standard-versus-extension handling,
  reference-shell version capture, and explicit expected-result provenance.

## Acceptance criteria

- [ ] Every inventoried requirement has a source, scope decision, owner, and
  evidence field; unimplemented behavior is visibly open rather than marked passed.
- [ ] Conditional, unspecified, and implementation-defined behavior is labeled,
  and unresolved scope/choice decisions have an owner and resolution path.
- [ ] Existing native/Docker smoke checks are mapped only to behavior they prove,
  with future parser, expansion, utility, and PTY fixtures clearly identified.
- [ ] A documented sample differential case distinguishes specification evidence
  from a reference-shell comparison and records executable/version/environment.
- [ ] People and agents can navigate the matrix from POSIX tracking and find
  both a ticket's requirements and a requirement's planned/passing evidence.

## Validation

Check source and repository links, inspect representative requirements across
all major categories, and independently review the inventory for missing families.
Document unresolved gaps without requiring unimplemented features to pass.

## Implementation notes/evidence

Record review evidence here. Maintain the matrix throughout implementation;
CSH-037 performs the final audit. This planning baseline makes no compliance claim
and does not close [CSH-012](CSH-012-conformance-and-portability.md).
