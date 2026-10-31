# CSH-107 omitted-who creation mode qualification

This increment adds 72 independently authored mkdir/mkfifo cases, required in
direct execution and cshell string/file/stdin modes (288 assertions). It is
stacked on CSH-106 commit `9440db6`; integration remains gated on that dependency.
No selected-profile allowances are introduced.

## Contract and independent oracle

[mkdir OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkdir.html)
and [mkfifo OPTIONS](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mkfifo.html)
use the [chmod symbolic mode rules](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/chmod.html),
with assumed initial modes 0777 and 0666 respectively. When who is absent,
addition and removal exclude bits in the invoking process's creation mask.
Assignment first clears all permission bits, then sets the requested bits
allowed by the mask. Permission copies use the mode at that point in the
sequence. Conditional execute applies to directories even after clearing all
permissions; the authored FIFOs have no initial execute bits.

Literal expected modes are authored for each utility and masks 027, 077 and
777. They do not come from provider output or a symbolic-mode parser. The
matrix covers removal, clearing followed by addition, assignment, copy
addition/removal/assignment, conditional execute, empty assignment and multiple
actions in a clause, plus explicit-who controls. The existing child helper sets
and reads back the umask and independently creates a probe directory/FIFO,
requiring their exact masked modes before executing the selected provider.
A missing or wrong marker is a failure, even when the utility result otherwise
matches. Every case requires empty stdout/stderr, zero status, exact final
object type/mode and successful cleanup.

Four new harness regressions check matrix completeness and distinguishing
expected modes; reject altered permissions, channels, status and mask markers;
prevent dispatch after partial setup; and prove cleanup/reaping after failed
exec and timeout in all four modes. Existing creation tests also exercise
wrong kernel-probe observations and restrictive-directory timeout cleanup.
No shell or vendor C source changed.

## Selected providers and retained stock failures

Apple mkdir and mkfifo retain masked group permission bits when `=u` follows
`u=rw,g=r,o=`. With mask 077 the result is 0640 rather than 0600; with mask 777
it is 0640 rather than 0000. Both utilities fail in all four modes: 16 new
stock assertions. Linux stock providers pass the new cases. These failures
remain separate from selected-profile results and are never waived.

The opt-in profile builds GNU coreutils 9.7 mkdir and mkfifo from the existing
checksum-verified archive. It uses the shared configured coreutils build; the
existing cp/rm patches do not modify creation utilities. Both platforms select
these local binaries. The manifest records their exact realpaths, SHA-256,
archive digest, configure flags and build targets. The retained configure,
shared build and creation logs document the toolchain. No system binary or
installation is changed. Every prior selected expectation and stock failure
must survive unchanged, as enforced by `verify.py`.

## Qualification boundary

Only the authored final modes are qualified. Further symbolic-mode and parent
graphs, special bits, transient permissions, inherited ACLs, other credentials,
path/depth limits and capacity exhaustion remain open. FIFO transfer is outside
creation. No mount, disk filling, privilege change, kernel fault injection or
libc allocation fault is supplied. The 21 individual utility dispositions and
four original U-040 conditions transfer to
[CSH-108](../../tickets/CSH-108-filesystem-environment-residuals.md)
([#227](https://github.com/melliott18/cshell/issues/227)). U-034/U-040 remain
partial; utility/libc/platform vendors retain implementation ownership.

## Validation

| Check | Native macOS | Linux/Docker |
| --- | --- | --- |
| Selected filesystem profile | 11495 pass, 0 fail | 11535 pass, 0 fail |
| New omitted-who assertions | 288 pass | 288 pass |
| General host integration | 1162 pass, 0 gaps | 1162 pass, 0 gaps |
| Ownership / filesystem harness | 10 / 128 pass | 10 / 128 pass |
| Runtime / terminal cases | 3950 / 33 pass | 3950 / 33 pass |
| Harness suite | 93 tests pass | 93 tests, one Darwin-only skip |
| Stock full / provider failures | 705 / 16 retained | 578 / 8 retained |
| Regular format / compiled database | 14 / 5 pass | 14 / 5 pass |

Final native macOS and unprivileged Debian/Linux Docker counts and command
statuses are recorded in `summary.json` and platform command records.
The verifier requires all 288 new assertions on both platforms, every CSH-106
expectation, all previous stock failures, exact provider/source provenance and
cleanup. No hosted native-Linux or sanitizer run is claimed.

The initial native build reached provisioning after the new profile definition
was written but before its new Make prerequisites were loaded by that running
make process. It failed on the missing mkdir provider. A subsequent build used
the completed Makefile and built both new providers before validation. The
initial failure, final build and preliminary focused probes remain under
`development/`; they are not substituted for the final validation matrix.

## Reproduction

```sh
# Provision gtest, g[, gfind and gdd on the provisioning process's PATH.
make -j4 cshell host-profile
python3 docs/evidence/csh-107/validate.py native
python3 docs/evidence/csh-107/supplement.py native

docker build -f docs/evidence/csh-107/Dockerfile.linux -t cshell-test:csh-107 .
docker create --init --name cshell-csh107-validation cshell-test:csh-107 \
  sh -c 'python3 docs/evidence/csh-107/validate.py linux && python3 docs/evidence/csh-107/supplement.py linux'
docker start -a cshell-csh107-validation
docker cp cshell-csh107-validation:/work/build/csh107-validation ./build/csh107-linux-results
docker cp cshell-csh107-validation:/work/build/csh107-supplement ./build/csh107-linux-supplement
docker rm cshell-csh107-validation

python3 docs/evidence/csh-107/retain.py build/csh107-validation build/csh107-supplement \
  build/csh107-linux-results build/csh107-linux-supplement
python3 docs/evidence/csh-107/verify.py
```

Native provisioning uses a copy of the predecessor worktree's qualified gfind
under this worktree's ignored build/local-bin. Selected validation must exit
zero; full stock and stock provider audits must remain nonzero. Reports retain
output, status, effects, setup, cleanup, platform identity and source hashes.
`SHA256SUMS` covers retained files here except itself.
