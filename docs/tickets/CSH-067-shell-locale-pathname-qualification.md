# CSH-067: Qualify remaining shell locale and pathname boundaries

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-042, CSH-047, CSH-053
- Branch: Assigned when work starts
- Issue: [#136](https://github.com/melliott18/cshell/issues/136)

## Goal

Give the remaining shell locale and public pathname conditions explicit evidence or a precisely scoped unmet prerequisite.

## Scope

- ENV-004, LEX-002/004/005, EXP-004/007/008/009/010, EXEC-012, U-017/027/031 and SH-003.
- Inventory the finite residuals in invocation-syntax-evidence.md and expansion-evidence.md: stateful/installed non-UTF encodings; multicharacter collating elements and equivalence classes; public-runtime symlink/trailing-slash/search-permission/read-I/O boundaries currently supported only by module fixtures; shell/libc diagnostic locale applicability.
- Distinguish unavailable raw filename bytes on APFS from source decoding failures. CSH-053 already has passing byte-decoding witnesses. Determine normative applicability before labeling absence of translated catalogs a defect.
- External utility locale/ACL contracts remain CSH-064; do not duplicate them.

## Acceptance criteria

- [ ] Each listed condition has a normative clause, applicability decision, implementation and strict runtime witness or a named external prerequisite.
- [ ] Record locale names/definitions, libc, filesystem, credentials and raw-byte fixtures; qualify only exercised conditions.
- [ ] Add public-runtime regressions for confirmed defects, retaining passing module evidence separately.
- [ ] Update the linked maps and skip ownership without converting unavailable capabilities to passes.

## Validation

Reproduce make test-portability and the CSH-053 cases on native macOS and Linux; use supplied locales and owned permission fixtures. Retain capability skips and avoid relying on a reference shell as the normative oracle.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.
