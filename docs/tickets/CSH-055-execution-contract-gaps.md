# CSH-055: Complete residual execution contracts

- Status: ready
- Type: fix
- Kind: implementation
- Parent: None
- Depends on: CSH-031, CSH-039
- Branch: Assigned when work starts
- Issue: [#92](https://github.com/melliott18/cshell/issues/92)

## Goal

Fix the prefix-PATH lookup defect and complete the narrower unverified
execution obligations identified by [CSH-049](CSH-049-execution-evidence.md).
The [clause map](../execution-evidence.md) retains passing witnesses; this
follow-up does not invalidate them or promote their whole families to verified.

## Confirmed defect: EXEC-004

At baseline `daa1be1`, and with the unchanged runtime in CSH-049, a temporary
PATH prefix does not affect the selection of the PATH-associated `pwd` builtin.
Create executable `bin/pwd` containing `#!/bin/sh` and
`printf 'custom-pwd\n'`, then execute:

```sh
./cshell -c 'PATH=bin pwd'
```

Required: `custom-pwd\n`, empty stderr, status 0. Observed on native macOS and Debian Docker:
the absolute working directory plus newline, empty stderr, status 0.
`runtime_simple` resolves the category before prefix values are applied;
`path_builtin_category` consequently searches the old PATH. The external-only
prefix PATH witnesses do not expose this category-selection error.

Sources: [2.9.1.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_02)
and [2.9.1.4](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01_04).
[The strict reproducer](../../tests/fixtures/execution-known-gaps.json) asserts
the required result, not the buggy output. It is intentionally separate from
passing default suites. Run it with the normal bounded harness:

```sh
python3 tests/smoke.py ./cshell --suite tests/fixtures/execution-known-gaps.json
```

## Remaining clause coverage

- RED-001/EXEC-005: public-runtime initially closed stdout/stderr and combined
  standard-descriptor masks in string/file modes, inherited open descriptor
  flags and argv[0] after direct/PATH execution. Existing seven-mask pipeline
  tests are API evidence. POSIX permits reopening closed standard descriptors;
  sanitizer startup can do so, and the oracle must distinguish that permission
  from loss of a required inherited descriptor.
- EXEC-001/003: no-name redirection/substitution environment combinations with
  traps and expansion side effects. Preserve source-permitted alternatives.
- EXEC-015: inject unrecoverable command-read failures with already-buffered
  commands, asserting no subsequent command execution except EXIT actions;
  interactive failure must also exit. Cover the dot-file exception and
  `command .` suppression separately. EOF/EINTR/module errors are insufficient.
- EXEC-014: nested function syntax/error recovery and restoration combinations;
  keep documented parser/function recursion ceilings linked to CSH-046.
- U-003/U-004: continue from while/until condition lists and nested lexical
  combinations; distinguish function/eval/non-lexical enclosure policy from
  required same-environment lexical enclosure.

Other residual owners remain CSH-047 (expansion), CSH-048 (environment/state),
CSH-052 (host utilities/fallback), CSH-053 (multibyte lexical boundaries), and
CSH-054 (signals/jobs). SH-009/O-026 absolute filesystem capabilities remain
host-qualified in CSH-043/049, not a promise to test every filesystem.

## Acceptance criteria

- [ ] Prefix PATH participates in PATH-associated builtin selection, including
  replacement PATH, repeated prefixes, restored attributes, functions,
  `command -p`, pipelines and failure cleanup. The strict reproducer passes
  in all three modes and joins the default suite.
- [ ] Every remaining condition above has normative/policy classification,
  exact assertions and scoped native macOS/Linux run records or a concrete
  narrower follow-up owner.
- [ ] Reverse links, matrix state and CSH-012's closed compliance gate remain
  accurate; expected failures are never counted as passes.

## Validation

Run `make test-execution-evidence test-execute test-pipeline test-context
 test-control test-runtime test-runtime-pty test-harness`, then full normal,
Docker and relevant ASan/UBSan checks. Record source, suite, binary identity,
compiler/flags, OS/libc and capability skips under the evidence policy.
