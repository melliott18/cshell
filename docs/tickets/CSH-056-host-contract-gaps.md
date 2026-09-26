# CSH-056: Resolve residual host utility contracts

- Status: ready
- Type: test
- Kind: implementation
- Parent: None
- Depends on: CSH-039
- Branch: Assigned when work starts
- Issue: Not yet assigned

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

- [ ] Provision or qualify supported native/Docker hosts for the five known gaps.
- [ ] Run the strict reproducer successfully with executable/package identities.
- [ ] Supply the residual witnesses or retain individually justified capability
  limitations with source, environment and owning follow-up.
- [ ] Update the stable condition rows and CSH-012 gate without promoting broad
  utility families from selected tests.
