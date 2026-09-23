# CSH-036: Map POSIX requirements to implementation and test evidence

- Status: done
- Type: docs
- Kind: implementation
- Parent: CSH-012
- Depends on: CSH-001
- Branch: docs/CSH-036-conformance-matrix
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

- [x] Every inventoried requirement has a source, scope decision, owner, and
  evidence field; unimplemented behavior is visibly open rather than marked passed.
- [x] Conditional, unspecified, and implementation-defined behavior is labeled,
  and unresolved scope/choice decisions have an owner and resolution path.
- [x] Existing native/Docker smoke checks are mapped only to behavior they prove,
  with future parser, expansion, utility, and PTY fixtures clearly identified.
- [x] A documented sample differential case distinguishes specification evidence
  from a reference-shell comparison and records executable/version/environment.
- [x] People and agents can navigate the matrix from POSIX tracking and find
  both a ticket's requirements and a requirement's planned/passing evidence.

## Validation

Check source and repository links, inspect representative requirements across
all major categories, and independently review the inventory for missing families.
Document unresolved gaps without requiring unimplemented features to pass.

## Implementation notes/evidence

Implemented on `docs/CSH-036-conformance-matrix`, from `main` at `233a4ca`, in a
separate worktree. This documentation baseline adds no runtime behavior and makes
no compliance claim. CSH-012 remains open; CSH-037 owns the final audit.

Deliverables:

- [Language and invocation matrix](../posix-matrix.md): 65 stable requirement
  families spanning Chapter 2, `sh`, jobs/signals and implementation choices.
- [Utilities and options](../posix-utilities.md): 66 rows covering all 15 special
  builtins and 16 intrinsic utilities, regular/host utilities, utility defaults,
  shell options and unresolved UP/XSI profile decisions.
- [Evidence conventions](../posix-evidence.md): requirement states, fixture and
  environment records, narrowly mapped prototype smoke observations, and an
  executed reference-only differential example with specification-derived output.
- [Reverse ownership index](../posix-owners.md): all 131 requirement rows mapped
  to their 23 explicitly named owner tickets, plus harness/milestone/audit roles.
  POSIX tracking, testing, the documentation index and ticket index link to it.

Validation performed on 2026-09-23:

- Link/table validation: checked all 52 repository Markdown files, 824 relative
  links including fragments, table column consistency, and 110 distinct official
  source URL/anchor pairs across 26 Issue 8 pages. All passed. Sources were fetched
  with `curl --fail --location -A 'Mozilla/5.0'` and their HTML `id`/`name` targets
  checked; an initial web fetch returned 403, while direct HTTPS retrieval worked.
  Rechecked the final documents after review corrections. The one-off checker was
  `python3 /tmp/csh-036-check-docs.py`; it checked paths, heading/explicit anchors,
  unescaped table separators and fetched normative anchors, without adding a
  repository test framework. Checked unique requirement IDs and reverse-owner
  completeness against the owner cells in both tables.
- Independent read-only review compared the official Chapter 2, `sh`, Chapter 1,
  and utility inventories with all three authored documents and the reverse
  index. It found no remaining missing major families or ownership blockers for
  this baseline. Review corrections included required separate function/variable
  namespaces, case pattern ordering, lazy parameter operator words, aliases in
  execution environments, the NUL-free input precondition, and UP applicability.
  Additional depth remains assigned below rather than hidden as passed coverage.
- `make clean && make -j8 && make test`: all three existing smoke cases passed
  on macOS 14.8.7 (23J520), Darwin 23.6.0 arm64, Apple Clang 15.0.0, Apple Flex
  2.6.4, GNU Make 3.81, Python 3.12.2. The existing generated scanner signedness
  warning remains; no runtime files changed.
- `make docker-test DOCKER_IMAGE=cshell-test:csh-036`: all three smoke cases
  passed on Linux 6.4.16-linuxkit aarch64, Debian Bookworm, GCC 12.2.0,
  Flex 2.6.4, GNU Make 4.3, Python 3.11.2 and glibc 2.36. Resolved image:
  `sha256:6e2c19335d31470c54c794e8a27583e0533dd248d3e965fde6e7e148dc057375`;
  Debian base digest:
  `sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251`.
  These reruns support only the [three smoke witnesses](../posix-evidence.md#existing-smoke-evidence),
  not the unimplemented requirements.
- The documented parameter-default sample passed on `/bin/bash --posix`
  3.2.57(1)-release and `/bin/ksh` 93u+ with exact output, status and filesystem
  assertions. Executable hashes, version probes, clean environment and a runnable
  reproducer are in the [sample record](../posix-evidence.md#sample-differential-case).
  cshell was not tested on this unsupported expansion script.
- `git diff --check`: passed. No diagrams changed.

Remaining work is explicit: implementation tickets refine family rows into
clause/operand/error fixtures and add implementation/results links; CSH-029
allocates missing history/vi/mail work before selecting full UP; the profile
owners resolve XSI and documented choices; CSH-037 audits all rows and platforms.
No unimplemented requirement is marked verified. Native/Docker smoke results do
not establish cross-platform conformance or close any behavioral milestone.

Integrated into `main` through [pull request #44](https://github.com/melliott18/cshell/pull/44)
on 2026-09-23. Implementation commit: `a574faf`; merge commit: `8e097b2`.
The parent milestone remains open pending CSH-037 and its other completion gates.
