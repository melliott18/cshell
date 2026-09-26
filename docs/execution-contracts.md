# Residual execution contracts: CSH-055

[CSH-055](tickets/CSH-055-execution-contract-gaps.md) extends the
[CSH-049 clause map](execution-evidence.md). It fixes prefix-PATH category
selection and dot read-error suppression, and prevents non-EXIT trap dispatch
after a fatal command-read error. It does not promote entire matrix families to
verified or open [CSH-012's compliance gate](tickets/CSH-012-conformance-and-portability.md).

## Sources and oracle

The reviewed source is POSIX.1-2024 Shell Command Language
[2.8.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_08_01),
[2.9.1](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_01),
[2.9.5](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_09_05),
and [continue](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html#tag_19_18).
No reference shell is an oracle. Diagnostics are cshell policy, with host errno
text derived using `os.strerror`. The public source was checked on 2026-09-26.

`E` below means [execution_cases.py](../tests/execution_cases.py), with the
`execution: ` prefix in generated fixtures. Cases run in string, file and stdin
modes except the two explicitly interactive syntax witnesses (string/file).
They join the default runtime suite and `make test-execution-evidence`.
The original [strict PATH reproducer](../tests/fixtures/execution-known-gaps.json)
is retained as a passing regression; the old filename preserves external links.
Its previous expected failures remain failures in the historical CSH-049 record.

## Lookup, preparation and control witnesses

| Scope | Assertions and classification |
| --- | --- |
| EXEC-004 prefix PATH | E `prefix PATH selects external pwd` requires `custom-pwd\n`, status 0, empty stderr. `expanded sequential PATH prefixes`, `repeated prefix PATH and restore attributes`, `prefix restores exported PATH`, `empty prefix PATH searches current directory`, and `prefix selects standard builtin from replaced PATH` cover last-prefix selection, scalar expansion, exported/unexported restoration, current-directory search and switching back to the standard builtin. Sequential prefix visibility is D-006 policy; effective PATH lookup is required. |
| EXEC-004 precedence/defaults | E `prefix function precedence and command bypass` requires the function first and external replacement through `command`; `default PATH overrides prefix for command p` compares output to the direct standard pwd. `prefix PATH in pipeline stages` checks both stage positions. Function prefix export/restoration is project policy; function precedence and `command -p` lookup are required. |
| EXEC-004 cleanup | E `missing prefix target and restore` requires status 127 then original PATH/output; `prefix redirect failure restores PATH` requires status 1 and original PATH; `readonly PATH prevents target execution` requires status 1, diagnostic and absent subsequent file. `control_faults` in [execute_faults.c](../tests/execute_faults.c) sweeps allocations through standard/missing PATH lookup and nested functions; it checks restored PATH value/attributes, absent TEMP, caller parameters/depth, live allocations, descriptors and child ownership. |
| EXEC-001/003 environments | E `no-name trap and expansion environments` requires persistent assignment `childchild-exit`, disposable `${made:=out}` redirect mutation, empty `out`, status 0 and the parent's EXIT action. `redirect substitution trap isolated` requires filename `outchild`, status 7 and the parent's unchanged EXIT action. Distinct disposable redirect state and substitution state, and their permitted ordering, are selected policies; assignment persistence and last-substitution status are requirements. These tests do not rule out source-permitted shared environments in other implementations. |
| EXEC-005 imported names | E `invalid imported environment name policy` observes `BAD-NAME=<unset>` in an external helper. Dropping imported names that are not shell names is a selected unspecified policy. |
| EXEC-014 nested functions | E `nested function return restores scopes` checks two parameter frames, prefix values, separate inner/outer redirect files and status 9. `nested syntax interactive restoration` and `nested syntax noninteractive unwind` parse malformed nested function syntax through eval: status 2, exact diagnostic, empty redirect files, restored caller argument/value, interactive continuation versus only the noninteractive EXIT action. Allocation sweeps cover nested definition/invocation failure. The 128 function/evaluation/parser nesting ceilings remain [CSH-046 limitations](tickets/CSH-046-invocation-syntax-evidence.md); these are not unbounded-recursion claims. |
| U-003/U-004 conditions | E `continue in while condition` and `continue in until condition` skip the first condition iteration, print only body 2 and finish at 3/status 0. `nested lexical while condition continue outer` and its until counterpart cross case/brace/condition nesting, print a/b, and leave body/later files absent. These are required same-environment lexical enclosures. |
| U-004 nonlexical policy | E `eval nonlexical continue policy` transfers to the caller loop; `function nonlexical continue policy` rejects crossing the function boundary with status 2. Neither is a portable requirement. Existing U-003 lexical break witnesses and signal ownership in CSH-054 remain unchanged. |

## Descriptor and command-read witnesses

[execution_contracts.py](../tests/execution_contracts.py) runs through the same
bounded process-group runner as the execution API tests: five-second deadline,
2 MiB combined-output bound, descendant cleanup and exact stdout/stderr/status.
It supplies PATH=`os.defpath`, C locale, fresh HOME/TMPDIR and, on Darwin,
`MallocNanoZone=0`. It inherits no arbitrary shell variables. Interactive stdin
prompt bytes are explicitly asserted. `make test-execution-contracts` is included
in both `make test` and `make test-execution-evidence`.

| Scope | Assertions and classification |
| --- | --- |
| RED-001/EXEC-005 (32 cases) | Masks 0–7 × string/file × direct/PATH execution. The uninstrumented `execute_helper launch-fds` opens fd 8 O_RDWR/O_APPEND without FD_CLOEXEC, closes selected standard fds, then execs the public cshell. The script redirects/closes/restores fd 8 and redirects builtin stdout before executing the observer. `inspect-inherited` checks exact argv[0] (absolute operand or bare `observer`), inherited access/append/fd flags, and availability of every initially open standard fd. Appending must retain `seed\n` and add exactly `inherited-ok\n`; status is 0 and temporary redirects are empty. Closed standard fds may remain closed or be reopened, including by sanitizer startup. This is a required inheritance check with the permitted reopening alternative, not a requirement that standard fds stay closed. |
| EXEC-015 main input (6 cases) | Two injection boundaries × noninteractive file, interactive file and stdin. One boundary follows a complete simple command and semicolon in a partially buffered physical line; the other follows a full simple-command line inside an unfinished brace group. Both require no buffered/later output, exact location/EIO diagnostic, status 128 and only `exit:128\n`. No inference from EOF or EINTR is used. |
| EXEC-015 pending trap (1 case) | The injected EIO also raises caught USR1, making its action pending before finalization. Only the previously defined EXIT action may run; the USR1 action prints a forbidden marker if dispatched. The fixture requires just `exit:128\n`, the exact read diagnostic and status 128. Suppression remains active throughout EXIT evaluation. |
| EXEC-015 dot exception (12 cases) | Interactive/noninteractive × direct dot/`command .` × three invocation modes. A successfully executed sourced line prints `sourced`; failure after a buffered command/semicolon prevents all later sourced commands. Direct noninteractive dot exits 128; interactive dot and either `command .` mode continue with status 128 and finally run EXIT at status 0. The exact EIO diagnostic is checked. This is the required special-utility exception and command suppression, not syntax-error suppression. |

[command_read_faults.c](../tests/command_read_faults.c) interposes only the
`read` call in a separately compiled `input.c`. It matches the selected file's
device/inode (so descriptor relocation is immaterial) and injects EIO at an exact
byte offset. The binary links the ordinary public main, parser, executor and
other objects. `-c` has no descriptor reads of its own, so it is covered through
dot operands rather than pretending to inject a string read syscall. All normal
runtime fixtures also execute the uninstrumented public binary.

## Remaining scope

The named CSH-055 conditions above have concrete assertions; platform results
and limitations are in the [run record](tickets/CSH-055-execution-contract-gaps.md#validation-record).
Full expansion combinations remain CSH-047, full environment/state combinations
CSH-048, multibyte source CSH-053, signals/jobs CSH-054, and host utilities/fallback
CSH-052/056. Arbitrary descriptor layouts and all filesystem capabilities are
not inferred from these finite cases. CSH-049 retains the overall evidence map
and cross-platform integration record. Full POSIX compliance remains unclaimed.
