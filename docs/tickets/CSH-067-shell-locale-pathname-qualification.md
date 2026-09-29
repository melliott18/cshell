# CSH-067: Qualify remaining shell locale and pathname boundaries

- Status: done
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-042, CSH-047, CSH-053
- Branch: `test/CSH-067-locale-pathname-qualification`
- Issue: [#136](https://github.com/melliott18/cshell/issues/136)

## Goal

Give the remaining shell locale and public pathname conditions explicit evidence or a precisely scoped unmet prerequisite.

## Scope

- ENV-004, LEX-002/004/005, EXP-004/007/008/009/010, EXEC-012, U-017/027/031 and SH-003.
- Inventory the finite residuals in invocation-syntax-evidence.md and expansion-evidence.md: stateful/installed non-UTF encodings; multicharacter collating elements and equivalence classes; public-runtime symlink/trailing-slash/search-permission/read-I/O boundaries currently supported only by module fixtures; shell/libc diagnostic locale applicability.
- Distinguish unavailable raw filename bytes on APFS from source decoding failures. CSH-053 already has passing byte-decoding witnesses. Determine normative applicability before labeling absence of translated catalogs a defect.
- External utility locale/ACL contracts remain CSH-064; do not duplicate them.

## Acceptance criteria

- [x] Each listed condition has a normative clause, applicability decision, implementation and strict runtime witness or a named external prerequisite.
- [x] Record locale names/definitions, libc, filesystem, credentials and raw-byte fixtures; qualify only exercised conditions.
- [x] Add public-runtime regressions for confirmed defects, retaining passing module evidence separately.
- [x] Update the linked maps and skip ownership without converting unavailable capabilities to passes.

## Validation

Reproduce make test-portability and the CSH-053 cases on native macOS and Linux; use supplied locales and owned permission fixtures. Retain capability skips and avoid relying on a reference shell as the normative oracle.

## Implementation notes/evidence

Opened by the [CSH-012 requirement, defect, platform and documentation review](../conformance-acceptance-review.md)
at source `c8c1c91372e6e77cf2e7032765cd3c068fa1906d`.
[Strict probe inputs and actual results](../evidence/csh-012/acceptance-c8c1c91/contracts.json)
and [review evidence](../evidence/csh-012/acceptance-c8c1c91/README.md)
are retained. No production repair or completion is claimed by this review.

## Implementation and validation record

The [finite condition map](../locale-pathname-qualification.md) records every
assigned row, normative applicability, implementation, strict witnesses and
external prerequisites P1–P6. New `make test-locale-pathname` is included in
`make test-portability` and normal/sanitizer CI. It adds public symlink,
trailing-slash, owned read/search permission, unreadable-source, EUC-JP
single-shift, reusable alias and supplied collation witnesses. Partial directory
reads use a separately labeled instrumented public runtime; existing module
ownership/failure checks remain separate. No production defect was confirmed.

[Retained logs and byte-exact records](../evidence/csh-067/README.md) qualify
native macOS and Docker Linux at baseline `f07568223c02f488924e8599bf9b9f1013b03164`:

- Focused: macOS 50 passes / one capability skip; Linux 56 passes / zero skips.
- Portability driver including CSH-053: macOS 2,206 passes / five capability
  groups skipped; Linux 727 passes / three groups skipped; zero failures.
- `make test-fields`: 110/110 on each; `make test-harness`: 86 tests, OK on each.
- Focused runtime and field API checks pass ASan/UBSan on each platform.
- Native Ubuntu CI provisioning is configured; local Linux evidence is Docker,
  not a claim that native Ubuntu ran locally.

The English application-message policy is distinguished from translated libc
suffixes; the lack of application translations is not by itself a violation of
the cited recommendation. Single-shift support is exercised; locking-shift
behavior is explicitly unsupported under its implementation-defined contract.
APFS raw-filename rejection does not invalidate passing raw source decoding.
Prerequisites P1–P6 retain skip ownership without claiming all encodings,
filesystems or diagnostics verified. Review status awaits integration.
