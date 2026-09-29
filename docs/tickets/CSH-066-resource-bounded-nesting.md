# CSH-066: Remove arbitrary shell nesting limits

- Status: ready
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-005, CSH-028, CSH-041
- Branch: Assigned when work starts
- Issue: [#135](https://github.com/melliott18/cshell/issues/135)

## Goal

Replace fixed recursive-depth rejection with storage and execution bounded by actual available resources.

## Scope

- XCU §2.9 and sh INPUT FILES/STDIN; SH-006, GRAM-002/004/005, EXP-001/005/006 and EXEC-014.
- Audit parser 128, executor tree 256, evaluation/function/substitution 128, expansion 128 and arithmetic 128 guards. The brace probe directly demonstrates only parser/tree rejection; other guards are source-inspected limitations.
- Prefer iterative owned work structures where needed. Raising a constant alone does not satisfy the contract.

## Acceptance criteria

- [ ] Record all fixed guards and replace arbitrary limits with safe resource-aware handling, including partial-tree destruction and interruption.
- [ ] Valid brace depths 127/128/129 execute in all input modes; add deeper and mixed construct witnesses without claiming finite samples prove unlimited capacity.
- [ ] Allocation/resource exhaustion fails diagnostically without stack overflow, leaks, partial unintended effects or leaked children.
- [ ] Update guard fixtures so known rejection is no longer presented as the required success oracle; run parser, expansion, execution, runtime and sanitizer checks.

## Validation

The retained probe has six failures at depths 128/129 and three passing depth-127 controls. The existing tests/invocation.py guard cases deliberately expect rejection and remain useful safety evidence until this repair; they do not establish unrestricted command size.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.
