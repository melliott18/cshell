# CSH-049 residual execution review

This review turns the formerly unbounded “wider filesystem/target-expansion
combinations” note into explicit conditions, assertions and platform results.
It extends the [25-row clause map](execution-evidence.md); it does not promote
those parent families or close the CSH-012 conformance gate.

## Requirements and test selection

The reviewed Issue 8 sources are Shell Command Language
[2.7](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07),
[2.7.2](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_07_02),
[2.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01),
and [2.9.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01).
The official page returned 403 directly; indexed official-source excerpts for
redirection ordering, failure, noclobber atomicity and no-name commands were
retrievable. The existing clause map supplies the other source classifications.
No reference-shell output was used as an oracle.

The target-expansion inventory covers the named expansion mechanisms, scalar
context and evaluation timing. The filesystem inventory separates open results,
object types, permissions and offsets. It does not require constructing every
possible pathname, disk size or mount configuration to test shell behavior.
A host-specific limit is recorded as such; injected syscall errors establish
shell error handling, not physical filesystem capability. Existing large-file
and resource-limit probes remain required alongside the new tests.

## New production-runtime partitions

[execution_redirection_cases.py](../tests/execution_redirection_cases.py) adds
564 cases to both the complete runtime suite and `test-execution-evidence`.
Case names start with `execution: residual `; each has exact stdout, stderr,
status and relevant file content/absence assertions. No existing expected
result or deadline is weakened.

| Condition / requirement | Named cases and assertions |
| --- | --- |
| RED-001 target expansions | `target {expansion} {operator}`: eight operand forms (quote removal, parameter, command substitution, backquote, arithmetic, tilde, pattern removal and concatenation) × six operations (`<`, `>`, `>\|`, `>>`, `<>`, noclobber `>`) × three invocation modes = 144. Existing glob matches and IFS bytes expose accidental splitting/globbing. Arithmetic side effects occur once. Reads preserve input, output truncates, append ignores a helper seek, and read/write shares the current offset. |
| RED-001 interactive policy | `interactive target ...`: the same 48 semantic scenarios in `-ic` and `-i file` = 96. Assert cshell's selected no-globbing behavior when interactive; this is a permitted policy, not a requirement that all shells choose it. Interactive stdin/prompt behavior remains in the existing PTY suites. |
| RED-001 zero-length targets | `empty target {expansion} {operator}`: quoted empty, unset parameter, empty parameter and empty substitution × six operations × three modes = 72. The operand must remain an empty pathname and fail, preserving earlier effects while preventing later expansion/command effects. |
| RED-005 dynamic descriptors | `duplicate {expansion} {operator}`: parameter, command, arithmetic and quoted operands × `<&`/`>&` × three modes = 24. Exact copied/written bytes establish the selected source descriptor. Existing close, direction, overflow and inherited-mask cases remain in the original map/API suites. |
| RED-001–003/006 real open errors | `filesystem {kind} {operator}`: directory, non-directory parent, missing parent and cyclic symlink × four write-capable operators × three modes = 48. Earlier files truncate, failed command output and later operand-expansion files remain absent, diagnostic/status are exact, and parent stdout restores. |
| RED-002/003/006 aliases and creation | `filesystem symbolic/hard ...`, `noclobber symbolic/hard`, `dangling link creates ...` = 42. Underlying file content distinguishes truncate/append/read-write, aliases to existing regular files are protected by noclobber, and ordinary opens create dangling-link referents. Existing dangling-noclobber rejection remains a separately documented permitted choice. |
| RED-002/EXEC-006 nonregular/concurrent | `FIFO concurrent noclobber=False/True` × three modes = six. A background reader and foreground writer exchange exact bytes and wait status within five seconds. `/dev/null` and exclusive-creation contenders remain in the option suite. |
| RED-001/EXEC-003/006/008/010–014 contexts | `context {name}` covers brace, subshell, function body, function-definition redirect, eval, dot, if, for, while, until, case, pipeline, substitution and background × three modes = 42. Target arithmetic runs once, file content is exact, and parent mutation versus child isolation is explicit. `unwind break/continue/return 7` adds nine cases checking skipped effects, restored stdout and transfer status. |
| RED-002/003/006 creation permissions | `creation permissions {operator} mask={mask} existing={bool}` = 81. Operators × umasks 000/027/077 × existing/missing file, excluding the already-covered noclobber rejection. An external stat observer asserts creation mode after umask and unchanged permissions for existing files; content asserts truncation/preservation independently. |

These counts sum to 564. The 319 previous execution witnesses remain unchanged,
so the focused JSON suite contains 883 cases. The original 51 CSH-055 public
read/descriptor probes remain selected by the same Make target.

## Controlled error and race boundaries

[redirection_edges.py](../tests/redirection_edges.py) adds 204 bounded public-main
cases. [redirection_faults.c](../tests/redirection_faults.c) replaces only
`open`/`fstat` calls in a separately built copy of redirect.c. The production
binary has no test hooks. These are labelled injected boundaries, not claims
that real media or process-wide limits were exhausted.

- Six errors (EACCES, ENOSPC, EROFS, EMFILE, ENFILE, EIO) × six categories
  (no-name, special, regular, `command`-wrapped special, function, external) ×
  five input/interactive modes = 180. Each checks exact diagnostic, earlier
  file effects, absence of body/later expansion effects, unchanged prefix
  value, preserved inherited fd 7 and closed fd 8. EXIT actions test restoration
  even for noninteractive special-builtin termination. A regular `command :`
  must recover. No-name prefix timing is cshell's documented permitted policy.
- One EINTR followed by a successful open, across six operators and three
  modes = 18. Assert retry without extra output, lost bytes or truncation.
- Replace a FIFO with a regular file after the noclobber stat and before its
  open, three modes. The opened-fd check must reject it and preserve all bytes.
  The replacement is deterministic, not a sleep-based race assertion.
- Fail the opened-fd stat of a noclobber `/dev/null` symlink, three modes.
  Assert EIO propagation and parent recovery rather than treating an
  unverifiable object as safe to overwrite.

`make test-redirection-edges` runs these; both `make test` and
`make test-execution-evidence` include it, so native, Docker and sanitizer CI
cannot silently omit the new partitions. Every invocation has a fresh directory,
controlled C-locale environment, five-second bound, 65,536-byte output cap and
the existing bounded cleanup. No capability skip is added.

## Review of the remaining criterion

The originally unchecked criterion in CSH-049 requires remaining applicable runtime
cases to pass on supported platforms, with capability reasons and owners.
Its concrete untested execution conditions are now represented above. The
original 25 rows still supply ordering, here-documents, assignment categories,
lookup/fallback, argv/environment, pipelines/status, control flow, error
consequences and offset assertions; CSH-055 supplies the named residual contracts.
CSH-047/048/053/054/058 provide their integrated cross-feature witnesses.

Physical media exhaustion and absolute writable limits of every filesystem
are not asserted as completed experiments. The shell promises open/error/offset
semantics, with the actual host limit measured by CSH-043; it does not promise
that every representable offset can be written on every filesystem. Likewise,
“all target combinations” is not treated as a finite proof over every shell
program. The tables identify exactly which semantic dimensions were reviewed.

CSH-057's continuation and PTY timeout repairs are integrated. Its historical
retention failure remains unknown-cause under the
[formal disposition](evidence/csh-057-retention-disposition/README.md), with
unchanged test enforcement and same-ticket recurrence ownership. CSH-064 owns
host-profile/ACL conditions. Existing locale,
privilege and raw-pathname capability limits retain their owners. These are
cross-project residuals, not silently converted into CSH-049 passing cases or
waived requirements. Full-family verification and CSH-012 remain open.

Validation results and source/binary identities are recorded in the
[CSH-049 ticket](tickets/CSH-049-execution-evidence.md).
