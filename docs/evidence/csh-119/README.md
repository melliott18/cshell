# CSH-119: ls hidden entries and dot directories

Based on CSH-118 commit `083c982`, not yet integrated. No shell implementation
or selected provider changes. The Issue 8 ls OPTIONS and STDOUT clauses supply
-a/-A selection, -r order, -i inode numbers, and -F/-p suffixes. The retained
ls.html source is checked against the normative section-map SHA-256.

Twenty-four private graphs run in direct exec and string/file/stdin modes,
for 96 assertions per platform. Default, -A and -a combine with reverse C
ordering and plain/inode/-F/-p rendering. Hidden files, directories and a
symlink accompany visible file/directory controls. Dot and dot-dot refer to
distinct, privately owned directories, independently measured by lstat before
exec. Authored names and rules, never provider output, determine expectations.
Metadata, bytes, link text and directory entries must remain unchanged. Only
inode-column space padding is permitted. Access times are excluded because
inspection may change them. Cleanup and setup errors are mandatory failures.

Harness regressions exercise all modes, bad output, mutation, partial setup,
failed exec and real provider timeout cleanup. The native stock ls is used
in the harness matrix; selected-provider qualification is recorded separately.

CSH-120 / issue #252 owns all remaining contracts and all four retained
conditions. Arbitrary/recursive graphs, devices, other credentials/ACLs,
terminal layouts, non-C locales, races, resource failures and full utility
contracts remain unqualified. U-034/U-040 remain partial.

## Reproduction

Run `make -j4 cshell host-profile` with the documented GNU tools (including
gfind) on PATH. Use a private TMPDIR with the invoking user's group, then
`python3 docs/evidence/csh-119/validate.py native`.

Build `docs/evidence/csh-119/Dockerfile.linux` as `cshell-test:csh-119` and run
`python3 docs/evidence/csh-119/validate.py linux` inside it. The base is the
existing CSH-118 image; the fixture user is unprivileged. Copy its
`/work/build/csh119-validation` results and the native results here. Compress
raw logs losslessly and run `python3 docs/evidence/csh-119/verify.py`.

## Development limitations

Initial native provisioning lacked gfind on PATH; a private copy of the
CSH-118 provider resolved provisioning. The first Linux attempt exhausted the
Docker writable filesystem. The next attempt used Docker's default noexec
memory-backed temporary mounts and was stopped after helper execution failed.
The final attempt uses bounded executable tmpfs mounts for /tmp (512 MiB) and
/work/build/tests (256 MiB, uid/gid 10001), with reports bound to this worktree.
Only task-owned containers and the task's superseded image were removed.
These setup errors are retained under development/; they are not utility
filesystem-exhaustion qualification.

The native requested command stopped at the existing permissions-harness
control: a five-second helper timeout prevented chmod from updating its file.
An isolated diagnostic reproduced the timeout and verified child cleanup.
The host load average exceeded 300. No timeout, allowance or expected result
was relaxed. All 192 filesystem harness tests passed. A separate supplemental
run collects the remaining filesystem targets; it does not erase the failed
requested command or establish complete host-profile acceptance.

## Final bounded evidence

The native combined filesystem profile passes 13,035 assertions and Linux
passes 13,075, each with zero failures and exactly 96 additions over CSH-118.
Every focused filesystem target passes on both platforms. The verifier checks
exact source/provider hashes, unchanged predecessor expectations, all new
case/mode pairs, channels/status, unchanged objects and cleanup. Stock failures
remain exactly 853/578 for full audits and 16/8 for provider audits (native/Linux).

The isolated native permissions harness subsequently passes all six tests.
The initial full required command still failed on each platform, so this is
bounded filesystem evidence, not complete host-profile acceptance. The Linux
failure is ed/signal-int in direct mode. All gaps remain explicit; the ticket
stays in progress and the PR is a draft. No sanitizer or separately hosted
native-Linux validation is claimed. The task-owned containers were removed.
