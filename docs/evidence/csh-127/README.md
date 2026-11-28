# CSH-127: ls base-profile permission fields

Based on CSH-126 commit `9e611d4`, still awaiting integration. The retained
Issue 8 `ls.html` is unchanged. STDOUT defines r/w/x/- and s/S; OPTIONS
supplies -d, -l and -n. Sticky-bit t/T is XSI-shaded and excluded.

CSH-127 supplies 128 ls cases / 512 assertions for base-profile permission rendering on owned regular files and empty directories. Both -l and -n cross all four set-user-ID/owner-execute states with all four set-group-ID/group-execute states and absent or full other permissions. Independent pre-exec chmod/lstat readback requires the exact authored mode, fixture UID and primary GID. Exact s/S and r/w/x/- fields, account or numeric IDs, old UTC date, channels/status, unchanged metadata including ctime, bytes, directory entries and cleanup are required. No fixture is executed. Sticky-bit t/T rendering is XSI-only and outside this base profile. Selected providers are unchanged. Other identities and ACLs, special-bit execution semantics, missing-account fallback, recent timestamps, arbitrary graphs, terminal layouts, non-C locales and resource failures remain unqualified.

The matrix crosses four owner special/execute states, four group
special/execute states, and absent/full other permissions on regular files
and empty directories. Both named and numeric long formats are required.
All objects belong to the unprivileged fixture UID and its primary GID;
chmod is followed by exact lstat mode readback. A kernel that clears a
requested bit fails setup before provider exec. No object is executed,
no identity is changed and no inherited ACL or special-bit execution
semantics are claimed. Access times are excluded because inspectors may
update them. Ctime and all other measured metadata must remain unchanged.

Six harness regressions check literal permission expectations and mutations,
all invocation modes, partial setup failure, rejected mode readback,
fixture mutation, failed exec and bounded timeout/reaping/cleanup.

Selected source pins, provider code and build flags are unchanged. All
predecessor expectations and stock failures must be retained exactly.
CSH-128 / issue #268 owns all remaining contracts and four retained
conditions. U-034/U-040 remain partial.

## Reproduction

Build `make -j4 cshell host-profile` with GNU prerequisites on PATH. The
private `build/prerequisites/gfind` was copied from the CSH-126 worktree;
its exact identity is recorded in the selected manifest. Use a private
TMPDIR owned by the invoking user and primary group:

```sh
PATH="$PWD/build/prerequisites:$PATH" TMPDIR="$PWD/build/csh127-tmp" \
  python3 docs/evidence/csh-127/validate.py native
sh docs/evidence/csh-127/linux.sh
python3 docs/evidence/csh-127/collect.py
python3 docs/evidence/csh-127/verify.py
```

Linux reuses the unchanged CSH-119 shell/provider image with this checkout's
tests and accounting mounted read-only. Fixtures run as UID/GID 10001 on
bounded executable tmpfs. Remove the task-owned container after collection.
Native providers are rebuilt from pinned sources. Separate stock full and
provider audits retain their nonzero results and exact failure identities.

## Initial Linux language failure

The first complete Make command returned 2 because the existing
`ed/signal-int` command-string witness failed to capture its final response.
Its 15,043 selected filesystem assertions all passed. The language suite
reported 1,088 passes and one failure; the child exited with status zero and
was reaped, and its fixture was removed. The raw command log and language
report are retained as `linux-initial-command-0.log.gz` and
`linux-language-initial.json.gz`. An unchanged isolated rerun passed all three
signal invocation modes (`linux-ed-signal-recheck.json`).

[CSH-129](../../tickets/CSH-129-ed-signal-response.md) /
[#269](https://github.com/melliott18/cshell/issues/269) owns investigation of
the response boundary. Descriptor EOF ordering is a hypothesis, not a proven
cause. No helper, provider, expectation, retry policy or allowance was changed.
The evidence verifier requires a successful complete rerun as well as the
retained initial failure and isolated rerun.

## Validation result — 2026-11-20

Native macOS 14.8.7 arm64 (UID 501) and Linux arm64/Docker with glibc 2.36
(UID/GID 10001) pass the complete 48-target required Make command. Both pass
232 filesystem harness tests, 13 ownership tests and 1,162 host integration
assertions with zero gaps. All 24 ticket tests and offline/live identity checks
pass with 129 reservations.

| Evidence | Native macOS | Linux/Docker |
| --- | ---: | ---: |
| Selected full filesystem profile | 14,971 pass / 0 fail | 15,043 pass / 0 fail |
| New permission-field assertions | 512 pass / 0 fail | 512 pass / 0 fail |
| Filesystem harness tests | 232 pass | 232 pass |
| Stock full-audit failures | 1,069 unchanged | 578 unchanged |
| Stock provider-audit failures | 16 unchanged | 8 unchanged |
| Final complete required Make command | exit 0 | exit 0 |

The first Linux command had one existing language-helper failure, documented
above and assigned to CSH-129. Its unchanged isolated and complete reruns
passed; the final language suite has 1,089 passes. The initial failure is
retained and checked by the verifier, not treated as an allowance.

The evidence verifier passes on both platforms. It checks exact new outputs,
every predecessor expectation, exact stock failure identities, source/provider
provenance, unchanged ctime and cleanup. No provider changes or allowances
were introduced. The task-owned containers were removed. No sanitizer,
separately hosted native-Linux or hosted CI result is claimed.

CSH-127 is ready for review, stacked on unmerged CSH-126. CSH-128 owns all
remaining filesystem contracts and four retained conditions. Integration and
whole-utility qualification are not claimed.
