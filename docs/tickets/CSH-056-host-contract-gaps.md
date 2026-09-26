# CSH-056: Resolve residual host utility contracts

- Status: review
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-039
- Branch: test/CSH-056-host-contracts
- Issue: [#97](https://github.com/melliott18/cshell/issues/97)

## Goal

Resolve the specific host provisioning/semantic gaps and remaining boundary
witnesses identified by [CSH-052](CSH-052-host-utility-evidence.md). The
[clause map](../host-utility-evidence.md) and
[run records](../evidence/csh-052/README.md) retain passing scopes separately.
No shell runtime fix is implied when the selected external binary is responsible.

## Confirmed host gaps

| Stable condition | Required outcome | Observed host outcome |
| --- | --- | --- |
| U-026/host-status-map | external `kill -l 143`: `TERM\n`, empty stderr, zero | Debian procps-ng 4.0.2: empty stdout, diagnostic `unknown signal name 143`, zero |
| U-034/host-ed | exec-accessible ed performs the declared line-print operation | ed absent from Debian bookworm-slim test image |
| U-035/numbered | `printf '%2$s:%1$s\n' a b c d`: `b:a\nd:c\n`, zero | coreutils 9.1: invalid conversion diagnostic, status 1 |
| U-035/b-precision | `printf '[%.3b]' 'ab\tcd'`: bracketed ab and tab, zero | coreutils 9.1: stdout `[`, invalid conversion diagnostic, status 1 |
| U-037/missing-timestamps | `test new -nt absent` and `test absent -ot new` (also `[`) succeed | macOS 14.8.7 system utilities return 1, empty streams |

The strict reproducer retains specification-derived assertions:

```sh
make cshell build/tests/host_utility_helper
python3 tests/host_utilities.py ./cshell build/tests/host_utility_helper --strict-gaps
```

Each operation runs in string, file and stdin modes with bounded cleanup.
The default target prints `GAP` only for the exact known signatures; strict
mode returns nonzero for any gap. Never fix a test by adopting the defective
host output as its required result. Select a suitable executable/package or
document a narrower supported system image before claiming these branches.
Changing the host profile must preserve lookup, exec accessibility, argv,
environment and status behavior and rerun existing utility-dependent fixtures.

## Remaining condition witnesses

- U-035/locale-errors: non-C LC_NUMERIC and LC_MESSAGES, numbered missing
  operands' permitted alternatives, numeric overflow result and continuation
  after a conversion error. Floating conversion support is optional in base.
- U-036/host-environment: POSIXLY_CORRECT changes to GNU echo and explicit
  identity/policy of user-selected alternative implementations.
- U-037/capabilities: positive block-device predicate and denied permission
  cases with known effective identities. No positive device result can be
  inferred from the negative regular-file case.
- U-040/host-boundaries: error/interruption/write-failure propagation and
  actual documented limits for each scoped host utility, plus locales outside
  C. Existing ulimit inheritance is not an inventory of all host limits.

Internal kill/jobs remain CSH-054, PATH-prefix pwd selection CSH-055, and shell
locale/lexical boundaries CSH-042/053. Full unrelated host utility semantics
remain outside this repository's implementation scope; §1.6 is not waived.

## Acceptance criteria

- [x] Provision or qualify supported native/Docker hosts for the five known gaps.
- [x] Run the strict reproducer successfully with executable/package identities.
- [x] Supply the residual witnesses or retain individually justified capability
  limitations with source, environment and owning follow-up.
- [x] Update the stable condition rows and CSH-012 gate without promoting broad
  utility families from selected tests.

## Implementation and validation

Implemented on `test/CSH-056-host-contracts` in a separate managed worktree.
The [qualified profile](../../tools/host-profile/README.md) selects external
executables with ordinary PATH/exec behavior. The original assertions remain
unchanged. It uses a pinned standalone FreeBSD printf with GNU getopt and
buffered-output-error adapters, BusyBox kill on Linux, provisioned ed, and GNU
test/bracket on macOS. No cshell runtime source changes are needed.

The [condition map](../host-contract-profile.md) adds numbered missing-operand
alternatives, exact conversion overflow/continuation, French numeric/diagnostic
environments, explicit Apple/GNU echo policy, positive block-node/non-root
permission witnesses, host error/write/interruption checks and queried limits.
Each remaining per-utility capability has a source/environment/reason and an
owner in [CSH-057](CSH-057-host-boundary-capabilities.md) ([#101](https://github.com/melliott18/cshell/issues/101)).
CSH-012 stays closed; no entire utility page is certified.

The [retained run records](../evidence/csh-056/README.md) contain source/binary
identities and exact commands/results. Native and Docker final strict profiles
pass 919 assertions each, with zero gaps. Full tests, 3,045-case runtime reruns
under the profile, PTY checks, and all 70 harness self-tests pass on both hosts.
Focused ASan/UBSan checks cover the selected host profile and C adapters.

The first runtime rerun caught a pwd diagnostic change caused by symlinking all
host tools. The final profile includes only required replacements, preserving
the PATH-associated pwd builtin; final reruns pass without relaxing assertions.
