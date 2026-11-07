# CSH-095 numeric magic evidence

Collected 2026-10-19 in a separate worktree on published CSH-094 commit
`50ceaacb724d345a5ac7cdc4d012d929c11a73e4`. Integration remains gated on that
unmerged dependency.

## Scope and independent oracle

Issue 8 [file](https://pubs.opengroup.org/onlinepubs/9799919799/utilities/file.html)
EXTENDED DESCRIPTION specifies native numeric values, masks, comparison and
size predicates, and first-match/continuation ordering. OPTIONS specifies the
user-authored `-m` database; STDOUT, STDERR and EXIT STATUS supply the channel
and status contract. `normative-sources.json` records the retrieved page hash
(direct HTTPS retrieval after the web reader returned 403).

`tests/host_filesystem_magic.py` supplies 46 cases, each run by direct exec and
cshell string/file/stdin dispatch: 184 assertions per platform. The cases cover
signed byte/short minima and maxima, comparisons across zero, masks and bit
tests on negative values, hexadecimal/octal short constants, complete/truncated
numeric values, and first-match order with matching/nonmatching continuations.
Each numeric predicate has positive and negative samples. Two equal top-level
predicates swap messages to distinguish source ordering from predicate rank;
a failed continuation must not allow the second top-level match to print.

Python constructs sample bytes from native signed C values, with independently
checked ctypes widths. Readback precedes provider execution. Records retain
native widths, byte order, exact sample/database bytes, and every argument.
Literal messages are authored in the database; no reference utility generates
expected output. Assertions require exact stdout, empty stderr, status zero,
and unchanged input bytes. These are private regular-file environments, not
fault injection, filesystem exhaustion or default-database qualification.

Four added harness regressions cover native numeric values, corrupted
channels/status/input effects, setup failure before execution, and failed exec
and timeout cleanup in all four modes. The initial Linux exec-failure regression
allowed a shell to continue PATH search past the deliberately broken executable
and invoke the real system file. Restricting that synthetic fixture to its own
PATH removed the fallback; the initial failure log is retained separately.
The provider qualification itself never used that synthetic broken executable.

## Results

All required targets pass on native macOS 14.8.7 arm64 UID 501 and Debian 12
arm64 Docker UID 10001, including 10 ownership tests and 80 harness tests on
each host. Final results are recorded in `summary.json`, compressed command
logs and JSON reports.

| Profile/target | macOS | Linux |
| --- | --- | --- |
| Host integration | 1162 pass, 0 fail | 1162 pass, 0 fail |
| Selected filesystem profile | 1659 pass, 0 fail | 1699 pass, 0 fail |
| Allocation faults | 240 pass, 0 fail | 200 pass, 0 fail |
| Selected provider audit | 168 pass, 0 fail | 184 pass, 0 fail |
| Private residual environments | 104 pass, 0 fail | 104 pass, 0 fail |
| Isolated graphs/magic/timestamps | 112 pass, 0 fail | 112 pass, 0 fail |
| Owned terminal overwrites | 39 pass, 0 fail | 39 pass, 0 fail |
| Operand/recursive decisions | 68 pass, 0 fail | 68 pass, 0 fail |
| Metadata/timestamps | 64 pass, 0 fail | 64 pass, 0 fail |
| Recursive prompts | 30 pass, 0 fail | 30 pass, 0 fail |
| Pathname limits | 32 pass, 0 fail | 32 pass, 0 fail |
| Physical cwd changes | 32 pass, 0 fail | 32 pass, 0 fail |
| Creation modes | 104 pass, 0 fail | 104 pass, 0 fail |
| Output errors | 32 pass, 0 fail | 56 pass, 0 fail |
| Logical cwd fallback | 48 pass, 0 fail | 48 pass, 0 fail |
| New numeric magic | 184 pass, 0 fail | 184 pass, 0 fail |
| Stock full audit | 1566 pass, 73 fail | 1633 pass, 42 fail |
| Stock provider audit | 152 pass, 16 fail | 176 pass, 8 fail |

Stock Make audits exit 2 and direct provider audits exit 1, as required.
The final source digest is
`beaf0e708c4e632a9dc777b9cdb6122c0f4ffc7f720ba9640970eb75fe0ae438`.
 `verify.py` requires every previous selected case/mode to remain,
exactly 184 new passing assertions, unchanged stock failure IDs/modes, successful
cleanup for every filesystem case, and one final source digest on both hosts.
No provider source, build flags or selected-profile allowances change.
No sanitizer or hosted-CI qualification is claimed.

## Reproduction and provenance

```sh
# Native PATH must provide gtest, g[, gfind and gdd.
make -j4 cshell host-profile
python3 docs/evidence/csh-095/validate.py native

# Reuse the identified CSH-094 Debian provider image, overlay final test inputs.
docker build -f docs/evidence/csh-095/Dockerfile.linux -t cshell-test:csh-095 .
docker create --init --name cshell-csh095-final cshell-test:csh-095 \
  python3 docs/evidence/csh-095/validate.py linux
docker start -a cshell-csh095-final
docker cp cshell-csh095-final:/work/build/csh095-validation ./build/csh095-linux-results
docker rm cshell-csh095-final

# Verify retained evidence without executing providers.
python3 docs/evidence/csh-095/verify.py
```

`validate.py` runs all ticket-required targets plus the new focused target and
retains separate stock audits with required command statuses 0, 2 and 1. JSON
reports contain provider hashes, source identity, stdout/stderr, status, effects,
setup errors and cleanup. The selected native gfind was copied from CSH-094's
ignored build; other local providers were rebuilt from their pinned sources.
Linux uses Docker `--init`, UID 10001, no host mounts and the CSH-094 Debian
image recorded in `linux-image.json`. Its overlay contains the current tests,
Makefile and tools. The final report hashes independently establish source
identity equality across hosts. `SHA256SUMS` covers retained artifacts other
than this narrative.

## Remaining ownership

[CSH-096](../../tickets/CSH-096-filesystem-environment-residuals.md)
([#203](https://github.com/melliott18/cshell/issues/203)) owns every unsupplied
contract with its environment, reason and utility/libc/platform implementation
owner. Other numeric types/widths, unsigned ranges, cross-database `-m/-M/-d`
precedence, default classification, encodings and locales remain unqualified.
All four original U-040 conditions remain open. Historical evidence and stock
failures are preserved. This uses the explicit-disposition acceptance alternative;
no whole utility or U-034/U-040 completion is claimed.
