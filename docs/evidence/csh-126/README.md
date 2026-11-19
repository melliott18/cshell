# CSH-126: ls owner/group long listings and format precedence

Based on CSH-125 commit `330c8c3`, still awaiting integration. The retained
Issue 8 `ls.html` is byte-for-byte unchanged. OPTIONS (-l, -n, -1, -C, -m,
-x and -d), OPERANDS and STDOUT supply the field and precedence oracle.
ENVIRONMENT VARIABLES supplies the C locale and explicit UTC timezone.
STDERR and EXIT STATUS require empty diagnostics and success.

Sixty cases run through direct exec, command strings, script files and stdin:
240 assertions per platform. The five object types are regular files, hard
links, directories, FIFOs and symlinks. Twelve option sequences cover -l, -n,
-n -l, -l -n, -1 -l, -l -1, and -C/-m/-x followed by either -l or -n. Numeric
selection persists through a following -l; -1 does not disable long output;
a following -l/-n restores long output after a column or stream option.
XSI-only -g and -o are outside the selected base profile.

The existing CSH-088 private metadata fixture supplies object construction and
independently reads back the authored January 2, 2000 UTC timestamp. The new
oracle checks lstat metadata and resolves the actual owner and group through
getpwuid/getgrgid before provider execution. Missing, numeric-looking,
non-ASCII or whitespace-containing account names fail setup, so this witness
cannot silently collapse into a numeric-ID or missing-account fallback test.
There are no credential or account-database changes.

Every output must contain exactly one complete line with the measured mode,
link count, owner/group fields, size, old UTC date, authored pathname, and
symlink target where applicable. Column padding and the existing supported
alternate-access markers may vary; semantic fields may not. Exact channels and
status, preserved identities/modes/sizes/link counts/timestamps, file bytes,
link texts, directory entries and successful cleanup are mandatory. Access
times are excluded because inspection can update them. FIFOs are never opened.

Six harness regressions cover all 60 independent literal field expectations,
rejection of corrupted fields and output, all four invocation modes, mutations,
failed metadata/account probes, partial setup, failed exec and bounded timeouts
with process reaping and private-directory cleanup.

Selected providers, source pins and build flags are unchanged. All predecessor
stock failures remain failures. Stock Apple ls adds 20 failures for -l -1: it prints only the pathname instead of preserving long format. All predecessor stock failures remain intact; these failures are not allowances. The selected GNU provider passes every new case. CSH-127 / issue #266 owns all 21 remaining
utility contracts and four retained U-040 conditions. Missing-account fallback,
other identities/ACLs, recent or future timestamps, further options, arbitrary
graphs, terminal layouts, non-C locales and resource failures remain open.
U-034/U-040 stay partial; whole-utility qualification is not claimed.

## Reproduction

Build `make -j4 cshell host-profile` with the documented GNU prerequisites on
PATH. The private `build/prerequisites/gfind` was copied from the CSH-125
worktree; its exact identity is retained in the selected manifest. Use a private
TMPDIR owned by the invoking user and primary group:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh126-tmp" \
  python3 docs/evidence/csh-126/validate.py native
sh docs/evidence/csh-126/linux.sh
python3 docs/evidence/csh-126/collect.py
python3 docs/evidence/csh-126/verify.py
```

Linux reuses the unchanged CSH-119 shell/provider image with this checkout's
tests and accounting mounted read-only. Fixtures run as uid/gid 10001 on
bounded executable tmpfs. Remove the task-owned container after collection.
Native providers are rebuilt from pinned sources. Separate stock full and
provider audits retain their nonzero results and exact failure identities.
No privileged fixture or host-volume exhaustion is used.

## Validation result — 2026-11-19

Native macOS 14.8.7 arm64 (UID 501) and Linux arm64/Docker with glibc 2.36
(UID/GID 10001) pass the complete 47-target required Make command. Both pass
all 226 filesystem harness tests, 13 ownership tests and 1,162 host integration
assertions with zero gaps. All 24 ticket tests and offline/live identity checks
pass with 127 reservations.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Selected full filesystem profile | 14,459 pass / 0 fail | 14,531 pass / 0 fail |
| New long-listing assertions | 240 pass / 0 fail | 240 pass / 0 fail |
| Filesystem harness tests | 226 pass | 226 pass |
| Stock full-audit failures | 1,069 (1,049 retained + 20 new) | 578 unchanged |
| Stock provider-audit failures | 16 unchanged | 8 unchanged |
| Complete requested make command | exit 0 | exit 0 |

The evidence verifier passes on both platforms. It checks exact new outputs,
every predecessor expectation, exact stock failure identities, source/provider
provenance and cleanup. The 20 new Apple failures have zero status, empty
stderr and unchanged fixtures; stdout contains only the pathname and newline.
No allowances or provider changes were introduced. The task-owned container
was removed. No sanitizer, separately hosted native-Linux or hosted CI result
is claimed.

CSH-126 is ready for review, stacked on unmerged CSH-125. CSH-127 owns all
remaining contracts and four retained conditions. Integration and whole-utility
qualification are not claimed.
